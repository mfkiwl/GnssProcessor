#!/usr/bin/env python3
"""Card NRF section 24.3 item 4, the bed for remedy (b): a simulator fixture whose GPS carries constant code biases per
(receiver, satellite) and code observable, as observed GPS does, with Galileo unbiased as the control.

    py -3.14 scripts/nrf_code_bias_bed.py make --base C:/GnssProcessor/runs/simnet60_quiet_col_24h \\
        --out D:/GnssProcessorSupport/runs_nom/simb_cb1 --sigma-m 0.12 --seed 1 --label cb1
    py -3.14 scripts/nrf_code_bias_bed.py make ... --block-every 4 --block-offset-m 0.13 --label cb2
    py -3.14 scripts/nrf_code_bias_bed.py verify --base C:/GnssProcessor/runs/simnet60_quiet_col_24h --out D:/GnssProcessorSupport/runs_nom/simb_cb1
    py -3.14 scripts/nrf_code_bias_bed.py --selftest

`make` copies the base fixture and adds to every GPS code observation of --signals (default C1C,C2W) a constant bias
per (receiver, satellite, signal): a draw from N(0, --sigma-m) seeded by (--seed, receiver, satellite, signal), so a
key's bias does not depend on which others exist, rounded to the millimetre.  --block-every k adds --block-offset-m
to the GPS III satellites' codes (the BLOCK IIIA entries of the ATX valid on the fixture's date, or --block-sats) at
every k-th receiver in sorted order, starting with the first: a receiver-and-block offset, as some observed receivers
show (card NRF section 51).  The same bias on both codes moves the Melbourne-Wubbena wide lane by -bias / 0.862 m
cycle.  Phase, Galileo and every other file are untouched; each receiver's table is written to its
truth_code_bias.csv (satellite, signal, bias_m, draw_m, block_m).  GENERATED.txt records the command, the block
receivers and the edited files' sha256; `verify` proves that only the GPS code fields moved, each by its table entry.
"""
import argparse
import datetime
import glob
import hashlib
import os
import random
import shutil
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))).replace(os.sep, "/")
ATX = next((p for p in (ROOT + "/data/static/atx/igs20.atx", "C:/GnssProcessor/data/static/atx/igs20.atx")
            if os.path.exists(p)), ROOT + "/data/static/atx/igs20.atx")   # a worktree reads the main tree's data


def fixture_dir(path):
    return path.replace("\\", "/") if os.path.isabs(path) else ROOT + "/" + path


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def obs_types(lines, system):
    """The observation codes of one system from a RINEX 3 header."""
    codes, want = [], 0
    for ln in lines:
        if ln[60:].startswith("END OF HEADER"):
            break
        if ln[60:].startswith("SYS / # / OBS TYPES"):
            if ln[0] == system:
                want = int(ln[3:6])
                codes += ln[7:58].split()
            elif ln[0] == " " and want and len(codes) < want:
                codes += ln[7:58].split()
    return codes


def first_obs_date(lines):
    for ln in lines:
        if ln[60:].startswith("TIME OF FIRST OBS"):
            f = ln[:43].split()
            return datetime.date(int(f[0]), int(f[1]), int(f[2]))
    raise SystemExit("no TIME OF FIRST OBS")


def gps_iii(date, atx=ATX):
    """GPS satellites whose ATX entry valid on `date` is a BLOCK III type."""
    out, cur = set(), None
    for ln in open(atx, encoding="latin-1"):
        lab = ln[60:].strip()
        if lab == "TYPE / SERIAL NO":
            cur = {"type": ln[:20].strip(), "prn": ln[20:40].strip(), "from": None, "until": None}
        elif cur is not None and lab == "VALID FROM":
            cur["from"] = datetime.date(*[int(float(x)) for x in ln[:43].split()[:3]])
        elif cur is not None and lab == "VALID UNTIL":
            cur["until"] = datetime.date(*[int(float(x)) for x in ln[:43].split()[:3]])
        elif cur is not None and lab == "END OF ANTENNA":
            p = cur["prn"]
            if (p.startswith("G") and len(p) == 3 and cur["type"].startswith("BLOCK III") and cur["from"]
                    and cur["from"] <= date and (cur["until"] is None or cur["until"] >= date)):
                out.add(p)
            cur = None
    return out


def draw(seed, station, sat, signal, sigma):
    return round(random.Random("%d|%s|%s|%s" % (seed, station, sat, signal)).gauss(0.0, sigma), 3)


def bias_rinex(text, table):
    """The RINEX text with table[(sat, signal)] (m) added to each GPS code field; the count of edits."""
    lines = text.split("\n")
    codes = obs_types(lines, "G")
    cols = {}
    for (sat, sig), b in table.items():
        if sig not in codes:
            raise SystemExit("no %s observations for GPS" % sig)
        cols.setdefault(sat, []).append((codes.index(sig), b))
    in_body, edits = False, 0
    for i, ln in enumerate(lines):
        if not in_body:
            in_body = ln[60:].startswith("END OF HEADER")
            continue
        if ln.startswith(">") or ln[:3] not in cols:
            continue
        body = ln[3:]
        for k, b in cols[ln[:3]]:
            field = body[16 * k:16 * k + 16]
            if len(field) < 14 or not field[:14].strip():
                continue   # no code this epoch
            new = "%14.3f" % (float(field[:14]) + b)
            if len(new) != 14:
                raise SystemExit("code out of the F14.3 range after the bias: %s" % new)
            body = body[:16 * k] + new + body[16 * k + 14:]
            edits += 1
        lines[i] = ln[:3] + body
    return "\n".join(lines), edits


def tables(stations_rinex, a, iii):
    """(station -> {(sat, signal): (bias, draw, block)}, the block receivers)."""
    signals = a.signals.split(",")
    block_rx = sorted(stations_rinex)[::a.block_every] if a.block_every > 0 and a.block_offset_m else []
    out = {}
    for st, rinex in stations_rinex.items():
        text = open(rinex, "rb").read().decode("ascii").replace("\r\n", "\n")
        sats = sorted({ln[:3] for ln in text.split("END OF HEADER", 1)[1].split("\n") if ln[:1] == "G"})
        t = {}
        for sat in sats:
            for sig in signals:
                d = draw(a.seed, st, sat, sig, a.sigma_m)
                blk = a.block_offset_m if (st in block_rx and sat in iii) else 0.0
                t[(sat, sig)] = (round(d + blk, 3), d, blk)
        out[st] = t
    return out, block_rx


def station_rinex(base):
    out = {}
    for d in sorted(os.listdir(base)):
        if os.path.isdir(os.path.join(base, d)):
            r = glob.glob(os.path.join(base, d, "%s_R_*.rnx" % d))
            if len(r) == 1:
                out[d] = r[0]
    return out


def make(a):
    base, out = fixture_dir(a.base), fixture_dir(a.out)
    if os.path.exists(out):
        raise SystemExit("%s exists: a bed is made once (remove it first to remake it)" % out)
    rin = station_rinex(base)
    first = open(next(iter(rin.values())), "rb").read().decode("ascii").split("\n")
    iii = set(a.block_sats.split(",")) if a.block_sats else gps_iii(first_obs_date(first))
    tab, block_rx = tables(rin, a, iii)
    os.makedirs(out)
    for d in sorted(os.listdir(base)):
        src = os.path.join(base, d)
        if os.path.isdir(src):
            if d == "logs":
                continue
            shutil.copytree(src, os.path.join(out, d))
        else:
            shutil.copy2(src, os.path.join(out, d))
    lines = []
    total = 0
    for st, rinex in rin.items():
        dst = os.path.join(out, st, os.path.basename(rinex))
        raw = open(rinex, "rb").read().decode("ascii")
        crlf = "\r\n" in raw
        new, edits = bias_rinex(raw.replace("\r\n", "\n"), {k: v[0] for k, v in tab[st].items()})
        total += edits
        open(dst, "wb").write((new.replace("\n", "\r\n") if crlf else new).encode("ascii"))
        tpath = os.path.join(out, st, "truth_code_bias.csv")
        with open(tpath, "w", newline="\n") as fh:
            fh.write("satellite,signal,bias_m,draw_m,block_m\n")
            for (sat, sig), (b, d, blk) in sorted(tab[st].items()):
                fh.write("%s,%s,%.3f,%.3f,%.3f\n" % (sat, sig, b, d, blk))
        lines.append("sha256 %s %s/%s" % (sha256(dst), st, os.path.basename(dst)))
        lines.append("sha256 %s %s/truth_code_bias.csv" % (sha256(tpath), st))
    cmd = ("py -3.14 scripts/nrf_code_bias_bed.py make --base %s --out %s --sigma-m %g --seed %d --signals %s "
           "--block-every %d --block-offset-m %g%s --label %s" % (
               a.base, a.out, a.sigma_m, a.seed, a.signals, a.block_every, a.block_offset_m,
               (" --block-sats " + a.block_sats) if a.block_sats else "", a.label))
    with open(os.path.join(out, "GENERATED.txt"), "w", newline="\n") as fh:
        fh.write("Code-bias bed %s of card NRF (section 24.3 item 4, the bed for remedy (b)): %s with constant GPS code "
                 "biases per (receiver, satellite, signal); Galileo and every phase unbiased.\n\n" % (a.label, a.base))
        fh.write("Draw: N(0, %g m) per (receiver, satellite, signal), seed %d, signals %s.\n" % (a.sigma_m, a.seed, a.signals))
        fh.write("Block offset: %g m on the GPS III satellites (%s) at %d receiver(s): %s.\n" % (
            a.block_offset_m, ",".join(sorted(iii)), len(block_rx), ",".join(block_rx) or "none"))
        fh.write("Made by: %s\n" % cmd)
        fh.write("Code fields edited: %d over %d receivers (scripts/nrf_code_bias_bed.py verify).\n" % (total, len(rin)))
        fh.write("\n".join(lines) + "\n")
    print("bed %s: %d GPS code fields biased at %d receivers (block offset at %d); %s" % (
        a.label, total, len(rin), len(block_rx), out))


def verify(a):
    base, out = fixture_dir(a.base), fixture_dir(a.out)
    rin = station_rinex(base)
    bad = []
    for d in sorted(os.listdir(base)):
        p = os.path.join(base, d)
        if d == "logs":
            continue
        files = [os.path.join(d, f) for f in os.listdir(p)] if os.path.isdir(p) else [d]
        for rel in files:
            if os.path.isdir(os.path.join(base, rel)):
                continue
            b, o = os.path.join(base, rel), os.path.join(out, rel)
            if not os.path.exists(o):
                bad.append("missing " + rel)
                continue
            if rel.endswith(".rnx"):
                continue
            if open(b, "rb").read() != open(o, "rb").read():
                bad.append("differs " + rel)
    for st, rinex in rin.items():
        tab = {}
        for ln in open(os.path.join(out, st, "truth_code_bias.csv")).read().splitlines()[1:]:
            sat, sig, bias = ln.split(",")[:3]
            tab[(sat, sig)] = float(bias)
        want, _ = bias_rinex(open(rinex, "rb").read().decode("ascii").replace("\r\n", "\n"), tab)
        got = open(os.path.join(out, st, os.path.basename(rinex)), "rb").read().decode("ascii").replace("\r\n", "\n")
        if got != want:
            bad.append("%s: the RINEX differs from the base by more than its table" % st)
    print("verify %s: %s" % (out, "PASS" if not bad else "FAIL " + "; ".join(bad[:10])))
    return 0 if not bad else 1


def selftest():
    hdr = ("     3.04           OBSERVATION DATA    M                   RINEX VERSION / TYPE\n"
           "G    4 C1C L1C C2W L2W                                      SYS / # / OBS TYPES\n"
           "E    2 C1C L1C                                              SYS / # / OBS TYPES\n"
           "                                                            END OF HEADER\n")
    body = ("> 2024 05 08 00 00 30.0000000  0  2\n"
            + "G04" + "".join("%14.3f 8" % v for v in (20000000.0, 105000000.123, 20000001.5, 81000000.456)) + "\n"
            + "E07" + "".join("%14.3f 8" % v for v in (23000000.0, 121000000.0)) + "\n")
    text = hdr + body
    new, n = bias_rinex(text, {("G04", "C1C"): 0.125, ("G04", "C2W"): -0.04})
    ok = n == 2 and "  20000000.125" in new and "  20000001.460" in new and "105000000.123" in new
    ok = ok and "E07  23000000.000" in new
    r1, r2 = draw(1, "S01000SIM", "G04", "C1C", 0.12), draw(1, "S01000SIM", "G04", "C1C", 0.12)
    ok = ok and r1 == r2 and draw(2, "S01000SIM", "G04", "C1C", 0.12) != r1
    print("selftest: %s" % ("PASS" if ok else "FAIL"))
    return 0 if ok else 1


def main():
    if "--selftest" in sys.argv:
        return selftest()
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    m = sub.add_parser("make")
    m.add_argument("--base", required=True)
    m.add_argument("--out", required=True)
    m.add_argument("--sigma-m", type=float, default=0.12)
    m.add_argument("--seed", type=int, default=1)
    m.add_argument("--signals", default="C1C,C2W")
    m.add_argument("--block-every", type=int, default=0)
    m.add_argument("--block-offset-m", type=float, default=0.0)
    m.add_argument("--block-sats", default="")
    m.add_argument("--label", required=True)
    v = sub.add_parser("verify")
    v.add_argument("--base", required=True)
    v.add_argument("--out", required=True)
    a = ap.parse_args()
    return make(a) if a.cmd == "make" else verify(a)


if __name__ == "__main__":
    sys.exit(main())

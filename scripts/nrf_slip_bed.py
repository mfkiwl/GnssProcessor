#!/usr/bin/env python3
"""Card NRF stage N2b-3: a slip bed made from a simulator fixture by one scripted, unflagged slip.

    py -3.14 scripts/nrf_slip_bed.py make --base runs/simarl_r3c --out D:/GnssProcessorSupport/runs_nom/simnrf_s1 \\
        --station S05000SIM --sat G26 --tow 265830 --l1 25 --l2 0 --label s1
    py -3.14 scripts/nrf_slip_bed.py verify --base runs/simarl_r3c --out D:/GnssProcessorSupport/runs_nom/simnrf_s1
    py -3.14 scripts/nrf_slip_bed.py --selftest

`make` copies the base fixture's station directories and its network_fixture.json, adds the slip to the phase of
one satellite at one station from the slip's epoch on (L1C by --l1 cycles, L2W by --l2 cycles, the loss-of-lock
flag left as it was, so the slip is unflagged), and appends one row per band to that station's truth_slips.csv
(week, tow_s, satellite, signal, delta_cycles, flagged 0, the elevation from truth_atmo.csv, source scripted): the
same record a scripted slip of the simulator writes.  A scripted slip draws no random number, so the bed differs from
the base only in that station's RINEX and truth_slips.csv; `verify` proves it (every other file byte-identical, and
in the RINEX only the slipped satellite's two phase fields from the slip's epoch on, each by its delta).
GENERATED.txt in the bed records the command and the edited files' sha256.
"""
import argparse
import csv
import datetime
import glob
import hashlib
import io
import os
import shutil
import sys

GPS_EPOCH = datetime.datetime(1980, 1, 6)
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))).replace(os.sep, "/")
BANDS = ("L1C", "L2W")


def fixture_dir(path):
    return path.replace("\\", "/") if os.path.isabs(path) else ROOT + "/" + path


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def epoch_tow(line):
    """The GPS time of week (s) of a RINEX 3 epoch line ('> yyyy mm dd hh mm ss.sssssss ...')."""
    f = line[1:].split()
    sec = float(f[5])
    dt = datetime.datetime(int(f[0]), int(f[1]), int(f[2]), int(f[3]), int(f[4])) + datetime.timedelta(seconds=sec)
    return (dt - GPS_EPOCH).total_seconds() % 604800.0


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


def shift_rinex(text, sat, tow, deltas):
    """The RINEX text with `deltas` (code -> cycles) added to `sat`'s phase from `tow` on; the count of edits."""
    lines = text.split("\n")
    codes = obs_types(lines, sat[0])
    cols = {c: codes.index(c) for c in deltas if deltas[c]}
    for c in deltas:
        if deltas[c] and c not in codes:
            raise SystemExit("no %s observations for system %s" % (c, sat[0]))
    in_body, now, edits = False, None, 0
    for i, ln in enumerate(lines):
        if not in_body:
            in_body = ln[60:].startswith("END OF HEADER")
            continue
        if ln.startswith(">"):
            now = epoch_tow(ln)
            continue
        if now is None or now + 1e-6 < tow or not ln.startswith(sat):
            continue
        body = ln[3:]
        for c, k in cols.items():
            field = body[16 * k:16 * k + 16]
            if len(field) < 14 or not field[:14].strip():
                continue   # no phase this epoch
            value = float(field[:14]) + deltas[c]
            new = "%14.3f" % value
            if len(new) != 14:
                raise SystemExit("phase out of the F14.3 range after the shift: %s" % new)
            body = body[:16 * k] + new + body[16 * k + 14:]
            edits += 1
        lines[i] = ln[:3] + body
    return "\n".join(lines), edits


def elevation(station_dir, sat, tow):
    with open(os.path.join(station_dir, "truth_atmo.csv"), newline="") as fh:
        for r in csv.DictReader(fh):
            if r["satellite"] == sat and abs(float(r["tow_s"]) - tow) < 1e-3:
                return float(r["elev_deg"])
    raise SystemExit("%s is not in view at TOW %.0f (truth_atmo.csv)" % (sat, tow))


def make(a):
    base, out = fixture_dir(a.base), fixture_dir(a.out)
    if os.path.exists(out):
        raise SystemExit("%s exists: a bed is made once (remove it first to remake it)" % out)
    stations = sorted(d for d in os.listdir(base) if os.path.isdir(os.path.join(base, d)))
    if a.station not in stations:
        raise SystemExit("no station %s in %s" % (a.station, base))
    os.makedirs(out)
    for d in stations:
        shutil.copytree(os.path.join(base, d), os.path.join(out, d))
    for f in os.listdir(base):
        if os.path.isfile(os.path.join(base, f)):
            shutil.copy2(os.path.join(base, f), os.path.join(out, f))
    sdir = os.path.join(out, a.station)
    rinex = glob.glob(os.path.join(sdir, "%s_R_*.rnx" % a.station))
    if len(rinex) != 1:
        raise SystemExit("%d RINEX files for %s" % (len(rinex), a.station))
    raw = open(rinex[0], "rb").read().decode("ascii")
    crlf = "\r\n" in raw
    text = raw.replace("\r\n", "\n")
    deltas = {"L1C": a.l1, "L2W": a.l2}
    shifted, edits = shift_rinex(text, a.sat, a.tow, deltas)
    if edits == 0:
        raise SystemExit("no phase of %s at %s from TOW %.0f" % (a.sat, a.station, a.tow))
    if crlf:
        shifted = shifted.replace("\n", "\r\n")
    open(rinex[0], "wb").write(shifted.encode("ascii"))
    elev = elevation(sdir, a.sat, a.tow)
    slips = os.path.join(sdir, "truth_slips.csv")
    week = None
    with open(os.path.join(sdir, "truth_tropo.csv"), newline="") as fh:
        week = next(csv.DictReader(fh))["week"]
    raw_s = open(slips, "rb").read().decode("ascii")
    nl = "\r\n" if "\r\n" in raw_s else "\n"
    source = ",scripted" if raw_s.split(nl)[0].rstrip().endswith(",source") else ""   # the header's own columns
    add = "".join("%s,%.3f,%s,%s,%d,0,%.2f%s%s" % (week, a.tow, a.sat, c, deltas[c], elev, source, nl)
                  for c in BANDS if deltas[c])
    if not raw_s.endswith(nl):
        raw_s += nl
    open(slips, "wb").write((raw_s + add).encode("ascii"))
    with open(os.path.join(out, "GENERATED.txt"), "w", newline="\n") as fh:
        fh.write("Slip bed %s of card NRF stage N2b-3: %s plus one scripted, unflagged slip.\n\n" % (a.label, a.base))
        fh.write("Slip: %s %s at TOW %.0f (elevation %.2f deg): L1C %+d cycles, L2W %+d cycles, LLI as it was.\n"
                 % (a.station, a.sat, a.tow, elev, a.l1, a.l2))
        fh.write("Made by: py -3.14 scripts/nrf_slip_bed.py make --base %s --out %s --station %s --sat %s --tow %.0f "
                 "--l1 %d --l2 %d --label %s\n" % (a.base, a.out, a.station, a.sat, a.tow, a.l1, a.l2, a.label))
        fh.write("Phase fields edited: %d.  Only %s's RINEX and truth_slips.csv differ from the base "
                 "(scripts/nrf_slip_bed.py verify).\n" % (edits, a.station))
        fh.write("sha256 %s %s\n" % (sha256(rinex[0]), os.path.basename(rinex[0])))
        fh.write("sha256 %s %s/truth_slips.csv\n" % (sha256(slips), a.station))
    print("bed %s: %d phase fields shifted at %s %s from TOW %.0f; %s" % (a.label, edits, a.station, a.sat, a.tow, out))


def verify(a):
    base, out = fixture_dir(a.base), fixture_dir(a.out)
    gen = open(os.path.join(out, "GENERATED.txt")).read()
    line = [ln for ln in gen.splitlines() if ln.startswith("Slip: ")][0].split()
    station, sat, tow = line[1], line[2], float(line[5])
    l1 = int(gen.split("L1C ")[1].split(" cycles")[0])
    l2 = int(gen.split("L2W ")[1].split(" cycles")[0])
    bad = []
    for d in sorted(os.listdir(base)):
        p = os.path.join(base, d)
        files = [os.path.join(d, f) for f in os.listdir(p)] if os.path.isdir(p) else [d]
        for rel in files:
            if os.path.isdir(os.path.join(base, rel)):
                continue
            b, o = os.path.join(base, rel), os.path.join(out, rel)
            if not os.path.exists(o):
                bad.append("missing " + rel)
                continue
            same = open(b, "rb").read() == open(o, "rb").read()
            special = rel.replace(os.sep, "/").startswith(station + "/") and (
                rel.endswith(".rnx") or rel.endswith("truth_slips.csv"))
            if special and same:
                bad.append("unchanged " + rel)
            if not special and not same:
                bad.append("differs " + rel)
    rinex = glob.glob(os.path.join(base, station, "%s_R_*.rnx" % station))[0]
    text = open(rinex, "rb").read().decode("ascii").replace("\r\n", "\n")
    want, _ = shift_rinex(text, sat, tow, {"L1C": l1, "L2W": l2})
    got = open(os.path.join(out, station, os.path.basename(rinex)), "rb").read().decode("ascii").replace("\r\n", "\n")
    if got != want:
        bad.append("the RINEX differs from the base by more than the slip")
    print("verify %s: %s" % (out, "PASS" if not bad else "FAIL " + "; ".join(bad[:10])))
    return 0 if not bad else 1


def selftest():
    hdr = ("     3.04           OBSERVATION DATA    M                   RINEX VERSION / TYPE\n"
           "G    4 C1C L1C C2W L2W                                      SYS / # / OBS TYPES\n"
           "                                                            END OF HEADER\n")
    body = ("> 2024 05 08 01 50 00.0000000  0  2\n"
            "G26  20849172.034 8 109563132.090 8  20849173.077 8  85373846.600 8\n"
            "G01  20849172.034 8 109563132.090 8  20849173.077 8  85373846.600 8\n"
            "> 2024 05 08 01 50 30.0000000  0  2\n"
            "G26  20849172.034 8 109563132.090 8  20849173.077 8  85373846.600 8\n"
            "G01  20849172.034 8 109563132.090 8  20849173.077 8  85373846.600 8\n")
    out, n = shift_rinex(hdr + body, "G26", 265830.0, {"L1C": 25, "L2W": 1})
    ok = n == 2
    lines = out.split("\n")
    ok &= lines[4] == "G26  20849172.034 8 109563132.090 8  20849173.077 8  85373846.600 8"   # before the slip
    ok &= lines[7] == "G26  20849172.034 8 109563157.090 8  20849173.077 8  85373847.600 8"   # from the slip on
    ok &= lines[8] == "G01  20849172.034 8 109563132.090 8  20849173.077 8  85373846.600 8"   # another satellite
    ok &= abs(epoch_tow("> 2024 05 08 01 50 30.0000000  0 14") - 265830.0) < 1e-6
    print("selftest:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


def main():
    if "--selftest" in sys.argv:
        return selftest()
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = p.add_subparsers(dest="cmd", required=True)
    m = sub.add_parser("make")
    m.add_argument("--base", required=True)
    m.add_argument("--out", required=True)
    m.add_argument("--station", required=True)
    m.add_argument("--sat", required=True)
    m.add_argument("--tow", type=float, required=True)
    m.add_argument("--l1", type=int, default=0)
    m.add_argument("--l2", type=int, default=0)
    m.add_argument("--label", required=True)
    v = sub.add_parser("verify")
    v.add_argument("--base", required=True)
    v.add_argument("--out", required=True)
    a = p.parse_args()
    if a.cmd == "make":
        make(a)
        return 0
    return verify(a)


if __name__ == "__main__":
    sys.exit(main())

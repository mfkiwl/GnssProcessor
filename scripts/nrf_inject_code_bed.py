#!/usr/bin/env python3
"""Card NRF section 102, tests S2: a simulator fixture with constant code biases injected on chosen links, so that a
satellite whose level is re-expressed through a biased link takes the bias into its level (the defect of an untied
satellite, section 100.1).

    py -3.14 scripts/nrf_inject_code_bed.py make --base D:/GnssProcessorSupport/runs_nom/simb_mode1 \\
        --out D:/GnssProcessorSupport/runs_nom/simb_mode1i --station S24000SIM --sats E34,E02,E36 \\
        --signals C1C,C5Q --bias-m 0.25 --label mode1i
    py -3.14 scripts/nrf_inject_code_bed.py make --base D:/GnssProcessorSupport/runs_nom/simb_mode1 \\
        --out D:/GnssProcessorSupport/runs_nom/simb_mode1d --system E --signals C1C,C5Q,C1X,C5X \\
        --draw-sigma-m 0.15 --seed 1 --label mode1d
    py -3.14 scripts/nrf_inject_code_bed.py verify --base D:/GnssProcessorSupport/runs_nom/simb_mode1 \\
        --out D:/GnssProcessorSupport/runs_nom/simb_mode1d
    py -3.14 scripts/nrf_inject_code_bed.py --selftest

Two ways of choosing the links (the satellite system is --system, or the satellites' letter):
- one receiver: --station with --sats, each of --signals of those satellites moved by --bias-m;
- every link: --draw-sigma-m s, each of --signals present at each receiver, of each satellite of the system that the
  receiver observes, moved by its own draw from N(0, s), seeded by (--seed, receiver, satellite, signal) so that a
  link's bias does not depend on which others exist, rounded to the millimetre: an observed receiver's long-lived
  code multipath, constant through the day.
The same bias on C1C and C5Q of Galileo moves the link's Melbourne-Wubbena wide lane by -bias / 0.751 m cycle.
Phases and every other file are untouched; each edited receiver's truth_injected_code.csv lists its satellites,
signals and biases; GENERATED.txt keeps the base's record and adds the command and the edited files' sha256.
`verify` reads every edited receiver's RINEX field by field against the base and proves that only the fields of its
table moved, each by its entry, that the other receivers' files are the base's, and every other file too.
"""
import argparse
import os
import random
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import nrf_mode_bed as mb  # noqa: E402  (obs_types, read_text, write_text, sha256, stations, fixture_dir)

TRUTH = "truth_injected_code.csv"


def inject_table(text, system, table):
    """The RINEX text (LF line ends) with table[(sat, signal)] (m) added to those fields; the count of edits."""
    lines = text.split("\n")
    codes = mb.obs_types(lines, system)
    cols = {}
    for (sat, sig), b in table.items():
        if sig not in codes:
            raise SystemExit("the file has no %s observations of %s" % (system, sig))
        cols.setdefault(sat, []).append((codes.index(sig), b))
    in_body, edits = False, 0
    for i, ln in enumerate(lines):
        if not in_body:
            in_body = ln[60:].startswith("END OF HEADER")
            continue
        if ln[:3] not in cols:
            continue
        body = ln[3:]
        for k, b in cols[ln[:3]]:
            field = body[16 * k:16 * k + 16]
            if len(field) < 14 or not field[:14].strip():
                continue
            new = "%14.3f" % (float(field[:14]) + b)
            if len(new) != 14:
                raise SystemExit("field out of the F14.3 range after the bias: %s" % new)
            body = body[:16 * k] + new + body[16 * k + 14:]
            edits += 1
        lines[i] = ln[:3] + body
    return "\n".join(lines), edits


def draw(seed, station, sat, signal, sigma):
    return round(random.Random("%d|%s|%s|%s" % (seed, station, sat, signal)).gauss(0.0, sigma), 3)


def satellites(text, system):
    return sorted({ln[:3] for ln in text.split("END OF HEADER", 1)[1].split("\n") if ln[:1] == system})


def tables(base, a):
    """station -> {(sat, signal): bias} for the receivers the bed edits."""
    st = mb.stations(base)
    signals = a.signals.split(",")
    out = {}
    if a.draw_sigma_m > 0.0:
        for s, rinex in st.items():
            text, _ = mb.read_text(rinex)
            codes = mb.obs_types(text.split("\n"), a.system)
            t = {(sat, g): draw(a.seed, s, sat, g, a.draw_sigma_m)
                 for sat in satellites(text, a.system) for g in signals if g in codes}
            if t:
                out[s] = t
        return out
    if a.station not in st:
        raise SystemExit("no receiver %s in %s" % (a.station, base))
    out[a.station] = {(sat, g): a.bias_m for sat in a.sats.split(",") for g in signals}
    return out


def make(a):
    base, out = mb.fixture_dir(a.base), mb.fixture_dir(a.out)
    if os.path.exists(out):
        raise SystemExit("%s exists: a bed is made once (remove it first to remake it)" % out)
    if not a.system:
        a.system = a.sats.split(",")[0][0] if a.sats else "E"
    tab = tables(base, a)
    st = mb.stations(base)
    os.makedirs(out)
    for d in sorted(os.listdir(base)):
        src = os.path.join(base, d)
        if os.path.isdir(src):
            if d == "logs":
                continue
            shutil.copytree(src, os.path.join(out, d))
        else:
            shutil.copy2(src, os.path.join(out, d))
    lines, total = [], 0
    for s, t in sorted(tab.items()):
        text, crlf = mb.read_text(st[s])
        new, edits = inject_table(text, a.system, t)
        total += edits
        dst = os.path.join(out, s, os.path.basename(st[s]))
        mb.write_text(dst, new, crlf)
        tpath = os.path.join(out, s, TRUTH)
        with open(tpath, "w", newline="\n") as fh:
            fh.write("satellite,signal,bias_m\n")
            for (sat, g), b in sorted(t.items()):
                fh.write("%s,%s,%.3f\n" % (sat, g, b))
        lines.append("sha256 %s %s/%s" % (mb.sha256(dst), s, os.path.basename(dst)))
        lines.append("sha256 %s %s/%s" % (mb.sha256(tpath), s, TRUTH))
    how = ("each link's own draw from N(0, %g m), seed %d, signals %s of system %s at every receiver"
           % (a.draw_sigma_m, a.seed, a.signals, a.system) if a.draw_sigma_m > 0.0
           else "%g m on %s of %s at %s" % (a.bias_m, a.signals, a.sats, a.station))
    cmd = "py -3.14 scripts/nrf_inject_code_bed.py " + " ".join(sys.argv[1:])
    with open(os.path.join(out, "GENERATED.txt"), "a", newline="\n") as fh:   # after the base's own record
        fh.write("\n---\nInjected code bed %s of card NRF (section 102): %s with %s.\n\n" % (a.label, a.base, how))
        fh.write("Made by: %s\n" % cmd)
        fh.write("Fields edited: %d at %d receiver(s) (scripts/nrf_inject_code_bed.py verify).\n" % (total, len(tab)))
        fh.write("\n".join(lines) + "\n")
    print("bed %s: %d fields edited at %d receiver(s), %s; %s" % (a.label, total, len(tab), how, out))


def verify(a):
    base, out = mb.fixture_dir(a.base), mb.fixture_dir(a.out)
    st = mb.stations(base)
    edited = {s for s in st if os.path.exists(os.path.join(out, s, TRUTH))}
    bad, moved = [], 0
    for d in sorted(os.listdir(base)):
        p = os.path.join(base, d)
        if d == "logs":
            continue
        rels = [os.path.join(d, f) for f in os.listdir(p)] if os.path.isdir(p) else [d]
        for rel in rels:
            if os.path.isdir(os.path.join(base, rel)):
                continue
            o = os.path.join(out, rel)
            if not os.path.exists(o):
                bad.append("missing " + rel)
            elif d in edited and rel.endswith(".rnx"):
                continue
            elif rel == "GENERATED.txt":
                if not open(o).read().startswith(open(os.path.join(base, rel)).read()):
                    bad.append("GENERATED.txt does not keep the base's record")
            elif open(os.path.join(base, rel), "rb").read() != open(o, "rb").read():
                bad.append("differs " + rel)
    for s in sorted(edited):
        tab = {}
        for row in open(os.path.join(out, s, TRUTH)).read().splitlines()[1:]:
            sat, g, b = row.split(",")
            tab[(sat, g)] = float(b)
        bt, _ = mb.read_text(st[s])
        ot, _ = mb.read_text(os.path.join(out, s, os.path.basename(st[s])))
        bl, ol = bt.split("\n"), ot.split("\n")
        end = next(i for i, ln in enumerate(bl) if ln[60:].startswith("END OF HEADER"))
        codes = mb.obs_types(bl, next(iter(tab))[0][0])
        if bl[:end + 1] != ol[:end + 1] or len(bl) != len(ol):
            bad.append("%s: the header or the line count differs" % s)
            continue
        for x, y in zip(bl[end + 1:], ol[end + 1:]):
            if x == y:
                continue
            if x[:3] != y[:3] or len(x) != len(y):
                bad.append("%s: a line other than a record of the table differs: %r" % (s, x[:20]))
                break
            for k, code in enumerate(codes):
                fx, fy = x[3 + 16 * k:3 + 16 * k + 16], y[3 + 16 * k:3 + 16 * k + 16]
                if fx == fy:
                    continue
                want = tab.get((x[:3], code))
                if want is None or fx[14:] != fy[14:] or abs(float(fy[:14]) - float(fx[:14]) - want) > 0.0015:
                    bad.append("%s %s %s moved off the table" % (s, x[:3], code))
                    break
                moved += 1
    print("verify %s: %s (%d fields moved by their table entries at %d receiver(s))"
          % (out, "PASS" if not bad else "FAIL " + "; ".join(bad[:8]), moved, len(edited)))
    return 0 if not bad else 1


def selftest():
    hdr = ("     3.04           OBSERVATION DATA    M                   RINEX VERSION / TYPE\n"
           "G    2 C1C L1C                                              SYS / # / OBS TYPES\n"
           "E    4 C1C L1C C5Q L5Q                                      SYS / # / OBS TYPES\n"
           "                                                            END OF HEADER\n")
    body = ("> 2024 05 08 00 00 30.0000000  0  3\n"
            + "G04" + "".join("%14.3f 8" % v for v in (20000000.0, 105000000.123)) + "\n"
            + "E07" + "".join("%14.3f 8" % v for v in (23000000.0, 121000000.0, 23000002.0, 90000000.5)) + "\n"
            + "E09" + "".join("%14.3f 8" % v for v in (24000000.0, 126000000.0, 24000002.0, 94000000.5)) + "\n")
    new, n = inject_table(hdr + body, "E", {("E07", "C1C"): 0.25, ("E07", "C5Q"): 0.25, ("E09", "C5Q"): -0.125})
    lines = new.split("\n")
    e07 = [float(lines[6][3 + 16 * k:3 + 16 * k + 14]) for k in range(4)]
    e09 = [float(lines[7][3 + 16 * k:3 + 16 * k + 14]) for k in range(4)]
    ok = n == 3 and e07 == [23000000.25, 121000000.0, 23000002.25, 90000000.5]
    ok = ok and e09 == [24000000.0, 126000000.0, 24000001.875, 94000000.5]
    ok = ok and lines[5] == ("G04" + "".join("%14.3f 8" % v for v in (20000000.0, 105000000.123)))
    ok = ok and draw(1, "S01000SIM", "E07", "C1C", 0.15) == draw(1, "S01000SIM", "E07", "C1C", 0.15)
    ok = ok and draw(1, "S01000SIM", "E07", "C1C", 0.15) != draw(2, "S01000SIM", "E07", "C1C", 0.15)
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
    m.add_argument("--station", default="")
    m.add_argument("--sats", default="")
    m.add_argument("--system", default="")
    m.add_argument("--signals", default="C1C,C5Q")
    m.add_argument("--bias-m", type=float, default=0.25)
    m.add_argument("--draw-sigma-m", type=float, default=0.0)
    m.add_argument("--seed", type=int, default=1)
    m.add_argument("--label", required=True)
    v = sub.add_parser("verify")
    v.add_argument("--base", required=True)
    v.add_argument("--out", required=True)
    a = ap.parse_args()
    return make(a) if a.cmd == "make" else verify(a)


if __name__ == "__main__":
    sys.exit(main())

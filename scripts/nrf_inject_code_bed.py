#!/usr/bin/env python3
"""Card NRF section 102, test S2: a simulator fixture with a constant code bias injected on chosen satellites at one
receiver, so that a satellite whose tree edge is that receiver's link takes the bias into its level (the defect of
an untied satellite, section 100.1).

    py -3.14 scripts/nrf_inject_code_bed.py make --base D:/GnssProcessorSupport/runs_nom/simb_mode1 \\
        --out D:/GnssProcessorSupport/runs_nom/simb_mode1i --station S24000SIM --sats E34,E02,E36 \\
        --signals C1C,C5Q --bias-m 0.25 --label mode1i
    py -3.14 scripts/nrf_inject_code_bed.py verify --base D:/GnssProcessorSupport/runs_nom/simb_mode1 \\
        --out D:/GnssProcessorSupport/runs_nom/simb_mode1i
    py -3.14 scripts/nrf_inject_code_bed.py --selftest

`make` copies the base fixture and adds --bias-m to every observation of --signals of the --sats at the --station
(the satellite system is the satellites' letter).  The same bias on C1C and C5Q of Galileo moves the link's
Melbourne-Wubbena wide lane by -bias / 0.751 m cycle (-0.333 for 0.25 m) and its ionosphere-free code by the bias,
and leaves the geometry-free code alone.  Phases and every other file are untouched; the station's
truth_injected_code.csv lists the satellites, signals and bias; GENERATED.txt records the command and the edited
file's sha256.  `verify` reads the station's RINEX field by field against the base and proves that only those
fields moved, each by the bias, and that every other file is the base's.
"""
import argparse
import os
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import nrf_mode_bed as mb  # noqa: E402  (obs_types, read_text, write_text, sha256, stations, fixture_dir)


def inject(text, system, sats, signals, bias):
    """The RINEX text (LF line ends) with bias added to the signals of the satellites; the count of edited fields."""
    lines = text.split("\n")
    codes = mb.obs_types(lines, system)
    cols = [codes.index(s) for s in signals if s in codes]
    if len(cols) != len(signals):
        raise SystemExit("the file has no %s observations of %s" % (system, ",".join(s for s in signals if s not in codes)))
    in_body, edits = False, 0
    for i, ln in enumerate(lines):
        if not in_body:
            in_body = ln[60:].startswith("END OF HEADER")
            continue
        if ln[:3] not in sats:
            continue
        body = ln[3:]
        for k in cols:
            field = body[16 * k:16 * k + 16]
            if len(field) < 14 or not field[:14].strip():
                continue
            new = "%14.3f" % (float(field[:14]) + bias)
            if len(new) != 14:
                raise SystemExit("field out of the F14.3 range after the bias: %s" % new)
            body = body[:16 * k] + new + body[16 * k + 14:]
            edits += 1
        lines[i] = ln[:3] + body
    return "\n".join(lines), edits


def make(a):
    base, out = mb.fixture_dir(a.base), mb.fixture_dir(a.out)
    if os.path.exists(out):
        raise SystemExit("%s exists: a bed is made once (remove it first to remake it)" % out)
    st = mb.stations(base)
    if a.station not in st:
        raise SystemExit("no receiver %s in %s" % (a.station, base))
    sats, signals = a.sats.split(","), a.signals.split(",")
    system = sats[0][0]
    if any(s[0] != system for s in sats):
        raise SystemExit("the satellites must be of one system")
    os.makedirs(out)
    for d in sorted(os.listdir(base)):
        src = os.path.join(base, d)
        if os.path.isdir(src):
            if d == "logs":
                continue
            shutil.copytree(src, os.path.join(out, d))
        else:
            shutil.copy2(src, os.path.join(out, d))
    rinex = st[a.station]
    text, crlf = mb.read_text(rinex)
    new, edits = inject(text, system, set(sats), signals, a.bias_m)
    dst = os.path.join(out, a.station, os.path.basename(rinex))
    mb.write_text(dst, new, crlf)
    tpath = os.path.join(out, a.station, "truth_injected_code.csv")
    with open(tpath, "w", newline="\n") as fh:
        fh.write("satellite,signal,bias_m\n")
        for s in sats:
            for g in signals:
                fh.write("%s,%s,%.3f\n" % (s, g, a.bias_m))
    cmd = ("py -3.14 scripts/nrf_inject_code_bed.py make --base %s --out %s --station %s --sats %s --signals %s "
           "--bias-m %g --label %s" % (a.base, a.out, a.station, a.sats, a.signals, a.bias_m, a.label))
    with open(os.path.join(out, "GENERATED.txt"), "a", newline="\n") as fh:   # after the base's own record
        fh.write("\n---\nInjected code bed %s of card NRF (section 102, test S2): %s with %g m added to %s of %s at "
                 "%s.\n\n" % (a.label, a.base, a.bias_m, a.signals, a.sats, a.station))
        fh.write("Made by: %s\n" % cmd)
        fh.write("Fields edited: %d (scripts/nrf_inject_code_bed.py verify).\n" % edits)
        fh.write("sha256 %s %s/%s\n" % (mb.sha256(dst), a.station, os.path.basename(dst)))
        fh.write("sha256 %s %s/truth_injected_code.csv\n" % (mb.sha256(tpath), a.station))
    print("bed %s: %d fields of %s of %s at %s moved by %g m; %s" % (a.label, edits, a.signals, a.sats, a.station,
                                                                  a.bias_m, out))


def verify(a):
    base, out = mb.fixture_dir(a.base), mb.fixture_dir(a.out)
    gen = open(os.path.join(out, "GENERATED.txt")).read()
    station = gen.rsplit("Injected code bed ", 1)[1].split(" at ", 1)[1].split(".\n", 1)[0].strip()
    tab = {}
    for row in open(os.path.join(out, station, "truth_injected_code.csv")).read().splitlines()[1:]:
        s, g, b = row.split(",")
        tab[(s, g)] = float(b)
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
            elif d == station and rel.endswith(".rnx"):
                continue
            elif rel == "GENERATED.txt":
                if not open(o).read().startswith(open(os.path.join(base, rel)).read()):
                    bad.append("GENERATED.txt does not keep the base's record")
            elif open(os.path.join(base, rel), "rb").read() != open(o, "rb").read():
                bad.append("differs " + rel)
    rinex = mb.stations(base)[station]
    bt, _ = mb.read_text(rinex)
    ot, _ = mb.read_text(os.path.join(out, station, os.path.basename(rinex)))
    bl, ol = bt.split("\n"), ot.split("\n")
    end = next(i for i, ln in enumerate(bl) if ln[60:].startswith("END OF HEADER"))
    codes = mb.obs_types(bl, next(iter(tab))[0][0])
    if bl[:end + 1] != ol[:end + 1] or len(bl) != len(ol):
        bad.append("the header or the line count differs")
    for x, y in zip(bl[end + 1:], ol[end + 1:]):
        if x == y:
            continue
        if x[:3] != y[:3] or len(x) != len(y):
            bad.append("a line other than a record of the table differs: %r" % x[:20])
            break
        for k, code in enumerate(codes):
            fx, fy = x[3 + 16 * k:3 + 16 * k + 16], y[3 + 16 * k:3 + 16 * k + 16]
            if fx == fy:
                continue
            want = tab.get((x[:3], code))
            if want is None or fx[14:] != fy[14:] or abs(float(fy[:14]) - float(fx[:14]) - want) > 0.0015:
                bad.append("%s %s moved off the table" % (x[:3], code))
                break
            moved += 1
    print("verify %s: %s (%d fields moved by the bias)" % (out, "PASS" if not bad else "FAIL " + "; ".join(bad[:8]),
                                                           moved))
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
    new, n = inject(hdr + body, "E", {"E07"}, ["C1C", "C5Q"], 0.25)
    lines = new.split("\n")
    e07 = [float(lines[6][3 + 16 * k:3 + 16 * k + 14]) for k in range(4)]
    ok = n == 2 and e07 == [23000000.25, 121000000.0, 23000002.25, 90000000.5]
    ok = ok and lines[5].startswith("G04") and lines[5] == ("G04" + "".join("%14.3f 8" % v for v in (20000000.0,
                                                                                                    105000000.123)))
    ok = ok and lines[7] == ("E09" + "".join("%14.3f 8" % v for v in (24000000.0, 126000000.0, 24000002.0, 94000000.5)))
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
    m.add_argument("--station", required=True)
    m.add_argument("--sats", required=True)
    m.add_argument("--signals", default="C1C,C5Q")
    m.add_argument("--bias-m", type=float, default=0.25)
    m.add_argument("--label", required=True)
    v = sub.add_parser("verify")
    v.add_argument("--base", required=True)
    v.add_argument("--out", required=True)
    a = ap.parse_args()
    return make(a) if a.cmd == "make" else verify(a)


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""Card NRF section 106, the single Galileo network's first step: the truth files of a simulator bed with the combined
Galileo mode renamed to the pilot mode, for the runs whose observation files are relabelled the same way
(`rapid_arm.py make --rinex "relabel;sys=E;stations=family:X;from=?1X;to=?1C" --rinex "relabel;sys=E;stations=
family:X;from=?5X;to=?5Q"`), so that the ring fix's truth audit (network.ring_fix.truth_root) finds every link.

    py -3.14 scripts/nrf_truth_alias.py make --bed D:/GnssProcessorSupport/runs_nom/simb_mode1 \\
        --out D:/GnssProcessorSupport/runs_nom/simb_mode1_ta
    py -3.14 scripts/nrf_truth_alias.py verify --bed D:/GnssProcessorSupport/runs_nom/simb_mode1 \\
        --out D:/GnssProcessorSupport/runs_nom/simb_mode1_ta
    py -3.14 scripts/nrf_truth_alias.py --selftest

`make` writes, for every receiver directory of the bed, the three files the audit reads (truth_ambiguities.csv,
truth_slips.csv, truth_windup.csv): the wind-up as it is, and the other two with the Galileo signals L1X and L5X
renamed to L1C and L5Q (the integers, slips and every other column unchanged); a receiver without a combined-mode
signal is copied as it is.  No receiver of the beds tracks both modes on a band, so no two rows collide (checked).
`verify` proves that each written file equals the bed's but for those renames.
"""
import argparse
import os
import sys

FILES = ("truth_ambiguities.csv", "truth_slips.csv", "truth_windup.csv")
RENAME = {"L1X": "L1C", "L5X": "L5Q"}


def alias_text(text, name):
    """The file's text with the Galileo combined-mode signals renamed (the signal column of the two files that have one)."""
    if name == "truth_windup.csv":
        return text
    lines = text.split("\n")
    head = lines[0].split(",")
    if "signal" not in head:
        return text
    i_sat, i_sig = head.index("satellite"), head.index("signal")
    out, seen = [lines[0]], set()
    for ln in lines[1:]:
        if not ln.strip():
            out.append(ln)
            continue
        f = ln.split(",")
        if f[i_sat].startswith("E") and f[i_sig] in RENAME:
            f[i_sig] = RENAME[f[i_sig]]
        if name == "truth_ambiguities.csv":
            key = (f[i_sat], f[i_sig])
            if key in seen:
                raise SystemExit("%s: two rows for %s %s after the rename (a receiver tracking both modes)" % (name, *key))
            seen.add(key)
        out.append(",".join(f))
    return "\n".join(out)


def stations(bed):
    return sorted(d for d in os.listdir(bed) if os.path.isfile(os.path.join(bed, d, "truth_ambiguities.csv")))


def make(a):
    if os.path.exists(a.out):
        raise SystemExit("%s exists" % a.out)
    n_renamed = 0
    for s in stations(a.bed):
        os.makedirs(os.path.join(a.out, s))
        for name in FILES:
            src = os.path.join(a.bed, s, name)
            if not os.path.exists(src):
                continue
            text = open(src, newline="").read()
            new = alias_text(text, name)
            n_renamed += new != text
            with open(os.path.join(a.out, s, name), "w", newline="") as fh:
                fh.write(new)
    with open(os.path.join(a.out, "GENERATED.txt"), "w", newline="\n") as fh:
        fh.write("Truth alias of %s (card NRF section 106): L1X and L5X of Galileo renamed to L1C and L5Q in "
                 "truth_ambiguities.csv and truth_slips.csv; truth_windup.csv as it is.\nMade by: py -3.14 "
                 "scripts/nrf_truth_alias.py %s\nFiles renamed: %d\n" % (a.bed, " ".join(sys.argv[1:]), n_renamed))
    print("truth alias %s: %d receivers, %d files renamed" % (a.out, len(stations(a.bed)), n_renamed))


def verify(a):
    bad = []
    for s in stations(a.bed):
        for name in FILES:
            src, dst = os.path.join(a.bed, s, name), os.path.join(a.out, s, name)
            if not os.path.exists(src):
                continue
            if not os.path.exists(dst):
                bad.append("missing " + dst)
                continue
            want = alias_text(open(src, newline="").read(), name)
            if open(dst, newline="").read() != want:
                bad.append("differs " + dst)
    print("verify %s: %s" % (a.out, "PASS" if not bad else "FAIL " + "; ".join(bad[:6])))
    return 0 if not bad else 1


def selftest():
    amb = "satellite,signal,N_int,wavelength_m\nG03,L1C,-22,0.19\nE04,L1X,7,0.19\nE04,L5X,-3,0.25\nE04,L7Q,5,0.24\n"
    out = alias_text(amb, "truth_ambiguities.csv")
    ok = out == "satellite,signal,N_int,wavelength_m\nG03,L1C,-22,0.19\nE04,L1C,7,0.19\nE04,L5Q,-3,0.25\nE04,L7Q,5,0.24\n"
    ok = ok and alias_text("week,tow_s,satellite,windup_cycles\n2313,1.0,E04,0.2\n", "truth_windup.csv").endswith("0.2\n")
    try:
        alias_text("satellite,signal,N_int,wavelength_m\nE04,L1X,7,0.19\nE04,L1C,7,0.19\n", "truth_ambiguities.csv")
        ok = False
    except SystemExit:
        pass
    print("selftest: %s" % ("PASS" if ok else "FAIL"))
    return 0 if ok else 1


def main():
    if "--selftest" in sys.argv:
        return selftest()
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    for c in ("make", "verify"):
        p = sub.add_parser(c)
        p.add_argument("--bed", required=True)
        p.add_argument("--out", required=True)
    a = ap.parse_args()
    return make(a) if a.cmd == "make" else verify(a)


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""Card IRDU section 15: a copy of a network run's product stream without the code-bias and phase-bias records of
chosen satellites for chosen spans, the clock records kept (the made case of the users' phase-bias rule).

    py -3.14 scripts/irdu_pb_remove.py <source net tag> <destination net tag> --remove SAT:SIGNALS:FROM:TO [...]

SAT is a satellite ("G13"); SIGNALS is "all" (every code-bias and phase-bias record of the satellite) or a list of
phase signals joined by "+" ("L2W"), each taking the code signal of the same band with it (C2W for L2W); FROM and TO
are minutes from the stream's first epoch, the span [FROM, TO).  The destination folder (_rap_<tag> under
RAPID_RUNS_ROOT, default D:/GnssProcessorSupport/runs_nom) receives the edited products.txt and copies of the
source's arm.json and rapid.json, so scripts/irdu_users.py makes user replays on it.  Every other line is kept
byte for byte.  Printed: the records removed per satellite and kind.
"""
import argparse
import collections
import os
import shutil
from pathlib import Path

RUNS = Path(os.environ.get("RAPID_RUNS_ROOT") or "D:/GnssProcessorSupport/runs_nom")


def parse_remove(spec):
    sat, sigs, t_from, t_to = spec.split(":")
    sig_set = None if sigs == "all" else set(sigs.split("+"))
    return sat, sig_set, float(t_from), float(t_to)


def band(sig):
    return sig[1] if len(sig) > 1 else ""


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("src")
    ap.add_argument("dst")
    ap.add_argument("--remove", action="append", required=True)
    a = ap.parse_args()
    rules = [parse_remove(s) for s in a.remove]
    src, dst = RUNS / ("_rap_" + a.src), RUNS / ("_rap_" + a.dst)
    dst.mkdir(parents=True, exist_ok=True)
    for f in ("arm.json", "rapid.json"):
        shutil.copyfile(src / f, dst / f)
    removed = collections.Counter()
    t0 = None
    minute = None
    with open(src / "products.txt", encoding="utf-8", newline="") as fi, \
            open(dst / "products.txt", "w", encoding="utf-8", newline="") as fo:
        for ln in fi:
            f = ln.split(",")
            if f[0] == "E":
                tow = float(f[2])
                t0 = tow if t0 is None else t0
                minute = (tow - t0) / 60.0
            elif f[0] in ("B", "P") and minute is not None:
                sat, sig = f[1], f[2]
                drop = False
                for r_sat, r_sigs, r_from, r_to in rules:
                    if sat != r_sat or not (r_from <= minute < r_to):
                        continue
                    if r_sigs is None or (f[0] == "P" and sig in r_sigs) \
                            or (f[0] == "B" and band(sig) in {band(s) for s in r_sigs}):
                        drop = True
                        break
                if drop:
                    removed[(sat, f[0], sig)] += 1
                    continue
            fo.write(ln)
    print("%s -> %s" % (src.name, dst.name))
    for (sat, kind, sig), n in sorted(removed.items()):
        print("  removed %s %s %s: %d records" % (sat, kind, sig, n))


if __name__ == "__main__":
    main()

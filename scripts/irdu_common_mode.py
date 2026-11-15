#!/usr/bin/env python3
"""Card IRDU section 12.6: the common mode of a stream's errors across satellites, phase against code.

    py -3.14 scripts/irdu_common_mode.py <run> [<run> ...] [--from-min 30] [--to-min 120] [--fixture DIR]

Each satellite's error in the ionosphere-free phase correction (lambda_b E_b combined; x cancels) and in the
ionosphere-free code correction (r), against truth (card IRD section 8's algebra), less the satellite's own mean over
the window (what a float user's ambiguity takes, for the phase); then the mean over the satellites of each epoch: the
common mode cm(t), which a user takes into its clock only if its clock follows it.  Printed per 15 min: cm of the
phase, of the code and their difference (mm), and the largest move of each over the window.
"""
import argparse
import os
import sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import simnet_wire_integer_consistency as WIC  # noqa: E402

F1, F2 = 1575.42e6, 1227.60e6
C = 299792458.0
L1, L2 = C / F1, C / F2
G1 = F1 * F1 / (F1 * F1 - F2 * F2)
G2 = F2 * F2 / (F1 * F1 - F2 * F2)


def series(run, fixture, from_min, to_min):
    osb, sc_truth, epochs, _ = WIC.dual_load(fixture, run)
    t0 = min(ep["tow"] for ep in epochs)
    per = defaultdict(dict)
    for ep in epochs:
        if not (t0 + 60 * from_min <= ep["tow"] < t0 + 60 * to_min):
            continue
        for s, v in WIC.dual_sat_values(ep, osb, sc_truth, ("L1C", "L2W")).items():
            if s.startswith("G"):
                per[s][ep["tow"]] = (G1 * L1 * v["E1"] - G2 * L2 * v["E2"], v["r"])
    cm = defaultdict(lambda: [[], []])
    for s, ser in per.items():
        mp = sum(v[0] for v in ser.values()) / len(ser)
        mc = sum(v[1] for v in ser.values()) / len(ser)
        for t, (p, c) in ser.items():
            cm[t][0].append(p - mp)
            cm[t][1].append(c - mc)
    out = {t: (sum(v[0]) / len(v[0]), sum(v[1]) / len(v[1])) for t, v in sorted(cm.items())}
    return out, t0


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("runs", nargs="+")
    ap.add_argument("--from-min", type=float, default=30.0)
    ap.add_argument("--to-min", type=float, default=120.0)
    ap.add_argument("--fixture", default="C:/GnssProcessor/runs/simarl_r3c")
    a = ap.parse_args()
    for run in a.runs:
        out, t0 = series(run, a.fixture, a.from_min, a.to_min)
        bins = defaultdict(list)
        for t, (p, c) in out.items():
            bins[int((t - t0) // 900)].append((p, c))
        parts = []
        for k, v in sorted(bins.items()):
            p = sum(x[0] for x in v) / len(v)
            c = sum(x[1] for x in v) / len(v)
            parts.append("%d-%d %+.0f/%+.0f/%+.0f" % (15 * k, 15 * k + 15, 1000 * p, 1000 * c, 1000 * (p - c)))
        ps = [v[0] for v in out.values()]
        cs = [v[1] for v in out.values()]
        print("%-28s common mode phase/code/difference by 15 min (mm): %s | range phase %.0f code %.0f mm" % (
            os.path.basename(run.rstrip("/\\")), " ".join(parts), 1000 * (max(ps) - min(ps)),
            1000 * (max(cs) - min(cs))))


if __name__ == "__main__":
    main()

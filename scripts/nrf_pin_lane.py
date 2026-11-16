#!/usr/bin/env python3
"""Card NRF, the pin lane: at every tree pin the eq34 chain sets by rounding a float (an uncertified re-host,
row RehostUncertified), the float pair's spread along the family's near-degenerate lane pair.

    py -3.14 scripts/nrf_pin_lane.py <run> [<run> ...] [--list N]

A lane pair d = (a, b) moves the two bands' ambiguities by a and b cycles and leaves the ionosphere-free phase almost
unchanged (a f1 close to b f2), so rounding each band on its own cannot tell the lanes apart: only the ionosphere-like
part of the float separates them.  For each pin, the chord row of its arc at the last epoch before the pin
(logs/network_chain_frame.csv: the two floats and their conditional covariance Q, cycles) gives the float's standard
deviation along d in units of the lane spacing, s = sqrt(d' Q d) / (d' d); s of 0.25 puts the neighbouring lane two
sigmas away.  Also reported: the float's distance from the rounded lane along d, in lane spacings.

Pairs: GPS L1/L2 (7, 9) (ionosphere-free cost 6.3 mm, two wide-lane cycles, 1.34 m of L1 ionosphere); Galileo
E1/E5a (3, 4) (5.6 mm, one wide-lane cycle, 0.565 m of L1 ionosphere).
"""
import argparse
import csv
import collections
import math
import os
import sys

RUNS = os.environ.get("RAPID_RUNS_ROOT") or "D:/GnssProcessorSupport/runs_nom"
C = 299792458.0
FREQ = {("G", "1"): 1575.42e6, ("G", "2"): 1227.60e6, ("G", "5"): 1176.45e6,
        ("E", "1"): 1575.42e6, ("E", "5"): 1176.45e6, ("E", "7"): 1207.14e6}
PAIR = {("G", "1", "2"): (7, 9), ("G", "1", "5"): (24, 31), ("E", "1", "5"): (3, 4), ("E", "1", "7"): (13, 17)}


def resolve(run):
    return os.path.abspath(run) if os.path.isdir(run) else os.path.join(RUNS, "_rap_" + run)


def lane_cost(c, b1, b2, a, b):
    """(ionosphere-free cost m, L1 ionosphere shift m) of moving the two bands by (a, b) cycles."""
    f1, f2 = FREQ[(c, b1)], FREQ[(c, b2)]
    l1, l2 = C / f1, C / f2
    d_if = C * (f1 * a - f2 * b) / (f1 * f1 - f2 * f2)
    gamma = (f1 / f2) ** 2
    d_iono = abs(a * l1 - b * l2) / (gamma - 1.0)
    return d_if, d_iono


def read_chords(path):
    """{(station, sat, family): {tow: (f1, f2, q11, q12, q22)}}"""
    out = collections.defaultdict(dict)
    with open(path, newline="") as fh:
        for r in csv.DictReader(fh):
            try:
                out[(r["arc_sta"], r["arc_sat"], r["family"])][round(float(r["tow"]), 3)] = (
                    float(r["float_cyc_1"]), float(r["float_cyc_2"]), float(r["q11"]), float(r["q12"]), float(r["q22"]))
            except (KeyError, ValueError):
                pass
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("runs", nargs="+")
    ap.add_argument("--list", type=int, default=0)
    a = ap.parse_args()
    for run in a.runs:
        d = resolve(run)
        chords = read_chords(os.path.join(d, "logs", "network_chain_frame.csv"))
        by_fam = collections.defaultdict(lambda: collections.defaultdict(dict))
        for (sta, sat, fam), rows in chords.items():
            by_fam[(sta, sat)][fam] = rows
        pins = {}
        with open(os.path.join(d, "logs", "network_chain_edges.csv"), newline="") as fh:
            for r in csv.DictReader(fh):
                if r["row"] != "RehostUncertified":
                    continue
                key = (round(float(r["tow"]), 3), r["edge_sta"], r["edge_sat"])
                pins.setdefault(key, set()).add(r["band"])
        rows = []
        for (tow, sta, sat), bands in sorted(pins.items()):
            fams = by_fam.get((sta, sat), {})
            for fam, recs in fams.items():
                prev = [t for t in recs if t < tow - 1e-3]
                if not prev:
                    continue
                t0 = max(prev)
                f1, f2, q11, q12, q22 = recs[t0]
                c = sat[0]
                sigs = fam.split("|")[-1].split("+")
                if len(sigs) != 2:
                    continue
                b1, b2 = sigs[0][1], sigs[1][1]
                pair = PAIR.get((c, b1, b2))
                if pair is None:
                    continue
                pa, pb = pair
                dd = pa * pa + pb * pb
                var = pa * pa * q11 + 2 * pa * pb * q12 + pb * pb * q22
                s = math.sqrt(max(var, 0.0)) / dd
                # Distance of the float from the rounded lane, along d, in lane spacings.
                r1, r2 = f1 - round(f1), f2 - round(f2)
                along = (pa * r1 + pb * r2) / dd
                rows.append((s, tow, sta, sat, fam, along, tow - t0))
        print("== %s: %d pins set by an uncertified re-host with a chord row before them" % (run, len(rows)))
        for fam in sorted({x[4] for x in rows}):
            sub = sorted(x[0] for x in rows if x[4] == fam)
            c = fam[0]
            sig = fam.split("|")[-1].split("+")
            pair = PAIR.get((c, sig[0][1], sig[1][1]))
            d_if, d_iono = lane_cost(c, sig[0][1], sig[1][1], *pair)
            n = len(sub)
            print("  %-14s lane pair %s (ionosphere-free %.1f mm, L1 ionosphere %.3f m): %d pins; sigma along the lane in "
                  "spacings p50 %.3f, p90 %.3f, max %.3f; above 0.25: %d; above 0.125: %d" % (
                      fam, pair, 1e3 * abs(d_if), d_iono, n, sub[n // 2], sub[int(0.9 * (n - 1))], sub[-1],
                      sum(1 for x in sub if x > 0.25), sum(1 for x in sub if x > 0.125)))
        if a.list:
            for s, tow, sta, sat, fam, along, age in sorted(rows, reverse=True)[:a.list]:
                print("    TOW %.0f %s-%s %s: sigma %.3f spacings, float %.3f spacings from its rounded lane (row %.0f s "
                      "before)" % (tow, sta, sat, fam, s, along, age))
    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""Card IRDU section 12.4 (a): what the log-only producer search would fix, graded against truth by ring and time.

    python scripts/irdu_search_grade.py <run> --fixture DIR --frame FILE [--minutes 10,20,30,60] [--json out.json]

The search of these arms (network.ambiguity_resolution with its trace; log only, nothing reaches the solve) writes every
double difference of its star basis to logs/network_producer_ar.csv: (sta_r, sat_j) against (ref_sta, ref_sat) per
signal, its float, sigma, the integer it fixed and whether it was kept.  The truth of a row is the double difference of
the simulator's slip-accumulated integers plus the producer's wind-up branch of each arc (the algebra of
scripts/simnet_producer_ar_grade.py, whose helpers are imported).  A row's ring is the ring of its link (sta_r, sat_j) in
the frame-target file (scripts/irdu_frame_targets.py --all; the bed without re-seats keeps one tree).

Printed per run: at the epochs 10, 20, 30 and 60 min after the run's first epoch, the kept rows and the wrong ones per
band (L1C, L2W) and the wide lane of the double differences kept on both bands, overall and by ring; and the same
summed over the windows 0-10, 10-20, 20-30, 30-60 and 60-120 min (row-epochs).
"""
import argparse
import csv
import json
import os
import sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import simnet_producer_ar_grade as PAG  # noqa: E402
from simnet_amb_integer import load_truth, n_at  # noqa: E402

WINDOWS = ((0, 10), (10, 20), (20, 30), (30, 60), (60, 121))


def rings_of(frame_path):
    out = {}
    with open(frame_path, newline="") as fh:
        for r in csv.DictReader(fh):
            if r.get("ring") not in (None, "", "None"):
                out[(r["station"], r["sat"])] = int(r["ring"])
    return out


def grade(run, fixture, frame_path, minutes):
    stations = sorted(d for d in os.listdir(fixture)
                      if os.path.isfile(os.path.join(fixture, d, "truth_ambiguities.csv")))
    n_int, slips = load_truth(fixture, stations)
    branches, _ = PAG.load_windup_branches(fixture, run, stations)
    ring = rings_of(frame_path)
    rows = []
    t0 = None
    with open(os.path.join(run, "logs", "network_producer_ar.csv"), newline="", encoding="utf-8",
              errors="replace") as fh:
        for r in csv.DictReader(fh):
            tow = float(r["tow"])
            t0 = tow if t0 is None else min(t0, tow)
            if r["kept"] != "1":
                continue
            sig = r["signal"]
            sr, sj, fr, fp = r["sta_r"], r["sat_j"], r["ref_sta"], r["ref_sat"]
            ns = [n_at(n_int, slips, a, b, sig, tow) for a, b in ((sr, sj), (sr, fp), (fr, sj), (fr, fp))]
            if None in ns:
                continue
            ns = [n + PAG.branch_at(branches, a, b, tow)
                  for n, (a, b) in zip(ns, ((sr, sj), (sr, fp), (fr, sj), (fr, fp)))]
            dd_true = (ns[0] - ns[1]) - (ns[2] - ns[3])
            fx = int(round(float(r["fixed_int"])))
            rows.append({"tow": tow, "sig": sig, "key": (tow, sr, sj, fr, fp), "fx": fx, "true": dd_true,
                         "ring": ring.get((sr, sj))})
    # the wide lane of the double differences kept on both bands
    by_key = defaultdict(dict)
    for r in rows:
        by_key[r["key"]][r["sig"]] = r
    wl = []
    for k, d in by_key.items():
        if "L1C" in d and "L2W" in d:
            a, b = d["L1C"], d["L2W"]
            wl.append({"tow": a["tow"], "sig": "WL", "fx": a["fx"] - b["fx"], "true": a["true"] - b["true"],
                       "ring": a["ring"]})
    allrows = rows + wl
    res = {"run": run, "t0": t0, "at": {}, "windows": {}}

    def tally(sel):
        out = defaultdict(lambda: [0, 0])
        for r in sel:
            for key in ((r["sig"], "all"), (r["sig"], "ring %s" % r["ring"])):
                out[key][0] += 1
                out[key][1] += int(r["fx"] != r["true"])
        return {"%s|%s" % k: v for k, v in sorted(out.items())}
    for m in minutes:
        t = t0 + 60.0 * m
        res["at"][str(m)] = tally([r for r in allrows if abs(r["tow"] - t) < 1.0])
    for a, b in WINDOWS:
        res["windows"]["%d-%d" % (a, b)] = tally([r for r in allrows
                                                  if t0 + 60.0 * a - 1e-3 <= r["tow"] < t0 + 60.0 * b - 1e-3])
    return res


def print_result(res, label):
    print("== %s: the search's kept rows (kept / wrong); bands L1C, L2W, the wide lane of rows kept on both" % label)
    for name, block in (("at the epoch", res["at"]), ("window", res["windows"])):
        for when, t in block.items():
            parts = []
            for sig in ("L1C", "L2W", "WL"):
                v = t.get("%s|all" % sig, [0, 0])
                parts.append("%s %d/%d" % (sig, v[0], v[1]))
            rings = sorted({k.split("|")[1] for k in t if k.startswith("L1C|ring")})
            by_ring = ", ".join("%s %d/%d" % (rg.replace("ring ", "r"), t["L1C|" + rg][0], t["L1C|" + rg][1])
                                for rg in rings)
            print("   %-12s %-7s %s | L1C by ring: %s" % (name, when, " ".join(parts), by_ring or "-"))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("run")
    ap.add_argument("--fixture", default="C:/GnssProcessor/runs/simarl_r3c")
    ap.add_argument("--frame", required=True)
    ap.add_argument("--minutes", default="10,20,30,60")
    ap.add_argument("--label")
    ap.add_argument("--json")
    a = ap.parse_args()
    res = grade(os.path.abspath(a.run), a.fixture, a.frame, [float(x) for x in a.minutes.split(",")])
    print_result(res, a.label or os.path.basename(a.run))
    if a.json:
        with open(a.json, "w") as fh:
            json.dump(res, fh, indent=1)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Card IRDU section 11.3, reading ZWD: each receiver's wet-delay error against the simulated truth, by its depth in
the chain's tree and by time.

    py -3.14 scripts/irdu_zwd_error.py <run dir or tag> [<run dir or tag> ...] [--fixture DIR] [--bin-min 15]
        [--json out.json]
    py -3.14 scripts/irdu_zwd_error.py --selftest

The network's estimate is logs/network_zwd.csv (network.trace_zwd: zwd_m, the absolute zenith wet delay, and its
formal std_m per station and epoch); the truth is the station's truth_tropo.csv in the fixture (zwd_m per epoch).
error = zwd_m - truth.  A receiver's depth is read from logs/network_chain_edges.csv (the receiver's child row; the
root, which has none, is depth 0).  Per depth and time bin (minutes from the run's first epoch): n station-epochs,
|error| p50 and p95, the between-epoch step of the estimate |zwd(t) - zwd(t-30 s)| p50 and p95 (its wander, which a
hop passes on as the mapping-function difference times the step), and the formal sigma p50.
"""
import argparse
import csv
import json
import math
import os
import sys
from collections import defaultdict

RUNS = os.environ.get("RAPID_RUNS_ROOT") or "D:/GnssProcessorSupport/runs_nom"


def pct(v, q):
    v = sorted(v)
    if not v:
        return float("nan")
    k = (len(v) - 1) * q / 100.0
    lo = int(math.floor(k))
    hi = min(lo + 1, len(v) - 1)
    return v[lo] + (v[hi] - v[lo]) * (k - lo)


def read_truth(fixture, station):
    p = os.path.join(fixture, station, "truth_tropo.csv")
    out = {}
    if not os.path.isfile(p):
        return out
    with open(p, newline="") as fh:
        for r in csv.DictReader(fh):
            out[round(float(r["tow_s"]), 3)] = float(r["zwd_m"])
    return out


def receiver_depths(run):
    """{station: depth} from the edge trace (the receiver's child row of band L1C at the first epoch it appears;
    the root gets 0)."""
    p = os.path.join(run, "logs", "network_chain_edges.csv")
    dep, root = {}, None
    with open(p, newline="") as fh:
        for r in csv.DictReader(fh):
            root = root or r["r1"]
            if r["band"] != "L1C":
                continue
            c = r["child"]
            if c.startswith("S") and c not in dep:
                dep[c] = int(r["depth"])
    if root:
        dep.setdefault(root, 0)
    return dep


def analyse(run, fixture, bin_min=15.0):
    dep = receiver_depths(run)
    est = defaultdict(dict)
    with open(os.path.join(run, "logs", "network_zwd.csv"), newline="") as fh:
        for r in csv.DictReader(fh):
            est[r["station"]][round(float(r["tow"]), 3)] = (float(r["zwd_m"]), float(r["std_m"] or "nan"))
    t0 = min(min(v) for v in est.values())
    cells = defaultdict(lambda: {"err": [], "step": [], "sig": []})
    for st, series in est.items():
        truth = read_truth(fixture, st)
        d = dep.get(st)
        if d is None or not truth:
            continue
        prev = None
        for t in sorted(series):
            z, s = series[t]
            b = int((t - t0) // (60.0 * bin_min))
            for key in ((d, b), ("all", b)):
                if t in truth:
                    cells[key]["err"].append(abs(z - truth[t]))
                if math.isfinite(s):
                    cells[key]["sig"].append(s)
                if prev is not None and abs(t - prev[0] - 30.0) < 1e-3:
                    cells[key]["step"].append(abs(z - prev[1]))
            prev = (t, z)
    out = {}
    for (d, b), c in cells.items():
        out["%s|%d" % (d, b)] = {"n": len(c["err"]), "err_p50": pct(c["err"], 50), "err_p95": pct(c["err"], 95),
                                 "step_p50": pct(c["step"], 50), "step_p95": pct(c["step"], 95),
                                 "sig_p50": pct(c["sig"], 50)}
    nbin = 1 + max(int(k.split("|")[1]) for k in out)
    depths = sorted({k.split("|")[0] for k in out if k.split("|")[0] != "all"}, key=int) + ["all"]
    return {"run": run, "fixture": fixture, "bin_min": bin_min, "nbin": nbin, "depths": depths, "cells": out,
            "receivers_by_depth": {str(k): sum(1 for v in dep.values() if v == k) for k in sorted(set(dep.values()))}}


def print_result(res):
    print("== wet-delay error against truth: %s (bins of %.0f min); receivers by depth %s"
          % (res["run"], res["bin_min"], res["receivers_by_depth"]))
    print("   per cell: |error| p50 / p95 (mm) | step p50 / p95 (mm) | formal sigma p50 (mm)")
    for d in res["depths"]:
        line = "  depth %-4s" % d
        for b in range(res["nbin"]):
            x = res["cells"].get("%s|%d" % (d, b))
            line += ("  %3d-%3d: %5.1f/%6.1f | %4.1f/%5.1f | %5.1f" % (
                b * res["bin_min"], (b + 1) * res["bin_min"], 1e3 * x["err_p50"], 1e3 * x["err_p95"],
                1e3 * x["step_p50"], 1e3 * x["step_p95"], 1e3 * x["sig_p50"]) if x else "")
        print(line)


def selftest():
    ok = True

    def chk(c, msg):
        nonlocal ok
        print(("PASS " if c else "FAIL ") + msg)
        ok &= bool(c)

    chk(abs(pct([1, 2, 3, 4], 50) - 2.5) < 1e-12, "percentile by linear interpolation")
    chk(math.isnan(pct([], 50)), "an empty cell reads nan")
    return ok


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("runs", nargs="*")
    ap.add_argument("--fixture", default="C:/GnssProcessor/runs/simarl_r3c")
    ap.add_argument("--bin-min", type=float, default=15.0)
    ap.add_argument("--json")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        sys.exit(0 if selftest() else 1)
    allres = []
    for x in a.runs:
        run = x if os.path.isdir(x) else os.path.join(RUNS, "_rap_" + x)
        res = analyse(run, a.fixture, a.bin_min)
        print_result(res)
        allres.append(res)
    if a.json:
        with open(a.json, "w") as fh:
            json.dump(allres, fh, indent=1)


if __name__ == "__main__":
    main()

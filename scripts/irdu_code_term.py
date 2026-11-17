#!/usr/bin/env python3
"""Card IRDU section 12.2: what a stream's code half and phase half give a float user, satellite against satellite.

    python scripts/irdu_code_term.py <run dir or tag> [...] [--fixture DIR] [--source products|prehold] [--bin-min 15]

Per satellite and epoch, against truth (scripts/simnet_wire_integer_consistency.py's wire algebra, card IRD section 8):

  r        the code error common to both bands (the range-like term: wc1 - mu1 x), metres
  phi_IF   the ionosphere-free phase error (f1^2 w1 - f2^2 w2) / (f1^2 - f2^2), metres, w_b the phase error of band b

A user's receiver clock takes up whatever is common to all satellites, so each is read against the epoch's median over
satellites.  Per bin (minutes from the run's first epoch):
  r spread       p50 and p95 of |r - median r| over satellites and epochs
  r drift        p50 and p95 of the change of (r - median r) of one satellite across the bin
  phi_IF drift   the same for phi_IF (a constant per satellite is taken up by the user's float ambiguity; its change is
                 not)
"""
import argparse
import json
import math
import os
import sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import simnet_wire_integer_consistency as WIC  # noqa: E402

RUNS = os.environ.get("RAPID_RUNS_ROOT") or "D:/GnssProcessorSupport/runs_nom"
F1, F2 = 1575.42e6, 1227.60e6
C = 299792458.0


def pct(v, q):
    v = sorted(v)
    if not v:
        return float("nan")
    k = (len(v) - 1) * q / 100.0
    lo = int(math.floor(k))
    hi = min(lo + 1, len(v) - 1)
    return v[lo] + (v[hi] - v[lo]) * (k - lo)


def median(v):
    return pct(v, 50)


def terms(run, fixture, source):
    """{tow: {sat: (r, phi_if)}} for GPS."""
    osb, sc, eps, _ = WIC.dual_load(fixture, run, source)
    out = {}
    l1, l2 = C / F1, C / F2
    for e in sorted(eps, key=lambda e: e["tow"]):
        v = WIC.dual_sat_values(e, osb, sc, ("L1C", "L2W"), xcorr=False)
        row = {}
        for s, x in v.items():
            if s[0] != "G":
                continue
            w1, w2 = x["E1"] * l1, x["E2"] * l2          # raw phase errors (metres), x-correction off
            phi_if = (F1 * F1 * w1 - F2 * F2 * w2) / (F1 * F1 - F2 * F2)
            row[s] = (x["r"], phi_if)
        out[round(e["tow"], 3)] = row
    return out


def analyse(run, fixture, source="products", bin_min=15.0):
    t = terms(run, fixture, source)
    tows = sorted(t)
    t0 = tows[0]
    centred = {}
    for tow in tows:
        row = t[tow]
        if len(row) < 4:
            continue
        mr = median([v[0] for v in row.values()])
        mp = median([v[1] for v in row.values()])
        centred[tow] = {s: (v[0] - mr, v[1] - mp) for s, v in row.items()}
    nbin = int(math.ceil((tows[-1] - t0 + 30.0) / (60.0 * bin_min)))
    res = {"run": run, "source": source, "bins": {}}
    for b in range(nbin):
        lo, hi = t0 + 60.0 * bin_min * b, t0 + 60.0 * bin_min * (b + 1)
        sel = [tow for tow in sorted(centred) if lo - 1e-3 <= tow < hi - 1e-3]
        if len(sel) < 2:
            continue
        spread = [abs(v[0]) for tow in sel for v in centred[tow].values()]
        first, last = centred[sel[0]], centred[sel[-1]]
        common = set(first) & set(last)
        dr = [abs(last[s][0] - first[s][0]) for s in common]
        dp = [abs(last[s][1] - first[s][1]) for s in common]
        res["bins"]["%d-%d" % (b * bin_min, (b + 1) * bin_min)] = {
            "r_spread_p50": pct(spread, 50), "r_spread_p95": pct(spread, 95),
            "r_drift_p50": pct(dr, 50), "r_drift_p95": pct(dr, 95),
            "phi_drift_p50": pct(dp, 50), "phi_drift_p95": pct(dp, 95), "n_sats": len(common)}
    return res


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("runs", nargs="+")
    ap.add_argument("--fixture", default="C:/GnssProcessor/runs/simarl_r3c")
    ap.add_argument("--source", default="products", choices=("products", "prehold"))
    ap.add_argument("--bin-min", type=float, default=15.0)
    ap.add_argument("--json")
    a = ap.parse_args()
    allres = []
    for x in a.runs:
        run = x if os.path.isdir(x) else os.path.join(RUNS, "_rap_" + x)
        res = analyse(run, a.fixture, a.source, a.bin_min)
        allres.append(res)
        print("== %s (%s): r spread p50 / p95 | r drift across the bin p50 / p95 | phi_IF drift p50 / p95 (mm)"
              % (run, a.source))
        for b, v in res["bins"].items():
            print("   %-8s %6.1f / %6.1f | %6.1f / %6.1f | %6.1f / %6.1f  (%d satellites)" % (
                b, 1e3 * v["r_spread_p50"], 1e3 * v["r_spread_p95"], 1e3 * v["r_drift_p50"], 1e3 * v["r_drift_p95"],
                1e3 * v["phi_drift_p50"], 1e3 * v["phi_drift_p95"], v["n_sats"]))
    if a.json:
        with open(a.json, "w") as fh:
            json.dump(allres, fh, indent=1)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Card IRDU section 11, reading STREAM: the stream's between-satellite potential against truth by the pair's depth in
the chain's tree and by time, through the code biases and on the phase alone.

    py -3.14 scripts/irdu_stream_depth.py <run dir or tag> [--fixture DIR] [--source prehold|products] [--bin-min 15]
        [--json out.json]
    py -3.14 scripts/irdu_stream_depth.py --selftest

Per satellite pair (s, p) of GPS and epoch (scripts/simnet_wire_integer_consistency.py, the one owner of the wire
algebra; E_b the stream's error of satellite s on band b in cycles):

  WL, NL     D_WL = D_1 - D_2 and D_NL = D_1 + f2/(f1-f2) (D_WL - round(D_WL)) with E_b corrected through the code
             biases (E_b = (Wp_b + mu_b x) / lambda_b, x the stream's code error in the geometry-free direction): what
             a user's float converges to (card IRD section 8)
  WLp, NLp   the same on the phase alone (E_b = Wp_b / lambda_b): the stream's phase clock (clock plus phase bias)
             between satellites, what a user's phase reads before its own ionosphere estimate takes up the code
  MW         the Melbourne-Wubbena channel of the pair (cycles)

The pair's depth is the larger tree depth of its two satellites (the `depth` attribute of the pre-hold trace).  Per
pair and time bin (minutes from the run's first epoch), with at least 10 epochs of the pair in the bin:
  offset     |circular mean| of the channel's fraction over the bin (an integer stream reads 0)
  step       the median |change between consecutive epochs| of the channel (unwrapped)
The table pools pairs by depth class (1, 2, 3, 4, 5 and deeper) and bin: n, offset p50 and the share within 0.10
cycle, step p50 and p95 (the per-pair medians pooled).
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
CHANNELS = ("WL", "NL", "WLp", "NLp", "MW")


def circ_offset(v):
    s = sum(math.sin(2 * math.pi * x) for x in v)
    c = sum(math.cos(2 * math.pi * x) for x in v)
    return abs(math.atan2(s, c) / (2 * math.pi))


def unwrapped_steps(v):
    out = []
    for a, b in zip(v, v[1:]):
        d = b - a
        out.append(abs(d - round(d)) if abs(d) < 0.5 else abs(d))
    return out


def pct(v, q):
    v = sorted(v)
    if not v:
        return float("nan")
    k = (len(v) - 1) * q / 100.0
    lo = int(math.floor(k))
    hi = min(lo + 1, len(v) - 1)
    return v[lo] + (v[hi] - v[lo]) * (k - lo)


def pair_channels(a, b, ap, bp):
    ch = WIC.dual_pair_channels(a, b)
    chp = WIC.dual_pair_channels(ap, bp)
    return {"WL": ch["WL"], "NL": ch["NL"], "WLp": chp["WL"], "NLp": chp["NL"], "MW": ch["MW"]}


def depth_class(d):
    return None if d is None or d < 0 else min(d, 5)


def analyse(run, fixture, source="prehold", bin_min=15.0):
    osb, sc, eps, _ = WIC.dual_load(fixture, run, source)
    eps = sorted(eps, key=lambda e: e["tow"])
    t0 = eps[0]["tow"]
    series = defaultdict(list)       # (s, p) -> [(tow, depth class, channels)]
    for e in eps:
        v = {s: x for s, x in WIC.dual_sat_values(e, osb, sc, ("L1C", "L2W")).items() if s[0] == "G"}
        vp = {s: x for s, x in WIC.dual_sat_values(e, osb, sc, ("L1C", "L2W"), xcorr=False).items() if s[0] == "G"}
        sats = sorted(set(v) & set(vp))
        for i in range(len(sats)):
            for j in range(i + 1, len(sats)):
                s, p = sats[i], sats[j]
                try:
                    d = max(int(v[s]["a1"].get("depth")), int(v[p]["a1"].get("depth")))
                except (TypeError, ValueError):
                    d = None
                series[(s, p)].append((e["tow"], depth_class(d), pair_channels(v[s], v[p], vp[s], vp[p])))
    nbin = int(math.ceil((eps[-1]["tow"] - t0 + 30.0) / (60.0 * bin_min)))
    cells = defaultdict(lambda: defaultdict(list))      # (depth class or 'all', bin) -> channel -> [(offset, step)]
    for k, s in series.items():
        groups = defaultdict(list)
        for tow, d, ch in s:
            groups[(d, int((tow - t0) // (60.0 * bin_min)))].append((tow, ch))
        for (d, b), rows in groups.items():
            if len(rows) < 10:
                continue
            rows.sort()
            for c in CHANNELS:
                vals = [r[1][c] for r in rows]
                off = circ_offset(vals)
                st = unwrapped_steps(vals)
                stm = pct(st, 50) if st else float("nan")
                if d is not None:
                    cells[(d, b)][c].append((off, stm))
                cells[("all", b)][c].append((off, stm))
    # section 11 C's event rule: the pooled p95 of every pair-epoch D_WL step over the 10 min before each 5 min mark
    steps_at = defaultdict(list)
    for k, s in series.items():
        for (ta, _, ca), (tb, _, cb) in zip(s, s[1:]):
            if tb - ta > 31.0:
                continue
            d = cb["WL"] - ca["WL"]
            steps_at[tb].append(abs(d - round(d)) if abs(d) < 0.5 else abs(d))
    settle = {}
    for m in range(10, int((eps[-1]["tow"] - t0) // 60) + 1, 5):
        tm = t0 + 60.0 * m
        pool = [x for t, v in steps_at.items() if tm - 600.0 < t <= tm for x in v]
        settle[m] = pct(pool, 95) if pool else float("nan")
    res = {"run": run, "fixture": fixture, "source": source, "bin_min": bin_min, "t0": t0, "nbin": nbin,
           "pairs": len(series), "cells": {}, "settle_wl_step_p95_10min": settle}
    for (d, b), chans in cells.items():
        out = {}
        for c, v in chans.items():
            offs = [x[0] for x in v]
            steps = [x[1] for x in v if not math.isnan(x[1])]
            out[c] = {"n": len(v), "off_p50": pct(offs, 50), "off_le010": sum(o <= 0.10 for o in offs) / len(offs),
                      "step_p50": pct(steps, 50), "step_p95": pct(steps, 95)}
        res["cells"]["%s|%d" % (d, b)] = out
    return res


def print_table(res, channels=("WL", "NL", "WLp", "NLp")):
    print("== stream by depth and time: %s (source %s, bins of %.0f min)" % (res["run"], res["source"], res["bin_min"]))
    print("pooled D_WL step p95 over the 10 min before each 5 min mark (section 11 C's event rule): " + ", ".join(
        "%d min %.3f" % (int(m), v) for m, v in sorted(res["settle_wl_step_p95_10min"].items(), key=lambda kv: int(kv[0]))))
    print("pairs %d; per cell: n pair-bins | offset p50, share within 0.10 | step p50, p95 (cycles; NL in NL cycles)"
          % res["pairs"])
    for c in channels:
        print("channel %s" % c)
        hdr = "  depth  " + "".join("%-27s" % ("%3d-%3d min" % (b * res["bin_min"], (b + 1) * res["bin_min"]))
                                    for b in range(res["nbin"]))
        print(hdr)
        for d in ("1", "2", "3", "4", "5", "all"):
            line = "  %-6s " % d
            for b in range(res["nbin"]):
                x = res["cells"].get("%s|%d" % (d, b), {}).get(c)
                line += ("%3d %.3f %3.0f%% %.3f %.3f  " % (x["n"], x["off_p50"], 100 * x["off_le010"], x["step_p50"],
                                                           x["step_p95"]) if x else "%-27s" % "  -")
            print(line)


def selftest():
    ok = True

    def chk(c, msg):
        nonlocal ok
        print(("PASS " if c else "FAIL ") + msg)
        ok &= bool(c)

    chk(circ_offset([3.0, 4.0, -2.0]) < 1e-12, "an integer series has offset 0")
    chk(abs(circ_offset([0.2, 1.2, 2.2]) - 0.2) < 1e-12, "a constant fraction is the offset")
    st = unwrapped_steps([0.0, 0.1, 1.05, 1.1])
    chk(all(abs(a - b) < 1e-9 for a, b in zip(st, [0.1, 0.95, 0.05])), "steps below half a cycle wrap, larger ones do not")
    chk(depth_class(7) == 5 and depth_class(None) is None, "depth classes")
    return ok


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("run", nargs="?")
    ap.add_argument("--fixture")
    ap.add_argument("--source", default="prehold", choices=("prehold", "products"))
    ap.add_argument("--bin-min", type=float, default=15.0)
    ap.add_argument("--json")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        sys.exit(0 if selftest() else 1)
    run = a.run if os.path.isdir(a.run) else os.path.join(RUNS, "_rap_" + a.run)
    fixture = a.fixture
    if fixture is None:
        fx = json.load(open(os.path.join(run, "rapid.json")))["ird"]["fixture"]
        fixture = fx if os.path.isabs(fx) else os.path.join("C:/GnssProcessor", fx)
    res = analyse(run, fixture, a.source, a.bin_min)
    print_table(res)
    if a.json:
        with open(a.json, "w") as fh:
            json.dump(res, fh, indent=1)


if __name__ == "__main__":
    main()

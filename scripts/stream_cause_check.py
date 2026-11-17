#!/usr/bin/env python3
"""Card NRF, order D.2: the cause side of the stream's step declaration.  Every chain event that moves a satellite
signal's level against the stream's phase discontinuity counters, and every increment against the chain events.

    py -3.14 scripts/stream_cause_check.py <run> [<run> ...] [--list N]

Chain events (the run's own traces):
  release   a CHAIN declared_keys row: the satellite's keys on the signal declared moved by a cut release (re-host,
            slip, return, merge) whose step is unknown
  re-pin    a tree edge of logs/network_chain_edges.csv with a known non-zero step (pinmove_m): the shift walk moves the
            edge's child and every vertex below it by the step, the sign alternating down the tree; the satellites of
            that subtree, with the step in cycles
An increment is a rise of the P record's phase_disc between two consecutive epochs (network.serialize_disc_counters).
Printed per run: releases with and without an increment at that epoch on that satellite signal; re-pins by step size
(at or above 0.15 cycle, below), with and without an increment; increments by what stands behind them at that epoch
(a release, a re-pin of 0.15 cycle or more, a smaller re-pin, a forced mark, nothing in the chain).  --list prints
releases without an increment and increments with nothing in the chain behind them.
"""
import argparse
import collections
import csv
import os
import sys

RUNS = os.environ.get("RAPID_RUNS_ROOT") or "D:/GnssProcessorSupport/runs_nom"
C = 299792458.0
FREQ = {("G", "1"): 1575.42e6, ("G", "2"): 1227.60e6, ("G", "5"): 1176.45e6, ("E", "1"): 1575.42e6,
        ("E", "5"): 1176.45e6, ("E", "7"): 1207.14e6, ("E", "6"): 1278.75e6}


def resolve(run):
    return os.path.abspath(run) if os.path.isdir(run) else os.path.join(RUNS, "_rap_" + run)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("runs", nargs="+")
    ap.add_argument("--list", type=int, default=0)
    ap.add_argument("--tol", type=float, default=0.15)
    a = ap.parse_args()
    for run in a.runs:
        d = resolve(run)
        # Increments of the phase counters.
        incs, forced, prev, tows = set(), set(), {}, []
        cur, now = {}, None
        with open(os.path.join(d, "products.txt"), encoding="utf-8", errors="replace") as fh:
            for line in fh:
                k = line[:2]
                if k == "E,":
                    if now is not None:
                        for key, v in cur.items():
                            if key in prev and v > prev[key]:
                                incs.add((now,) + key)
                        prev.update(cur)
                    q = line.rstrip().split(",")
                    now, cur = round(float(q[2])), {}
                    tows.append(now)
                    if len(q) > 6 and q[6] == "1":
                        forced.add((now, "const", q[7] if len(q) > 7 else "*"))
                elif k == "P," and now is not None:
                    q = line.rstrip().split(",")
                    if len(q) > 6 and q[6].lstrip("-").isdigit():
                        cur[(q[1], q[2])] = int(q[6])
                elif k == "R," and now is not None:
                    for s in line.rstrip().split(",")[1:]:
                        forced.add((now, "sat", s))
        if now is not None:
            for key, v in cur.items():
                if key in prev and v > prev[key]:
                    incs.add((now,) + key)
        forced_sat = {(t, s) for t, kind, s in forced if kind == "sat"}
        forced_const = collections.defaultdict(set)
        for t, kind, s in forced:
            if kind == "const":
                forced_const[t].update(s if s != "*" else "GERCJ")
        # Releases: declared keys.
        rel = set()
        with open(os.path.join(d, "logs", "network_events.csv"), newline="") as fh:
            for r in csv.DictReader(fh):
                if r["tier"] == "CHAIN" and r["event"] == "declared_keys":
                    sig = next((x[4:] for x in r["detail"].split() if x.startswith("sig=")), "")
                    rel.add((round(float(r["tow"])), r["sat"], sig))
        # Re-pins: known non-zero steps, propagated to the satellites below.
        repin = {}
        by_epoch = collections.defaultdict(list)
        with open(os.path.join(d, "logs", "network_chain_edges.csv"), newline="") as fh:
            for r in csv.DictReader(fh):
                by_epoch[(round(float(r["tow"])), r["band"])].append(r)
        for (t, band), rows in by_epoch.items():
            kids = collections.defaultdict(list)
            for r in rows:
                kids[r["parent"]].append(r["child"])
            for r in rows:
                if r["known"] != "1":
                    continue
                pm = float(r["pinmove_m"] or 0.0)
                if pm == 0.0:
                    continue
                lam = C / FREQ.get((r["system"], band[1]), 1575.42e6)
                stack, seen = [(r["child"], 0)], set()
                while stack:
                    v, dpt = stack.pop()
                    if v in seen:
                        continue
                    seen.add(v)
                    if len(v) == 3 and v[1:].isdigit():
                        key = (t, v, band)
                        repin[key] = repin.get(key, 0.0) + (-1) ** (dpt + 1) * pm / lam
                    stack += [(k, dpt + 1) for k in kids.get(v, [])]
        rel_hit = sum(1 for x in rel if x in incs)
        big = {k: v for k, v in repin.items() if abs(v) >= a.tol}
        small = {k: v for k, v in repin.items() if abs(v) < a.tol}
        print("== %s: phase increments %d" % (run, len(incs)))
        print("   releases (declared keys) %d: with an increment at that epoch on that satellite signal %d, without %d"
              % (len(rel), rel_hit, len(rel) - rel_hit))
        print("   re-pins of %.2f cycle or more %d: with an increment %d; smaller re-pins %d: with an increment %d"
              % (a.tol, len(big), sum(1 for k in big if k in incs), len(small), sum(1 for k in small if k in incs)))
        why = collections.Counter()
        lone = []
        for x in sorted(incs):
            t, s, sig = x
            if x in rel:
                why["a release"] += 1
            elif x in big:
                why["a re-pin of %.2f cycle or more" % a.tol] += 1
            elif x in small:
                why["a smaller re-pin"] += 1
            elif (t, s) in forced_sat or s[0] in forced_const.get(t, set()):
                why["a forced mark"] += 1
            else:
                why["nothing in the chain at that epoch"] += 1
                lone.append(x)
        print("   increments by what stands behind them: %s" % "; ".join("%s %d" % kv for kv in why.most_common()))
        if a.list:
            for x in sorted(x for x in rel if x not in incs)[:a.list]:
                print("      release without an increment: TOW %d %s %s" % x)
            for x in lone[:a.list]:
                print("      increment with nothing in the chain: TOW %d %s %s" % x)
    return 0


if __name__ == "__main__":
    sys.exit(main())

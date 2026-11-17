#!/usr/bin/env python3
"""Card IRDU section 12.10: which phase records of a stream cross the emitter's discontinuity gate, when, and why.

    py -3.14 scripts/irdu_pb_steps.py <network run> [--from-min 0] [--frac 0.25]

The emitter declares a phase discontinuity when a satellite's emitted phase bias moves between consecutive epochs by
more than frac * lambda of its signal (the stream's header: discfrac=0.25; NetworkProductEmitter::discThresholdM), and
a consumer resets that ambiguity.  For every crossing: the satellite, signal, time (minutes from the run's first
epoch), the move, the move shared by the satellites at that epoch (the median over the satellites of the signal) and the
satellite's own part, and the network's arcs of that satellite at that epoch against the previous one (the chain's
tree edges, logs/network_chain_edges.csv, and its chords, logs/network_chain_frame.csv): arcs that started and ended.
"""
import argparse
import csv
import os
from collections import defaultdict

C = 299792458.0
LAMBDA = {"L1C": C / 1575.42e6, "L2W": C / 1227.60e6}


def read_phase(path):
    out = defaultdict(dict)      # tow -> {(sat, sig): P}
    order = []
    tow = None
    with open(path, encoding="utf-8") as fh:
        for ln in fh:
            if ln.startswith("E,"):
                tow = round(float(ln.split(",")[2]), 3)
                order.append(tow)
            elif tow is not None and ln.startswith("P,G"):
                f = ln.split(",")
                if f[2] in LAMBDA:
                    out[tow][(f[1], f[2])] = float(f[3])
    return out, order


def read_arcs(run):
    arcs = defaultdict(set)      # tow -> {(sta, sat)}
    p = os.path.join(run, "logs", "network_chain_edges.csv")
    with open(p, newline="") as fh:
        for r in csv.DictReader(fh):
            if r["band"] == "L1C":
                arcs[round(float(r["tow"]), 3)].add((r["edge_sta"], r["edge_sat"]))
    p = os.path.join(run, "logs", "network_chain_frame.csv")
    with open(p, newline="") as fh:
        for r in csv.DictReader(ln for ln in fh if not ln.startswith("#")):
            arcs[round(float(r["tow"]), 3)].add((r["arc_sta"], r["arc_sat"]))
    return arcs


def median(v):
    v = sorted(v)
    n = len(v)
    return v[n // 2] if n % 2 else 0.5 * (v[n // 2 - 1] + v[n // 2])


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("run")
    ap.add_argument("--from-min", type=float, default=0.0)
    ap.add_argument("--frac", type=float, default=0.25)
    a = ap.parse_args()
    ph, order = read_phase(os.path.join(a.run, "products.txt"))
    arcs = read_arcs(a.run)
    t0 = order[0]
    crossings = []
    for prev, t in zip(order, order[1:]):
        for sig in LAMBDA:
            moves = {s: ph[t][(s, g)] - ph[prev][(s, g)] for (s, g) in ph[t] if g == sig and (s, g) in ph[prev]}
            if not moves:
                continue
            shared = median(list(moves.values()))
            thr = a.frac * LAMBDA[sig]
            for s, d in moves.items():
                if abs(d) > thr:
                    now = {st for st, sat in arcs.get(t, ()) if sat == s}
                    before = {st for st, sat in arcs.get(prev, ()) if sat == s}
                    crossings.append(((t - t0) / 60.0, s, sig, d, shared, d - shared,
                                      sorted(now - before), sorted(before - now), len(now)))
    late = [c for c in crossings if c[0] >= a.from_min]
    print("== %s: %d crossings of the gate (0.25 cycle) over the run, %d from %.0f min" % (
        os.path.basename(a.run.rstrip("/\\")), len(crossings), len(late), a.from_min))
    for (m, s, sig, d, shared, own, started, ended, n) in late:
        print("   %6.1f min %s %s move %+7.1f mm (shared %+6.1f, own %+7.1f); arcs of %s: %d, started at %s, ended at %s" % (
            m, s, sig, 1000 * d, 1000 * shared, 1000 * own, s, n, ",".join(started) or "-", ",".join(ended) or "-"))
    by_min = defaultdict(int)
    for c in crossings:
        by_min[int(c[0] // 5) * 5] += 1
    print("   crossings per 5 min from the start: " + ", ".join("%d-%d %d" % (k, k + 5, v) for k, v in sorted(by_min.items())))


if __name__ == "__main__":
    main()

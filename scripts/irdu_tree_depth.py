#!/usr/bin/env python3
"""Card IRDU section 12.4, route (b): how deep the chain's tree hangs its satellites against the shortest paths the
observation graph allows, and how each too-deep satellite got there.  Measure only.

    py -3.14 scripts/irdu_tree_depth.py <run> [--minutes 10,30,60,90,110] [--json out.json]

The tree of each epoch is logs/network_chain_edges.csv (band L1C: the pair family pins the same edges on both bands;
one row per tree edge with its child, parent, the child's depth, the edge's cause and row).  The observation graph of
the epoch is the tree edges plus the chords of logs/network_chain_frame.csv.  Per time (minutes from the run's first
epoch), the satellites' depth histogram in the tree, by breadth-first shortest paths from the same root, and from the
best root (the receiver whose shortest-path tree has the smallest largest depth, then the smallest depth sum).  For
each satellite deeper than its shortest path at the last time: the epoch its present tree edge began, the edge's cause
and row then, its tree depth and its shortest-path depth at that epoch (deeper already at attachment, or made deeper
later by a shorter route that opened while the edge was kept).
"""
import argparse
import csv
import json
import os
from collections import Counter, defaultdict, deque


def read_trees(run):
    trees = defaultdict(dict)            # tow -> child -> row
    with open(os.path.join(run, "logs", "network_chain_edges.csv"), newline="") as fh:
        for r in csv.DictReader(fh):
            if r["band"] != "L1C":
                continue
            trees[round(float(r["tow"]), 3)][r["child"]] = r
    return trees


def read_chords(run, tows):
    out = defaultdict(set)
    with open(os.path.join(run, "logs", "network_chain_frame.csv"), newline="") as fh:
        for r in csv.DictReader(ln for ln in fh if not ln.startswith("#")):
            t = round(float(r["tow"]), 3)
            if t in tows:
                out[t].add((r["arc_sta"], r["arc_sat"]))
    return out


def bfs_depths(adj, root):
    d = {root: 0}
    q = deque([root])
    while q:
        u = q.popleft()
        for w in sorted(adj[u]):
            if w not in d:
                d[w] = d[u] + 1
                q.append(w)
    return d


def is_sat(v):
    return not v.startswith("S") or len(v) <= 3   # satellites are G01..; stations S..SIM


def sat_hist(depths):
    return dict(sorted(Counter(v for k, v in depths.items() if is_sat(k)).items()))


def edge_key(row):
    return (row["edge_sta"], row["edge_sat"])


def analyse(run, minutes):
    trees = read_trees(run)
    tows = sorted(trees)
    t0 = tows[0]
    want = {}
    for m in minutes:
        t = min(tows, key=lambda x: abs(x - (t0 + 60.0 * m)))
        want[t] = m
    chords = read_chords(run, set(tows))
    res = {"run": run, "at": {}, "too_deep": []}
    last_t = max(want)
    for t in sorted(want):
        tree = trees[t]
        root = next(iter(tree.values()))["r1"]
        adj = defaultdict(set)
        for row in tree.values():
            a, b = edge_key(row)
            adj[a].add(b)
            adj[b].add(a)
        for a, b in chords.get(t, ()):
            adj[a].add(b)
            adj[b].add(a)
        tree_d = {root: 0}
        tree_d.update({c: int(row["depth"]) for c, row in tree.items()})
        sp = bfs_depths(adj, root)
        best = None
        for rx in sorted(v for v in adj if not is_sat(v)):
            d = bfs_depths(adj, rx)
            key = (max(d.values()), sum(v for k, v in d.items() if is_sat(k)), rx)
            if best is None or key < best[0]:
                best = (key, d)
        res["at"][str(want[t])] = {"tow": t, "root": root, "tree": sat_hist(tree_d), "shortest": sat_hist(sp),
                                   "best_root": best[0][2], "best": sat_hist(best[1]),
                                   "sats": sum(1 for k in tree_d if is_sat(k)),
                                   "too_deep": sum(1 for k in tree_d if is_sat(k) and tree_d[k] > sp.get(k, 99))}
        if t == last_t:
            for sat in sorted(k for k in tree_d if is_sat(k) and tree_d[k] > sp.get(k, 99)):
                ek = edge_key(tree[sat])
                start = t
                for u in reversed([x for x in tows if x <= t]):
                    row = trees[u].get(sat)
                    if row is None or edge_key(row) != ek:
                        break
                    start = u
                srow = trees[start][sat]
                # shortest-path depth at the start epoch
                adj0 = defaultdict(set)
                for row in trees[start].values():
                    a, b = edge_key(row)
                    adj0[a].add(b)
                    adj0[b].add(a)
                for a, b in chords.get(start, ()):
                    adj0[a].add(b)
                    adj0[b].add(a)
                sp0 = bfs_depths(adj0, srow["r1"])
                res["too_deep"].append({"sat": sat, "parent": tree[sat]["parent"], "depth": tree_d[sat],
                                        "shortest": sp[sat], "edge_since_min": round((start - t0) / 60.0, 1),
                                        "cause_then": srow["legacy_cause"], "row_then": srow["row"],
                                        "depth_then": int(srow["depth"]), "shortest_then": sp0.get(sat)})
    return res


def print_result(res, label):
    print("== %s" % label)
    for m, a in res["at"].items():
        print("   %5s min root %s: satellites by depth: tree %s | shortest %s | best root %s %s | too deep %d of %d" % (
            m, a["root"], a["tree"], a["shortest"], a["best_root"], a["best"], a["too_deep"], a["sats"]))
    for d in res["too_deep"]:
        print("   too deep at the end: %s under %s depth %d (shortest %d); edge since %.1f min (%s, %s), depth then %d, "
              "shortest then %s" % (d["sat"], d["parent"], d["depth"], d["shortest"], d["edge_since_min"],
                                    d["cause_then"], d["row_then"], d["depth_then"], d["shortest_then"]))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("run")
    ap.add_argument("--minutes", default="0,10,30,60,90,110")
    ap.add_argument("--label")
    ap.add_argument("--json")
    a = ap.parse_args()
    res = analyse(os.path.abspath(a.run), [float(x) for x in a.minutes.split(",")])
    print_result(res, a.label or os.path.basename(a.run))
    if a.json:
        with open(a.json, "w") as fh:
            json.dump(res, fh, indent=1)


if __name__ == "__main__":
    main()

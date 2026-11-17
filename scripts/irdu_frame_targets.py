#!/usr/bin/env python3
"""Card IRDU section 12: the chain-frame targets of the oracle pin, one file per case.

    python scripts/irdu_frame_targets.py <run> <fixture> --tow T --out FILE [--rings 2,3 | --all] [--systems G]
    python scripts/irdu_frame_targets.py --selftest

The run's chain trace (logs/network_chain_edges.csv and logs/network_chain_frame.csv) gives the tree of epoch T and
every arc the network carried then (the tree links and the chords of the chord table).  For each arc and band the
integer in the chain's frame is ird_frame_census.frame_integer (the one owner of the frame algebra): a tree link reads
its own target, a chord N~ = N_true(chord) + sum over its tree path of c (N_true(arc) - k_arc), with N_true the
simulator's slip-accumulated integer plus the producer's wind-up branch of the arc.

Output columns (the header network.cycle_slip.oracle_pin_frame_file requires, then one extra): station, sat, signal,
frame_int, role, ring.  role is `tree` for a tree link of epoch T (the oracle pin checks it against the chain's pin
every epoch and never pins it) or `chord`.  ring is the larger tree depth of the arc's two vertices (the root
receiver at depth 0): ring k holds the links from the depth-k vertices up the tree.  Every tree link is written;
chords only of the rings asked for (--rings) or all of them (--all).

The file is valid while the chain keeps the tree of epoch T: on the bed without re-seats (section 11.1) it keeps it
for the whole run, and the oracle pin releases every frame pin for good if it ever moves.
"""
import argparse
import csv
import os
import sys
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ird_frame_census as IFC  # noqa: E402

BANDS = ("L1C", "L2W")


def node_depths(forest, system, band, tow):
    """{vertex: depth} of the band's tree at tow; the root (a receiver, no parent row) at 0."""
    tree = forest.tree((system, band), tow)
    if tree is None:
        return {}
    dep = {}
    for child, e in tree.nodes.items():
        dep[child] = e.depth
        dep.setdefault(e.r1, 0)
    return dep


def arc_ring(dep, sta, sat):
    a, b = dep.get(sta), dep.get(sat)
    return None if a is None or b is None else max(a, b)


def build(run, fixture, tow, rings=None, systems=("G",)):
    edges = IFC.read_edges(run, systems)
    chords = IFC.read_chords(run, systems)
    forest = IFC.Forest(edges)
    truth = IFC.Truth(fixture, run)
    tow = round(float(tow), 3)
    if tow not in forest.index:
        raise SystemExit("TOW %.3f is not an epoch of the edge trace" % tow)
    rows, why = [], Counter()
    arcs = set()
    for system in systems:
        for band in BANDS:
            tree = forest.tree((system, band), tow)
            if tree is None:
                continue
            for e in tree.nodes.values():
                arcs.add((system, e.sta, e.sat))
    for c in chords:
        if c.tow == tow:
            arcs.add((c.system, c.sta, c.sat))
    for system, sta, sat in sorted(arcs):
        for band in BANDS:
            dep = node_depths(forest, system, band, tow)
            v, w = IFC.frame_integer(forest, truth, system, band, sta, sat, tow)
            if v is None:
                why[w] += 1
                continue
            role = "tree" if w == "tree edge" else "chord"
            ring = arc_ring(dep, sta, sat)
            if role == "chord" and rings is not None and ring not in rings:
                why["chord outside the rings asked for"] += 1
                continue
            rows.append((sta, sat, band, int(v), role, ring))
    return rows, why


def write(rows, path):
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w", newline="") as fh:
        w = csv.writer(fh, lineterminator="\n")
        w.writerow(["station", "sat", "signal", "frame_int", "role", "ring"])
        for r in rows:
            w.writerow(r)


def selftest():
    ok = True

    def chk(c, msg):
        nonlocal ok
        print(("PASS " if c else "FAIL ") + msg)
        ok &= bool(c)

    dep = {"R0": 0, "G01": 1, "R2": 2, "G03": 3}
    chk(arc_ring(dep, "R2", "G01") == 2 and arc_ring(dep, "R2", "G03") == 3 and arc_ring(dep, "R0", "G03") == 3,
        "an arc's ring is the larger depth of its two vertices")
    chk(arc_ring(dep, "R9", "G01") is None, "an arc with a vertex off the tree has no ring")
    return ok


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("run", nargs="?")
    ap.add_argument("fixture", nargs="?")
    ap.add_argument("--tow", type=float)
    ap.add_argument("--out")
    ap.add_argument("--rings", default=None, help="comma list of the chord rings to write")
    ap.add_argument("--all", action="store_true", help="write the chords of every ring")
    ap.add_argument("--systems", default="G")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        sys.exit(0 if selftest() else 1)
    if not a.all and not a.rings:
        raise SystemExit("name the chord rings (--rings 2,3) or --all")
    rings = None if a.all else {int(x) for x in a.rings.split(",")}
    rows, why = build(os.path.abspath(a.run), os.path.abspath(a.fixture), a.tow, rings, tuple(a.systems.split(",")))
    write(rows, a.out)
    n_tree = sum(1 for r in rows if r[4] == "tree")
    by_ring = Counter(r[5] for r in rows if r[4] == "chord")
    print("%s: %d tree links, %d chords (by ring %s); skipped %s" % (
        a.out, n_tree, len(rows) - n_tree, dict(sorted(by_ring.items())), dict(why) or "nothing"))


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Card NRF stages N3b and O1: the audit of two runs' integers against each other, without truth.

    py -3.14 scripts/nrf_two_run_audit.py <run A> <run B> [--states held,decided,would_hold] [--json out.json]
    py -3.14 scripts/nrf_two_run_audit.py --selftest

At every epoch common to both runs and on each band (constellation and signal), the links whose integers both runs
know are compared: a ring-fix link in one of --states (logs/network_ring_fix.csv: its n1 on the first signal, n2 on
the second) or a tree link of the chain with its integer pin (logs/network_chain_edges.csv, target_cyc).  The two
frames differ by one potential per receiver and one per satellite, so on the graph of common links the difference
D = N_A - N_B must equal x_receiver - y_satellite.  A breadth-first walk from one vertex of each component assigns
the potentials over a spanning tree of the common links and checks every other link: the checks are the independent
closed loops (common links - vertices + components), and a failing check is a loop whose integers the runs disagree
on.  An error both runs share passes (the audit's known limit).

Two runs with different starts differ by more than a frame: under the accumulated wind-up convention each run gives an
arc the wind-up branch floor(wu(t0) + 0.5) at its own start of that arc, so an arc older than the later start carries
another integer in each run (the same on both bands of a link, as a wrong N1 with a right wide lane would).  --windup
removes each run's branch (simulation only, from the fixture's truth); --born-after keeps only the arcs both runs start
together, which needs no truth.

Printed per band: epochs, common links by kind (both ring-fix links, ring-fix in A and tree in B, tree in A and ring-fix
in B, both tree links), checks, failing; and the first failing loops (epoch, band, the closing link and its D against
the potentials).  A run directory is <RAPID_RUNS_ROOT>/_rap_<tag> for a bare tag (default
D:/GnssProcessorSupport/runs_nom).
"""
import argparse
import collections
import csv
import json
import math
import os
import sys

RUNS = os.environ.get("RAPID_RUNS_ROOT") or "D:/GnssProcessorSupport/runs_nom"


def resolve(run):
    return os.path.abspath(run) if os.path.isdir(run) else os.path.join(RUNS, "_rap_" + run)


def read_run(run, states):
    """{tow: {band: {(station, sat): (integer, kind)}}}, kind "rf" (a ring-fix link) or "tree" (a tree pin)."""
    out = collections.defaultdict(lambda: collections.defaultdict(dict))
    logs = os.path.join(run, "logs")
    p = os.path.join(logs, "network_ring_fix.csv")
    if os.path.exists(p):
        with open(p, newline="") as fh:
            for r in csv.DictReader(fh):
                if r["state"] not in states or r["n1"] == "" or r["n2"] == "":
                    continue
                tow = round(float(r["tow"]), 3)
                sysl = r["sat"][:1]
                out[tow][sysl + "|" + r["sig1"]][(r["station"], r["sat"])] = (int(r["n1"]), "rf")
                out[tow][sysl + "|" + r["sig2"]][(r["station"], r["sat"])] = (int(r["n2"]), "rf")
    with open(os.path.join(logs, "network_chain_edges.csv"), newline="") as fh:
        for r in csv.DictReader(fh):
            t = r["target_cyc"].strip()
            if not t:
                continue
            v = float(t)
            if abs(v - round(v)) > 1e-6:
                continue
            tow = round(float(r["tow"]), 3)
            band = r["system"] + "|" + r["band"]
            key = (r["edge_sta"], r["edge_sat"])
            if key not in out[tow][band]:   # a ring-fix row and a tree row of one link: the tree pin is the integer
                out[tow][band][key] = (int(round(v)), "tree")
            else:
                out[tow][band][key] = (int(round(v)), "tree")
    return out


ARC_GAP_S = 300.0   # the producer's arc rule: a gap longer than this starts a new arc (and a new wind-up branch)


def arc_starts(run):
    """{(station, sat): [segment start tows]} from <run>/logs/network_slip_raw.csv (every tracked arc each epoch)."""
    tows = collections.defaultdict(list)
    with open(os.path.join(run, "logs", "network_slip_raw.csv"), newline="") as fh:
        for r in csv.DictReader(fh):
            tows[(r["station"], r["sat"])].append(round(float(r["tow"]), 3))
    out = {}
    for key, ts in tows.items():
        ts = sorted(set(ts))
        starts = [ts[0]]
        for prev, t in zip(ts, ts[1:]):
            if t - prev > ARC_GAP_S:
                starts.append(t)
        out[key] = starts
    return out


def arc_start_at(starts, key, tow):
    """The start of the arc of `key` that covers `tow` (None when the arc is not tracked then)."""
    s = starts.get(key)
    if not s:
        return None
    best = None
    for t0 in s:
        if t0 <= tow + 1e-6:
            best = t0
    return best


class WindupTruth:
    """Simulation only: the producer's wind-up branch of an arc, floor(wu(t0) + 0.5) at the arc's start (the
    convention of the ring fix's truth model), from <fixture>/<station>/truth_windup.csv."""

    def __init__(self, fixture):
        self.fixture = fixture
        self.cache = {}

    def series(self, station):
        if station not in self.cache:
            d = collections.defaultdict(dict)
            with open(os.path.join(self.fixture, station, "truth_windup.csv"), newline="") as fh:
                for r in csv.DictReader(fh):
                    d[r["satellite"]][round(float(r["tow_s"]), 3)] = float(r["windup_cycles"])
            self.cache[station] = d
        return self.cache[station]

    def branch(self, station, sat, t0):
        w = self.series(station).get(sat, {}).get(round(t0, 3))
        return None if w is None else int(math.floor(w + 0.5))


def check_epoch(a, b):
    """(checks, failures, kinds) for one band at one epoch: a and b map (station, sat) -> (integer, kind)."""
    common = [k for k in a if k in b]
    kinds = collections.Counter((a[k][1], b[k][1]) for k in common)
    adj = collections.defaultdict(list)
    for (sta, sat) in common:
        d = a[(sta, sat)][0] - b[(sta, sat)][0]
        adj["R:" + sta].append(("S:" + sat, d, (sta, sat)))
        adj["S:" + sat].append(("R:" + sta, -d, (sta, sat)))
    pot, used, checks, fails = {}, set(), 0, []
    for start in adj:
        if start in pot:
            continue
        pot[start] = 0
        queue = collections.deque([start])
        while queue:
            v = queue.popleft()
            for w, d, link in adj[v]:
                # the edge v -> w carries pot[v] - pot[w] = d (receiver minus satellite on a receiver vertex)
                if w not in pot:
                    pot[w] = pot[v] - d
                    used.add(link)
                    queue.append(w)
                elif link not in used:
                    used.add(link)
                    checks += 1
                    if pot[v] - pot[w] != d:
                        fails.append((link, d, pot[v] - pot[w]))
    return checks, fails, kinds


def audit(run_a, run_b, states, windup_fixture=None, born_after=None):
    A, B = read_run(run_a, states), read_run(run_b, states)
    starts_a = starts_b = None
    wt = WindupTruth(windup_fixture) if windup_fixture else None
    if wt is not None or born_after is not None:
        starts_a, starts_b = arc_starts(run_a), arc_starts(run_b)
    per_band = collections.defaultdict(lambda: {"epochs": 0, "checks": 0, "failing": 0, "kinds": collections.Counter(),
                                                "dropped": 0})
    failures = []
    for tow in sorted(set(A) & set(B)):
        for band in sorted(set(A[tow]) & set(B[tow])):
            a_links, b_links = A[tow][band], B[tow][band]
            if starts_a is not None:
                a2, b2 = {}, {}
                for key in set(a_links) & set(b_links):
                    sa, sb = arc_start_at(starts_a, key, tow), arc_start_at(starts_b, key, tow)
                    if sa is None or sb is None:
                        per_band[band]["dropped"] += 1
                        continue
                    if born_after is not None and (sa < born_after - 1e-6 or sb < born_after - 1e-6):
                        per_band[band]["dropped"] += 1
                        continue
                    na, nb = a_links[key][0], b_links[key][0]
                    if wt is not None:
                        ka, kb = wt.branch(key[0], key[1], sa), wt.branch(key[0], key[1], sb)
                        if ka is None or kb is None:
                            per_band[band]["dropped"] += 1
                            continue
                        # the producer's integer of an arc carries its branch: remove each run's own
                        na, nb = na - ka, nb - kb
                    a2[key], b2[key] = (na, a_links[key][1]), (nb, b_links[key][1])
                a_links, b_links = a2, b2
            checks, fails, kinds = check_epoch(a_links, b_links)
            pb = per_band[band]
            pb["epochs"] += 1
            pb["checks"] += checks
            pb["failing"] += len(fails)
            pb["kinds"].update(kinds)
            for link, d, expect in fails:
                failures.append({"tow": tow, "band": band, "station": link[0], "sat": link[1], "d": d,
                                 "potentials": expect})
    return per_band, failures


def selftest():
    # Run B's frame differs by +2 at receiver R1 and -1 at satellite S2; one link of B is off by one.
    a = {("R1", "S1"): (10, "rf"), ("R1", "S2"): (20, "tree"), ("R2", "S1"): (30, "rf"), ("R2", "S2"): (40, "rf")}
    shift = {"R1": 2, "R2": 0, "S1": 0, "S2": -1}
    b = {k: (v[0] - (shift[k[0]] - shift[k[1]]), v[1]) for k, v in a.items()}
    c1, f1, _ = check_epoch(a, b)
    ok = c1 == 1 and not f1
    b2 = dict(b)
    b2[("R2", "S2")] = (b[("R2", "S2")][0] + 1, "rf")
    c2, f2, _ = check_epoch(a, b2)
    ok &= c2 == 1 and len(f2) == 1
    print("selftest:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


def main():
    if "--selftest" in sys.argv:
        return selftest()
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("run_a")
    ap.add_argument("run_b")
    ap.add_argument("--states", default="held,decided,would_hold")
    ap.add_argument("--windup", metavar="FIXTURE", help="simulation only: remove each run's wind-up branch of every "
                    "arc (truth_windup.csv at the run's own start of the arc, from logs/network_slip_raw.csv)")
    ap.add_argument("--born-after", type=float, metavar="TOW", help="compare only arcs that start at or after "
                    "this time of week in both runs (the same wind-up branch in both; usable without truth)")
    ap.add_argument("--json")
    a = ap.parse_args()
    ra, rb = resolve(a.run_a), resolve(a.run_b)
    per_band, failures = audit(ra, rb, set(a.states.split(",")), a.windup, a.born_after)
    print("== two-run audit: %s  vs  %s  (states %s%s%s)" % (ra, rb, a.states,
          ", wind-up branches removed from %s" % a.windup if a.windup else "",
          ", arcs born after TOW %.0f" % a.born_after if a.born_after is not None else ""))
    tot_c = tot_f = 0
    for band, pb in sorted(per_band.items()):
        k = pb["kinds"]
        print("   %-7s epochs %4d  common links: rf-rf %7d  rf-tree %6d  tree-rf %6d  tree-tree %7d   checks %7d  "
              "failing %d  (links dropped %d)" % (band, pb["epochs"], k[("rf", "rf")], k[("rf", "tree")], k[("tree", "rf")],
                              k[("tree", "tree")], pb["checks"], pb["failing"], pb["dropped"]))
        tot_c += pb["checks"]
        tot_f += pb["failing"]
    print("   total checks %d, failing %d" % (tot_c, tot_f))
    for f in failures[:20]:
        print("   FAIL tow %.0f %s %s %s: D %d against the potentials' %d" % (
            f["tow"], f["band"], f["station"], f["sat"], f["d"], f["potentials"]))
    if a.json:
        with open(a.json, "w") as fh:
            json.dump({"run_a": ra, "run_b": rb, "states": a.states,
                       "bands": {b: {"epochs": v["epochs"], "checks": v["checks"], "failing": v["failing"],
                                     "kinds": {"%s-%s" % kk: n for kk, n in v["kinds"].items()}}
                                 for b, v in per_band.items()},
                       "failures": failures}, fh, indent=1)
    return 0 if tot_f == 0 else 1


if __name__ == "__main__":
    sys.exit(main())

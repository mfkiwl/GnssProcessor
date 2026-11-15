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

Printed per band: epochs, common links by kind (both ring-fix links, ring-fix in A and tree in B, tree in A and ring-fix
in B, both tree links), checks, failing; and the first failing loops (epoch, band, the closing link and its D against
the potentials).  A run directory is <RAPID_RUNS_ROOT>/_rap_<tag> for a bare tag (default
D:/GnssProcessorSupport/runs_nom).
"""
import argparse
import collections
import csv
import json
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


def audit(run_a, run_b, states):
    A, B = read_run(run_a, states), read_run(run_b, states)
    per_band = collections.defaultdict(lambda: {"epochs": 0, "checks": 0, "failing": 0, "kinds": collections.Counter()})
    failures = []
    for tow in sorted(set(A) & set(B)):
        for band in sorted(set(A[tow]) & set(B[tow])):
            checks, fails, kinds = check_epoch(A[tow][band], B[tow][band])
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
    ap.add_argument("--json")
    a = ap.parse_args()
    ra, rb = resolve(a.run_a), resolve(a.run_b)
    per_band, failures = audit(ra, rb, set(a.states.split(",")))
    print("== two-run audit: %s  vs  %s  (states %s)" % (ra, rb, a.states))
    tot_c = tot_f = 0
    for band, pb in sorted(per_band.items()):
        k = pb["kinds"]
        print("   %-7s epochs %4d  common links: rf-rf %7d  rf-tree %6d  tree-rf %6d  tree-tree %7d   checks %7d  "
              "failing %d" % (band, pb["epochs"], k[("rf", "rf")], k[("rf", "tree")], k[("tree", "rf")],
                              k[("tree", "tree")], pb["checks"], pb["failing"]))
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

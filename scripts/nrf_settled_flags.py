#!/usr/bin/env python3
"""Card NRF, section 43's design question: which satellite signals could the stream flag as settled, and how often would
such a flag flip?  Read from a run's traces, nothing built.

    py -3.14 scripts/nrf_settled_flags.py <run> [<run> ...] [--from-h 1]

Per pair family (the ring fix's, e.g. E:L1X/L5X) and epoch, two candidate rules for a satellite:
  A  held      the satellite has a held link of the family at the epoch (logs/network_ring_fix.csv, state held), or its
               tree edge on the family's first band entered the tree as a held link (a RINGFIX to_tree row) and has
               stayed a tree edge since
  B  reached   the satellite is reached from the family's datum receiver through held links and such certified tree
               edges only (the root's own component of that graph)
Printed per family from --from-h on: satellite-epochs in the tree, the share flagged under each rule by hour, the
satellites flagged per epoch (p10 and p50), and the flips (0 to 1 or 1 to 0) per satellite-hour.
"""
import argparse
import collections
import csv
import os
import sys

RUNS = os.environ.get("RAPID_RUNS_ROOT") or "D:/GnssProcessorSupport/runs_nom"


def resolve(run):
    return os.path.abspath(run) if os.path.isdir(run) else os.path.join(RUNS, "_rap_" + run)


def pct(v, q):
    v = sorted(v)
    return v[min(len(v) - 1, int(q * (len(v) - 1)))] if v else 0


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("runs", nargs="+")
    ap.add_argument("--from-h", type=float, default=1.0)
    a = ap.parse_args()
    for run in a.runs:
        d = os.path.join(resolve(run), "logs")
        held = collections.defaultdict(set)        # (tow, fam) -> {(station, sat)}
        fams = set()
        with open(os.path.join(d, "network_ring_fix.csv"), newline="") as fh:
            for r in csv.DictReader(fh):
                fam = r["sat"][0] + ":" + r["sig1"] + "/" + r["sig2"]
                fams.add(fam)
                if r["state"] == "held":
                    held[(round(float(r["tow"])), fam)].add((r["station"], r["sat"]))
        to_tree = collections.defaultdict(set)     # tow -> {(station, sat, sig1)}
        with open(os.path.join(d, "network_events.csv"), newline="") as fh:
            for r in csv.DictReader(fh):
                if r["tier"] == "RINGFIX" and r["event"] == "to_tree":
                    sig1 = next((x[5:] for x in r["detail"].split() if x.startswith("sig1=")), "")
                    to_tree[round(float(r["tow"]))].add((r["station"], r["sat"], sig1))
        edges = collections.defaultdict(list)      # (tow, band) -> rows
        tows = []
        with open(os.path.join(d, "network_chain_edges.csv"), newline="") as fh:
            for r in csv.DictReader(fh):
                t = round(float(r["tow"]))
                if not tows or tows[-1] != t:
                    tows.append(t)
                edges[(t, r["band"])].append(r)
        t0 = tows[0]
        for fam in sorted(fams):
            c, sigs = fam.split(":")
            b1 = sigs.split("/")[0]
            cert = {}                               # (station, sat) -> certified tree edge on b1
            prev_flag = {"A": {}, "B": {}}
            flips = {"A": 0, "B": 0}
            sat_ep = 0
            share = collections.defaultdict(lambda: [0, 0, 0])   # hour -> [in tree, A, B]
            nflag = {"A": collections.defaultdict(list), "B": collections.defaultdict(list)}
            for t in tows:
                rows = [r for r in edges.get((t, b1), []) if r["edge_sat"].startswith(c)]
                if not rows:
                    continue
                tree = {(r["edge_sta"], r["edge_sat"]) for r in rows}
                for k in list(cert):
                    if k not in tree:
                        del cert[k]
                for sta, sat, s1 in to_tree.get(t, ()):
                    if s1 == b1 and (sta, sat) in tree:
                        cert[(sta, sat)] = True
                hl = held.get((t, fam), set())
                sats = {r["edge_sat"] for r in rows}
                flag_a = {s: any(x[1] == s for x in hl) or any(k[1] == s for k in cert) for s in sats}
                # B: reached from the datum receiver through held links and certified tree edges.
                adj = collections.defaultdict(set)
                for sta, sat in list(hl) + list(cert):
                    adj["R:" + sta].add("S:" + sat)
                    adj["S:" + sat].add("R:" + sta)
                roots = {"R:" + r["r1"] for r in rows}
                seen, stack = set(roots), list(roots)
                while stack:
                    v = stack.pop()
                    for w in adj[v]:
                        if w not in seen:
                            seen.add(w)
                            stack.append(w)
                flag_b = {s: ("S:" + s) in seen for s in sats}
                if t < t0 + 3600.0 * a.from_h:
                    prev_flag = {"A": flag_a, "B": flag_b}
                    continue
                h = int((t - t0) // 3600) + 1
                for s in sats:
                    share[h][0] += 1
                    share[h][1] += flag_a[s]
                    share[h][2] += flag_b[s]
                    sat_ep += 1
                    for k, f in (("A", flag_a), ("B", flag_b)):
                        if s in prev_flag[k] and prev_flag[k][s] != f[s]:
                            flips[k] += 1
                nflag["A"][h].append(sum(flag_a.values()))
                nflag["B"][h].append(sum(flag_b.values()))
                prev_flag = {"A": flag_a, "B": flag_b}
            hours = sat_ep * 30.0 / 3600.0
            if not hours:
                continue
            print("== %s %s (from hour %g): %.0f satellite-hours in the tree" % (run, fam, a.from_h + 1, hours))
            for h in sorted(share):
                n, fa, fb = share[h]
                print("   hour %d: flagged A %.0f %%, B %.0f %%; satellites flagged per epoch A p10 %d p50 %d, B p10 %d p50 %d"
                      % (h, 100.0 * fa / n, 100.0 * fb / n, pct(nflag["A"][h], 0.1), pct(nflag["A"][h], 0.5),
                         pct(nflag["B"][h], 0.1), pct(nflag["B"][h], 0.5)))
            print("   flips per satellite-hour: A %.2f, B %.2f" % (flips["A"] / hours, flips["B"] / hours))
    return 0


if __name__ == "__main__":
    sys.exit(main())

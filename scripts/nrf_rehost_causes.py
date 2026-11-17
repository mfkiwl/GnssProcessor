#!/usr/bin/env python3
"""Card NRF, remedy (a): every chain re-host of a run, why its old edge went, and what the re-host did with the moved
side's carries.

    py -3.14 scripts/nrf_rehost_causes.py <run> [<run> ...] [--list N] [--held-only]

A re-host is a tree edge whose child had a parent at the previous epoch on the band and whose arc was not a tree edge
then (row RehostUncertified or RehostCertified of logs/network_chain_edges.csv).  Kept: the edge's step is known (the
rehost row did not release it: network.ring_fix.rehost_keep_carry on a held link); released: unknown, with the
cut_release row of logs/network_events.csv.  Held: a RINGFIX hold of the new edge's link stands before the epoch.

The old edge is the child's edge at the previous epoch, (old parent, child).  Its arc at the re-host's epoch is classed:
  in tree     still a tree edge of the band (re-arranged, flipped or not): nothing happened to it
  slip        tracked, with a slip or jump event on that receiver and satellite at the epoch (the free-epoch latch)
  tracked     tracked, no slip or jump event: re-arranged by the walk (a held link taken first, a root move)
  gap         not tracked at the epoch, tracked again later in the run
  set         not tracked at the epoch and not again in the run
and the receiver of the old edge: whether every arc it had at the previous epoch carries a slip or jump event at the
re-host's epoch or is missing then (a receiver-wide event).

Printed per run: re-hosts by family, kept or released, held or not, and old-edge class; the kept re-hosts' steps
(pinmove_m) and re-targets; --list prints the kept ones.
"""
import argparse
import collections
import csv
import os
import sys

RUNS = os.environ.get("RAPID_RUNS_ROOT") or "D:/GnssProcessorSupport/runs_nom"
SLIP_EVENTS = {"gf_jump", "if_td", "if_td_flag", "mw_jump", "lli", "slip", "sig_resume", "slip_latch", "gf_arc_jump",
               "common_band", "block_slip", "jump"}


def resolve(run):
    return os.path.abspath(run) if os.path.isdir(run) else os.path.join(RUNS, "_rap_" + run)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("runs", nargs="+")
    ap.add_argument("--list", type=int, default=0)
    ap.add_argument("--held-only", action="store_true")
    a = ap.parse_args()
    for run in a.runs:
        d = os.path.join(resolve(run), "logs")
        edges = collections.defaultdict(dict)   # tow -> {(band, child): row}
        tows = []
        with open(os.path.join(d, "network_chain_edges.csv"), newline="") as fh:
            for r in csv.DictReader(fh):
                t = round(float(r["tow"]))
                if not tows or tows[-1] != t:
                    tows.append(t)
                edges[t][(r["band"], r["child"])] = r
        tracked = collections.defaultdict(set)   # (station, sat) -> tows
        with open(os.path.join(d, "network_ionosphere.csv"), newline="") as fh:
            for r in csv.DictReader(fh):
                tracked[(r["station"], r["sat"])].add(round(float(r["tow"])))
        slips, holds, cuts = collections.defaultdict(set), collections.defaultdict(list), collections.defaultdict(list)
        with open(os.path.join(d, "network_events.csv"), newline="") as fh:
            for r in csv.DictReader(fh):
                t = round(float(r["tow"]))
                ev, sat, sta = r["event"], r["sat"], r["station"]
                if ev in SLIP_EVENTS or r["tier"].startswith("T1") or (r["tier"].startswith("T0") and ev != "common_band"):
                    slips[t].add((sta, sat))
                elif r["tier"] == "RINGFIX" and ev == "hold":
                    holds[(sta, sat)].append(t)
                elif r["tier"] == "CHAIN" and ev == "cut_release":
                    cuts[t].append(r)
        idx = {t: i for i, t in enumerate(tows)}
        out = []
        for t in tows:
            i = idx[t]
            if i == 0:
                continue
            prev = edges[tows[i - 1]]
            for (band, child), r in edges[t].items():
                if not r["row"].startswith("Rehost"):
                    continue
                old = prev.get((band, child))
                if old is None:
                    continue
                o_sta, o_sat = old["edge_sta"], old["edge_sat"]
                n_sta, n_sat = r["edge_sta"], r["edge_sat"]
                in_tree = any(e["edge_sta"] == o_sta and e["edge_sat"] == o_sat for (b2, _), e in edges[t].items()
                              if b2 == band)
                trk = tracked.get((o_sta, o_sat), set())
                if in_tree:
                    cls = "in tree"
                elif t in trk:
                    cls = "slip" if (o_sta, o_sat) in slips[t] else "tracked"
                elif any(x > t for x in trk):
                    cls = "gap"
                else:
                    cls = "set"
                # Receiver-wide: every arc of the old edge's receiver at the previous epoch slipped or is missing now.
                arcs = [s for (st, s), ts in tracked.items() if st == o_sta and tows[i - 1] in ts]
                rx_wide = bool(arcs) and all((t not in tracked[(o_sta, s)]) or ((o_sta, s) in slips[t]) for s in arcs)
                held = any(h < t for h in holds.get((n_sta, n_sat), []))
                kept = r["known"] == "1"
                fam = r["system"] + "|" + band
                out.append((t, fam, child, o_sta, o_sat, n_sta, n_sat, cls, rx_wide, held, kept,
                            float(r["pinmove_m"] or 0.0), r["target_cyc"]))
        print("== %s: %d re-hosts" % (run, len(out)))
        tab = collections.Counter((x[1], "kept" if x[10] else "released", "held" if x[9] else "not held", x[7]) for x in out)
        for k in sorted(tab):
            if a.held_only and k[2] != "held":
                continue
            print("   %-8s %-8s %-8s old edge %-8s %d" % (k + (tab[k],)))
        kept = [x for x in out if x[10]]
        steps = [x for x in kept if abs(x[11]) > 1e-9]
        print("   kept %d (receiver-wide event at the old edge's receiver: %d); with a non-zero step %d%s"
              % (len(kept), sum(1 for x in kept if x[8]), len(steps),
                 (": " + ", ".join("TOW %d %s-%s %+.4f m" % (x[0], x[5], x[6], x[11]) for x in steps[:10])) if steps else ""))
        for x in kept[:a.list]:
            print("      TOW %d %s child %s: old %s-%s (%s%s) new %s-%s target %s" % (
                x[0], x[1], x[2], x[3], x[4], x[7], ", receiver-wide" if x[8] else "", x[5], x[6], x[12]))
    return 0


if __name__ == "__main__":
    sys.exit(main())

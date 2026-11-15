#!/usr/bin/env python3
"""Card NRF stage G0: what opens the ring fix's event window on a link (a ring-fix run's traces, no truth needed).

    py -3.14 scripts/nrf_window_causes.py <run dir or tag> [--json out.json]

The window test of the decision (ringFixDecideStep) reads only the link's own state: both carried entries present
and not latched, their re-level stamps, the link a chord for the window, no tree tenure and no release within it.
An episode is a run of consecutive epochs on which a link is refused for the window; its cause is read at its first
epoch t from the traces, in this order (the first that applies):
  left the tree the link has no chord row at t - 30 s and was a tree edge on either band then
                (logs/network_chain_edges.csv)
  chord start   the link has no chord row at t - 30 s otherwise (its first row, or back after a gap)
  own release   a RINGFIX release of the link at t - 30 s or t
  own arc event an event on the link's arc at t - 30 s or t from the slip tiers (T0 to T2), SIGNAL or RAIM with
                action refloat, shifted, shifted_fresh, degrade or reentry
  station event the link's receiver dropped from or readmitted to the solve (TOPOLOGY) at t - 30 s or t
  upstream cut  a CHAIN cut_release at t - 30 s or t on either band whose moved side (the subtree of its root
                vertex in the previous epoch's tree) holds the link's receiver or satellite; split by whether a
                held-first re-attachment of known step 0 took that moved side at that epoch (RINGFIX reattach)
  other         none of these (a re-level or a carry re-birth from elsewhere)
Printed per pair family and ring: chord link-epochs, window link-epochs, episodes, episodes per link-hour, and the
episodes and window link-epochs by cause.
"""
import argparse
import bisect
import collections
import csv
import json
import os
import re
import sys

RUNS = os.environ.get("RAPID_RUNS_ROOT") or "D:/GnssProcessorSupport/runs_nom"
CAUSES = ("left the tree", "chord start", "own release", "own arc event", "station event", "upstream cut, held step 0",
          "upstream cut, other", "other")


def resolve(run):
    return os.path.abspath(run) if os.path.isdir(run) else os.path.join(RUNS, "_rap_" + run)


def fields(text):
    return dict(m.groups() for m in re.finditer(r"(\w+)=(\S+)", text or ""))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("run")
    ap.add_argument("--json")
    a = ap.parse_args()
    logs = os.path.join(resolve(a.run), "logs")
    # Chord rows per link (family = system and the two signals).
    rows = collections.defaultdict(list)
    fams = set()
    with open(os.path.join(logs, "network_ring_fix.csv"), newline="") as fh:
        for r in csv.DictReader(fh):
            fam = (r["sat"][:1], r["sig1"], r["sig2"])
            fams.add(fam)
            rows[(r["station"], r["sat"], fam)].append(
                (round(float(r["tow"]), 3), r["ring"], r["state"] == "refused" and r["refused"] == "window"))
    bands = {(f[0], f[1]) for f in fams} | {(f[0], f[2]) for f in fams}
    # Trees: per (tow, system, band) the parent of each vertex, and the tree edges as (station, sat).
    parent = collections.defaultdict(dict)
    tree_edges = collections.defaultdict(set)
    with open(os.path.join(logs, "network_chain_edges.csv"), newline="") as fh:
        for r in csv.DictReader(fh):
            key = (round(float(r["tow"]), 3), r["system"], r["band"])
            if (r["system"], r["band"]) not in bands:
                continue
            parent[key][r["child"]] = r["parent"]
            tree_edges[key].add((r["edge_sta"], r["edge_sat"]))
    # Events.
    releases, slips, reattach = set(), set(), collections.defaultdict(list)
    station_ev = set()
    cuts = collections.defaultdict(list)   # (tow, system, band) -> [root]
    with open(os.path.join(logs, "network_events.csv"), newline="") as fh:
        for r in csv.DictReader(fh):
            t = round(float(r["tow"]), 3)
            tier, ev, act = r["tier"], r["event"], r["action"]
            if tier == "RINGFIX" and ev == "release":
                releases.add((t, r["station"], r["sat"]))
            elif tier == "RINGFIX" and ev == "reattach":
                f = fields(r["detail"])
                steps = dict(s.split(":") for s in re.findall(r"(L\w+:-?\d+)", r["detail"]))
                reattach[t].append((r["station"], r["sat"], steps))
            elif tier == "CHAIN" and ev == "cut_release":
                f = fields(r["detail"])
                sysl = r["sat"][:1] if r["sat"] else ""
                cuts[(t, sysl, f.get("sig", ""))].append(f.get("root", ""))
            elif ((tier[:2] in ("T0", "T1", "T2") or tier in ("SIGNAL", "RAIM"))
                  and act in ("refloat", "shifted", "shifted_fresh", "degrade", "reentry")):
                slips.add((t, r["station"], r["sat"]))
            elif tier == "TOPOLOGY" and ev in ("sta_pd_dropped", "sta_readmitted"):
                station_ev.add((t, r["station"]))

    def subtree(key, root):
        par = parent.get(key)
        if not par:
            return {root}
        kids = collections.defaultdict(list)
        for c, p in par.items():
            kids[p].append(c)
        out, todo = {root}, [root]
        while todo:
            v = todo.pop()
            for c in kids.get(v, ()):
                if c not in out:
                    out.add(c)
                    todo.append(c)
        return out

    sub_cache = {}

    def upstream(t, sysl, sigs, sta, sat):
        """'held' or 'other' when a cut release at t or t - 30 moved the link's receiver or satellite, else None."""
        found = None
        for tc in (t, round(t - 30.0, 3)):
            for sig in sigs:
                for root in cuts.get((tc, sysl, sig), ()):
                    ck = (round(tc - 30.0, 3), sysl, sig, root)
                    if ck not in sub_cache:
                        sub_cache[ck] = subtree((round(tc - 30.0, 3), sysl, sig), root)
                    side = sub_cache[ck]
                    if sta in side or sat in side:
                        held = any((root in (rs, rv)) and steps.get(sig) == "0" for rs, rv, steps in reattach.get(tc, ()))
                        if held:
                            return "held"
                        found = "other"
        return found

    per = collections.defaultdict(lambda: {"rows": 0, "window": 0, "episodes": 0,
                                           "ep_cause": collections.Counter(), "win_cause": collections.Counter()})
    for (sta, sat, fam), v in rows.items():
        v.sort()
        tows = [x[0] for x in v]
        sysl, sigs = fam[0], (fam[1], fam[2])
        i = 0
        while i < len(v):
            t, ring, win = v[i]
            pk = (fam, ring)
            per[pk]["rows"] += 1
            if not win:
                i += 1
                continue
            # an episode: consecutive window rows 30 s apart
            j = i
            while j + 1 < len(v) and v[j + 1][2] and v[j + 1][0] - v[j][0] <= 30.0 + 1e-6:
                j += 1
            n = j - i + 1
            tp = round(t - 30.0, 3)
            prev_ok = i > 0 and abs(v[i - 1][0] - tp) < 1e-6
            if not prev_ok and (i == 0 or bisect.bisect_left(tows, tp) == bisect.bisect_right(tows, tp)):
                cause = ("left the tree" if any((sta, sat) in tree_edges.get((tp, sysl, s), ()) for s in sigs)
                         else "chord start")
            elif (tp, sta, sat) in releases or (t, sta, sat) in releases:
                cause = "own release"
            elif (tp, sta, sat) in slips or (t, sta, sat) in slips:
                cause = "own arc event"
            elif (tp, sta) in station_ev or (t, sta) in station_ev:
                cause = "station event"
            else:
                u = upstream(t, sysl, sigs, sta, sat)
                cause = ("upstream cut, held step 0" if u == "held" else
                         "upstream cut, other" if u == "other" else "other")
            per[pk]["episodes"] += 1
            per[pk]["ep_cause"][cause] += 1
            per[pk]["win_cause"][cause] += n
            per[pk]["window"] += n
            # the remaining rows of the episode count as rows too
            for k in range(i + 1, j + 1):
                per[(fam, v[k][1])]["rows"] += 1
            i = j + 1
    res = {}
    print("== %s" % resolve(a.run))
    for fam in sorted({f for f, _ in per}):
        famname = "%s:%s/%s" % fam
        rings = sorted({r for f, r in per if f == fam}, key=lambda x: int(x) if x.lstrip("-").isdigit() else 99)
        print("  %s" % famname)
        tot = collections.Counter()
        for ring in rings:
            p = per[(fam, ring)]
            link_h = p["rows"] * 30.0 / 3600.0
            res["%s ring %s" % (famname, ring)] = {"rows": p["rows"], "window": p["window"], "episodes": p["episodes"],
                                                   "episodes_per_link_hour": p["episodes"] / link_h if link_h else None,
                                                   "episodes_by_cause": dict(p["ep_cause"]),
                                                   "window_by_cause": dict(p["win_cause"])}
            for c in CAUSES:
                tot[c] += p["ep_cause"][c]
            print("    ring %-3s rows %6d window %5.1f %% episodes %4d (%.2f per link-hour): %s" % (
                ring, p["rows"], 100.0 * p["window"] / p["rows"] if p["rows"] else 0.0, p["episodes"],
                p["episodes"] / link_h if link_h else 0.0,
                ", ".join("%s %d" % (c, p["ep_cause"][c]) for c in CAUSES if p["ep_cause"][c])))
        print("    all rings, episodes by cause: " + ", ".join("%s %d" % (c, tot[c]) for c in CAUSES if tot[c]))
    if a.json:
        with open(a.json, "w") as fh:
            json.dump(res, fh, indent=1)
    return 0


if __name__ == "__main__":
    sys.exit(main())

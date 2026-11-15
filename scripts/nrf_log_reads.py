#!/usr/bin/env python3
"""Card NRF stage O1: the reads of a ring-fix run under the log rule (network.ring_fix.rule "log") from its trace.

    py -3.14 scripts/nrf_log_reads.py <run dir or tag> [--json out.json]

From <run>/logs/network_ring_fix.csv (one row per considered pair-family chord and epoch; state would_hold where the
frozen rule would decide, refused with its cause otherwise):
  by hour     links with a would-be decision and would-be link-epochs, from the run's first epoch (the first row of
              logs/network_chain_edges.csv)
  by ring     would-be link-epochs and links by the ring of the first would-be decision
  birth       minutes from a link's first chord row to its first would-be decision (p50, p90, n; links never decided);
              and from the start of the arc that holds that decision (logs/network_slip_raw.csv, a gap of more than
              300 s starts an arc), for all links and for arcs that start after the run's first epoch
  readings    frac_wl, frac_if and sigma_if at each link's first would-be decision (p50, p90, max)
  refusals    link-epochs refused, by cause; links refused by the wide-lane bound (cause wl_fraction: every other test
              passed, persistence included) at least once, and of them never decided
A run directory is <RAPID_RUNS_ROOT>/_rap_<tag> for a bare tag (default D:/GnssProcessorSupport/runs_nom).
"""
import argparse
import collections
import csv
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from nrf_two_run_audit import arc_start_at, arc_starts  # noqa: E402  (the producer's arc rule, one copy)

RUNS = os.environ.get("RAPID_RUNS_ROOT") or "D:/GnssProcessorSupport/runs_nom"


def resolve(run):
    return os.path.abspath(run) if os.path.isdir(run) else os.path.join(RUNS, "_rap_" + run)


def pct(v, q):
    v = sorted(v)
    return v[min(len(v) - 1, int(q * len(v)))] if v else float("nan")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("run")
    ap.add_argument("--json")
    a = ap.parse_args()
    run = resolve(a.run)
    logs = os.path.join(run, "logs")
    with open(os.path.join(logs, "network_chain_edges.csv"), newline="") as fh:
        t0 = float(next(csv.DictReader(fh))["tow"])
    first_row, first_wh = {}, {}
    hour_links, hour_eps = collections.defaultdict(set), collections.Counter()
    ring_eps = collections.Counter()
    refused = collections.Counter()
    wl_links = set()
    rows_n = 0
    with open(os.path.join(logs, "network_ring_fix.csv"), newline="") as fh:
        for r in csv.DictReader(fh):
            rows_n += 1
            key = (r["station"], r["sat"], r["sig1"], r["sig2"])
            tow = float(r["tow"])
            first_row.setdefault(key, tow)
            if r["state"] == "would_hold":
                h = int((tow - t0) // 3600) + 1
                hour_links[h].add(key)
                hour_eps[h] += 1
                ring_eps[r["ring"]] += 1
                if key not in first_wh:
                    first_wh[key] = (tow, r)
            elif r["state"] == "refused":
                refused[r["refused"]] += 1
                if r["refused"] == "wl_fraction":
                    wl_links.add(key)
    births = [(first_wh[k][0] - first_row[k]) / 60.0 for k in first_wh]
    starts = arc_starts(run)
    run_first = min((s[0] for s in starts.values()), default=t0)
    arc_births, arc_births_in = [], []
    for k, (tow, _) in first_wh.items():
        a0 = arc_start_at(starts, (k[0], k[1]), tow)
        if a0 is None:
            continue
        arc_births.append((tow - a0) / 60.0)
        if a0 > run_first + 1e-6:
            arc_births_in.append((tow - a0) / 60.0)
    ring_links = collections.Counter(first_wh[k][1]["ring"] for k in first_wh)
    readings = {}
    for col in ("frac_wl", "frac_if", "sigma_if"):
        v = [float(first_wh[k][1][col]) for k in first_wh if first_wh[k][1][col] not in ("", None)]
        readings[col] = {"p50": pct(v, 0.5), "p90": pct(v, 0.9), "max": max(v) if v else float("nan"), "n": len(v)}
    res = {"run": run, "rows": rows_n, "links_seen": len(first_row), "links_would": len(first_wh),
           "by_hour": {h: {"links": len(hour_links[h]), "link_epochs": hour_eps[h]} for h in sorted(hour_eps)},
           "by_ring_link_epochs": dict(ring_eps), "by_ring_links": dict(ring_links),
           "birth_to_first_min": {"p50": pct(births, 0.5), "p90": pct(births, 0.9), "n": len(births)},
           "arc_start_to_first_min": {"p50": pct(arc_births, 0.5), "p90": pct(arc_births, 0.9), "n": len(arc_births)},
           "arc_born_in_run_to_first_min": {"p50": pct(arc_births_in, 0.5), "p90": pct(arc_births_in, 0.9),
                                            "n": len(arc_births_in)},
           "readings_at_first": readings, "refused": dict(refused),
           "wl_bound_links": len(wl_links), "wl_bound_links_never_decided": len(wl_links - set(first_wh))}
    print("== %s" % run)
    print("   chord rows %d, links seen %d, links with a would-be decision %d" % (rows_n, len(first_row), len(first_wh)))
    print("   by hour (links, link-epochs): " + "; ".join(
        "h%d %d, %d" % (h, len(hour_links[h]), hour_eps[h]) for h in sorted(hour_eps)))
    print("   by ring of the first would-be decision (links): " + ", ".join(
        "ring %s: %d" % (k, v) for k, v in sorted(ring_links.items(), key=lambda x: int(x[0]) if x[0].lstrip('-').isdigit() else 99)))
    print("   minutes from the first chord row to the first would-be decision: p50 %.1f, p90 %.1f (n %d)" % (
        res["birth_to_first_min"]["p50"], res["birth_to_first_min"]["p90"], len(births)))
    print("   minutes from the arc's start to the first would-be decision: p50 %.1f, p90 %.1f (n %d); arcs that "
          "start after the run's first epoch: p50 %.1f, p90 %.1f (n %d)" % (
              pct(arc_births, 0.5), pct(arc_births, 0.9), len(arc_births),
              pct(arc_births_in, 0.5), pct(arc_births_in, 0.9), len(arc_births_in)))
    for col, d in readings.items():
        print("   %-8s at the first would-be decision: p50 %.3f, p90 %.3f, max %.3f (n %d)" % (
            col, d["p50"], d["p90"], d["max"], d["n"]))
    print("   refused link-epochs by cause: " + ", ".join("%s %d" % kv for kv in sorted(refused.items())))
    print("   links refused by the wide-lane bound at least once: %d (never decided: %d)" % (
        len(wl_links), res["wl_bound_links_never_decided"]))
    if a.json:
        with open(a.json, "w") as fh:
            json.dump(res, fh, indent=1)
    return 0


if __name__ == "__main__":
    sys.exit(main())

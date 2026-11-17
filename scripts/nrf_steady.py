#!/usr/bin/env python3
"""Card NRF stage N2: the steady-state reads of a ring-fix run from its trace.

    py -3.14 scripts/nrf_steady.py <run dir or tag> --cutover-tow T [--json out.json]

From <run>/logs/network_ring_fix.csv (one row per pair-family chord and epoch).  A link's life starts at its first
row at or after the cut-over, or at its first row after a release (a row that is not held after one that was);
it ends at its first held or decided row.  Printed, by ring: the links born after the cut-over, how many were held,
the minutes from birth to hold (median, p90); the share of chord link-epochs held after the cut-over; the held
link-epochs the trace's audit reads wrong after the cut-over.
"""
import argparse
import collections
import csv
import json
import os

RUNS = os.environ.get("RAPID_RUNS_ROOT") or "D:/GnssProcessorSupport/runs_nom"


def pct(v, q):
    v = sorted(v)
    return v[min(len(v) - 1, int(q * len(v)))] if v else float("nan")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("run")
    ap.add_argument("--cutover-tow", type=float, required=True)
    ap.add_argument("--json")
    a = ap.parse_args()
    run = a.run if os.path.isdir(a.run) else os.path.join(RUNS, "_rap_" + a.run)
    rows = collections.defaultdict(list)
    with open(os.path.join(run, "logs", "network_ring_fix.csv"), newline="") as fh:
        for r in csv.DictReader(fh):
            rows[(r["station"], r["sat"])].append(r)
    born, held_n, waits = collections.Counter(), collections.Counter(), collections.defaultdict(list)
    chord_eps = held_eps = wrong_eps = 0
    for key, rs in rows.items():
        rs.sort(key=lambda r: float(r["tow"]))
        birth = None
        prev_held = False
        for r in rs:
            t = float(r["tow"])
            is_held = r["state"] in ("held", "decided")
            if t >= a.cutover_tow:
                chord_eps += 1
                if r["state"] == "held":
                    held_eps += 1
                    if r["audit"] == "wrong":
                        wrong_eps += 1
            if t < a.cutover_tow:
                prev_held = is_held
                continue
            if birth is None and not is_held and (prev_held or r is rs[0] or float(rs[0]["tow"]) >= a.cutover_tow
                                                  or t == a.cutover_tow or True):
                if not prev_held or True:
                    birth = (t, int(r["ring"]) if r["ring"] not in ("", "-1") else -1)
                    born[birth[1]] += 1
            if birth is not None and is_held:
                held_n[birth[1]] += 1
                waits[birth[1]].append((t - birth[0]) / 60.0)
                birth = None
            prev_held = is_held
    res = {"run": run, "cutover_tow": a.cutover_tow, "by_ring": {}, "chord_link_epochs": chord_eps,
           "held_link_epochs": held_eps, "held_share": held_eps / chord_eps if chord_eps else None,
           "wrong_held_link_epochs": wrong_eps}
    print("== %s, after TOW %.0f: chord link-epochs %d, held %d (%.1f %%), wrong held %d" % (
        run, a.cutover_tow, chord_eps, held_eps, 100.0 * held_eps / max(chord_eps, 1), wrong_eps))
    for ring in sorted(born):
        w = waits[ring]
        res["by_ring"][str(ring)] = {"born": born[ring], "held": held_n[ring], "wait_p50_min": pct(w, 0.5),
                                     "wait_p90_min": pct(w, 0.9)}
        print("   ring %2d: lives begun %4d, held %4d, minutes from birth to hold p50 %.1f p90 %.1f" % (
            ring, born[ring], held_n[ring], pct(w, 0.5), pct(w, 0.9)))
    if a.json:
        with open(a.json, "w") as fh:
            json.dump(res, fh, indent=1)


if __name__ == "__main__":
    main()

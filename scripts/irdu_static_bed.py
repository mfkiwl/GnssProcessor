#!/usr/bin/env python3
"""Card IRDU section 11 B: the no-re-seat bed, the arcs of a run that the network tracked through the whole window.

    python scripts/irdu_static_bed.py derive <run> --out config/sim/irdu/irdu_nr_arcs.json
        [--min-elev 15.5] [--drop-arc S43000SIM/G22 ...]
    python scripts/irdu_static_bed.py ops <arcs.json>
    python scripts/irdu_static_bed.py --selftest

`derive` reads <run>/logs/network_pf_rows.csv (network.trace_postfit_rows: one row per station, satellite, signal
and epoch the solve used, with the line of sight's elevation) and keeps an arc (station, GPS satellite) when both
phase signals (L1C, L2W) have a row at every epoch of the run and the arc's lowest elevation is at least --min-elev
(a margin above the network's 15 degree mask, so that a run on the rewritten files keeps the same arcs).  Arcs named
by --drop-arc are removed as well (the arc of a scripted slip).  The output lists, per station, the satellites kept
and the `strip` op of scripts/rapid_arm.py that blanks every other GPS satellite of that station for the whole run
(the op leaves the header alone; a satellite absent from a file is a no-op).  On such a bed no arc rises, sets,
returns or slips during the window, so the chain's tree has no cause to change after its first epoch; whether it
does not is read from the run's edge trace (card IRDU section 11, gate G-B0), not assumed.

`ops` prints the ops of an arcs file, one per line (scripts/ird_make_arms.py reads the same file for its bed).
"""
import argparse
import csv
import json
import os
import sys
from collections import defaultdict

GPS_PRNS = ["G%02d" % i for i in range(1, 33)]
PHASE = ("L1C", "L2W")


def derive(run, min_elev=15.5, drop=()):
    p = os.path.join(run, "logs", "network_pf_rows.csv")
    seen = defaultdict(set)
    elev = defaultdict(lambda: 90.0)
    stations, tows = set(), set()
    with open(p, newline="") as fh:
        for r in csv.DictReader(ln for ln in fh if not ln.startswith("#")):
            stations.add(r["station"])
            if r["kind"] != "phase" or r["signal"] not in PHASE or not r["sat"].startswith("G"):
                continue
            t = round(float(r["tow"]), 3)
            tows.add(t)
            k = (r["station"], r["sat"])
            seen[k].add((t, r["signal"]))
            elev[k] = min(elev[k], float(r["elev_deg"]))
    tows = sorted(tows)
    drop = {tuple(d.split("/")) for d in drop}
    kept = defaultdict(list)
    for k, s in seen.items():
        if k in drop or elev[k] < min_elev:
            continue
        if all((t, sig) in s for t in tows for sig in PHASE):
            kept[k[0]].append(k[1])
    out = {"source_run": run.replace("\\", "/"), "epochs": len(tows), "first_tow": tows[0], "last_tow": tows[-1],
           "min_elev_deg": min_elev, "dropped_arcs": sorted("/".join(d) for d in drop),
           "arcs_seen": len(seen), "arcs_kept": sum(len(v) for v in kept.values()),
           "kept": {st: sorted(kept.get(st, [])) for st in sorted(stations)}}
    out["strip"] = {st: [s for s in GPS_PRNS if s not in out["kept"][st]] for st in sorted(stations)}
    out["satellites_kept"] = sorted({s for v in out["kept"].values() for s in v})
    return out


def ops_of(arcs):
    """The rapid_arm.py --rinex ops of an arcs file: one whole-run strip per station."""
    return ["strip;types=???;stations=%s;sats=%s" % (st, ",".join(sats))
            for st, sats in sorted(arcs["strip"].items()) if sats]


def selftest():
    arcs = {"strip": {"A": ["G01", "G02"], "B": []}}
    ops = ops_of(arcs)
    ok = ops == ["strip;types=???;stations=A;sats=G01,G02"]
    print(("PASS" if ok else "FAIL") + " ops of an arcs file: one whole-run strip per station with satellites to strip")
    return ok


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("action", nargs="?", choices=("derive", "ops"))
    ap.add_argument("path", nargs="?")
    ap.add_argument("--out")
    ap.add_argument("--min-elev", type=float, default=15.5)
    ap.add_argument("--drop-arc", action="append", default=[])
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        sys.exit(0 if selftest() else 1)
    if a.action == "derive":
        res = derive(os.path.abspath(a.path), a.min_elev, a.drop_arc)
        per = sorted(len(v) for v in res["kept"].values())
        print("epochs %d (TOW %.0f to %.0f); arcs seen %d, kept %d; satellites kept %d; per station min %d p50 %d max %d"
              % (res["epochs"], res["first_tow"], res["last_tow"], res["arcs_seen"], res["arcs_kept"],
                 len(res["satellites_kept"]), per[0], per[len(per) // 2], per[-1]))
        if a.out:
            os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
            with open(a.out, "w") as fh:
                json.dump(res, fh, indent=1)
                fh.write("\n")
    elif a.action == "ops":
        for op in ops_of(json.load(open(a.path))):
            print(op)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Card NRF stage O2: the reads of a ring-fix run that holds integers, without truth (observed data).

    py -3.14 scripts/nrf_hold_reads.py <run dir or tag> [--json out.json]

From <run>/logs (network_ring_fix.csv, network_events.csv, network_raim.csv, network_epoch_status.csv,
network_slip_raw.csv) and <run>/stdout.txt:
  held share   held link-epochs over the pair-family chord link-epochs of the trace (state "held"), by hour of the run
               (from its first epoch, the first row of logs/network_chain_edges.csv) and by the row's ring
  decisions    RINGFIX hold events (action decide) by hour and by ring
  releases     RINGFIX release events by cause and by hour; a cause outside the named ones is counted as unnamed;
               every release by the residual monitor listed (time, link, integers, ring, seconds held)
  reattach     RINGFIX reattach events (held-first re-attachments) and the held links they kept
  birth        minutes from the start of the tracking arc (logs/network_slip_raw.csv, a gap of more than 300 s starts
               an arc) to the link's first hold, for all first holds and for arcs that start inside the run; and from
               the chord's first trace row
  run end      the ring fix's run-end lines (the closure decided = released + to tree + held)
  raim, epochs rows of network_raim.csv; epochs by disposition
A run directory is <RAPID_RUNS_ROOT>/_rap_<tag> for a bare tag (default D:/GnssProcessorSupport/runs_nom).
"""
import argparse
import collections
import csv
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from nrf_two_run_audit import arc_start_at, arc_starts  # noqa: E402  (the producer's arc rule, one copy)

RUNS = os.environ.get("RAPID_RUNS_ROOT") or "D:/GnssProcessorSupport/runs_nom"
NAMED = {"slip", "refloat", "gap", "chain", "monitor"}


def resolve(run):
    return os.path.abspath(run) if os.path.isdir(run) else os.path.join(RUNS, "_rap_" + run)


def pct(v, q):
    v = sorted(v)
    return v[min(len(v) - 1, int(q * len(v)))] if v else float("nan")


def detail_fields(text):
    return dict(m.groups() for m in re.finditer(r"(\w+)=(\S+)", text or ""))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("run")
    ap.add_argument("--json")
    a = ap.parse_args()
    run = resolve(a.run)
    logs = os.path.join(run, "logs")
    with open(os.path.join(logs, "network_chain_edges.csv"), newline="") as fh:
        t0 = float(next(csv.DictReader(fh))["tow"])

    def hour(tow):
        return int((tow - t0) // 3600) + 1

    n_h, h_h = collections.Counter(), collections.Counter()
    n_r, h_r = collections.Counter(), collections.Counter()
    first_row = {}
    with open(os.path.join(logs, "network_ring_fix.csv"), newline="") as fh:
        for r in csv.DictReader(fh):
            tow = float(r["tow"])
            key = (r["station"], r["sat"], r["sig1"], r["sig2"])
            first_row.setdefault(key, tow)
            held = r["state"] == "held"
            n_h[hour(tow)] += 1
            h_h[hour(tow)] += held
            n_r[r["ring"]] += 1
            h_r[r["ring"]] += held
    dec_h, dec_r = collections.Counter(), collections.Counter()
    rel_c, rel_h = collections.Counter(), collections.Counter()
    monitor, first_hold = [], {}
    reattach = kept = 0
    with open(os.path.join(logs, "network_events.csv"), newline="") as fh:
        for r in csv.DictReader(fh):
            if r["tier"] != "RINGFIX":
                continue
            tow = float(r["tow"])
            f = detail_fields(r["detail"])
            if r["event"] == "hold" and r["action"] == "decide":
                dec_h[hour(tow)] += 1
                dec_r[f.get("ring", "?")] += 1
                first_hold.setdefault((r["station"], r["sat"], f.get("sig1"), f.get("sig2")), tow)
            elif r["event"] == "release":
                cause = r["action"] if r["action"] in NAMED else "unnamed"
                rel_c[cause] += 1
                rel_h[hour(tow)] += 1
                if cause == "monitor":
                    monitor.append({"tow": tow, "station": r["station"], "sat": r["sat"], "n1": f.get("n1"),
                                    "n2": f.get("n2"), "ring": f.get("ring"), "held_s": f.get("held_s")})
            elif r["event"] == "reattach":
                reattach += 1
                kept += int(f.get("kept", "0"))
    starts = arc_starts(run)
    run_first = min((s[0] for s in starts.values()), default=t0)
    birth_all, birth_in, birth_row = [], [], []
    for key, tow in first_hold.items():
        a0 = arc_start_at(starts, (key[0], key[1]), tow)
        if a0 is not None:
            birth_all.append((tow - a0) / 60.0)
            if a0 > run_first + 1e-6:
                birth_in.append((tow - a0) / 60.0)
        if key in first_row:
            birth_row.append((tow - first_row[key]) / 60.0)
    runend = []
    stdout = os.path.join(run, "stdout.txt")
    if os.path.exists(stdout):
        with open(stdout, encoding="utf-8", errors="replace") as fh:
            runend = [ln.split("| Network", 1)[-1].strip() if "| Network" in ln else ln.split("] ", 3)[-1].strip()
                      for ln in fh if "Network (ring fix" in ln]
    with open(os.path.join(logs, "network_raim.csv"), newline="") as fh:
        raim_rows = sum(1 for _ in csv.DictReader(fh))
    with open(os.path.join(logs, "network_epoch_status.csv"), newline="") as fh:
        disp = collections.Counter(r["disposition"] for r in csv.DictReader(fh))

    def share(h, n, k):
        return round(100.0 * h[k] / n[k], 1) if n[k] else None

    res = {"run": run, "first_tow": t0,
           "held_share_by_hour": {k: share(h_h, n_h, k) for k in sorted(n_h)},
           "held_share_by_ring": {k: share(h_r, n_r, k) for k in sorted(n_r, key=lambda x: int(x) if x.lstrip("-").isdigit() else 99)},
           "chord_link_epochs_by_ring": dict(n_r), "held_link_epochs": sum(h_h.values()),
           "decisions_by_hour": dict(sorted(dec_h.items())), "decisions_by_ring": dict(dec_r),
           "releases_by_cause": dict(rel_c), "releases_by_hour": dict(sorted(rel_h.items())), "monitor": monitor,
           "reattach": reattach, "reattach_kept": kept, "links_held": len(first_hold),
           "birth_arc_min": {"p50": pct(birth_all, 0.5), "p90": pct(birth_all, 0.9), "n": len(birth_all)},
           "birth_arc_in_run_min": {"p50": pct(birth_in, 0.5), "p90": pct(birth_in, 0.9), "n": len(birth_in)},
           "birth_row_min": {"p50": pct(birth_row, 0.5), "p90": pct(birth_row, 0.9), "n": len(birth_row)},
           "raim_rows": raim_rows, "epochs": dict(disp), "run_end": runend}
    print("== %s (first epoch TOW %.0f)" % (run, t0))
    print("   held share by hour (%): " + "; ".join("h%d %s" % (k, v) for k, v in res["held_share_by_hour"].items()))
    print("   held share by ring (%): " + "; ".join("ring %s %s (of %d)" % (k, v, n_r[k])
                                                  for k, v in res["held_share_by_ring"].items()))
    print("   held link-epochs %d; links held %d" % (res["held_link_epochs"], len(first_hold)))
    print("   decisions by hour: %s; by ring: %s" % (dict(sorted(dec_h.items())), dict(sorted(dec_r.items()))))
    print("   releases by cause: %s; by hour: %s" % (dict(rel_c), dict(sorted(rel_h.items()))))
    for m in monitor:
        print("   monitor release: TOW %.0f %s-%s n1 %s n2 %s ring %s held %s s" % (
            m["tow"], m["station"], m["sat"], m["n1"], m["n2"], m["ring"], m["held_s"]))
    print("   re-attachments through held links %d, held links kept %d" % (reattach, kept))
    print("   minutes to the first hold: from the arc's start p50 %.1f p90 %.1f (n %d); arcs starting inside the run "
          "p50 %.1f p90 %.1f (n %d); from the chord's first row p50 %.1f p90 %.1f" % (
              pct(birth_all, 0.5), pct(birth_all, 0.9), len(birth_all), pct(birth_in, 0.5), pct(birth_in, 0.9),
              len(birth_in), pct(birth_row, 0.5), pct(birth_row, 0.9)))
    print("   RAIM rows %d; epochs %s" % (raim_rows, dict(disp)))
    for ln in runend:
        print("   | " + ln[:400])
    if a.json:
        with open(a.json, "w") as fh:
            json.dump(res, fh, indent=1)
    return 0


if __name__ == "__main__":
    sys.exit(main())

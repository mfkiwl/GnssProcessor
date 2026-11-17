#!/usr/bin/env python3
"""Card NRF stage N2b: the reads of a ring-fix run from its traces and its run-end lines.

    py -3.14 scripts/nrf_reads.py <run dir or tag> [<run> ...] [--slip-tow T --slip-link STATION:SAT] [--json out.json]

Per run, from <run>/logs and <run>/stdout.txt:
  held share     the share of pair-family chord link-epochs held (logs/network_ring_fix.csv, state "held"), by 15-min
                 bin from the run's first epoch (the first row of logs/network_chain_edges.csv), and over the last 30 min
  releases       RINGFIX release events by cause (logs/network_events.csv); re-attachments (RINGFIX reattach) and the
                 held links they kept
  run end        the ring fix's run-end lines (stdout.txt): cuts by kind, the truth audit, the log rule, the oracle
  raim           rows of logs/network_raim.csv and of them refloated (column refloated > 0)
  epochs         rows of logs/network_epoch_status.csv by disposition (every epoch emitted: no "withhold")
With --slip-tow and --slip-link (stage N2b-3): the link's trace rows from 2 epochs before the slip to its next hold,
the RINGFIX events of the slip's epoch and the 4 after it, the RAIM rows and refloats in the 10 min after the slip,
the held links released at the slip's epoch and the 4 after it, and the minutes until the link is held again, with
the truth token of that hold (truth=right / truth=WRONG).
A run directory is <RAPID_RUNS_ROOT>/_rap_<tag> when a bare tag is given (default D:/GnssProcessorSupport/runs_nom).
"""
import argparse
import collections
import csv
import json
import os
import re
import sys

RUNS = os.environ.get("RAPID_RUNS_ROOT") or "D:/GnssProcessorSupport/runs_nom"
BIN_S = 900.0


def resolve(run):
    return os.path.abspath(run) if os.path.isdir(run) else os.path.join(RUNS, "_rap_" + run)


def first_tow(logs):
    """The run's first epoch: the first row of the chain's record, else of the epoch status (a run without the chain)."""
    for name in ("network_chain_edges.csv", "network_epoch_status.csv"):
        p = os.path.join(logs, name)
        if os.path.exists(p):
            with open(p, newline="") as fh:
                return float(next(csv.DictReader(fh))["tow"])
    raise SystemExit("%s: no network_chain_edges.csv or network_epoch_status.csv" % logs)


def held_share(logs, t0):
    n, h = collections.Counter(), collections.Counter()
    last_tow = t0
    rows = []
    with open(os.path.join(logs, "network_ring_fix.csv"), newline="") as fh:
        for r in csv.DictReader(fh):
            tow = float(r["tow"])
            last_tow = max(last_tow, tow)
            rows.append((tow, r["state"] == "held"))
    for tow, held in rows:
        b = int((tow - t0) // BIN_S)
        n[b] += 1
        h[b] += held
    late_n = sum(1 for tow, _ in rows if tow > last_tow - 1800.0 + 1e-6)
    late_h = sum(1 for tow, held in rows if held and tow > last_tow - 1800.0 + 1e-6)
    bins = [round(100.0 * h[b] / n[b]) if n[b] else None for b in range(max(n) + 1)] if n else []
    return bins, (100.0 * late_h / late_n if late_n else float("nan"))


def events(logs):
    rel = collections.Counter()
    reattach, kept = 0, 0
    with open(os.path.join(logs, "network_events.csv"), newline="") as fh:
        for r in csv.DictReader(fh):
            if r["tier"] != "RINGFIX":
                continue
            if r["event"] == "release":
                rel[r["action"]] += 1
            elif r["event"] == "reattach":
                reattach += 1
                m = re.search(r"kept=(\d+)", r["detail"])
                kept += int(m.group(1)) if m else 0
    return dict(rel), reattach, kept


def run_end(run):
    out = []
    p = os.path.join(run, "stdout.txt")
    if not os.path.exists(p):
        return out
    with open(p, encoding="utf-8", errors="replace") as fh:
        for ln in fh:
            if "Network (ring fix" in ln and "] [main_log]" in ln and not ln.startswith("[----"):
                out.append(ln.split("[warning] ", 1)[-1].strip())
    return out


def raim(logs):
    p = os.path.join(logs, "network_raim.csv")
    rows = refl = 0
    with open(p, newline="") as fh:
        for r in csv.DictReader(fh):
            rows += 1
            try:
                refl += float(r.get("refloated") or 0) > 0
            except ValueError:
                pass
    return rows, refl


def epochs(logs):
    c = collections.Counter()
    with open(os.path.join(logs, "network_epoch_status.csv"), newline="") as fh:
        for r in csv.DictReader(fh):
            c[r["disposition"]] += 1
    return dict(c)


def slip_reads(logs, t0, tow, station, sat):
    out = {"link": "%s:%s" % (station, sat), "slip_tow": tow}
    trace = []
    with open(os.path.join(logs, "network_ring_fix.csv"), newline="") as fh:
        for r in csv.DictReader(fh):
            if r["station"] == station and r["sat"] == sat and float(r["tow"]) >= tow - 60.0:
                trace.append(r)
    trace.sort(key=lambda r: float(r["tow"]))
    out["state_before"] = [(r["tow"], r["state"]) for r in trace if float(r["tow"]) < tow]
    held_again = None
    for r in trace:
        if float(r["tow"]) > tow + 1e-6 and r["state"] in ("decided",):
            held_again = float(r["tow"])
            break
    ev_slip, rel_window, hold_tok = [], collections.Counter(), None
    with open(os.path.join(logs, "network_events.csv"), newline="") as fh:
        for r in csv.DictReader(fh):
            if r["tier"] != "RINGFIX":
                continue
            t = float(r["tow"])
            if tow - 1e-6 <= t <= tow + 4 * 30.0 + 1e-6:
                if r["event"] == "release":
                    rel_window[r["action"]] += 1
                if r["station"] == station and r["sat"] == sat:
                    ev_slip.append((r["tow"], r["event"], r["action"], r["detail"][:120]))
            if (held_again is not None and r["event"] == "hold" and r["station"] == station and r["sat"] == sat
                    and abs(t - held_again) < 1e-6):
                m = re.search(r"truth=(\w+)", r["detail"])
                hold_tok = m.group(1) if m else "none"
    out["link_events"] = ev_slip
    out["releases_slip_epoch_plus4"] = dict(rel_window)
    out["minutes_to_hold_again"] = None if held_again is None else (held_again - tow) / 60.0
    out["hold_again_truth"] = hold_tok
    rows = refl = 0
    with open(os.path.join(logs, "network_raim.csv"), newline="") as fh:
        for r in csv.DictReader(fh):
            if tow - 1e-6 <= float(r["tow"]) < tow + 600.0 - 1e-6:
                rows += 1
                try:
                    refl += float(r.get("refloated") or 0) > 0
                except ValueError:
                    pass
    out["raim_rows_10min"] = rows
    out["raim_refloat_rows_10min"] = refl
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("runs", nargs="+")
    ap.add_argument("--slip-tow", type=float)
    ap.add_argument("--slip-link")
    ap.add_argument("--json")
    a = ap.parse_args()
    res = []
    for run in a.runs:
        d = resolve(run)
        logs = os.path.join(d, "logs")
        t0 = first_tow(logs)
        r = {"run": d}
        has_rf = os.path.exists(os.path.join(logs, "network_ring_fix.csv"))
        if has_rf:
            r["held_share_15min"], r["held_share_last30"] = held_share(logs, t0)
            r["releases"], r["reattach"], r["reattach_kept"] = events(logs)
        r["raim_rows"], r["raim_refloat_rows"] = raim(logs)
        r["epochs"] = epochs(logs)
        r["run_end"] = run_end(d)
        if a.slip_tow is not None and a.slip_link:
            st, sat = a.slip_link.split(":")
            r["slip"] = slip_reads(logs, t0, a.slip_tow, st, sat) if has_rf else None
            if not has_rf:
                rows = refl = 0
                with open(os.path.join(logs, "network_raim.csv"), newline="") as fh:
                    for x in csv.DictReader(fh):
                        if a.slip_tow - 1e-6 <= float(x["tow"]) < a.slip_tow + 600.0 - 1e-6:
                            rows += 1
                            refl += float(x.get("refloated") or 0) > 0
                r["slip"] = {"raim_rows_10min": rows, "raim_refloat_rows_10min": refl}
        res.append(r)
        print("== %s" % d)
        if has_rf:
            print("  held share by 15 min (%%): %s; last 30 min %.1f %%" % (
                " ".join("-" if v is None else str(v) for v in r["held_share_15min"]), r["held_share_last30"]))
            print("  releases by cause: %s; re-attachments %d, held links kept %d" % (
                r["releases"], r["reattach"], r["reattach_kept"]))
        print("  raim rows %d (refloated %d); epochs %s" % (r["raim_rows"], r["raim_refloat_rows"], r["epochs"]))
        for ln in r["run_end"]:
            print("  | " + ln[:600])
        if "slip" in r and r["slip"]:
            print("  slip: " + json.dumps(r["slip"]))
    if a.json:
        with open(a.json, "w") as fh:
            json.dump(res, fh, indent=1)
    return 0


if __name__ == "__main__":
    sys.exit(main())

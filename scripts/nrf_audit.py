#!/usr/bin/env python3
"""Card NRF: an independent re-grade of a ring-fix run (network.ring_fix) from its own traces.

    py -3.14 scripts/nrf_audit.py <run dir or tag> [--frame FILE] [--json out.json]
    py -3.14 scripts/nrf_audit.py --selftest

Reads <run>/logs/network_ring_fix.csv (one row per pair-family chord and epoch: ring, candidate, state held / decided
/ refused with its cause, the gate's reading, the held or rounded integers, the residual monitor) and the RINGFIX rows
of <run>/logs/network_events.csv (hold and release with its cause), and re-audits every held integer against a
frame-target file (default: the run's own network.ring_fix.audit_frame_file; scripts/irdu_frame_targets.py), without
reading the run's own audit column.  Printed:

  decisions      links decided, by ring; the first decision per ring (minutes from the run's first epoch); decisions
                 wrong against the file
  held           links held at 30, 60, 90 and 120 min, by ring; held link-epochs and wrong held link-epochs; the
                 minute each ring of the file is complete (every chord of the ring held), if ever
  releases       by cause, with the links
  refusals       link-epochs refused, by cause
  would-be       per time, the chords not held whose gate passes (sigma at most 0.10, fraction at most 0.20): the
                 log-only acceptance count on the run's own chord table

Minutes count from the run's first epoch (the first row of logs/network_chain_edges.csv).
A run directory is <RAPID_RUNS_ROOT>/_rap_<tag> when a bare tag is given (default D:/GnssProcessorSupport/runs_nom).
"""
import argparse
import collections
import csv
import json
import math
import os
import sys

RUNS = os.environ.get("RAPID_RUNS_ROOT") or "D:/GnssProcessorSupport/runs_nom"
MAX_SIGMA, MAX_FRAC = 0.10, 0.20
MINUTES = (30, 60, 90, 119.5)


def resolve(run):
    if os.path.isdir(run):
        return os.path.abspath(run)
    return os.path.join(RUNS, "_rap_" + run)


def read_frame(path):
    """(station, sat, signal) -> frame integer; (station, sat) -> (ring, role)."""
    ints, meta = {}, {}
    with open(path, newline="") as fh:
        for r in csv.DictReader(fh):
            ints[(r["station"], r["sat"], r["signal"])] = int(r["frame_int"])
            ring = r.get("ring")
            meta[(r["station"], r["sat"])] = (int(ring) if ring not in (None, "", "None") else None, r["role"])
    return ints, meta


def audit_file_of(run):
    try:
        with open(os.path.join(run, "arm.json")) as fh:
            return json.load(fh)["network"]["ring_fix"]["audit_frame_file"]
    except (OSError, KeyError, ValueError):
        return None


def wrong(ints, sta, sat, sig1, sig2, n1, n2):
    """None when the file lists neither band; else True when a listed band differs."""
    a1, a2 = ints.get((sta, sat, sig1)), ints.get((sta, sat, sig2))
    if a1 is None and a2 is None:
        return None
    return (a1 is not None and a1 != n1) or (a2 is not None and a2 != n2)


def analyse(run, frame_path):
    ints, meta = read_frame(frame_path)
    trace = os.path.join(run, "logs", "network_ring_fix.csv")
    rows_by_t = collections.defaultdict(list)
    with open(trace, newline="") as fh:
        for r in csv.DictReader(fh):
            rows_by_t[float(r["tow"])].append(r)
    tows = sorted(rows_by_t)
    # Minutes count from the run's first epoch: the first row of the chain's edge trace (as
    # scripts/irdu_ring_rounding.py counts them); the chord table starts after the leveling warm-up.
    t0 = tows[0] if tows else 0.0
    edges = os.path.join(run, "logs", "network_chain_edges.csv")
    if os.path.exists(edges):
        with open(edges, newline="") as fh:
            first = next(csv.DictReader(fh), None)
            if first is not None:
                t0 = min(t0, float(first["tow"]))
    res = {"run": run, "frame": frame_path, "epochs": len(tows)}
    decided, decided_wrong, decided_unlisted = collections.Counter(), 0, 0
    first = {}
    held_epochs = held_wrong = held_unlisted = 0
    refused = collections.Counter()
    held_at = {}
    would_be = {}
    ring_chords = collections.defaultdict(set)
    for (sta, sat), (ring, role) in meta.items():
        if role == "chord" and ring is not None:
            ring_chords[ring].add((sta, sat))
    ring_complete = {}
    for t in tows:
        minute = (t - t0) / 60.0
        held_now = set()
        for r in rows_by_t[t]:
            key = (r["station"], r["sat"])
            ring = int(r["ring"]) if r["ring"] not in ("", "-1") else -1
            if r["state"] == "held":
                held_now.add(key)
                held_epochs += 1
                w = wrong(ints, r["station"], r["sat"], r["sig1"], r["sig2"], int(r["n1"]), int(r["n2"]))
                if w is None:
                    held_unlisted += 1
                elif w:
                    held_wrong += 1
            elif r["state"] == "decided":
                decided[ring] += 1
                first.setdefault(ring, round(minute, 1))
                w = wrong(ints, r["station"], r["sat"], r["sig1"], r["sig2"], int(r["n1"]), int(r["n2"]))
                if w is None:
                    decided_unlisted += 1
                elif w:
                    decided_wrong += 1
            else:
                refused[r["refused"] or "?"] += 1
                if r["sigma_if"] and r["frac_if"] and float(r["sigma_if"]) <= MAX_SIGMA \
                        and float(r["frac_if"]) <= MAX_FRAC:
                    would_be[round(minute, 1)] = would_be.get(round(minute, 1), 0) + 1
        for ring, chords in ring_chords.items():
            if ring not in ring_complete and chords and chords <= held_now:
                ring_complete[ring] = round(minute, 1)
        for m in MINUTES:
            if m not in held_at and minute >= m - 1e-6:
                by_ring = collections.Counter()
                for key in held_now:
                    by_ring[meta.get(key, (None, None))[0]] += 1
                held_at[m] = {"total": len(held_now), "by_ring": dict(sorted(
                    (str(k), v) for k, v in by_ring.items()))}
    releases = collections.Counter()
    release_rows = []
    ev_path = os.path.join(run, "logs", "network_events.csv")
    if os.path.exists(ev_path):
        with open(ev_path, newline="") as fh:
            for r in csv.DictReader(fh):
                if r.get("tier") == "RINGFIX" and r.get("event") == "release":
                    releases[r.get("action") or "?"] += 1
                    release_rows.append(r)
    res.update({
        "decided": sum(decided.values()), "decided_by_ring": dict(sorted((str(k), v) for k, v in decided.items())),
        "first_decision_min_by_ring": dict(sorted((str(k), v) for k, v in first.items())),
        "decided_wrong": decided_wrong, "decided_unlisted": decided_unlisted,
        "held_link_epochs": held_epochs, "held_wrong": held_wrong, "held_unlisted": held_unlisted,
        "held_at_min": held_at, "ring_complete_min": dict(sorted((str(k), v) for k, v in ring_complete.items())),
        "ring_chords": {str(k): len(v) for k, v in sorted(ring_chords.items())},
        "refused": dict(refused), "releases_events": len(release_rows), "releases_by_cause": dict(releases),
        "would_be_by_min": {str(m): would_be.get(m, 0) for m in (5.0, 10.0, 20.0, 30.0, 60.0, 90.0, 119.5)},
    })
    return res


def print_result(res):
    print("== %s (frame %s, %d epochs)" % (res["run"], res["frame"], res["epochs"]))
    print("   decided %d by ring %s; first decision (min) by ring %s" % (
        res["decided"], res["decided_by_ring"], res["first_decision_min_by_ring"]))
    print("   decisions WRONG against the file %d (not listed %d)" % (res["decided_wrong"], res["decided_unlisted"]))
    print("   held link-epochs %d, WRONG %d, not listed %d" % (
        res["held_link_epochs"], res["held_wrong"], res["held_unlisted"]))
    for m, h in res["held_at_min"].items():
        print("   held at %3s min: %d %s" % (m, h["total"], h["by_ring"]))
    print("   chords per ring in the file %s; ring complete (min) %s" % (res["ring_chords"], res["ring_complete_min"]))
    print("   refused link-epochs %s" % res["refused"])
    print("   release events %d by cause %s" % (res["releases_events"], res["releases_by_cause"]))
    print("   would-be acceptances among chords not held, by minute %s" % res["would_be_by_min"])


def selftest():
    ok = True

    def chk(c, msg):
        nonlocal ok
        print(("PASS " if c else "FAIL ") + msg)
        ok &= bool(c)

    ints = {("A", "G01", "L1C"): 5, ("A", "G01", "L2W"): 3}
    chk(wrong(ints, "A", "G01", "L1C", "L2W", 5, 3) is False, "matching integers are right")
    chk(wrong(ints, "A", "G01", "L1C", "L2W", 5, 4) is True, "a band off is wrong")
    chk(wrong(ints, "B", "G01", "L1C", "L2W", 5, 3) is None, "an unlisted link is not graded")
    return ok


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("run", nargs="?")
    ap.add_argument("--frame")
    ap.add_argument("--json")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        sys.exit(0 if selftest() else 1)
    run = resolve(a.run)
    frame = a.frame or audit_file_of(run)
    if not frame:
        sys.exit("no frame-target file: pass --frame")
    res = analyse(run, frame)
    print_result(res)
    if a.json:
        with open(a.json, "w") as fh:
            json.dump(res, fh, indent=1)


if __name__ == "__main__":
    main()

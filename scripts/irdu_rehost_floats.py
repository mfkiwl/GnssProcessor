#!/usr/bin/env python3
"""Card IRDU section 11, measurement A: could the carried float have kept the chain's frame through a re-seat?

    python scripts/irdu_rehost_floats.py <run> <fixture> [--systems G] [--json out.json] [--list N]
    python scripts/irdu_rehost_floats.py --selftest

At every re-host row of a chain run (logs/network_chain_edges.csv, rows RehostCertified and RehostUncertified) the
new host arc was a chord of the chain at the previous observed epoch, and its carried float sits in the chord table
of that epoch (logs/network_chain_frame.csv, float_cyc_1 and float_cyc_2, the table the certifier reads).  The
truth of that float is the arc's integer in the incumbent frame, N~ = N_true(chord) + sum over the tree path of
c (N_true(arc) - k_arc) (scripts/ird_frame_census.py, frame_integer: one owner of the frame algebra).  Per re-host
arc and epoch, with both bands:

    e_1 = float_1 - N~_1, e_2 = float_2 - N~_2, e_WL = e_1 - e_2        (cycles, unwrapped)

Rounding the carried float keeps the frame on a band when |e| < 0.5 (the wide lane: |e_WL| < 0.5; the joint
reading: both bands).  The card's N_1 (section 2: the N_1 of the ionosphere-free row with the wide lane rounded) is
read beside the per-band e_1: n = (f1 n1 - f2 n2 - f2 round(n1 - n2)) / (f1 - f2), its error e_NL = n - N~_1, which
is right when the wide lane rounds right and |e_NL| < 0.5 (an ionosphere-like error of the two floats cancels in it);
its formal sigma is that of (f1 n1 - f2 n2) / (f1 - f2).  The same is read on every chord row of the table (the base rate), by the chord's age in
the table (time since the start of its unbroken run of rows), so that the re-hosts can be read against chords of
the same age.  The formal sigma of each float (sqrt q, the producer's unscaled covariance) and the certifier's
reading (kChainCertSigmaScale 3, determined at a conditional sigma of 0.05 cycle) are printed beside it.

Reading choices (printed again in the header of the output)
  - the age of a re-host arc is its age in the chord table at the previous epoch, and its age as a carried
    ambiguity (logs/network_amb_state.csv, age_ep of the arc's two signals, the smaller) when that trace exists;
  - a re-host arc without a chord row at the previous epoch is counted apart (no float to read);
  - percentiles are numpy's linear interpolation of |e|.
"""
import argparse
import csv
import json
import math
import os
import sys
from collections import Counter, defaultdict

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ird_frame_census as IFC  # noqa: E402  (the chain traces and the frame algebra)

AGE_BINS_MIN = ((0, 5), (5, 15), (15, 30), (30, 60), (60, 1e9))
F1, F2 = 1575.42e6, 1227.60e6   # GPS L1, L2 (the r3c family is GPS L1C + L2W)
CERT_SCALE = 3.0           # include/network/solve/ChainFrame.hpp, kChainCertSigmaScale
CERT_DET_SIGMA = 0.05      # kChainCertDeterminedSigmaCyc


def age_bin(age_min):
    for a, b in AGE_BINS_MIN:
        if a <= age_min < b:
            return (a, b)
    return None


def bin_label(ab):
    a, b = ab
    return "%3d to %3s min" % (a, "end" if b > 1e8 else "%d" % b)


def read_amb_age(run, wanted):
    """{(tow, sta, sat): smallest age_ep of the arc's signals} for the (tow, sta, sat) in `wanted`; empty
    when the trace is absent."""
    p = os.path.join(run, "logs", "network_amb_state.csv")
    out = {}
    if not os.path.isfile(p) or not wanted:
        return out
    with open(p, newline="", encoding="utf-8", errors="replace") as fh:
        rd = csv.reader(ln for ln in fh if not ln.startswith("#"))
        hdr = next(rd)
        ix = {c: i for i, c in enumerate(hdr)}
        for r in rd:
            if len(r) < len(hdr) or r[ix["event"]].startswith("erase"):
                continue
            key = (round(float(r[ix["tow"]]), 3), r[ix["station"]], r[ix["sat"]])
            if key not in wanted:
                continue
            try:
                a = int(r[ix["age_ep"]])
            except ValueError:
                continue
            out[key] = a if key not in out else min(out[key], a)
    return out


def chord_errors(forest, truth, c):
    """(e1, e2) of chord row c against the frame truth of its epoch, None where a band is ungradeable."""
    out = []
    for k in (1, 2):
        v, why = IFC.frame_integer(forest, truth, c.system, c.band(k), c.sta, c.sat, c.tow)
        out.append(None if (v is None or why == "tree edge") else c.flt(k) - v)
    return out


def summarize(rows):
    """rows: dicts with e1, e2 (cycles) -> share and quantiles."""
    if not rows:
        return {"n": 0}
    e1 = np.array([abs(r["e1"]) for r in rows])
    ew = np.array([abs(r["e1"] - r["e2"]) for r in rows])
    s1 = np.array([r["s1"] for r in rows])
    sw = np.array([r["sw"] for r in rows])
    both = np.array([abs(r["e1"]) < 0.5 and abs(r["e1"] - r["e2"]) < 0.5 for r in rows])
    enl = np.array([abs(r["enl"]) for r in rows])
    snl = np.array([r["snl"] for r in rows])
    card = np.array([r["wl_ok"] and abs(r["enl"]) < 0.5 for r in rows])
    return {"n": len(rows),
            "wl_p50": float(np.percentile(ew, 50)), "wl_p90": float(np.percentile(ew, 90)),
            "wl_round_ok": float(np.mean(ew < 0.5)), "wl_within_025": float(np.mean(ew < 0.25)),
            "n1_p50": float(np.percentile(e1, 50)), "n1_p90": float(np.percentile(e1, 90)),
            "n1_round_ok": float(np.mean(e1 < 0.5)), "n1_within_025": float(np.mean(e1 < 0.25)),
            "both_round_ok": float(np.mean(both)),
            "nl_p50": float(np.percentile(enl, 50)), "nl_p90": float(np.percentile(enl, 90)),
            "card_round_ok": float(np.mean(card)), "sigmanl_p50": float(np.percentile(snl, 50)),
            "znl_p50": float(np.percentile(enl / np.maximum(snl, 1e-9), 50)),
            "sigma1_p50": float(np.percentile(s1, 50)), "sigmawl_p50": float(np.percentile(sw, 50)),
            "z1_p50": float(np.percentile(e1 / np.maximum(s1, 1e-9), 50)),
            "zwl_p50": float(np.percentile(ew / np.maximum(sw, 1e-9), 50))}


def fmt(s):
    if not s.get("n"):
        return "n 0"
    return ("n %4d | WL |e| p50 %.3f p90 %.3f, right %5.1f %% | N1 (IF row, WL rounded) |e| p50 %.3f p90 %.3f, WL and "
            "N1 right %5.1f %% | band 1 alone |e| p50 %.3f, both bands right %5.1f %% | formal sigma WL %.3f N1(IF) %.3f "
            "band1 %.3f | |e|/sigma p50 WL %.2f N1(IF) %.2f"
            % (s["n"], s["wl_p50"], s["wl_p90"], 100 * s["wl_round_ok"], s["nl_p50"], s["nl_p90"],
               100 * s["card_round_ok"], s["n1_p50"], 100 * s["both_round_ok"], s["sigmawl_p50"], s["sigmanl_p50"],
               s["sigma1_p50"], s["zwl_p50"], s["znl_p50"]))


def card_n1(f1c, f2c):
    """The card's N_1 float (section 2): the ionosphere-free row with the wide lane rounded."""
    return (F1 * f1c - F2 * f2c - F2 * round(f1c - f2c)) / (F1 - F2)


def row_of(c, e1, e2, age_min):
    s1 = math.sqrt(max(c.q11, 0.0))
    sw = math.sqrt(max(c.q11 + c.q22 - 2.0 * c.q12, 0.0))
    snl = math.sqrt(max(F1 * F1 * c.q11 - 2.0 * F1 * F2 * c.q12 + F2 * F2 * c.q22, 0.0)) / (F1 - F2)
    z1, z2 = c.f1 - e1, c.f2 - e2          # the frame truth of the two bands (integers)
    wl_ok = round(c.f1 - c.f2) == round(z1 - z2)
    return {"tow": c.tow, "sta": c.sta, "sat": c.sat, "f1": c.f1, "f2": c.f2, "e1": e1, "e2": e2,
            "s1": s1, "sw": sw, "snl": snl, "wl_ok": wl_ok, "enl": card_n1(c.f1, c.f2) - z1,
            "age_min": age_min, "cert_sigma1": CERT_SCALE * s1}


def analyse(run, fixture, systems=("G",), list_n=12):
    edges = IFC.read_edges(run, systems)
    chords = IFC.read_chords(run, systems)
    forest = IFC.Forest(edges)
    truth = IFC.Truth(fixture, run)
    since = IFC.chord_runs(chords, forest)
    chord_at = {(c.tow, c.system, c.sta, c.sat): c for c in chords}
    # the re-host arcs: one entry per (tow, system, station, satellite), with the bands that re-hosted
    rehost = defaultdict(lambda: {"bands": set(), "rows": set(), "targets": {}, "certified": 0})
    for e in edges:
        if e.row in IFC.REHOST_ROWS:
            r = rehost[(e.tow, e.system, e.sta, e.sat)]
            r["bands"].add(e.band)
            r["rows"].add(e.row)
            r["targets"][e.band] = e.target
            r["certified"] += int(e.certified)
    wanted = set()
    for (tow, system, sta, sat) in rehost:
        pt = forest.previous(tow)
        if pt is not None:
            wanted.add((pt, sta, sat))
    amb_age = read_amb_age(run, wanted)
    out_rows, no_row, ungradeable, kept_by_target = [], Counter(), Counter(), Counter()
    for (tow, system, sta, sat), info in sorted(rehost.items()):
        pt = forest.previous(tow)
        c = chord_at.get((pt, system, sta, sat)) if pt is not None else None
        if c is None:
            no_row["no chord row at the previous epoch"] += 1
            continue
        e1, e2 = chord_errors(forest, truth, c)
        if e1 is None or e2 is None:
            ungradeable["a band without frame truth"] += 1
            continue
        age = (pt - since.get((c.key, pt), pt)) / 60.0
        r = row_of(c, e1, e2, age)
        r["rehost_tow"] = tow
        r["bands"] = sorted(info["bands"])
        r["certified"] = info["certified"]
        r["amb_age_min"] = amb_age[(pt, sta, sat)] * 0.5 if (pt, sta, sat) in amb_age else None
        # the pin the chain took against the incumbent frame (the row's target against N~ at pt)
        js = []
        for k in (1, 2):
            band = c.band(k)
            tgt = info["targets"].get(band)
            if tgt is None:
                continue
            v, why = IFC.frame_integer(forest, truth, system, band, sta, sat, pt)
            if v is not None and why != "tree edge":
                js.append(int(round(tgt - v)))
        r["pin_steps"] = js
        kept_by_target["frame kept by the pin (both bands j = 0)" if js and all(j == 0 for j in js)
                       else "pin stepped the frame"] += 1
        out_rows.append(r)
    # the base rate: every chord row of the table by its age
    base = defaultdict(list)
    for c in chords:
        e1, e2 = chord_errors(forest, truth, c)
        if e1 is None or e2 is None:
            continue
        age = (c.tow - since.get((c.key, c.tow), c.tow)) / 60.0
        ab = age_bin(age)
        if ab:
            base[ab].append(row_of(c, e1, e2, age))
    res = {"run": run, "fixture": fixture, "n_rehost_arcs": len(rehost), "graded": len(out_rows),
           "no_row": dict(no_row), "ungradeable": dict(ungradeable), "pin": dict(kept_by_target),
           "rehost_all": summarize(out_rows), "rehost_by_age": {}, "base_by_age": {}}
    print("== card IRDU section 11 A: the carried float of each re-host arc against its integer in the incumbent frame")
    print("run %s\nfixture %s" % (run, fixture))
    print("reading: the chord table of the epoch before the re-host; truth N~ in the frame of that epoch "
          "(ird_frame_census.frame_integer); age = time since the chord's run in the table began")
    print("re-host arcs %d (band rows %d): graded %d; %s; %s" % (
        len(rehost), sum(len(v["bands"]) for v in rehost.values()), len(out_rows), dict(no_row) or "every arc had a row",
        dict(ungradeable) or "no ungradeable arc"))
    print("the chain's own pin at those re-hosts: %s" % dict(kept_by_target))
    print("re-host arcs, all ages : " + fmt(res["rehost_all"]))
    for ab in AGE_BINS_MIN:
        sel = [r for r in out_rows if age_bin(r["age_min"]) == ab]
        res["rehost_by_age"][bin_label(ab)] = summarize(sel)
        res["base_by_age"][bin_label(ab)] = summarize(base[ab])
    print("by the arc's age in the chord table:")
    for ab in AGE_BINS_MIN:
        print("  re-host  %s: %s" % (bin_label(ab), fmt(res["rehost_by_age"][bin_label(ab)])))
        print("  all rows %s: %s" % (bin_label(ab), fmt(res["base_by_age"][bin_label(ab)])))
    ages = [r["amb_age_min"] for r in out_rows if r["amb_age_min"] is not None]
    if ages:
        print("re-host arcs' age as carried ambiguities (network_amb_state age_ep x 30 s): p10 %.1f p50 %.1f p90 %.1f min"
              % tuple(np.percentile(ages, [10, 50, 90])))
    cert_ok = sum(1 for r in out_rows if r["cert_sigma1"] <= CERT_DET_SIGMA)
    print("certifier reading: %d of %d re-host arcs have 3 x sigma(N1) <= 0.05 cycle (p50 3 x sigma %.3f cycle)"
          % (cert_ok, len(out_rows), float(np.percentile([r["cert_sigma1"] for r in out_rows], 50)) if out_rows else float("nan")))
    print("first %d re-host arcs:" % list_n)
    for r in out_rows[:list_n]:
        print("  tow %.0f %s %s age %.1f min: e1 %+.3f e2 %+.3f eWL %+.3f eN1(IF) %+.3f (sigma WL %.3f, N1(IF) %.3f), "
              "pin steps %s" % (r["rehost_tow"], r["sta"], r["sat"], r["age_min"], r["e1"], r["e2"], r["e1"] - r["e2"],
                                r["enl"], r["sw"], r["snl"], r["pin_steps"]))
    res["rows"] = out_rows
    return res


def selftest():
    ok = True

    def chk(c, msg):
        nonlocal ok
        print(("PASS " if c else "FAIL ") + msg)
        ok &= bool(c)

    base = {"s1": 0.1, "sw": 0.1, "snl": 0.1, "enl": 0.0, "wl_ok": True}
    rows = [dict(base, e1=0.1, e2=0.0), dict(base, e1=0.6, e2=0.0, wl_ok=False), dict(base, e1=0.2, e2=-0.4, wl_ok=False)]
    s = summarize(rows)
    chk(abs(s["n1_round_ok"] - 2 / 3) < 1e-12, "N1 rounding right on 2 of 3 rows")
    chk(abs(s["wl_round_ok"] - 1 / 3) < 1e-12, "WL rounding right on 1 of 3 rows (0.1, 0.6, 0.6)")
    chk(abs(s["both_round_ok"] - 1 / 3) < 1e-12, "both bands right on 1 of 3 rows")
    chk(abs(s["card_round_ok"] - 1 / 3) < 1e-12, "the card's N_1 right only where the wide lane is right")
    # an ionosphere-like error (e2 = (f1/f2) e1, the dispersive ratio of a phase advance in cycles) cancels in the
    # ionosphere-free row: floats N + e with N1 = 10, N2 = 7
    e1 = 0.4
    e2 = e1 * F1 / F2
    chk(abs(card_n1(10 + e1, 7 + e2) - 10) < 1e-9 and round((10 + e1) - (7 + e2)) == 3,
        "an ionosphere-like error of the two floats cancels in the card's N_1")
    chk(age_bin(4.9) == (0, 5) and age_bin(5.0) == (5, 15) and age_bin(500) == (60, 1e9), "age bins")
    return ok


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("run", nargs="?")
    ap.add_argument("fixture", nargs="?")
    ap.add_argument("--systems", default="G")
    ap.add_argument("--json")
    ap.add_argument("--list", type=int, default=12)
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        sys.exit(0 if selftest() else 1)
    res = analyse(os.path.abspath(a.run), os.path.abspath(a.fixture), tuple(a.systems.split(",")), a.list)
    if a.json:
        with open(a.json, "w") as fh:
            json.dump(res, fh, indent=1, default=str)


if __name__ == "__main__":
    main()

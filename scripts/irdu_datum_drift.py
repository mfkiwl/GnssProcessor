#!/usr/bin/env python3
"""Card IRDU section 12.8, task 3: which of the network's datums moves against which.  Measure only.

    py -3.14 scripts/irdu_datum_drift.py <network run> [--fixture DIR] [--from-min 30] [--to-min 120]

From the run's traces, each family's estimate against the simulator's truth, and the change of its part shared by the
family's members since --from-min (mm), per 15 min:

  rx clock   each station's receiver clock (logs/network_rx_states.csv, kind CLK) less its truth (truth_clock.csv,
             clock_bias_m); shared part = mean over the stations; the root (the chain's datum receiver, from
             logs/network_rpb_states.csv, pinned) beside
  rx phase   each non-root station's receiver phase bias per signal (logs/network_rpb_states.csv) less its truth
             (truth_rx_bias.csv, kind phase) relative to the root's truth; shared part = mean over the stations
  rx DCB     each station's receiver code-bias state (kind CB) less its own value at --from-min; mean
  sat code   each satellite's emitted code bias per signal (products B records) less its truth OSB; mean
  sat clock  each satellite's emitted clock (C records) less its truth clock; mean
  sat phase  the emitted phase biases' shared drift against the code (the truth-free S of irdu_code_datum.py)
"""
import argparse
import csv
import os
import sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import irdu_code_datum as CD  # noqa: E402
import simnet_wire_integer_consistency as WIC  # noqa: E402


def mean(v):
    return sum(v) / len(v) if v else float("nan")


def rows(path):
    with open(path, newline="", encoding="utf-8", errors="replace") as fh:
        yield from csv.DictReader(ln for ln in fh if not ln.startswith("#"))


def analyse(run, fixture, from_min, to_min):
    logs = os.path.join(run, "logs")
    # the root: the station whose phase bias is pinned
    root = None
    rpb = defaultdict(dict)                       # (sta, sig) -> {tow: value}
    for r in rows(os.path.join(logs, "network_rpb_states.csv")):
        t = round(float(r["tow"]), 3)
        if r["pinned"] == "1" and root is None:
            root = r["station"]
        rpb[(r["station"], r["signal"])][t] = float(r["value_m"])
    clk, dcb = defaultdict(dict), defaultdict(dict)
    for r in rows(os.path.join(logs, "network_rx_states.csv")):
        t = round(float(r["tow"]), 3)
        if r["kind"] == "CLK":
            clk[r["station"]][t] = float(r["value_m"])
        elif r["kind"] == "CB":
            dcb[(r["station"], r["key"])][t] = float(r["value_m"])
    tclk, tph = {}, {}
    stations = sorted({s for s in clk} | {k[0] for k in rpb})
    for s in stations:
        p = os.path.join(fixture, s, "truth_clock.csv")
        if os.path.exists(p):
            tclk[s] = {round(float(r["tow_s"]), 3): float(r["clock_bias_m"]) for r in rows(p)}
        p = os.path.join(fixture, s, "truth_rx_bias.csv")
        if os.path.exists(p):
            tph[s] = {r["code"]: float(r["value_m"]) for r in rows(p) if r["kind"] == "phase"}
    all_t = sorted({t for v in clk.values() for t in v})
    t0 = all_t[0]
    lo, hi = t0 + 60 * from_min, t0 + 60 * to_min
    win = [t for t in all_t if lo <= t < hi]
    series = defaultdict(dict)
    for t in win:
        e = [clk[s][t] - tclk[s][t] for s in clk if t in clk[s] and s in tclk and t in tclk[s]]
        series["rx clock (mean)"][t] = mean(e)
        if root in clk and t in clk[root] and root in tclk and t in tclk[root]:
            series["rx clock (root)"][t] = clk[root][t] - tclk[root][t]
        for sig in ("L1C", "L2W"):
            ev = [rpb[(s, sig)][t] - (tph[s][sig] - tph[root][sig]) for s in stations
                  if s != root and t in rpb.get((s, sig), {}) and s in tph and root in tph]
            series["rx phase %s (mean)" % sig][t] = mean(ev)
        dv = [v[t] - v[win[0]] for k, v in dcb.items() if t in v and win[0] in v]
        series["rx DCB (mean change)"][t] = mean(dv)
    # satellite side, from the products and the truth
    osb, sc_truth, epochs, _ = WIC.dual_load(fixture, run)
    for ep in epochs:
        t = ep["tow"]
        if not (lo <= t < hi):
            continue
        for band, sig in (("1", "C1C"), ("2", "C2W")):
            ev = [b - osb[(s, g)] for (s, g), b in ep["B"].items() if g == sig and s.startswith("G") and (s, g) in osb]
            series["sat code %s (mean)" % sig][t] = mean(ev)
        # The C record is the correction to the precise a priori clock, whose truth is the injected satellite-clock
        # error (zero when the simulator injects none, simnet_wire_integer_consistency.load_satclock_truth).
        ev = [c - sc_truth.get((t, s), 0.0) for s, c in ep["C"].items() if s.startswith("G")]
        series["sat clock (mean)"][t] = mean(ev)
    tf = CD.truthfree_shared(os.path.join(run, "products.txt"))
    for (t, band), v in tf.items():
        if lo <= t < hi:
            series["sat phase vs code %s (shared S)" % {"1": "L1C", "2": "L2W"}[band]][t] = v
    return root, series, t0


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("run")
    ap.add_argument("--fixture", default="C:/GnssProcessor/runs/simarl_r3c")
    ap.add_argument("--from-min", type=float, default=30.0)
    ap.add_argument("--to-min", type=float, default=120.0)
    a = ap.parse_args()
    root, series, t0 = analyse(os.path.abspath(a.run), a.fixture, a.from_min, a.to_min)
    print("== %s (root %s): change of each family's shared part since %.0f min (mm), per 15 min" % (
        os.path.basename(a.run.rstrip("/\\")), root, a.from_min))
    for name, ser in series.items():
        ts = sorted(ser)
        if not ts:
            continue
        base = ser[ts[0]]
        bins = defaultdict(list)
        for t in ts:
            bins[int((t - t0) // 900)].append(ser[t] - base)
        parts = " ".join("%d-%d %+.0f" % (15 * k, 15 * k + 15, 1000 * mean(v)) for k, v in sorted(bins.items()))
        vals = [ser[t] - base for t in ts]
        print("   %-34s %s | range %.0f" % (name, parts, 1000 * (max(vals) - min(vals))))


if __name__ == "__main__":
    main()

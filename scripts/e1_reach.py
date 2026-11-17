#!/usr/bin/env python3
"""Card BER, stage E1 (bad-epoch response): the reach of one event, an event run against its control (same build, same bed but
the event receiver's RINEX).

    py -3.14 scripts/e1_reach.py <event run> <control run> --station S12000SIM --sat G20 --tow 265230
        [--fixture C:/GnssProcessor/runs/simnet60_quiet_col_24h] [--json out.json]

Reads, all after the event epoch unless said:
  wet delay      every receiver's carried ZWD (logs/network_zwd.csv), max |event - control|; the event receiver's
                 error against truth (truth_tropo.csv), before and after
  receiver clock logs/network_rx_states.csv (kind CLK): max |event - control| after removing the epoch's median
                 difference over receivers (a common datum shift reaches no user)
  floats         logs/network_amb_state.csv: max |event - control| of the carried values (cycles of the signal) of
                 every arc but the event arc, per receiver
  stream         products.txt: satellite clocks (C) and phase biases (P) of every satellite, event - control, the
                 epoch's median over the constellation's satellites removed; max per satellite, the event satellite apart
  phase-bias     the same phase-bias changes of each satellite's two bands split by direction, GPS and Galileo apart:
  directions     d1 = I + G and d2 = gamma I + G with gamma = (f1/f2)^2, so G = (gamma d1 - d2)/(gamma - 1) is the
                 ionosphere-free part a user's position feels (reported with the satellite clock's change added),
                 I = (d2 - d1)/(gamma - 1) the part a slant ionosphere absorbs, and d1/lambda1 - d2/lambda2 the wide
                 lane in cycles
  events         logs/network_events.csv rows of the event run at the event epoch and the next one that the control
                 does not have, by tier, event and action
"""
import argparse
import collections
import csv
import json
import os
import statistics
import sys

RUNS = os.environ.get("RAPID_RUNS_ROOT") or "D:/GnssProcessorSupport/runs_nom"
# Carrier wavelengths (m) of the bed's phase signals (GPS L1/L2/L5, Galileo E1/E5a/E5b).
LAM = {"L1C": 0.19029367279836487, "L2W": 0.24421021342456825, "L5Q": 0.25482804879085386, "L7Q": 0.24834936958430670}
SPEED_OF_LIGHT = 299792458.0
# Carrier frequencies (Hz) by constellation letter and RINEX band digit.
FREQ = {("G", "1"): 1575.42e6, ("G", "2"): 1227.60e6, ("G", "5"): 1176.45e6,
        ("E", "1"): 1575.42e6, ("E", "5"): 1176.45e6, ("E", "7"): 1207.14e6, ("E", "6"): 1278.75e6}
# The second band of a satellite's pair, in order of preference, by constellation.
SECOND_BAND = {"G": ("2", "5"), "E": ("5", "7", "6")}


def resolve(run):
    return os.path.abspath(run) if os.path.isdir(run) else os.path.join(RUNS, "_rap_" + run)


def series(path, keycols, valcol, filt=None):
    out = {}
    with open(path, newline="") as fh:
        for r in csv.DictReader((ln for ln in fh if not ln.startswith("#"))):
            if filt and not filt(r):
                continue
            try:
                out[(round(float(r["tow"]), 3),) + tuple(r[c] for c in keycols)] = float(r[valcol])
            except (ValueError, KeyError):
                pass
    return out


def products(path):
    clk, pb = {}, {}
    tow = None
    with open(path) as fh:
        for ln in fh:
            if ln.startswith("E,"):
                tow = round(float(ln.split(",")[2]), 0)
            elif ln.startswith("C,") and tow is not None:
                f = ln.split(",")
                clk[(tow, f[1])] = float(f[2])
            elif ln.startswith("P,") and tow is not None:
                f = ln.split(",")
                pb[(tow, f[1], f[2])] = float(f[3])
    return clk, pb


def demedian(d_ev, d_ct, group_of, tmin):
    """{key: max |dx - median of its group at the epoch|} over epochs > tmin for keys (tow, *rest)."""
    by_t = collections.defaultdict(dict)
    for k, v in d_ev.items():
        if k[0] > tmin and k in d_ct:
            by_t[(k[0], group_of(k))][k] = v - d_ct[k]
    out = collections.defaultdict(float)
    for (t, g), dd in by_t.items():
        if len(dd) < 3:
            continue
        m = statistics.median(dd.values())
        for k, v in dd.items():
            out[k[1:]] = max(out[k[1:]], abs(v - m))
    return out


def demedian_epochs(d_ev, d_ct, group_of, tmin):
    """{key: dx - median of its group at the epoch} for keys (tow, *rest) over epochs > tmin (groups of 3 or more)."""
    by_t = collections.defaultdict(dict)
    for k, v in d_ev.items():
        if k[0] > tmin and k in d_ct:
            by_t[(k[0], group_of(k))][k] = v - d_ct[k]
    out = {}
    for _, dd in by_t.items():
        if len(dd) < 3:
            continue
        m = statistics.median(dd.values())
        for k, v in dd.items():
            out[k] = v - m
    return out


def pb_directions(pp_ev, pp_ct, pc_ev, pc_ct, tmin, event_sat):
    """Per constellation, the largest phase-bias change after the event of each satellite split by direction."""
    dpb = demedian_epochs(pp_ev, pp_ct, lambda k: (k[1][0], k[2]), tmin)
    dclk = demedian_epochs(pc_ev, pc_ct, lambda k: k[1][0], tmin)
    by = collections.defaultdict(dict)          # (tow, sat) -> {band digit: (signal, d)}
    for (t, sat, sig), d in dpb.items():
        by[(t, sat)].setdefault(sig[1], (sig, d))
    best = collections.defaultdict(lambda: collections.defaultdict(lambda: [0.0, 0.0, 0.0, 0.0]))
    for (t, sat), bands in by.items():
        c = sat[0]
        b2 = next((b for b in SECOND_BAND.get(c, ()) if b in bands), None)
        if "1" not in bands or b2 is None or (c, "1") not in FREQ or (c, b2) not in FREQ:
            continue
        f1, f2 = FREQ[(c, "1")], FREQ[(c, b2)]
        gamma = (f1 / f2) ** 2
        d1, d2 = bands["1"][1], bands[b2][1]
        iono = (d2 - d1) / (gamma - 1.0)
        free = (gamma * d1 - d2) / (gamma - 1.0)
        wl = d1 / (SPEED_OF_LIGHT / f1) - d2 / (SPEED_OF_LIGHT / f2)
        rec = best[c][sat]
        rec[0] = max(rec[0], abs(free + dclk.get((t, sat), 0.0)))
        rec[1] = max(rec[1], abs(iono))
        rec[2] = max(rec[2], abs(wl))
        rec[3] = max(rec[3], abs(free))
    out = {}
    for c, sats in best.items():
        others = {s: v for s, v in sats.items() if s != event_sat}
        top = lambda i: sorted(((v[i], s) for s, v in others.items()), reverse=True)[:3]
        out[c] = {"iono_free_with_clock_m": top(0), "iono_like_m": top(1), "wide_lane_cyc": top(2),
                  "iono_free_m": top(3), "event_sat": sats.get(event_sat)}
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("event")
    ap.add_argument("control")
    ap.add_argument("--station", required=True)
    ap.add_argument("--sat", required=True)
    ap.add_argument("--tow", type=float, required=True)
    ap.add_argument("--fixture", default="C:/GnssProcessor/runs/simnet60_quiet_col_24h")
    ap.add_argument("--json")
    a = ap.parse_args()
    ev, ct = resolve(a.event), resolve(a.control)
    T = a.tow - 1e-3
    res = {}
    # wet delay
    z_ev = series(os.path.join(ev, "logs", "network_zwd.csv"), ["station"], "zwd_m")
    z_ct = series(os.path.join(ct, "logs", "network_zwd.csv"), ["station"], "zwd_m")
    dz = collections.defaultdict(float)
    for k, v in z_ev.items():
        if k[0] > T and k in z_ct:
            dz[k[1]] = max(dz[k[1]], abs(v - z_ct[k]))
    truth = {}
    with open(os.path.join(a.fixture, a.station, "truth_tropo.csv"), newline="") as fh:
        for r in csv.DictReader(fh):
            truth[round(float(r["tow_s"]), 3)] = float(r["zwd_m"])
    err = {run: max((abs(z[k] - truth[k[0]]) for k in z if k[1] == a.station and k[0] > T and k[0] in truth),
                    default=float("nan")) for run, z in (("event", z_ev), ("control", z_ct))}
    others = sorted(((v, s) for s, v in dz.items() if s != a.station), reverse=True)
    res["zwd"] = {"event_station_max_diff_m": dz.get(a.station), "event_station_err_vs_truth_m": err,
                  "others_over_5mm": sum(1 for v, _ in others if v > 0.005), "others_top": others[:8]}
    # receiver clocks
    c_ev = series(os.path.join(ev, "logs", "network_rx_states.csv"), ["station"], "value_m", lambda r: r["kind"] == "CLK")
    c_ct = series(os.path.join(ct, "logs", "network_rx_states.csv"), ["station"], "value_m", lambda r: r["kind"] == "CLK")
    dc = demedian(c_ev, c_ct, lambda k: "all", T)
    oc = sorted(((v, s[0]) for s, v in dc.items() if s[0] != a.station), reverse=True)
    res["rx_clock"] = {"event_station_m": dc.get((a.station,)), "others_top_m": oc[:6]}
    # floats
    f_ev = series(os.path.join(ev, "logs", "network_amb_state.csv"), ["station", "sat", "signal"], "value_abs_m")
    f_ct = series(os.path.join(ct, "logs", "network_amb_state.csv"), ["station", "sat", "signal"], "value_abs_m")
    df = collections.defaultdict(float)
    for k, v in f_ev.items():
        if k[0] > T and k in f_ct and not (k[1] == a.station and k[2] == a.sat):
            lam = LAM.get(k[3])
            if lam:
                df[k[1]] = max(df[k[1]], abs(v - f_ct[k]) / lam)
    of = sorted(((v, s) for s, v in df.items() if s != a.station), reverse=True)
    res["floats_cycles"] = {"event_station_other_arcs": df.get(a.station), "others_top": of[:6]}
    # stream
    pc_ev, pp_ev = products(os.path.join(ev, "products.txt"))
    pc_ct, pp_ct = products(os.path.join(ct, "products.txt"))
    dclk = demedian(pc_ev, pc_ct, lambda k: k[1][0], T)
    dpb = demedian(pp_ev, pp_ct, lambda k: (k[1][0], k[2]), T)
    res["stream"] = {"clock_event_sat_m": dclk.get((a.sat,)),
                     "clock_others_top_m": sorted(((v, s[0]) for s, v in dclk.items() if s[0] != a.sat), reverse=True)[:6],
                     "pb_event_sat_m": {s[1]: v for s, v in dpb.items() if s[0] == a.sat},
                     "pb_others_top_m": sorted(((v, "%s %s" % s) for s, v in dpb.items() if s[0] != a.sat), reverse=True)[:6]}
    res["stream_pb_directions"] = pb_directions(pp_ev, pp_ct, pc_ev, pc_ct, T, a.sat)
    # events
    def rows(run):
        c = collections.Counter()
        with open(os.path.join(run, "logs", "network_events.csv"), newline="") as fh:
            for r in csv.DictReader(fh):
                t = float(r["tow"])
                if a.tow - 1e-3 <= t <= a.tow + 30.0 + 1e-3:
                    c[(r["tier"], r["event"], r["action"])] += 1
        return c
    e_ev, e_ct = rows(ev), rows(ct)
    extra = {"%s %s %s" % k: n - e_ct.get(k, 0) for k, n in e_ev.items() if n > e_ct.get(k, 0)}
    res["events_extra_at_event"] = dict(sorted(extra.items(), key=lambda x: -x[1]))
    print("== %s against %s (event %s %s at TOW %.0f)" % (ev, ct, a.station, a.sat, a.tow))
    print("  wet delay: event receiver max |event - control| %.4f m; its error against truth after the event: event %.4f, "
          "control %.4f m" % (dz.get(a.station, float("nan")), err["event"], err["control"]))
    print("  wet delay, other receivers: %d over 5 mm; top %s" % (
        res["zwd"]["others_over_5mm"], ", ".join("%s %.4f" % (s, v) for v, s in others[:6])))
    print("  receiver clocks (median difference removed): event receiver %.4f m; others top %s" % (
        dc.get((a.station,), float("nan")), ", ".join("%s %.4f" % (s, v) for v, s in oc[:5])))
    print("  floats of other arcs: event receiver %.3f cycle; others top %s" % (
        df.get(a.station, float("nan")), ", ".join("%s %.3f" % (s, v) for v, s in of[:5])))
    print("  stream clocks (median removed): %s %.4f m; others top %s" % (
        a.sat, dclk.get((a.sat,), float("nan")),
        ", ".join("%s %.4f" % (s, v) for v, s in res["stream"]["clock_others_top_m"][:5])))
    print("  stream phase biases (median removed): %s %s; others top %s" % (
        a.sat, res["stream"]["pb_event_sat_m"], ", ".join("%s %.4f" % (s, v) for v, s in res["stream"]["pb_others_top_m"][:5])))
    for c, d in sorted(res["stream_pb_directions"].items()):
        print("  phase biases of the other satellites by direction, %s: ionosphere-free with the clock %s m; "
              "ionosphere-like %s m; wide lane %s cycles" % (
                  {"G": "GPS", "E": "Galileo"}.get(c, c),
                  ", ".join("%s %.5f" % (s, v) for v, s in d["iono_free_with_clock_m"]),
                  ", ".join("%s %.5f" % (s, v) for v, s in d["iono_like_m"]),
                  ", ".join("%s %.4f" % (s, v) for v, s in d["wide_lane_cyc"])))
    print("  events of the event run at the event epoch and the next that the control lacks: %s" % (
        "; ".join("%s x%d" % kv for kv in list(res["events_extra_at_event"].items())[:25])))
    if a.json:
        with open(a.json, "w") as fh:
            json.dump(res, fh, indent=1, default=str)
    return 0


if __name__ == "__main__":
    sys.exit(main())

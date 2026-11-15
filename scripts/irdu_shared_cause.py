#!/usr/bin/env python3
"""Card IRDU section 13.3: which network state moves the part of the phase-bias steps every satellite shares.

    py -3.14 scripts/irdu_shared_cause.py <network run> --truth-root DIR [--station NAME] [--windows 5-40,40-120]
        [--series out.csv]

The shared move of band b at epoch t is the median over the GPS satellites of the emitted phase bias's change
(products.txt).  At the root receiver (the clock datum station, whose receiver phase bias is pinned: the eq34 root),
the phase observation of every satellite it sees fits to the millimetre (the root is the r1 column of the chain trace,
else the clock datum station), so a move of every satellite's phase bias
must be absorbed there by the root's own states (its clock, its wet delay through the mapping, its slant ionosphere
with the factor mu_b, its pinned or float ambiguities) and by the satellites' clocks.  With the emitted bias the
negative of the state (P = -B^s), the root's phase equation reads, for the shared part:

    s_b(t) = -[ d e_clk,root(t) - mu_sat(t) + m * d e_zwd,root(t) - mu_b * d e_I,root(t) ] + (colour, noise)

with e_x = estimate - truth (the fixture's truth_clock, truth_tropo and truth_atmo of the root), d the change between
consecutive epochs, m the median 1/sin(elevation) of the root's satellites, d e_I the median over the root's
satellites, mu_sat the median over the satellites of the clock innovation of the clock-anchor trace (dclk: the
estimator's satellite clock before the emitted clocks' frame hold, which removes that median from the emitted
clocks), mu_1 = 1 and mu_2 = (f1/f2)^2.  Each candidate is read alone (its correlation with s_b and the share of
s_b's variance it explains with the coefficient of the equation, no fit) and the sum of the four is the
prediction.  The receivers' phase biases (network_rpb_states.csv, the pinned root excepted) are read beside, and the
same candidates of the median non-root station as a control.  Also printed: the formal sigmas of the root's states,
the median non-root receiver phase bias and the median satellite clock, by 5 minutes.
"""
import argparse
import collections
import csv
import json
import math
import os
import statistics as st

C0 = 299792458.0
F1, F2 = 1575.42e6, 1227.60e6
LAM = {"L1C": C0 / F1, "L2W": C0 / F2}
MU = {"L1C": 1.0, "L2W": (F1 / F2) ** 2}


def rows(path):
    with open(path, newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(ln for ln in fh if not ln.startswith("#")))


def kt(x):
    return round(float(x), 3)


def corr(x, y):
    if len(x) < 3:
        return float("nan")
    mx, my = st.mean(x), st.mean(y)
    den = math.sqrt(sum((u - mx) ** 2 for u in x) * sum((v - my) ** 2 for v in y))
    return sum((u - mx) * (v - my) for u, v in zip(x, y)) / den if den > 0 else float("nan")


def explained(y, p):
    """Share of y's variance a prediction p removes: 1 - var(y - p) / var(y)."""
    if len(y) < 3:
        return float("nan")
    vy = st.pvariance(y)
    return 1.0 - st.pvariance([a - b for a, b in zip(y, p)]) / vy if vy > 0 else float("nan")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("run")
    ap.add_argument("--truth-root", required=True)
    ap.add_argument("--station", default="")
    ap.add_argument("--windows", default="5-40,15-40,40-120")
    ap.add_argument("--series", default="")
    a = ap.parse_args()
    logs = os.path.join(a.run, "logs")
    arm = json.load(open(os.path.join(a.run, "arm.json"), encoding="utf-8"))
    root = a.station
    if not root:
        # the eq34 root receiver of the chain trace (column r1), else the clock datum station
        roots = collections.Counter()
        p_edges = os.path.join(logs, "network_chain_edges.csv")
        if os.path.exists(p_edges):
            for r in rows(p_edges):
                roots[r["r1"]] += 1
        root = roots.most_common(1)[0][0] if roots else arm["network"].get("clock_datum_station", "")

    # emitted phase biases
    ep, P = [], {}
    with open(os.path.join(a.run, "products.txt"), encoding="utf-8") as fh:
        for ln in fh:
            f = ln.split(",")
            if f[0] == "E":
                t = kt(f[2])
                ep.append(t)
                P[t] = {}
            elif f[0] == "P" and f[1].startswith("G") and f[2] in LAM:
                P[t][(f[1], f[2])] = float(f[3])
    t0 = ep[0]

    # receiver states (clock, DCB) of every station, with formal sigmas
    clk, dcb, clk_sd, dcb_sd = (collections.defaultdict(dict) for _ in range(4))
    for r in rows(os.path.join(logs, "network_rx_states.csv")):
        t = kt(r["tow"])
        if r["kind"] == "CLK":
            clk[r["station"]][t] = float(r["value_m"])
            clk_sd[r["station"]][t] = float(r["std_m"])
        elif r["kind"] == "CB":
            dcb[r["station"]][t] = float(r["value_m"])
            dcb_sd[r["station"]][t] = float(r["std_m"])
    stations = sorted(clk)
    zwd, zwd_sd = collections.defaultdict(dict), collections.defaultdict(dict)
    for r in rows(os.path.join(logs, "network_zwd.csv")):
        zwd[r["station"]][kt(r["tow"])] = float(r["zwd_m"])
        zwd_sd[r["station"]][kt(r["tow"])] = float(r["std_m"])
    iono = collections.defaultdict(dict)   # (station, sat) -> t -> (slant L1 m, elevation)
    for r in rows(os.path.join(logs, "network_ionosphere.csv")):
        iono[(r["station"], r["sat"])][kt(r["tow"])] = (float(r["iono_total_m"]), float(r["elevation_deg"]))
    rpb, rpb_sd = collections.defaultdict(dict), collections.defaultdict(dict)
    for r in rows(os.path.join(logs, "network_rpb_states.csv")):
        if r["system"] != "GPS" or r["signal"] not in LAM:
            continue
        rpb[(r["station"], r["signal"])][kt(r["tow"])] = float(r["value_m"])
        rpb_sd[(r["station"], r["signal"])][kt(r["tow"])] = float(r["sigma_m"])
    dclk, csd = collections.defaultdict(dict), collections.defaultdict(dict)
    for r in rows(os.path.join(logs, "network_anchor_guard.csv")):
        if r.get("dclk", "") not in ("", None):
            dclk[kt(r["tow"])][r["sat"]] = float(r["dclk"])
            csd[kt(r["tow"])][r["sat"]] = float(r["clk_sd"])

    # truth of the stations
    tclk, tzwd, tion = {}, {}, {}
    for s in stations:
        d = os.path.join(a.truth_root, s)
        tclk[s] = {kt(r["tow_s"]): float(r["clock_bias_m"]) for r in rows(os.path.join(d, "truth_clock.csv"))}
        tzwd[s] = {kt(r["tow_s"]): float(r["zwd_m"]) for r in rows(os.path.join(d, "truth_tropo.csv"))}
        for r in rows(os.path.join(d, "truth_atmo.csv")):
            tion[(s, r["satellite"], kt(r["tow_s"]))] = float(r["I_L1_m"])

    def station_terms(s, p, t):
        """d e_clk, m * d e_zwd, median d e_I over the station's satellites, and its satellites, or None."""
        try:
            dc = (clk[s][t] - tclk[s][t]) - (clk[s][p] - tclk[s][p])
            dz = (zwd[s][t] - tzwd[s][t]) - (zwd[s][p] - tzwd[s][p])
        except KeyError:
            return None
        sats, maps, dis = [], [], []
        for (st_, sat), v in iono.items():
            if st_ != s or t not in v or p not in v:
                continue
            try:
                di = (v[t][0] - tion[(s, sat, t)]) - (v[p][0] - tion[(s, sat, p)])
            except KeyError:
                continue
            sats.append(sat)
            maps.append(1.0 / max(0.1, math.sin(math.radians(v[t][1]))))
            dis.append(di)
        if not sats:
            return None
        try:
            db = dcb[s][t] - dcb[s][p]
        except KeyError:
            db = 0.0
        return dc, st.median(maps) * dz, st.median(dis), sats, db

    out = []
    for p, t in zip(ep, ep[1:]):
        sh = {}
        for sig in LAM:
            d = [P[t][k] - P[p][k] for k in P[t] if k in P[p] and k[1] == sig]
            if d:
                sh[sig] = st.median(d)
        if len(sh) < 2:
            continue
        rt = station_terms(root, p, t)
        if rt is None:
            continue
        mus = st.median(dclk[t].values()) if dclk.get(t) else 0.0
        ctrl = [station_terms(s, p, t) for s in stations if s != root]
        ctrl = [c for c in ctrl if c is not None]
        cm = (st.median(c[0] for c in ctrl), st.median(c[1] for c in ctrl), st.median(c[2] for c in ctrl)) \
            if ctrl else (0.0, 0.0, 0.0)
        rmv = {}
        for sig in LAM:
            d = [rpb[(s, sig)][t] - rpb[(s, sig)][p] for s in stations if s != root
                 and t in rpb[(s, sig)] and p in rpb[(s, sig)]]
            rmv[sig] = st.median(d) if d else float("nan")
        out.append({"min": (t - t0) / 60.0, "s1": sh["L1C"], "s2": sh["L2W"], "clk": rt[0], "zwd": rt[1],
                    "ion": rt[2], "dcb": rt[4], "musat": mus, "c_clk": cm[0], "c_zwd": cm[1], "c_ion": cm[2],
                    "rpb1": rmv["L1C"], "rpb2": rmv["L2W"]})

    print("%s: root %s (the chain's root receiver); %d epoch pairs" % (os.path.basename(a.run.rstrip("/\\")), root, len(out)))
    for w in a.windows.split(","):
        lo, hi = (float(x) for x in w.split("-"))
        sel = [o for o in out if lo <= o["min"] < hi]
        if len(sel) < 5:
            continue
        print("  %g-%g min (%d epochs): median |shared| L1C %.1f mm, L2W %.1f mm; corr(shared, -median non-root "
              "receiver phase bias move) %.3f / %.3f" % (
                  lo, hi, len(sel), 1000 * st.median(abs(o["s1"]) for o in sel), 1000 * st.median(abs(o["s2"]) for o in sel),
                  corr([o["s1"] for o in sel], [-o["rpb1"] for o in sel]),
                  corr([o["s2"] for o in sel], [-o["rpb2"] for o in sel])))
        for sig, key in (("L1C", "s1"), ("L2W", "s2")):
            y = [o[key] for o in sel]
            terms = {
                "root clock": [-o["clk"] for o in sel],
                "satellites' common clock update": [o["musat"] for o in sel],
                "root wet delay (mapped)": [-o["zwd"] for o in sel],
                "root ionosphere (x mu_b)": [MU[sig] * o["ion"] for o in sel],
            }
            ctrl = {
                "root receiver DCB change (raw)": [o["dcb"] for o in sel],
                "median other station clock": [-o["c_clk"] for o in sel],
                "median other station wet delay": [-o["c_zwd"] for o in sel],
                "median other station ionosphere": [MU[sig] * o["c_ion"] for o in sel],
            }
            pred = [sum(v[i] for v in terms.values()) for i in range(len(sel))]
            print("    %s: the four root terms summed: corr %.3f, variance explained %.1f %%" % (
                sig, corr(y, pred), 100 * explained(y, pred)))
            for name, v in list(terms.items()) + list(ctrl.items()):
                print("      %-34s corr %+.3f  explained alone %+7.1f %%  median |term| %.1f mm" % (
                    name, corr(y, v), 100 * explained(y, v), 1000 * st.median(abs(x) for x in v)))
    # formal sigmas by 5 minutes
    print("  formal sigmas (median over the 5 min bin): root clock, root DCB, root wet delay, non-root receiver "
          "phase bias L1C (median over stations), satellite clock (median), metres")
    bins = collections.defaultdict(lambda: collections.defaultdict(list))
    for t in ep:
        b = int((t - t0) / 60.0 // 5) * 5
        if t in clk_sd.get(root, {}):
            bins[b]["clk"].append(clk_sd[root][t])
        if t in dcb_sd.get(root, {}):
            bins[b]["dcb"].append(dcb_sd[root][t])
        if t in zwd_sd.get(root, {}):
            bins[b]["zwd"].append(zwd_sd[root][t])
        v = [rpb_sd[(s, "L1C")][t] for s in stations if s != root and t in rpb_sd.get((s, "L1C"), {})]
        if v:
            bins[b]["rpb"].append(st.median(v))
        if csd.get(t):
            bins[b]["sclk"].append(st.median(csd[t].values()))
    for b in sorted(bins):
        f = lambda k: ("%.4f" % st.median(bins[b][k])) if bins[b][k] else "-"
        print("    %3d min: clock %s  DCB %s  wet delay %s  receiver phase bias %s  satellite clock %s" % (
            b, f("clk"), f("dcb"), f("zwd"), f("rpb"), f("sclk")))
    if a.series:
        with open(a.series, "w", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=list(out[0].keys()))
            w.writeheader()
            w.writerows(out)


if __name__ == "__main__":
    main()

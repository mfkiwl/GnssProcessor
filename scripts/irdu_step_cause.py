#!/usr/bin/env python3
"""Card IRDU section 13 (part 5): what causes the phase steps a stream declares, and the slip flags behind them.

    py -3.14 scripts/irdu_step_cause.py steps  <network run> [--to-min 40] [--list N]
    py -3.14 scripts/irdu_step_cause.py flags  <network run> [--truth-root DIR] [--bin-min 5]
    py -3.14 scripts/irdu_step_cause.py iftd   <network run>
    py -3.14 scripts/irdu_step_cause.py common <network run> [--truth-root DIR] [--station NAME]

steps   replays the emitter's phase discontinuity rule over the run's products.txt (NetworkProductEmitter: the counter
        of a satellite and signal steps when its emitted bias moves by more than discfrac * lambda between consecutive
        emissions, after the satellite's declared level step, the C record's lvl= token, is removed; or on a forced
        bump, the E record's datum_consts or an R record naming the satellite) and gives every declared step from the
        run's first epoch to --to-min one cause, the first of these that applies, searched at the step's epoch and
        at the epoch before it:
          slip:<detector>  a slip flag on an arc of the satellite, at any station: the IF-TD pool or reference gate,
                           MW (refloat or cold diagnostic), the receiver's loss-of-lock flag, RAIM attribution that
                           acted, the within-epoch test, the gross-LOS screen, the GF jump test, a gap re-entry, a
                           wind-up restart, the band-scope verdict that follows a flag;
          chain:<event>    a chain event of the satellite: a CHAIN, PHASE_DATUM, PHASE_ANCHOR, PBGAUGE, STRANSFORM or
                           TOPOLOGY event, a tree edge that is not the same edge as at the epoch before, a pin move;
          datum:<event>    a datum or clock event of the satellite: CLK_ANCHOR, CB_DATUM, RETRO, READMIT, PB_HOLD, an
                           anchor-guard decision other than ok, a forced bump;
          epoch:<event>    an acting event of another satellite or of a station at the same epochs;
          none             nothing found.
        Observe-only tiers (MDB, PRIORRES, CONGRUENCE, the per-epoch oracle-pin marker) are not causes.  Each step's
        move is also split into the part every satellite of the signal shares at that epoch (the median over the
        satellites with a baseline) and the satellite's own part, and the steps whose own part alone crosses the gate
        are counted.
flags   slip flags by detector in bins of --bin-min over the run, with the true slips of the fixture in the same bins
        (<truth root>/<station>/truth_slips.csv, restricted to the (station, satellite) arcs the run observed).
iftd    every IF-TD flag (pool and reference gate): the statistic, its threshold and the terms of the scale, and the
        events at that epoch for that station and satellite (the response).
common  the part of the phase-bias moves every satellite shares, in cycles (the median over the satellites of the
        move on each band divided by its wavelength), against the estimated receiver clock's error change of the
        named station (default: the run's clock datum station) and the median over the other stations, with
        correlations by window.
"""
import argparse
import collections
import csv
import glob
import json
import math
import os
import statistics as st

C0 = 299792458.0
FREQ = {("G", "L1C"): 1575.42e6, ("G", "L1W"): 1575.42e6, ("G", "L2W"): 1227.60e6, ("G", "L2L"): 1227.60e6,
        ("G", "L5Q"): 1176.45e6, ("E", "L1C"): 1575.42e6, ("E", "L1X"): 1575.42e6, ("E", "L5Q"): 1176.45e6,
        ("E", "L5X"): 1176.45e6, ("E", "L7Q"): 1207.14e6, ("C", "L2I"): 1561.098e6, ("C", "L6I"): 1268.52e6}

SLIP_TIERS = {"T0_mw_detect", "T1_if_slip", "T1_gf_jump", "T0_gap", "T0_windup", "T2_within_epoch", "T3_raim",
              "T4_attrib", "GROSSLOS", "T0_band_scope", "T5_clock_model", "T6_clock_monitor", "T3_stafactor",
              "T4_prior"}
CHAIN_TIERS = {"CHAIN", "PHASE_DATUM", "PHASE_ANCHOR", "PBGAUGE", "STRANSFORM", "TOPOLOGY"}
DATUM_TIERS = {"CLK_ANCHOR", "CB_DATUM", "RETRO", "READMIT", "PB_HOLD"}
STATION_TIERS = {"ZWD"}
OBSERVE_TIERS = {"MDB", "PRIORRES", "CONGRUENCE", "REDUNDANCY"}


def lam(sat, sig):
    f = FREQ.get((sat[0], sig))
    return C0 / f if f else None


def rows(path):
    if not os.path.exists(path):
        return []
    with open(path, newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(ln for ln in fh if not ln.startswith("#")))


def key_t(tow):
    return round(float(tow), 3)


def read_products(path):
    """Epochs, the phase biases and clocks per epoch, the forced bumps, the discfrac of the S record."""
    ep, P, lvl, forced_const, retro = [], {}, {}, {}, {}
    discfrac = 0.25
    tow = None
    with open(path, encoding="utf-8") as fh:
        for ln in fh:
            f = ln.rstrip("\n").split(",")
            if f[0] == "S":
                for tok in f:
                    if tok.startswith("discfrac="):
                        discfrac = float(tok.split("=", 1)[1])
            elif f[0] == "E":
                tow = key_t(f[2])
                ep.append(tow)
                P[tow], lvl[tow], retro[tow] = {}, {}, set()
                consts = set()
                if len(f) > 6 and f[6] not in ("", "0"):
                    consts = set(f[7]) if len(f) > 7 and f[7] else {"*"}
                forced_const[tow] = consts
            elif f[0] == "P" and tow is not None:
                P[tow][(f[1], f[2])] = float(f[3])
            elif f[0] == "C" and tow is not None:
                for tok in f[3:]:
                    if tok.startswith("lvl="):
                        lvl[tow][f[1]] = float(tok.split("=", 1)[1])
            elif f[0] == "R" and tow is not None:
                retro[tow].update(x for x in f[1:] if x)
    return ep, P, lvl, forced_const, retro, discfrac


def declared_steps(ep, P, lvl, forced_const, retro, discfrac):
    """The emitter's phase-disc rule, replayed: (tow, prev_tow, sat, sig, move_m, raw_move_m, kind)."""
    last, out = {}, []
    for t in ep:
        for (sat, sig), b in P[t].items():
            k = (sat, sig)
            lv = lvl[t].get(sat, 0.0)
            if k in last:
                prev_t, prev_b = last[k]
                raw = b - prev_b
                d = raw - lv
                L = lam(sat, sig)
                forced = ("*" in forced_const[t]) or (sat[0] in forced_const[t]) or (sat in retro[t])
                jump = L is not None and abs(d) > discfrac * L
                if forced or jump:
                    out.append((t, prev_t, sat, sig, d, raw, "forced" if forced and not jump else "value"))
            last[k] = (t, b)
    return out


def shared_moves(ep, P):
    """Per epoch and signal: the median move over the satellites with a baseline at the epoch before."""
    sh = {}
    for a, b in zip(ep, ep[1:]):
        by = collections.defaultdict(list)
        for (sat, sig), v in P[b].items():
            if (sat, sig) in P[a]:
                by[(sat[0], sig)].append(v - P[a][(sat, sig)])
        for g, v in by.items():
            sh[(b, g)] = st.median(v)
    return sh


def load_causes(run, ep):
    """Index of acting events: own[(tow, sat)] -> labels, others[tow] -> labels (station or other satellites)."""
    logs = os.path.join(run, "logs")
    own = collections.defaultdict(set)
    anyev = collections.defaultdict(list)       # tow -> [(sat, label)]
    observe = collections.Counter()
    for r in rows(os.path.join(logs, "network_events.csv")):
        t = key_t(r["tow"])
        tier, event, action = r["tier"], r["event"], r["action"]
        if tier in OBSERVE_TIERS or (tier == "INJECT" and action == "oracle_pin_epoch"):
            observe[(tier, event)] += 1
            continue
        if tier in SLIP_TIERS:
            if tier == "T1_if_slip":
                lab = "slip:IF-TD reference gate" if event.startswith("refsat") else "slip:IF-TD pool (%s)" % event
            elif tier == "T0_mw_detect":
                lab = "slip:MW %s" % action
            else:
                lab = "slip:%s %s" % (tier, event)
        elif tier in CHAIN_TIERS:
            lab = "chain:%s %s" % (tier, event)
        elif tier in DATUM_TIERS:
            lab = "datum:%s %s" % (tier, event)
        elif tier == "INJECT":
            lab = "chain:oracle pin %s" % action
        else:
            lab = "event:%s %s" % (tier, event)
        sat = r["sat"]
        if sat:
            own[(t, sat)].add(lab)
        anyev[t].append((sat or r["station"], lab))
    for r in rows(os.path.join(logs, "network_raim_attrib.csv")):
        if r.get("acted") == "1":
            t = key_t(r["tow"])
            sat = r["entity"].split("/")[-1]
            own[(t, sat)].add("slip:RAIM attribution")
            anyev[t].append((sat, "slip:RAIM attribution"))
    for r in rows(os.path.join(logs, "network_slip_raw.csv")):
        if r.get("lli1", "0") not in ("0", "") or r.get("lli2", "0") not in ("0", ""):
            t = key_t(r["tow"])
            own[(t, r["sat"])].add("slip:loss-of-lock flag")
            anyev[t].append((r["sat"], "slip:loss-of-lock flag"))
    for r in rows(os.path.join(logs, "network_if_slip.csv")):
        if r.get("flagged") == "1":
            t = key_t(r["tow"])
            lab = "slip:IF-TD reference gate" if r.get("is_ref") == "1" else "slip:IF-TD pool"
            own[(t, r["sat"])].add(lab)
            anyev[t].append((r["sat"], lab))
    for r in rows(os.path.join(logs, "network_anchor_guard.csv")):
        if r.get("decision", "ok") not in ("ok", ""):
            t = key_t(r["tow"])
            own[(t, r["sat"])].add("datum:anchor guard %s" % r["decision"])
            anyev[t].append((r["sat"], "datum:anchor guard %s" % r["decision"]))
    edges = collections.defaultdict(dict)
    for r in rows(os.path.join(logs, "network_chain_edges.csv")):
        t = key_t(r["tow"])
        if t == ep[0]:
            continue
        sat = r["edge_sat"]
        if r["legacy_cause"] not in ("same_edge",):
            own[(t, sat)].add("chain:edge %s" % r["legacy_cause"])
            anyev[t].append((sat, "chain:edge %s" % r["legacy_cause"]))
        try:
            pm = abs(float(r["pinmove_m"] or 0.0))
        except ValueError:
            pm = 0.0
        if pm > 1e-6:
            own[(t, sat)].add("chain:pin move")
            anyev[t].append((sat, "chain:pin move"))
    return own, anyev, observe


ORDER = ("slip", "chain", "datum", "epoch")


def classify(step, prev_ep, own, anyev):
    t, prev_t, sat = step[0], step[1], step[2]
    win = {t, prev_ep.get(t, t)}
    labs = set()
    for w in win:
        labs |= own.get((w, sat), set())
    for cat in ORDER[:3]:
        hit = sorted(l for l in labs if l.startswith(cat + ":"))
        if hit:
            return hit[0], hit
    other = sorted({l for w in win for s, l in anyev.get(w, []) if s != sat and not l.startswith("event:")})
    if other:
        return "epoch:" + other[0].split(":", 1)[1], other
    if step[6] == "forced":
        return "datum:forced bump", ["datum:forced bump"]
    return "none", []


def cmd_steps(a):
    ep, P, lvl, fc, retro, discfrac = read_products(os.path.join(a.run, "products.txt"))
    t0 = ep[0]
    prev_ep = dict(zip(ep[1:], ep))
    steps = declared_steps(ep, P, lvl, fc, retro, discfrac)
    sh = shared_moves(ep, P)
    own, anyev, observe = load_causes(a.run, ep)
    sel = [s for s in steps if (s[0] - t0) / 60.0 <= a.to_min]
    allm = sum(abs(s[4]) for s in sel)
    print("%s: discfrac %.2f; %d declared phase steps over the run, %d in the first %g min, %.2f m moved; last "
          "declared step at %.1f min (over the run %.1f min)" % (
              os.path.basename(a.run.rstrip("/\\")), discfrac, len(steps), len(sel), a.to_min, allm,
              (sel[-1][0] - t0) / 60.0 if sel else float("nan"), (steps[-1][0] - t0) / 60.0 if steps else float("nan")))
    bins = collections.Counter(int((s[0] - t0) / 60.0 // 5) * 5 for s in steps)
    print("  by 5 min (all of the run): " + ", ".join("%d: %d" % (k, v) for k, v in sorted(bins.items())))
    cause = collections.Counter()
    metres = collections.Counter()
    ownx = 0
    shx = 0
    detail = []
    for s in sel:
        c, labs = classify(s, prev_ep, own, anyev)
        cause[c] += 1
        metres[c] += abs(s[4])
        L = lam(s[2], s[3])
        shared = sh.get((s[0], (s[2][0], s[3])), 0.0)
        o = s[4] - shared
        if abs(o) > discfrac * L:
            ownx += 1
        if abs(shared) > discfrac * L:
            shx += 1
        detail.append(((s[0] - t0) / 60.0, s[2], s[3], s[4], shared, o, c))
    print("  cause | steps | share of steps | share of moved metres")
    for c, n in cause.most_common():
        print("  %-48s %5d  %5.1f %%  %5.1f %%" % (c, n, 100.0 * n / max(1, len(sel)), 100.0 * metres[c] / max(1e-12, allm)))
    print("  steps whose own part alone (move minus the median move of the signal's satellites) crosses the gate: "
          "%d of %d; whose shared part alone crosses it: %d" % (ownx, len(sel), shx))
    ob = collections.Counter(int(d[0] // 5) * 5 for d in detail
                             if abs(d[5]) > discfrac * lam(d[1], d[2]))
    print("  own part alone crossing, by 5 min: " + ", ".join("%d: %d" % (k, v) for k, v in sorted(ob.items())))
    # Control for the coincidence classes: steps per epoch at epochs with an acting event anywhere in the network
    # (at the epoch or the one before) against epochs without one, by 5 min window.
    nstep = collections.Counter(s[0] for s in sel)
    print("  steps per epoch, epochs with an acting event anywhere (this epoch or the one before) | without:")
    for lo in range(0, int(a.to_min), 5):
        w = [t for t in ep[1:] if lo <= (t - t0) / 60.0 < lo + 5]
        hit = [t for t in w if any(not l.startswith("event:") for s, l in anyev.get(t, []) + anyev.get(prev_ep.get(t, t), []))]
        miss = [t for t in w if t not in hit]
        f = (lambda v: "%5.1f (%2d epochs)" % (st.mean(nstep.get(t, 0) for t in v), len(v)) if v else "    - ( 0 epochs)")
        print("    %2d-%2d min: %s | %s" % (lo, lo + 5, f(hit), f(miss)))
    print("  observe-only events in the run (not causes): " + ", ".join("%s/%s %d" % (k[0], k[1], v)
                                                                       for k, v in sorted(observe.items())))
    if a.list:
        for d in detail[:a.list]:
            print("    %6.1f min %s %s move %+7.1f mm shared %+7.1f own %+7.1f  %s" % (
                d[0], d[1], d[2], 1000 * d[3], 1000 * d[4], 1000 * d[5], d[6]))


def truth_slips(root, arcs, t_lo, t_hi):
    out = []
    for f in glob.glob(os.path.join(root, "*", "truth_slips.csv")):
        sta = os.path.basename(os.path.dirname(f))
        for r in rows(f):
            t = float(r["tow_s"])
            if (sta, r["satellite"]) in arcs and t_lo <= t <= t_hi:
                out.append((t, sta, r["satellite"], r["signal"], float(r["delta_cycles"])))
    return out


def cmd_flags(a):
    logs = os.path.join(a.run, "logs")
    raw = rows(os.path.join(logs, "network_slip_raw.csv"))
    tows = sorted({key_t(r["tow"]) for r in raw})
    t0, t1 = tows[0], tows[-1]
    arcs = {(r["station"], r["sat"]) for r in raw}
    B = a.bin_min
    tab = collections.defaultdict(collections.Counter)

    def add(t, det):
        tab[det][int((t - t0) / 60.0 // B) * B] += 1
    for r in rows(os.path.join(logs, "network_if_slip.csv")):
        if r.get("flagged") == "1":
            add(key_t(r["tow"]), "IF-TD reference gate" if r.get("is_ref") == "1" else "IF-TD pool")
    for r in rows(os.path.join(logs, "network_events.csv")):
        t, tier, ev, act = key_t(r["tow"]), r["tier"], r["event"], r["action"]
        if tier == "T0_mw_detect":
            add(t, "MW %s" % act)
        elif tier == "T1_if_slip":
            add(t, "IF-TD event %s/%s" % (ev, act))
        elif tier in ("T1_gf_jump", "T0_gap", "T0_windup", "T2_within_epoch", "T3_raim", "GROSSLOS",
                      "T5_clock_model", "T6_clock_monitor", "T3_stafactor"):
            add(t, "%s %s/%s" % (tier, ev, act))
        elif tier == "ZWD" and ev == "slip_latch":
            add(t, "ZWD slip latch (follows a flag)")
        elif tier == "T0_band_scope":
            add(t, "band-scope verdict on an MW candidate")
    for r in rows(os.path.join(logs, "network_raim_attrib.csv")):
        if r.get("acted") == "1":
            add(key_t(r["tow"]), "RAIM attribution (acted)")
    for r in raw:
        if r.get("lli1", "0") not in ("0", "") or r.get("lli2", "0") not in ("0", ""):
            add(key_t(r["tow"]), "loss-of-lock flag")
    tr = truth_slips(a.truth_root, arcs, t0, t1) if a.truth_root else []
    for t, sta, sat, sig, dc in tr:
        add(t, "TRUE SLIPS (fixture)")
    nb = int((t1 - t0) / 60.0 // B) + 1
    cols = [i * B for i in range(nb)]
    print("%s: %d arcs observed, %.0f min; slip flags by detector in %g min bins (bin start, minutes)" % (
        os.path.basename(a.run.rstrip("/\\")), len(arcs), (t1 - t0) / 60.0, B))
    print("  %-40s %s | total" % ("detector", " ".join("%4d" % c for c in cols)))
    for det in sorted(tab):
        print("  %-40s %s | %d" % (det, " ".join("%4d" % tab[det].get(c, 0) for c in cols), sum(tab[det].values())))
    if a.truth_root:
        print("  true slips on the run's arcs: %d" % len(tr) + "".join(
            "\n    %.1f min %s %s %s %+g cycles" % ((t - t0) / 60.0, sta, sat, sig, dc) for t, sta, sat, sig, dc in tr))


def cmd_iftd(a):
    logs = os.path.join(a.run, "logs")
    ifr = [r for r in rows(os.path.join(logs, "network_if_slip.csv")) if r.get("flagged") == "1"]
    ev = rows(os.path.join(logs, "network_events.csv"))
    t0 = min(key_t(r["tow"]) for r in rows(os.path.join(logs, "network_epoch_status.csv")))
    iev = [r for r in ev if r["tier"] == "T1_if_slip"]
    print("%s: %d flagged IF-TD rows, %d T1_if_slip events" % (os.path.basename(a.run.rstrip("/\\")), len(ifr), len(iev)))
    for r in iev:
        t = key_t(r["tow"])
        print("  event %.1f min %s %s %s/%s statistic %s threshold %s %s" % (
            (t - t0) / 60.0, r["station"], r["sat"], r["event"], r["action"], r["statistic"], r["threshold"],
            r["detail"][:200]))
        same = [x for x in ev if key_t(x["tow"]) in (t, t + 30.0) and (x["sat"] == r["sat"] or x["station"] == r["station"])
                and x["tier"] not in OBSERVE_TIERS and x is not r]
        for x in same:
            print("     response %.1f min %s %s %s/%s/%s %s" % ((key_t(x["tow"]) - t0) / 60.0, x["station"], x["sat"],
                                                              x["tier"], x["event"], x["action"], x["detail"][:140]))
    for r in ifr:
        t = key_t(r["tow"])
        print("  row %.1f min %s %s %s-%s elev %s dd %s med %s s_pool %s ewma %s count %s w %s s_eff %s map %s thr %s "
              "floor %s |dev| %s warm %s ref %s" % ((t - t0) / 60.0, r["station"], r["sat"], r["sig1"], r["sig2"],
                                                    r["elev_deg"], r["dd_m"], r["med_m"], r["s_pool_m"],
                                                    r["ewma_scale_m"], r["count"], r["w_shrink"], r["s_eff_m"],
                                                    r["elev_map"], r["thr_m"], r["floor_m"], r["abs_dev_m"],
                                                    r["carry_warm"], r["is_ref"]))


def corr(x, y):
    mx, my = st.mean(x), st.mean(y)
    den = math.sqrt(sum((u - mx) ** 2 for u in x) * sum((v - my) ** 2 for v in y))
    return sum((u - mx) * (v - my) for u, v in zip(x, y)) / den if den > 0 else float("nan")


def cmd_common(a):
    ep, P, lvl, fc, retro, discfrac = read_products(os.path.join(a.run, "products.txt"))
    t0 = ep[0]
    station = a.station
    if not station:
        try:
            station = json.load(open(os.path.join(a.run, "arm.json")))["network"]["clock_datum_station"]
        except (KeyError, OSError, ValueError):
            station = ""
    clk = collections.defaultdict(dict)
    for r in rows(os.path.join(a.run, "logs", "network_rx_states.csv")):
        if r["kind"] == "CLK":
            clk[key_t(r["tow"])][r["station"]] = float(r["value_m"])
    sts = sorted({s for t in clk for s in clk[t]})
    truth = {}
    for s in sts:
        p = os.path.join(a.truth_root, s, "truth_clock.csv")
        truth[s] = {key_t(r["tow_s"]): float(r["clock_bias_m"]) for r in rows(p)}
    out = []
    for p_, b in zip(ep, ep[1:]):
        xs = []
        for sig in ("L1C", "L2W"):
            d = [P[b][k] - P[p_][k] for k in P[b] if k in P[p_] and k[1] == sig and k[0][0] == "G"]
            if d:
                xs.append(st.median(d) / lam("G", sig))
        if not xs:
            continue

        def err(s):
            return (clk[b][s] - truth[s][b]) - (clk[p_][s] - truth[s][p_])
        ok = [s for s in sts if s in clk[b] and s in clk[p_] and b in truth[s] and p_ in truth[s]]
        if station not in ok:
            continue
        others = [err(s) for s in ok if s != station]
        out.append(((b - t0) / 60.0, sum(xs) / len(xs), err(station), st.median(others) if others else 0.0))
    print("%s: shared move x (cycles, both GPS bands averaged) against the clock error change of %s and the median "
          "of the other stations" % (os.path.basename(a.run.rstrip("/\\")), station))
    for lo, hi in ((0, 5), (5, 40), (15, 40), (40, 120)):
        sel = [o for o in out if lo <= o[0] < hi]
        if len(sel) < 3:
            continue
        print("  %3d-%3d min: n %3d, median |x| %.3f cycles, corr(x, %s) %+.3f, corr(x, others) %+.3f, "
              "median |clock error change| %s %.1f mm, others %.1f mm" % (
                  lo, hi, len(sel), st.median(abs(o[1]) for o in sel), station,
                  corr([o[1] for o in sel], [o[2] for o in sel]), corr([o[1] for o in sel], [o[3] for o in sel]),
                  station, 1000 * st.median(abs(o[2]) for o in sel), 1000 * st.median(abs(o[3]) for o in sel)))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = ap.add_subparsers(dest="cmd", required=True)
    p = sp.add_parser("steps")
    p.add_argument("run")
    p.add_argument("--to-min", type=float, default=40.0)
    p.add_argument("--list", type=int, default=0)
    p = sp.add_parser("flags")
    p.add_argument("run")
    p.add_argument("--truth-root", default="")
    p.add_argument("--bin-min", type=float, default=5.0)
    p = sp.add_parser("iftd")
    p.add_argument("run")
    p = sp.add_parser("common")
    p.add_argument("run")
    p.add_argument("--truth-root", required=True)
    p.add_argument("--station", default="")
    a = ap.parse_args()
    {"steps": cmd_steps, "flags": cmd_flags, "iftd": cmd_iftd, "common": cmd_common}[a.cmd](a)


if __name__ == "__main__":
    main()

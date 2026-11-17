#!/usr/bin/env python3
"""Card IRDU section 11 C: one injected re-seat read against its one-change control, pair by pair on the stream.

    py -3.14 scripts/irdu_event_diff.py <control run or tag> <event run or tag> --event-tow T [--fixture DIR]
        [--source prehold|products] [--settle 0.05] [--json out.json]
    py -3.14 scripts/irdu_event_diff.py --selftest

Both runs are graded against truth with the wire algebra of scripts/simnet_wire_integer_consistency.py (D_WL and
D_NL of every GPS satellite pair, through the code biases; card IRD section 8).  The event's effect on a pair is the
difference delta(t) = D(event run, t) - D(control, t), unwrapped in time, at the epochs both runs emit the pair.  A
pair is MOVED when either satellite is declared by the event run's CHAIN rows at the event epoch (declared_keys:
the released subtree's satellites), else OTHER.

  step      the integer the pair's delta settles on (round of its median over the last 15 min): the frame step of
            the cut release (a declared integer step, not an error)
  excess    |delta(t) - step|: what the event costs the pair beyond its integer step; per 5 min bin after the event,
            p50 and p95 over the pairs of the class
  peak      the largest excess of each pair within 10 min after the event, p50 and max over the class
  settle    the time from the event until the pair's excess stays at or below --settle cycle (on both channels) to
            the end of the run; a pair that never does reads "not within the run"
  before    the largest |delta| over the 10 min before the event (0 when the two runs are identical before it)

The plateau reading of section 11 C is the excess over the last 15 min; the offsets of the event run's pairs against
truth over the same window are printed beside the control's (the |circular mean| of D's fraction).
"""
import argparse
import csv
import json
import math
import os
import sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import simnet_wire_integer_consistency as WIC  # noqa: E402

RUNS = os.environ.get("RAPID_RUNS_ROOT") or "D:/GnssProcessorSupport/runs_nom"


def pct(v, q):
    v = sorted(v)
    if not v:
        return float("nan")
    k = (len(v) - 1) * q / 100.0
    lo = int(math.floor(k))
    hi = min(lo + 1, len(v) - 1)
    return v[lo] + (v[hi] - v[lo]) * (k - lo)


def circ_offset(v):
    s = sum(math.sin(2 * math.pi * x) for x in v)
    c = sum(math.cos(2 * math.pi * x) for x in v)
    return abs(math.atan2(s, c) / (2 * math.pi))


def run_dir(x):
    return x if os.path.isdir(x) else os.path.join(RUNS, "_rap_" + x)


def pair_series(run, fixture, source):
    osb, sc, eps, _ = WIC.dual_load(fixture, run, source)
    out = defaultdict(dict)       # (s, p) -> {tow: (WL, NL)}
    for e in sorted(eps, key=lambda e: e["tow"]):
        v = {s: x for s, x in WIC.dual_sat_values(e, osb, sc, ("L1C", "L2W")).items() if s[0] == "G"}
        sats = sorted(v)
        for i in range(len(sats)):
            for j in range(i + 1, len(sats)):
                ch = WIC.dual_pair_channels(v[sats[i]], v[sats[j]])
                out[(sats[i], sats[j])][round(e["tow"], 3)] = (ch["E1"], ch["E2"])
    return out


def declared_at(run, tow):
    p = os.path.join(run, "logs", "network_events.csv")
    out = set()
    with open(p, encoding="utf-8", errors="replace") as fh:
        for r in csv.DictReader(fh):
            if r.get("tier") == "CHAIN" and r.get("event") == "declared_keys" and abs(float(r["tow"]) - tow) < 1:
                out.add(r["sat"])
    return out


KNL = 1227.60 / (1575.42 - 1227.60)     # f2 / (f1 - f2), GPS L1 / L2


def channels_of(d1, d2):
    """(WL, NL) of a pair's two band differences (cycles; NL in NL cycles), card IRD section 8."""
    wl = d1 - d2
    return wl, d1 + KNL * (wl - round(wl))


def pair_effect(ctl, evt, tow_event, settle):
    """The effect on one pair: ctl and evt map tow -> (D_1, D_2), the pair's band differences against truth (cycles,
    continuous: the wire algebra does not wrap them).  The event's difference is formed per band and then combined,
    delta_WL = dD_1 - dD_2 and delta_NL = dD_1 + f2/(f1-f2) (delta_WL - round(delta_WL)), so that an integer step of the
    wide lane does not leak into the narrow lane.  Returns None without 10 common epochs after the event."""
    tows = sorted(set(ctl) & set(evt))
    after = [t for t in tows if t >= tow_event - 1e-3]
    if len(after) < 10:
        return None
    before = [t for t in tows if tow_event - 600.0 <= t < tow_event - 1e-3]
    delta = {t: channels_of(evt[t][0] - ctl[t][0], evt[t][1] - ctl[t][1]) for t in tows}
    res = {}
    for k, name in ((0, "WL"), (1, "NL")):
        last = [delta[t][k] for t in after if t >= after[-1] - 900.0 + 1e-3]
        j = round(pct(last, 50))
        exc = {t: abs(delta[t][k] - j) for t in after}
        res[name] = {"step": int(j), "excess": exc,
                     "before": max((abs(delta[t][k]) for t in before), default=0.0)}
    # settle: from the event until both channels stay within `settle` to the end
    t_settle = None
    for t in reversed(after):
        if res["WL"]["excess"][t] > settle or res["NL"]["excess"][t] > settle:
            break
        t_settle = t
    res["settle_min"] = None if t_settle is None else (t_settle - tow_event) / 60.0
    res["peak"] = {n: max(res[n]["excess"][t] for t in after if t < tow_event + 600.0) for n in ("WL", "NL")}
    return res


TRUTH_WINDOWS = (("event epoch", 0.0, 0.25), ("0.5-10", 0.25, 10.0), ("10-25", 10.0, 25.0), ("25-45", 25.0, 45.0),
                 ("45-65", 45.0, 65.0), ("65-85", 65.0, 85.0))


def truth_windows(pairs, se, sc, tow_event):
    """The pairs read against truth (section 11.4's annotation): |wrap(D_WL)| and |wrap(D_NL)| p50 over the pairs and
    the epochs of each window after the event, event run / control (each run at the epochs it emits the pair)."""
    out = {}
    for name, lo, hi in TRUTH_WINDOWS:
        row = {}
        for k, ch in ((0, "WL"), (1, "NL")):
            vals = []
            for series in (se, sc):
                v = []
                for p in pairs:
                    for t, d in series[p].items():
                        if tow_event + 60.0 * lo - 1e-3 <= t < tow_event + 60.0 * hi - 1e-3:
                            x = channels_of(*d)[k]
                            v.append(abs(x - round(x)))
                vals.append(pct(v, 50))
            row[ch] = vals
        out[name] = row
    return out


def analyse(ctl_run, evt_run, fixture, tow_event, source="prehold", settle=0.05):
    sc = pair_series(ctl_run, fixture, source)
    se = pair_series(evt_run, fixture, source)
    moved_sats = declared_at(evt_run, tow_event)
    classes = defaultdict(list)
    for k in sorted(set(sc) & set(se)):
        eff = pair_effect(sc[k], se[k], tow_event, settle)
        if eff is None:
            continue
        cls = "moved" if (k[0] in moved_sats or k[1] in moved_sats) else "other"
        classes[cls].append((k, eff))
    t_end = max(max(v) for v in se.values())
    out = {"control": ctl_run, "event": evt_run, "event_tow": tow_event, "moved_sats": sorted(moved_sats),
           "settle_bar": settle, "classes": {}}
    for cls, rows in classes.items():
        o = {"n_pairs": len(rows)}
        for n in ("WL", "NL"):
            steps = defaultdict(int)
            for _, e in rows:
                steps[e[n]["step"]] += 1
            o[n] = {"steps": dict(sorted(steps.items())),
                    "before_max": max(e[n]["before"] for _, e in rows),
                    "peak_p50": pct([e["peak"][n] for _, e in rows], 50),
                    "peak_max": max(e["peak"][n] for _, e in rows), "bins": {}}
            nb = int((t_end - tow_event) // 300) + 1
            for b in range(nb):
                lo, hi = tow_event + 300 * b, tow_event + 300 * (b + 1)
                vals = [x for _, e in rows for t, x in e[n]["excess"].items() if lo - 1e-3 <= t < hi - 1e-3]
                if vals:
                    o[n]["bins"]["%d-%d" % (5 * b, 5 * (b + 1))] = (pct(vals, 50), pct(vals, 95))
        sm = [e["settle_min"] for _, e in rows]
        o["settle_min"] = {"p50": pct([x for x in sm if x is not None], 50) if any(x is not None for x in sm) else None,
                           "max": max((x for x in sm if x is not None), default=None),
                           "never": sum(1 for x in sm if x is None)}
        # plateau offsets against truth, last 15 min, event run and control
        offs_e, offs_c = [], []
        for k, _ in rows:
            te = [t for t in se[k] if t > t_end - 900.0]
            if len(te) >= 10:
                offs_e.append(circ_offset([channels_of(*se[k][t])[1] for t in te]))
                offs_c.append(circ_offset([channels_of(*sc[k][t])[1] for t in te if t in sc[k]]))
        o["plateau_nl_offset_p50"] = {"event": pct(offs_e, 50), "control": pct(offs_c, 50)}
        offs_e, offs_c = [], []
        for k, _ in rows:
            te = [t for t in se[k] if t > t_end - 900.0]
            if len(te) >= 10:
                offs_e.append(circ_offset([channels_of(*se[k][t])[0] for t in te]))
                offs_c.append(circ_offset([channels_of(*sc[k][t])[0] for t in te if t in sc[k]]))
        o["plateau_wl_offset_p50"] = {"event": pct(offs_e, 50), "control": pct(offs_c, 50)}
        o["truth_windows"] = truth_windows([k for k, _ in rows], se, sc, tow_event)
        o["pairs"] = [{"pair": "%s-%s" % k, "settle_min": e["settle_min"], "step_wl": e["WL"]["step"],
                       "step_nl": e["NL"]["step"], "peak_wl": e["peak"]["WL"], "peak_nl": e["peak"]["NL"]}
                      for k, e in rows]
        out["classes"][cls] = o
    return out


def print_result(res):
    print("== event %s against control %s at TOW %.0f; moved satellites (declared): %s; settle bar %.2f cycle"
          % (res["event"], res["control"], res["event_tow"], ",".join(res["moved_sats"]) or "-", res["settle_bar"]))
    for cls in ("moved", "other"):
        o = res["classes"].get(cls)
        if not o:
            continue
        print("%s pairs: %d" % (cls, o["n_pairs"]))
        for n in ("WL", "NL"):
            x = o[n]
            print("  %s: integer steps %s; |delta| before the event max %.4f; peak excess p50 %.3f max %.3f"
                  % (n, x["steps"], x["before_max"], x["peak_p50"], x["peak_max"]))
            print("     excess p50/p95 by 5 min after the event: " + ", ".join(
                "%s %.3f/%.3f" % (b, v[0], v[1]) for b, v in x["bins"].items()))
        s = o["settle_min"]
        print("  settle (both channels within the bar to the end): p50 %s min, max %s min, never %d"
              % ("%.1f" % s["p50"] if s["p50"] is not None else "-", "%.1f" % s["max"] if s["max"] is not None else "-",
                 s["never"]))
        print("  plateau (last 15 min) offset p50 against truth: WL event %.3f control %.3f; NL event %.3f control %.3f"
              % (o["plateau_wl_offset_p50"]["event"], o["plateau_wl_offset_p50"]["control"],
                 o["plateau_nl_offset_p50"]["event"], o["plateau_nl_offset_p50"]["control"]))
        print("  against truth, |wrap| p50 event / control by window after the event: " + "; ".join(
            "%s WL %.3f/%.3f NL %.3f/%.3f" % (w, v["WL"][0], v["WL"][1], v["NL"][0], v["NL"][1])
            for w, v in o["truth_windows"].items()))


def selftest():
    ok = True

    def chk(c, msg):
        nonlocal ok
        print(("PASS " if c else "FAIL ") + msg)
        ok &= bool(c)

    tows = [1000.0 + 30 * i for i in range(80)]
    ctl = {t: (0.1, 0.3) for t in tows}
    ev_t = tows[20]
    evt = {}
    for i, t in enumerate(tows):
        if t < ev_t:
            evt[t] = ctl[t]
        else:
            tr = 0.3 * math.exp(-(i - 20) / 5.0)      # a transient on both bands that decays below 0.05 in about 9 epochs
            evt[t] = (0.1 - 1 + tr, 0.3 - 3 + tr)      # band 1 steps -1, band 2 steps -3: WL +2, NL -1
    e = pair_effect(ctl, evt, ev_t, 0.05)
    chk(e["WL"]["step"] == 2 and e["NL"]["step"] == -1, "the integer steps of a cut release")
    chk(e["WL"]["before"] == 0.0, "identical before the event")
    chk(e["settle_min"] is not None and 4.0 <= e["settle_min"] <= 5.0, "settles when the transient falls below the bar (%.1f min)" % (e["settle_min"] or -1))
    chk(abs(e["peak"]["NL"] - 0.3) < 1e-9 and e["peak"]["WL"] < 1e-9,
        "the peak is the largest excess within 10 min (a transient common to both bands leaves the wide lane alone)")
    return ok


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("control", nargs="?")
    ap.add_argument("event", nargs="?")
    ap.add_argument("--event-tow", type=float)
    ap.add_argument("--fixture", default="C:/GnssProcessor/runs/simarl_r3c")
    ap.add_argument("--source", default="prehold", choices=("prehold", "products"))
    ap.add_argument("--settle", type=float, default=0.05)
    ap.add_argument("--json")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        sys.exit(0 if selftest() else 1)
    res = analyse(run_dir(a.control), run_dir(a.event), a.fixture, a.event_tow, a.source, a.settle)
    print_result(res)
    if a.json:
        with open(a.json, "w") as fh:
            json.dump(res, fh, indent=1)


if __name__ == "__main__":
    main()

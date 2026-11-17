#!/usr/bin/env python3
"""Card IRDU, the trace of a stream's integer property in time: the wire's between-satellite potential against
truth (the x-corrected E_b of scripts/simnet_wire_integer_consistency.py), pair by pair and epoch by epoch, split into
what a user could and could not fix.

    py -3.14 scripts/irdu_wire_trace.py <net tag> [--from-min 30] [--jump 0.10] [--list 15]

Per satellite pair (s, p) of one constellation and epoch, unwrapped in time along the pair's common life:
  D_WL = (E1_s - E2_s) - (E1_p - E2_p)                (wide lane, cycles)
  D_NL = D1 + f2/(f1-f2) (D_WL - round(D_WL))         (the narrow lane of the ionosphere-free row, NL cycles)
Readings (each with n):
  offset   per pair, |circular mean of the fraction| over the window: a constant non-integer offset is the frame's
           defect (the user's float converges to it)
  wander   per pair, the median |epoch-to-epoch change| and the p95
  jumps    epoch-to-epoch changes above --jump cycles, and the share of them at an epoch with a chain event of either
           satellite (CHAIN rows of logs/network_events.csv: re-host join/leave, cut_release, declared_keys, returning,
           root handover, split, merge), with the leading event names
  drift    per pair, the circular spread of the fraction (1 - resultant length) over the window
"""
import argparse
import csv
import math
import os
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import simnet_wire_integer_consistency as WIC  # noqa: E402

RUNS = Path(os.environ.get("RAPID_RUNS_ROOT") or "D:/GnssProcessorSupport/runs_nom")


def frac(x):
    return x - round(x)


def chain_events(run):
    """{tow: {sat: set(event names)}} from the CHAIN rows of network_events.csv (any column naming a satellite)."""
    p = Path(run) / "logs" / "network_events.csv"
    out = defaultdict(lambda: defaultdict(set))
    if not p.exists():
        return out
    with open(p, encoding="utf-8", errors="replace") as fh:
        rd = csv.reader(fh)
        hdr = next(rd, None)
        if hdr is None:
            return out
        ci = {c: i for i, c in enumerate(hdr)}
        for r in rd:
            if len(r) < len(hdr) or r[ci.get("tier", 2)] != "CHAIN":
                continue
            tow = round(float(r[ci["tow"]]), 3)
            name = r[ci.get("event", 3)]
            for col in ("sat", "station", "detail"):
                if col in ci:
                    for tok in r[ci[col]].replace("=", " ").split():
                        if len(tok) == 3 and tok[0] in "GERC" and tok[1:].isdigit():
                            out[tow][tok].add(name)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("tag")
    ap.add_argument("--fixture", default=None)
    ap.add_argument("--from-min", type=float, default=30.0)
    ap.add_argument("--jump", type=float, default=0.10)
    ap.add_argument("--list", type=int, default=15)
    ap.add_argument("--source", default="products", choices=("products", "prehold"))
    a = ap.parse_args()
    run = RUNS / ("_rap_" + a.tag)
    if a.fixture is None:
        import json
        fx = json.load(open(run / "rapid.json"))["ird"]["fixture"]
        a.fixture = fx if os.path.isabs(fx) else os.path.join("C:/GnssProcessor", fx)
    osb, sc, eps, _ = WIC.dual_load(a.fixture, str(run), a.source)
    eps = sorted(eps, key=lambda e: e["tow"])
    t0 = eps[0]["tow"]
    ev = chain_events(run)
    vals = {}
    for e in eps:
        v = WIC.dual_sat_values(e, osb, sc, ("L1C", "L2W"))
        vals[e["tow"]] = {s: x for s, x in v.items() if s[0] == "G"}
    tows = sorted(vals)
    series = defaultdict(list)          # (s, p) -> [(tow, wl, nl)] unwrapped
    for t in tows:
        sats = sorted(vals[t])
        for i in range(len(sats)):
            for j in range(i + 1, len(sats)):
                a_, b_ = vals[t][sats[i]], vals[t][sats[j]]
                ch = WIC.dual_pair_channels(a_, b_)
                series[(sats[i], sats[j])].append((t, ch["WL"], ch["NL"]))
    t_from = t0 + 60.0 * a.from_min
    off_wl, off_nl, spread_wl, spread_nl, wan_wl, wan_nl = [], [], [], [], [], []
    jumps = []
    for k, s in series.items():
        s = [x for x in s if x[0] >= t_from]
        if len(s) < 20:
            continue
        for idx, name in ((1, "wl"), (2, "nl")):
            v = [x[idx] for x in s]
            sn = sum(math.sin(2 * math.pi * x) for x in v)
            cs = sum(math.cos(2 * math.pi * x) for x in v)
            cm = math.atan2(sn, cs) / (2 * math.pi)
            rl = math.hypot(sn, cs) / len(v)
            (off_wl if name == "wl" else off_nl).append(abs(cm))
            (spread_wl if name == "wl" else spread_nl).append(1.0 - rl)
            d = []
            for (ta, va), (tb, vb) in zip([(x[0], x[idx]) for x in s], [(x[0], x[idx]) for x in s[1:]]):
                if tb - ta > 31.0:
                    continue
                step = frac(vb - va) if abs(vb - va) < 0.5 else vb - va
                d.append(abs(step))
                if abs(step) > a.jump:
                    evs = ev.get(tb, {})
                    names = evs.get(k[0], set()) | evs.get(k[1], set())
                    jumps.append((name, k, tb, step, tuple(sorted(names))))
            if d:
                d.sort()
                (wan_wl if name == "wl" else wan_nl).append((d[len(d) // 2], d[int(0.95 * (len(d) - 1))]))

    def q(v, p):
        v = sorted(v)
        return v[int(p * (len(v) - 1))] if v else float("nan")
    print("=== %s (source %s, from %.0f min, fixture %s)" % (a.tag, a.source, a.from_min, a.fixture))
    print("pairs %d" % len(off_wl))
    print("offset |circular mean| WL: p50 %.3f p90 %.3f, within 0.10 %.1f %%;  NL: p50 %.3f p90 %.3f, within 0.10 %.1f %%"
          % (q(off_wl, .5), q(off_wl, .9), 100 * sum(x <= .1 for x in off_wl) / max(1, len(off_wl)),
             q(off_nl, .5), q(off_nl, .9), 100 * sum(x <= .1 for x in off_nl) / max(1, len(off_nl))))
    print("spread (1 - R) WL: p50 %.3f p90 %.3f;  NL: p50 %.3f p90 %.3f"
          % (q(spread_wl, .5), q(spread_wl, .9), q(spread_nl, .5), q(spread_nl, .9)))
    print("wander per pair, median |epoch step| p50 (p95 p50): WL %.4f (%.3f), NL %.4f (%.3f) cycles"
          % (q([x[0] for x in wan_wl], .5), q([x[1] for x in wan_wl], .5),
             q([x[0] for x in wan_nl], .5), q([x[1] for x in wan_nl], .5)))
    for name in ("wl", "nl"):
        js = [j for j in jumps if j[0] == name]
        at_ev = [j for j in js if j[4]]
        print("jumps > %.2f cycle (%s): %d pair-steps at %d epochs; %d (%.0f %%) at an epoch with a chain event of a satellite of the pair"
              % (a.jump, name.upper(), len(js), len({j[2] for j in js}), len(at_ev), 100 * len(at_ev) / max(1, len(js))))
        c = Counter(n for j in at_ev for n in j[4])
        print("   events at those steps: %s" % ", ".join("%s %d" % kv for kv in c.most_common(8)))
        ep = Counter(j[2] for j in js)
        print("   epochs with the most jumping pairs: %s" % ", ".join(
            "%.0f (+%.0f min) %d" % (t, (t - t0) / 60.0, n) for t, n in ep.most_common(a.list)))
    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""Card IRDU section 12.4 (c): is a link's N_1 float error the wet-delay term of the hop?  Measure only.

    py -3.14 scripts/irdu_zwd_hop_regress.py <run> --all FILE [--fixture DIR] [--minutes 10,20,30,60,90,119.5]
        [--json out.json]
    py -3.14 scripts/irdu_zwd_hop_regress.py --selftest

<run> is a run of the bed without re-seats and without held chords (the reference row with the wet delay carried,
_rap_irdu_zw_nr3); --all is the frame-target file with every link (scripts/irdu_frame_targets.py --all), whose tree rows
give the chain's one tree and whose chord rows give each chord's frame integers and ring.

The algebra (card IRDU section 11.4).  With the tree links pinned at integers, the phase biases are set by the tree, so a
chord c = (r, s) reads, against its frame integer, the closure of the range errors around its fundamental cycle
s -> r -> s1 -> v1 -> s2 -> ... -> s (the chord, then the tree path from r back to s):

    e_c = (eps_c - sum over path links of sign * eps_l) / lambda.

With eps_l = -dZWD(receiver of l) * m(elevation of l) (dZWD = estimate - truth; the model's slant wet delay is the
zenith delay times the wet mapping function, which the simulator also uses), the receivers of the cycle contribute

    e_c = -(1 / lambda_NL) * sum over receivers v of the cycle of dZWD_v * (m(v, satellite before v) - m(v, after v)).

e_c is the ionosphere-free N_1 error with the true wide lane, (f1 e1 - f2 e2) / (f1 - f2), in N_1 cycles, so a range
error of d metres reads d / lambda_NL = 9.35 d cycles.  Two regressors per chord and epoch:

  x_rx    the chord's own receiver only: dZWD_r * (m(r, s) - m(r, s1)), s1 the first satellite of the tree path from r
          (the receiver's tree link toward s), the term the assignment names;
  x_cyc   every receiver of the cycle (the full prediction under wet-delay errors alone).

m is 1 / sin(elevation) (GMF wet is within 1 % of it above 15 degrees); elevations are the simulator's
(truth_atmo.csv of each station), the wet-delay truth its truth_tropo.csv, the estimate logs/network_zwd.csv.

Printed per time (minutes from the run's first epoch): n chords, |e| p50, the least-squares slope of e on x (with an
intercept) and its R^2, for x_rx and x_cyc, and |e + x / lambda_NL| p50 (what is left after removing the predicted term
with the theoretical slope -9.35, no fit); the same pooled over the windows 15-30, 30-60 and 60-120 min; and by ring.
"""
import argparse
import csv
import json
import math
import os
import sys
from collections import defaultdict, deque

F1, F2 = 1575.42e6, 1227.60e6
C = 299792458.0
LAM_NL = C / (F1 + F2)
WINDOWS = ((15, 30), (30, 60), (60, 120))


def wet_map(elev_deg):
    return 1.0 / math.sin(math.radians(elev_deg))


def read_frame_all(path):
    """(tree edges {(sta, sat)}, chords {(sta, sat): {'z1', 'z2', 'ring'}})."""
    tree, rows = set(), defaultdict(dict)
    with open(path, newline="") as fh:
        for r in csv.DictReader(fh):
            k = (r["station"], r["sat"])
            if r["role"] == "tree":
                tree.add(k)
                continue
            rows[k]["z1" if r["signal"] == "L1C" else "z2"] = int(r["frame_int"])
            rows[k]["ring"] = int(r["ring"]) if r.get("ring") not in (None, "", "None") else None
    return tree, {k: v for k, v in rows.items() if "z1" in v and "z2" in v}


def tree_path(adj, a, b):
    """Vertices of the tree path a -> b (inclusive), breadth first; None when b is not reachable."""
    prev = {a: None}
    q = deque([a])
    while q:
        u = q.popleft()
        if u == b:
            break
        for w in adj[u]:
            if w not in prev:
                prev[w] = u
                q.append(w)
    if b not in prev:
        return None
    out = [b]
    while out[-1] != a:
        out.append(prev[out[-1]])
    return out[::-1]


def cycle_terms(path, chord_sat):
    """The receivers of the fundamental cycle with (satellite before, satellite after), traversing
    chord_sat -> r -> s1 -> v1 -> ... -> chord_sat.  path = [r, s1, v1, s2, ..., chord_sat]."""
    seq = [chord_sat] + path                       # s, r, s1, v1, s2, ..., s
    out = []
    for i in range(1, len(seq) - 1, 2):            # receivers sit at the odd positions
        out.append((seq[i], seq[i - 1], seq[i + 1]))
    return out


def read_truth_zwd(fixture, sta):
    out = {}
    with open(os.path.join(fixture, sta, "truth_tropo.csv"), newline="") as fh:
        for r in csv.DictReader(fh):
            out[round(float(r["tow_s"]), 3)] = float(r["zwd_m"])
    return out


def read_elev(fixture, sta, tows):
    out = {}
    with open(os.path.join(fixture, sta, "truth_atmo.csv"), newline="") as fh:
        for r in csv.DictReader(fh):
            t = round(float(r["tow_s"]), 3)
            if t in tows:
                out[(t, r["satellite"])] = float(r["elev_deg"])
    return out


def ols(x, y):
    n = len(x)
    if n < 3:
        return float("nan"), float("nan"), float("nan")
    mx, my = sum(x) / n, sum(y) / n
    sxx = sum((a - mx) ** 2 for a in x)
    sxy = sum((a - mx) * (b - my) for a, b in zip(x, y))
    syy = sum((b - my) ** 2 for b in y)
    if sxx <= 0 or syy <= 0:
        return float("nan"), float("nan"), float("nan")
    beta = sxy / sxx
    return beta, my - beta * mx, sxy * sxy / (sxx * syy)


def p50(v):
    v = sorted(v)
    return v[len(v) // 2] if v else float("nan")


def summarize(pts):
    e = [p["e"] for p in pts]
    out = {"n": len(pts), "abs_e_p50": p50([abs(a) for a in e])}
    for name in ("x_rx", "x_cyc"):
        x = [p[name] for p in pts]
        beta, a, r2 = ols(x, e)
        out[name] = {"slope": beta, "intercept": a, "r2": r2,
                     "left_p50": p50([abs(p["e"] + p[name] / LAM_NL) for p in pts]),
                     "x_p50_mm": 1000.0 * p50([abs(v) for v in x])}
    return out


def analyse(run, all_path, fixture, minutes):
    tree, chords = read_frame_all(all_path)
    adj = defaultdict(set)
    for sta, sat in tree:
        adj[sta].add(sat)
        adj[sat].add(sta)
    t0 = None
    with open(os.path.join(run, "logs", "network_chain_edges.csv"), newline="") as fh:
        for r in csv.DictReader(fh):
            t0 = float(r["tow"]) if t0 is None else min(t0, float(r["tow"]))
    want = {round(t0 + 60.0 * m, 3): m for m in minutes}
    win_tows = set()
    with open(os.path.join(run, "logs", "network_zwd.csv"), newline="") as fh:
        zest = {}
        for r in csv.DictReader(fh):
            t = round(float(r["tow"]), 3)
            zest[(t, r["station"])] = float(r["zwd_m"])
            win_tows.add(t)
    tows = set(want) | {t for t in win_tows if any(t0 + 60 * a <= t < t0 + 60 * b for a, b in WINDOWS)}
    floats = defaultdict(dict)
    with open(os.path.join(run, "logs", "network_chain_frame.csv"), newline="") as fh:
        for r in csv.DictReader(ln for ln in fh if not ln.startswith("#")):
            t = round(float(r["tow"]), 3)
            k = (r["arc_sta"], r["arc_sat"])
            if t in tows and k in chords:
                floats[t][k] = (float(r["float_cyc_1"]), float(r["float_cyc_2"]))
    paths = {}
    stations = set()
    for k in chords:
        p = tree_path(adj, k[0], k[1])
        if p is None:
            continue
        paths[k] = cycle_terms(p, k[1])
        stations.update(v for v, _, _ in paths[k])
    ztrue = {s: read_truth_zwd(fixture, s) for s in stations}
    elev = {s: read_elev(fixture, s, tows) for s in stations}
    pts_by_t = defaultdict(list)
    missing = 0
    for t in sorted(floats):
        for k, (f1, f2) in floats[t].items():
            if k not in paths:
                continue
            v = chords[k]
            e = (F1 * (f1 - v["z1"]) - F2 * (f2 - v["z2"])) / (F1 - F2)
            x_cyc, x_rx, ok = 0.0, None, True
            for i, (rx, sb, sa) in enumerate(paths[k]):
                eb, ea = elev[rx].get((t, sb)), elev[rx].get((t, sa))
                ze, zt = zest.get((t, rx)), ztrue[rx].get(t)
                if None in (eb, ea, ze, zt):
                    ok = False
                    break
                term = (ze - zt) * (wet_map(eb) - wet_map(ea))
                x_cyc += term
                if i == 0:
                    x_rx = term
            if not ok:
                missing += 1
                continue
            pts_by_t[t].append({"e": e, "x_rx": x_rx, "x_cyc": x_cyc, "ring": v["ring"],
                                "cycle_rx": len(paths[k])})
    res = {"run": run, "lambda_nl": LAM_NL, "chords": len(chords), "with_path": len(paths), "missing": missing,
           "cycle_rx_p50": p50([len(p) for p in paths.values()]), "at": {}, "windows": {}, "ring_at": {}}
    for t, m in sorted(want.items(), key=lambda kv: kv[1]):
        pts = pts_by_t.get(t, [])
        res["at"][str(m)] = summarize(pts)
        by_ring = defaultdict(list)
        for p in pts:
            by_ring[p["ring"]].append(p)
        res["ring_at"][str(m)] = {str(rg): summarize(v) for rg, v in sorted(by_ring.items(), key=lambda kv: kv[0] or 0)}
        by_len = defaultdict(list)
        for p in pts:
            by_len[p["cycle_rx"]].append(p)
        res.setdefault("cycle_len_at", {})[str(m)] = {str(k): summarize(v) for k, v in sorted(by_len.items())}
    for a, b in WINDOWS:
        pts = [p for t, v in pts_by_t.items() if t0 + 60 * a <= t < t0 + 60 * b for p in v]
        res["windows"]["%d-%d" % (a, b)] = summarize(pts)
    return res


def print_result(res, label):
    print("== %s: %d chords (%d with a tree path; receivers per cycle p50 %s); lambda_NL %.4f m, theory slope %.2f "
          "cycles/m" % (label, res["chords"], res["with_path"], res["cycle_rx_p50"], res["lambda_nl"],
                        -1.0 / res["lambda_nl"]))
    for name, block in (("at", res["at"]), ("window", res["windows"])):
        for when, s in block.items():
            if not s.get("n"):
                print("   %-6s %-6s n 0" % (name, when))
                continue
            parts = []
            for xn in ("x_rx", "x_cyc"):
                q = s[xn]
                parts.append("%s: |x| p50 %.1f mm, slope %.2f, R2 %.2f, left %.3f" % (
                    xn, q["x_p50_mm"], q["slope"], q["r2"], q["left_p50"]))
            print("   %-6s %-6s n %4d |e| p50 %.3f | %s" % (name, when, s["n"], s["abs_e_p50"], " | ".join(parts)))
    for m, rings in res["ring_at"].items():
        print("   by ring at %s min: %s" % (m, "; ".join(
            "r%s n %d |e| %.3f R2 rx %.2f cyc %.2f" % (rg, s["n"], s["abs_e_p50"], s["x_rx"]["r2"], s["x_cyc"]["r2"])
            for rg, s in rings.items() if s.get("n"))))
    for m, lens in res.get("cycle_len_at", {}).items():
        print("   by receivers per cycle at %s min: %s" % (m, "; ".join(
            "%s rx n %d |e| %.3f |x_cyc| %.1f mm" % (k, s["n"], s["abs_e_p50"], s["x_cyc"]["x_p50_mm"])
            for k, s in lens.items() if s.get("n"))))


def selftest():
    ok = True

    def chk(c, msg):
        nonlocal ok
        print(("PASS " if c else "FAIL ") + msg)
        ok &= bool(c)

    adj = defaultdict(set)
    for sta, sat in (("R0", "G1"), ("R0", "G2"), ("R1", "G1"), ("R2", "G2")):
        adj[sta].add(sat)
        adj[sat].add(sta)
    p = tree_path(adj, "R1", "G2")
    chk(p == ["R1", "G1", "R0", "G2"], "the tree path from a receiver to a satellite runs through the root")
    terms = cycle_terms(p, "G2")
    chk(terms == [("R1", "G2", "G1"), ("R0", "G1", "G2")], "each receiver of the cycle gets its satellites before and after")
    # A synthetic cycle: the float error is the closure of the range errors; recompute it from first principles.
    dz = {"R1": 0.02, "R0": -0.01}
    el = {("R1", "G2"): 20.0, ("R1", "G1"): 60.0, ("R0", "G1"): 40.0, ("R0", "G2"): 70.0}
    eps = {k: -dz[k[0]] * wet_map(v) for k, v in el.items()}
    # chord (R1, G2); path R1 -> G1 (+), G1 -> R0 (-), R0 -> G2 (+)
    e_direct = (eps[("R1", "G2")] - (eps[("R1", "G1")] - eps[("R0", "G1")] + eps[("R0", "G2")])) / LAM_NL
    x = sum(dz[v] * (wet_map(el[(v, b)]) - wet_map(el[(v, a)])) for v, b, a in terms)
    chk(abs(e_direct + x / LAM_NL) < 1e-12, "the receiver sum equals the cycle closure of the range errors")
    beta, a, r2 = ols([0.0, 1.0, 2.0, 3.0], [1.0, -1.0, -3.0, -5.0])
    chk(abs(beta + 2.0) < 1e-12 and abs(r2 - 1.0) < 1e-12, "least squares recovers an exact line")
    return ok


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("run", nargs="?")
    ap.add_argument("--all")
    ap.add_argument("--fixture", default="C:/GnssProcessor/runs/simarl_r3c")
    ap.add_argument("--minutes", default="10,20,30,60,90,119.5")
    ap.add_argument("--label")
    ap.add_argument("--json")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        sys.exit(0 if selftest() else 1)
    res = analyse(os.path.abspath(a.run), a.all, a.fixture, [float(x) for x in a.minutes.split(",")])
    print_result(res, a.label or os.path.basename(a.run))
    if a.json:
        with open(a.json, "w") as fh:
            json.dump(res, fh, indent=1)


if __name__ == "__main__":
    main()

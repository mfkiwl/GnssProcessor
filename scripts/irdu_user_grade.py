#!/usr/bin/env python3
"""Card IRDU: a simulated user's float ambiguities and fixed integers on a product stream, graded against the
fixture's truth, datum-free.

    py -3.14 scripts/irdu_user_grade.py cell <net tag> [--users ...] [--from-min 30] [--json out.json]
    py -3.14 scripts/irdu_user_grade.py --selftest

<net tag>: the network run (folder _rap_<net tag>); its user runs are the folders scripts/irdu_users.py makes
(variant obs: no fix accepted; variant fix: the fixing control's resolver).  Every reading prints n.

Readings, per user and pooled over the users:

  FRAC   (obs runs) the float between-satellite ambiguity of every logged pair and epoch (CLFRAC lines of the resolver
         log at debug: sd_cyc against the resolver's reference satellite), from --from-min minutes after the user's
         first epoch: the wide lane w = n1 - n2 and the N_1 float of the ionosphere-free row with the wide lane
         rounded, n = (f1 n1 - f2 n2 - f2 round(w)) / (f1 - f2), each as |fraction to the nearest integer|: mean,
         share within 0.10 and 0.15 cycle.  Uniform null: mean 0.25, 20 % within 0.10, 30 % within 0.15.
  HELD   (fix runs) share of the wide-lane pair-epochs held on integers after the first 30 min of resolver activity
         (a WLFLOAT line within 0.01 cycle of an integer with sigma below 0.01: the fixing control's definition),
         and the minute of the first hold from the user's first epoch.
  WRONG  (fix runs) the held integers of each epoch (WLFLOAT held, and the CLFRAC lines of both signals of the pair
         within 0.01 cycle of an integer: F = round(sd_cyc)), referred to the epoch's largest reference group, minus
         the truth:  E_u(i) = F_u(i, r) - [N_u(i) - N_u(r)] per signal, N = the simulator's slip-accumulated integer
         plus the wind-up branch of the user's own arc (scripts/consumer_ar_grade.py's convention).
         (a) Between users: for every satellite pair (i, j) held at one epoch by two or more users,
             v_u = E_u(i) - E_u(j) must be the same at every user (the double difference of fixed minus truth between
             two users is zero).  With three or more users holding the pair, a user whose v differs from a strict
             majority is WRONG (attributed); a disagreement without a majority is UNRESOLVED (counted at every user
             involved).  A pair held by one user only is not compared.
         (b) In time: for every user and satellite pair, a change of v between two consecutive epochs at which the
             user holds the pair is a STEP; a step is DECLARED when the stream marks a discontinuity of either
             satellite on either signal between the two epochs (a change of the P record's phase_disc or gen=
             fields, an R record naming the satellite, or the E record's datum_changed), else UNDECLARED.
         The consensus offset O(i, j, t) (the value every user holding the pair agrees on, or the strict majority) is
         the product's integer offset of the pair; its changes in time are listed with their size and whether the
         stream declared them.
  POS    3D position error median per hour from logs/consumer_replay_hourly.csv, obs (float) and fix runs.

The user's truth: <fixture>/<user>/truth_ambiguities.csv and truth_slips.csv (scripts/simnet_amb_integer.load_truth)
and truth_windup.csv (scripts/consumer_ar_grade.Branches, arc starts read from the user's
logs/closed_loop_sat_trace.csv).
"""
import argparse
import csv
import glob
import itertools
import json
import math
import os
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from simnet_amb_integer import load_truth, n_at  # noqa: E402
import consumer_ar_grade as CAG  # noqa: E402

RUNS = Path(os.environ.get("RAPID_RUNS_ROOT") or "D:/GnssProcessorSupport/runs_nom")
TS = re.compile(r"^\[\s*(\d+),\s*([\d.]+)")
CLFRAC = re.compile(r"CLFRAC sat_i=(\w+) sat_ref=(\w+) sig=(\w+) sd_cyc=(-?[\d.]+)(?: frac=([-+]?[\d.]+))?")
WLF = re.compile(r"WLFLOAT tow=([\d.]+) sat_i=(\w+) sat_ref=(\w+) sig_hi=(\w+) sig_lo=(\w+) w=(-?[\d.]+) "
                 r"sigma=([-\d.eE+]+)")
FREQ = {"G": {"1": 1575.42e6, "2": 1227.60e6, "5": 1176.45e6}, "E": {"1": 1575.42e6, "5": 1176.45e6}}
HELD_TOL = 0.01


def frac(x):
    return x - round(x)


def resolver_logs(run):
    """Every rotated resolver log (ambiguity_resolver.N.log, the highest N the oldest), then the current one."""
    files = glob.glob(str(Path(run) / "logs" / "ambiguity_resolver*.log*"))

    def order(p):
        m = re.search(r"ambiguity_resolver\.(\d+)\.log", p)
        return -int(m.group(1)) if m else 0
    return sorted(files, key=order)


def parse_resolver(run):
    """clfrac: tow -> {(sat_i, sat_ref, sig): sd_cyc};  wlf: tow -> {(sat_i, sat_ref): (sig_hi, sig_lo, w, sigma)}"""
    clfrac = defaultdict(dict)
    wlf = defaultdict(dict)
    for p in resolver_logs(run):
        with open(p, encoding="utf-8", errors="replace") as fh:
            for ln in fh:
                if "CLFRAC sat_i" in ln:
                    t = TS.match(ln)
                    m = CLFRAC.search(ln)
                    if t and m:
                        clfrac[round(float(t.group(2)), 3)][(m.group(1), m.group(2), m.group(3))] = float(m.group(4))
                elif "WLFLOAT" in ln:
                    m = WLF.search(ln)
                    if m:
                        wlf[round(float(m.group(1)), 3)][(m.group(2), m.group(3))] = (
                            m.group(4), m.group(5), float(m.group(6)), float(m.group(7)))
    return clfrac, wlf


def user_first_tow(run):
    p = Path(run) / "logs" / "closed_loop_trace.csv"
    with open(p, encoding="utf-8", errors="replace") as fh:
        for r in csv.DictReader(l for l in fh if not l.startswith("#")):
            return round(float(r["tow"]), 3)
    return None


# ----------------------------------------------------------------------------------------------- FRAC
def float_fractions(clfrac, t_from):
    """[(tow, sys, w_frac, n_frac)] for every pair with both signals of its constellation's pair."""
    out = []
    for tow in sorted(clfrac):
        if tow < t_from:
            continue
        per_pair = defaultdict(dict)
        for (i, r, sig), v in clfrac[tow].items():
            per_pair[(i, r)][sig[1]] = v
        for (i, r), sig in per_pair.items():
            sy = i[0]
            bands = sorted(sig)
            if sy not in FREQ or len(bands) < 2:
                continue
            b1, b2 = bands[0], bands[1]
            f1, f2 = FREQ[sy][b1], FREQ[sy][b2]
            w = sig[b1] - sig[b2]
            n = (f1 * sig[b1] - f2 * sig[b2] - f2 * round(w)) / (f1 - f2)
            out.append((tow, sy, abs(frac(w)), abs(frac(n))))
    return out


def pair_fractions(clfrac, t_from):
    """{(sys, i, j): [N_1 fraction, ...]} of every satellite pair formed reference-free inside each epoch (the
    epoch's largest reference group per constellation; the reference carries 0 on both signals)."""
    out = defaultdict(list)
    for tow in sorted(clfrac):
        if tow < t_from:
            continue
        groups = defaultdict(lambda: defaultdict(dict))   # (sys, ref) -> sat -> {band: value}
        for (i, r, sig), v in clfrac[tow].items():
            groups[(i[0], r)][i][sig[1]] = v
        best = {}
        for (sy, r), sats in groups.items():
            if sy not in best or len(sats) > len(best[sy][1]):
                best[sy] = (r, sats)
        for sy, (r, sats) in best.items():
            if sy not in FREQ:
                continue
            vals = {i: b for i, b in sats.items() if len(b) >= 2}
            if not vals:
                continue
            bands = sorted(next(iter(vals.values())))[:2]
            vals[r] = {bands[0]: 0.0, bands[1]: 0.0}
            f1, f2 = FREQ[sy][bands[0]], FREQ[sy][bands[1]]
            for i, j in itertools.combinations(sorted(vals), 2):
                if bands[0] not in vals[i] or bands[1] not in vals[i] or bands[0] not in vals[j] or bands[1] not in vals[j]:
                    continue
                d1 = vals[i][bands[0]] - vals[j][bands[0]]
                d2 = vals[i][bands[1]] - vals[j][bands[1]]
                w = d1 - d2
                n = (f1 * d1 - f2 * d2 - f2 * round(w)) / (f1 - f2)
                out[(sy, i, j)].append(frac(n))
    return out


def circ_mean(v):
    s = sum(math.sin(2 * math.pi * x) for x in v)
    c = sum(math.cos(2 * math.pi * x) for x in v)
    return math.atan2(s, c) / (2 * math.pi)


def pair_stats(pf, min_n=20):
    cms = {k: circ_mean(v) for k, v in pf.items() if len(v) >= min_n}
    if not cms:
        return {"pairs": 0}
    a = [abs(x) for x in cms.values()]
    worst = sorted(cms.items(), key=lambda kv: -abs(kv[1]))[:5]
    return {"pairs": len(a), "w010": sum(x <= 0.10 for x in a) / len(a), "median": sorted(a)[len(a) // 2],
            "worst": [("%s-%s" % (k[1], k[2]), round(v, 3)) for k, v in worst]}


def frac_stats(v):
    if not v:
        return {"n": 0}
    return {"n": len(v), "mean": sum(v) / len(v), "w010": sum(x <= 0.10 for x in v) / len(v),
            "w015": sum(x <= 0.15 for x in v) / len(v)}


# ----------------------------------------------------------------------------------------------- HELD
def held_share(wlf, t_first):
    rows = []
    for tow, pairs in wlf.items():
        for (i, r), (_, _, w, s) in pairs.items():
            rows.append((tow, abs(frac(w)) < HELD_TOL and s < HELD_TOL))
    if not rows:
        return {"pair_epochs": 0, "held": None, "first_held_min": None}
    t0 = min(r[0] for r in rows)
    sel = [h for t, h in rows if t - t0 >= 1800.0]
    held_t = [t for t, h in rows if h]
    return {"pair_epochs": len(sel), "held": sum(sel) / len(sel) if sel else None,
            "first_held_min": (min(held_t) - t_first) / 60.0 if held_t and t_first is not None else None}


def held_integers(clfrac, wlf):
    """{tow: (ref, {sat: (F_hi, F_lo, sig_hi, sig_lo)})}: the held integers of each epoch referred to the largest
    reference group of the epoch (one constellation family on the GPS-only beds; per family otherwise)."""
    out = {}
    for tow, pairs in wlf.items():
        groups = defaultdict(dict)
        for (i, r), (hi, lo, w, s) in pairs.items():
            if not (abs(frac(w)) < HELD_TOL and s < HELD_TOL):
                continue
            a, b = clfrac.get(tow, {}).get((i, r, hi)), clfrac.get(tow, {}).get((i, r, lo))
            if a is None or b is None or abs(frac(a)) >= HELD_TOL or abs(frac(b)) >= HELD_TOL:
                continue
            groups[(i[0], hi, lo, r)][i] = (round(a), round(b), hi, lo)
        best = {}
        for (sy, hi, lo, r), sats in groups.items():
            if (sy, hi, lo) not in best or len(sats) > len(best[(sy, hi, lo)][1]):
                best[(sy, hi, lo)] = (r, sats)
        merged = {}
        for (sy, hi, lo), (r, sats) in best.items():
            merged[(sy, hi, lo)] = (r, dict(sats))
        out[tow] = merged
    return out


class UserTruth:
    """N_u(sat, sig, t) in the user's own convention: slip-accumulated truth plus the wind-up branch of its arc."""

    def __init__(self, fixture, user, run):
        self.user = user
        self.n_int, self.slips = load_truth(str(fixture), [user])
        _, sat_tows = CAG.load_consumer_trace(str(run))
        self.br = CAG.Branches(str(fixture), user, sat_tows, CAG.accumulated_windup(str(run)))

    def n(self, sat, sig, tow):
        base = n_at(self.n_int, self.slips, self.user, sat, sig, tow)
        return None if base is None else base + self.br.k(sat, tow)


def fixed_minus_truth(held, truth):
    """{tow: {family: {sat: (E_hi, E_lo)}}}, E of the reference = (0, 0)."""
    out = {}
    for tow, fams in held.items():
        o = {}
        for fam, (r, sats) in fams.items():
            sy, hi, lo = fam
            nr_hi, nr_lo = truth.n(r, hi, tow), truth.n(r, lo, tow)
            if nr_hi is None or nr_lo is None:
                continue
            e = {r: (0, 0)}
            for i, (fh, fl, _, _) in sats.items():
                ni_hi, ni_lo = truth.n(i, hi, tow), truth.n(i, lo, tow)
                if ni_hi is None or ni_lo is None:
                    continue
                e[i] = (fh - (ni_hi - nr_hi), fl - (ni_lo - nr_lo))
            if len(e) >= 2:
                o[fam] = e
        if o:
            out[tow] = o
    return out


# ----------------------------------------------------------------------------------------------- the stream
def stream_declarations(products):
    """{sat: sorted [(tow, token)]} of every declared discontinuity of a satellite's phase bias on the wire, and
    the epochs at which the E record declares a datum change (every satellite)."""
    last = {}
    decl = defaultdict(list)
    datum = []
    tow = None
    with open(products, encoding="utf-8", errors="replace") as fh:
        for ln in fh:
            if ln.startswith("E,"):
                f = ln.rstrip().split(",")
                tow = round(float(f[2]), 3)
                if len(f) > 6 and f[6] not in ("", "0"):
                    datum.append(tow)
            elif ln.startswith("P,") and tow is not None:
                f = ln.rstrip().split(",")
                sat, sig = f[1], f[2]
                disc = f[6] if len(f) > 6 and "=" not in f[6] else ""
                gen = next((x for x in f[6:] if x.startswith("gen=")), "")
                key = (disc, gen)
                if (sat, sig) in last and last[(sat, sig)] != key:
                    decl[sat].append((tow, "%s:%s>%s" % (sig, last[(sat, sig)], key)))
                last[(sat, sig)] = key
            elif ln.startswith("R,") and tow is not None:
                for sat in ln.rstrip().split(",")[1:]:
                    decl[sat].append((tow, "R"))
    return {s: sorted(v) for s, v in decl.items()}, sorted(datum)


def declared_between(decl, datum, sats, t1, t2):
    if any(t1 < t <= t2 for t in datum):
        return True
    return any(t1 < t <= t2 for s in sats for t, _ in decl.get(s, []))


# ----------------------------------------------------------------------------------------------- WRONG
def grade_wrong(e_by_user, decl, datum):
    """(a) between users and (b) in time, from {user: {tow: {family: {sat: (E_hi, E_lo)}}}}."""
    users = sorted(e_by_user)
    per_user = {u: Counter() for u in users}
    consensus = defaultdict(dict)        # (family, i, j) -> {tow: value}
    wrong_list = Counter()
    tows = sorted({t for u in users for t in e_by_user[u]})
    for t in tows:
        vals = defaultdict(dict)         # (family, i, j) -> {user: v}
        for u in users:
            for fam, e in e_by_user[u].get(t, {}).items():
                for i, j in itertools.combinations(sorted(e), 2):
                    vals[(fam, i, j)][u] = (e[i][0] - e[j][0], e[i][1] - e[j][1])
        for key, byu in vals.items():
            for u in byu:
                per_user[u]["held_pair_epochs"] += 1
            if len(byu) < 2:
                continue
            c = Counter(byu.values())
            top, k = c.most_common(1)[0]
            for u, v in byu.items():
                per_user[u]["compared"] += 1
            if len(c) == 1:
                consensus[key][t] = top
                continue
            if len(byu) >= 3 and k * 2 > len(byu):
                consensus[key][t] = top
                for u, v in byu.items():
                    if v != top:
                        per_user[u]["wrong"] += 1
                        wrong_list[(u, key[1], key[2], v[0] - top[0], v[1] - top[1], int((t - tows[0]) // 1800))] += 1
            else:
                for u in byu:
                    per_user[u]["unresolved"] += 1
    # (b) per user in time
    steps = []
    for u in users:
        series = defaultdict(list)
        for t in sorted(e_by_user[u]):
            for fam, e in e_by_user[u][t].items():
                for i, j in itertools.combinations(sorted(e), 2):
                    series[(fam, i, j)].append((t, (e[i][0] - e[j][0], e[i][1] - e[j][1])))
        for key, s in series.items():
            for (t1, v1), (t2, v2) in zip(s, s[1:]):
                per_user[u]["transitions"] += 1
                if v1 != v2:
                    d = declared_between(decl, datum, (key[1], key[2]), t1, t2)
                    per_user[u]["steps_declared" if d else "steps_undeclared"] += 1
                    steps.append((u, key[1], key[2], t1, t2, v2[0] - v1[0], v2[1] - v1[1], d))
    # consensus offset changes
    cons_steps = []
    for key, s in consensus.items():
        ts = sorted(s)
        for t1, t2 in zip(ts, ts[1:]):
            if s[t1] != s[t2]:
                d = declared_between(decl, datum, (key[1], key[2]), t1, t2)
                cons_steps.append((key[1], key[2], t1, t2, s[t2][0] - s[t1][0], s[t2][1] - s[t1][1], d))
    return per_user, wrong_list, steps, cons_steps, consensus


# ----------------------------------------------------------------------------------------------- POS
def hourly(run):
    p = Path(run) / "logs" / "consumer_replay_hourly.csv"
    if not p.exists():
        return []
    return [(int(r["hour"]), float(r["err3d_median_m"])) for r in csv.DictReader(open(p))]


# ----------------------------------------------------------------------------------------------- cell
def user_runs(tag, users):
    import irdu_users as IU
    return {u: {v: IU.user_dir(tag, v, u) for v in ("obs", "fix")} for u in users}


def grade_cell(tag, users, from_min=30.0):
    net = RUNS / ("_rap_" + tag)
    runs = user_runs(tag, users)
    meta = json.load(open(next(iter(runs.values()))["obs"] / "irdu_user.json"))
    fixture = Path(meta["fixture"])
    decl, datum = stream_declarations(net / "products.txt")
    res = {"tag": tag, "fixture": fixture.as_posix(), "users": {}, "pooled": {}}
    pooled_w, pooled_n = [], []
    e_by_user = {}
    for u in users:
        r_obs, r_fix = runs[u]["obs"], runs[u]["fix"]
        row = {}
        if (r_obs / "logs").exists():
            cl, _ = parse_resolver(r_obs)
            t_first = user_first_tow(r_obs)
            ff = float_fractions(cl, (t_first or 0) + 60.0 * from_min)
            row["frac_wl"] = frac_stats([x[2] for x in ff])
            row["frac_n1"] = frac_stats([x[3] for x in ff])
            row["pairs"] = pair_stats(pair_fractions(cl, (t_first or 0) + 60.0 * from_min))
            pooled_w += [x[2] for x in ff]
            pooled_n += [x[3] for x in ff]
            row["pos_obs"] = hourly(r_obs)
        if (r_fix / "logs").exists():
            cl, wl = parse_resolver(r_fix)
            t_first = user_first_tow(r_fix)
            row["held"] = held_share(wl, t_first)
            truth = UserTruth(fixture, u, r_fix)
            e_by_user[u] = fixed_minus_truth(held_integers(cl, wl), truth)
            row["pos_fix"] = hourly(r_fix)
        res["users"][u] = row
    res["pooled"]["frac_wl"] = frac_stats(pooled_w)
    res["pooled"]["frac_n1"] = frac_stats(pooled_n)
    npairs = sum(r.get("pairs", {}).get("pairs", 0) for r in res["users"].values())
    nwithin = sum(r.get("pairs", {}).get("pairs", 0) * r.get("pairs", {}).get("w010", 0.0)
                  for r in res["users"].values())
    res["pooled"]["pairs"] = {"pairs": npairs, "w010": nwithin / npairs if npairs else None}
    if e_by_user:
        per_user, wrong_list, steps, cons_steps, consensus = grade_wrong(e_by_user, decl, datum)
        for u in per_user:
            res["users"][u]["wrong"] = dict(per_user[u])
        res["wrong_top"] = [list(k) + [v] for k, v in wrong_list.most_common(20)]
        res["steps"] = steps
        res["consensus_steps"] = cons_steps
        res["consensus_pairs"] = len(consensus)
        tot = Counter()
        for u in per_user:
            tot.update(per_user[u])
        res["pooled"]["wrong"] = dict(tot)
    res["declared_sats"] = {s: len(v) for s, v in decl.items()}
    res["datum_changes"] = len(datum)
    return res


def pct(x):
    return "-" if x is None else "%.1f" % (100.0 * x)


def print_cell(res):
    print("=== %s  (fixture %s)" % (res["tag"], res["fixture"]))
    print("    stream: %d satellites with declared phase discontinuities (%d declarations), %d datum changes"
          % (len(res["declared_sats"]), sum(res["declared_sats"].values()), res["datum_changes"]))
    hdr = ("user", "WL mean", "WL<.10", "N1 mean", "N1<.10", "n frac", "pairs<.10 (n)", "held %", "first",
           "held p-e", "cmp", "wrong", "unres", "steps decl/undecl", "3D obs by h (mm)", "3D fix by h (mm)")
    print("    " + " | ".join(hdr))
    for u, r in res["users"].items():
        fw, fn = r.get("frac_wl", {}), r.get("frac_n1", {})
        h = r.get("held", {})
        w = r.get("wrong", {})
        ps = r.get("pairs", {})
        po = " ".join("%.0f" % (1000 * m) for _, m in r.get("pos_obs", []))
        pf = " ".join("%.0f" % (1000 * m) for _, m in r.get("pos_fix", []))
        print("    %s | %s | %s | %s | %s | %s | %s (%s) | %s | %s | %s | %s | %s | %s | %s/%s | %s | %s" % (
            u, "%.3f" % fw["mean"] if fw.get("n") else "-", pct(fw.get("w010")),
            "%.3f" % fn["mean"] if fn.get("n") else "-", pct(fn.get("w010")), fw.get("n", 0),
            pct(ps.get("w010")), ps.get("pairs", 0),
            pct(h.get("held")), "-" if h.get("first_held_min") is None else "%.0f" % h["first_held_min"],
            w.get("held_pair_epochs", 0), w.get("compared", 0), w.get("wrong", 0), w.get("unresolved", 0),
            w.get("steps_declared", 0), w.get("steps_undeclared", 0), po, pf))
    p = res["pooled"]
    fw, fn, w = p.get("frac_wl", {}), p.get("frac_n1", {}), p.get("wrong", {})
    print("    pooled | WL %s (%s %% <.10, %s %% <.15) | N1 %s (%s %% <.10, %s %% <.15) | n %d | pairs within 0.10 "
          "%s %% of %d | held pair-epochs %d, compared %d, wrong %d, unresolved %d, steps %d declared / %d undeclared" % (
              "%.3f" % fw["mean"] if fw.get("n") else "-", pct(fw.get("w010")), pct(fw.get("w015")),
              "%.3f" % fn["mean"] if fn.get("n") else "-", pct(fn.get("w010")), pct(fn.get("w015")), fw.get("n", 0),
              pct(p.get("pairs", {}).get("w010")), p.get("pairs", {}).get("pairs", 0),
              w.get("held_pair_epochs", 0), w.get("compared", 0), w.get("wrong", 0), w.get("unresolved", 0),
              w.get("steps_declared", 0), w.get("steps_undeclared", 0)))
    if res.get("consensus_steps") is not None:
        cs = res["consensus_steps"]
        print("    consensus offsets: %d satellite pairs; %d changes in time (%d declared)"
              % (res["consensus_pairs"], len(cs), sum(1 for c in cs if c[6])))
        for c in cs[:12]:
            print("       %s-%s %.0f->%.0f: %+d/%+d %s" % (c[0], c[1], c[2], c[3], c[4], c[5],
                                                       "declared" if c[6] else "UNDECLARED"))
    if res.get("wrong_top"):
        print("    wrong (user, i, j, d_hi, d_lo, half-hour bin): count")
        for x in res["wrong_top"][:12]:
            print("       ", x)


# ----------------------------------------------------------------------------------------------- selftest
def selftest():
    ok = True

    def chk(c, msg):
        nonlocal ok
        print("  %s  %s" % ("ok  " if c else "FAIL", msg))
        ok = ok and c
    # fractions: an exact integer pair reads 0, a half-cycle wide lane reads 0.5
    cl = {100.0: {("G01", "G02", "L1C"): 5.0, ("G01", "G02", "L2W"): 3.0,
                  ("G03", "G02", "L1C"): 5.5, ("G03", "G02", "L2W"): 5.0}}
    ff = sorted(float_fractions(cl, 0.0), key=lambda x: x[2])
    chk(len(ff) == 2 and ff[0][2] == 0.0 and ff[0][3] == 0.0 and abs(ff[1][2] - 0.5) < 1e-12,
        "fractions: integer pair 0, half-cycle wide lane 0.5")
    # pairs: reference-free, the reference joins with 0 on both signals; G01-G03 differ by (-0.5, -2.0)
    pf = pair_fractions(cl, 0.0)
    chk(set(pf) == {("G", "G01", "G02"), ("G", "G01", "G03"), ("G", "G02", "G03")}
        and pf[("G", "G01", "G02")] == [0.0], "pairs: every pair of the epoch, the reference included")
    # held integers: a pair held only when the WLFLOAT and both CLFRAC lines sit on integers
    wl = {100.0: {("G01", "G02"): ("L1C", "L2W", 2.0, 0.001), ("G03", "G02"): ("L1C", "L2W", 0.5, 0.001)}}
    h = held_integers(cl, wl)
    fam = ("G", "L1C", "L2W")
    chk(h[100.0][fam][0] == "G02" and list(h[100.0][fam][1]) == ["G01"] and h[100.0][fam][1]["G01"][:2] == (5, 3),
        "held integers: the integer pair kept, the half-cycle pair refused")

    # consensus: three users agree on (i, j) except one, a strict majority attributes the wrong one
    def ev(v):
        return {0.0: {fam: {"G01": (0, 0), "G02": v}}}
    per_user, wl_, steps, cons, _ = grade_wrong({"A": ev((1, 1)), "B": ev((1, 1)), "C": ev((2, 1))}, {}, [])
    chk(per_user["C"]["wrong"] == 1 and per_user["A"]["wrong"] == 0 and per_user["A"]["compared"] == 1,
        "between users: the minority value is wrong, the majority is not")
    per_user, _, _, _, _ = grade_wrong({"A": ev((1, 1)), "B": ev((2, 1))}, {}, [])
    chk(per_user["A"]["unresolved"] == 1 and per_user["B"]["unresolved"] == 1, "two users disagreeing: unresolved")
    # in time: a step without a declaration is undeclared, with one declared
    e = {0.0: {fam: {"G01": (0, 0), "G02": (1, 1)}}, 30.0: {fam: {"G01": (0, 0), "G02": (2, 1)}}}
    per_user, _, steps, cons, _ = grade_wrong({"A": e, "B": e}, {}, [])
    chk(per_user["A"]["steps_undeclared"] == 1 and len(cons) == 1 and not cons[0][6], "an undeclared step is counted")
    per_user, _, steps, cons, _ = grade_wrong({"A": e, "B": e}, {"G02": [(30.0, "L1C")]}, [])
    chk(per_user["A"]["steps_declared"] == 1 and cons[0][6], "a declared step is counted as declared")
    print("irdu_user_grade selftest: %s" % ("PASS" if ok else "FAIL"))
    return 0 if ok else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("action", nargs="?", choices=("cell",))
    ap.add_argument("tag", nargs="?")
    ap.add_argument("--users", default=None)
    ap.add_argument("--from-min", type=float, default=30.0)
    ap.add_argument("--json", default=None)
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    import irdu_users as IU
    users = a.users.split(",") if a.users else IU.USERS
    res = grade_cell(a.tag, users, a.from_min)
    print_cell(res)
    if a.json:
        json.dump(res, open(a.json, "w"), indent=1, default=str)
    return 0


if __name__ == "__main__":
    sys.exit(main())

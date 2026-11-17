#!/usr/bin/env python3
"""Card NRF, order D.2: does a product stream signal its steps?  Every phase step of a family's level that the stream-step
read classes whole or fraction against the stream's phase discontinuity counters, and every counter increment against
the steps.  No truth, no user.

    py -3.14 scripts/stream_disc_check.py <run> [<run> ...] --family E:L1X/L5X [--family G:L1C/L2W ...]
                                          [--from-h 0] [--to-h 99] [--tol 0.15] [--list 20]

Needs the counters on the records (network.serialize_disc_counters: the P record's phase_disc field).  Per family
(two phase signals and their code signals, L read as C), satellite and epoch, the level a user's phase reads (card IRD
section 8 on the emitted records):

    E_b = (C - P_b + mu_b x) / lambda_b,   x = ((C - B_1) - (C - B_2)) / (1 - gamma)

Between consecutive epochs of the stream (at most 45 s apart, at least 4 satellites in both), each satellite's step less
the family's median step (x_1, x_2) is classed quiet, whole, ionosphere-like or fraction with the tolerance, as the
requesting session's stream_jumps.py does (dn = (f1 x_1 - f2 x_2) / (f1 - f2)).  The signals a step moves: for a whole
step the bands with a non-zero whole number, for a fraction step the bands whose |x_b| reaches the tolerance.

Printed per run: steps by class; whole and fraction steps with and without an increment on each moved signal; and every
phase increment by what stands behind it: a whole or fraction step of that signal in a listed family; a forced mark (the
epoch's E record datum flag for the constellation, or the satellite in the epoch's R record); a key not classified
(the satellite or a bias missing at the previous epoch, a gap over 45 s, fewer than 4 satellites); a quiet or
ionosphere-like step of the signal; a signal in no listed family.  --list prints the first steps without an increment
and increments without a step.
"""
import argparse
import collections
import os
import sys

RUNS = os.environ.get("RAPID_RUNS_ROOT") or "D:/GnssProcessorSupport/runs_nom"
C_M = 299792458.0
FREQ = {("G", "1"): 1575.42e6, ("G", "2"): 1227.60e6, ("G", "5"): 1176.45e6,
        ("E", "1"): 1575.42e6, ("E", "5"): 1176.45e6, ("E", "7"): 1207.14e6, ("E", "6"): 1278.75e6,
        ("C", "2"): 1561.098e6, ("C", "6"): 1268.52e6, ("C", "1"): 1575.42e6, ("C", "5"): 1176.45e6}


def resolve(run):
    return os.path.abspath(run) if os.path.isdir(run) else os.path.join(RUNS, "_rap_" + run)


def read_stream(path):
    """[(tow, {sat: clock}, {(sat, sig): code}, {(sat, sig): (phase, disc)}, datum_consts or None, retro set)]"""
    eps, cur = [], None
    with open(path, encoding="utf-8", errors="replace") as fh:
        for line in fh:
            k = line[:2]
            if k == "E,":
                q = line.rstrip().split(",")
                consts = None
                if len(q) > 6 and q[6] == "1":
                    consts = set(q[7]) if len(q) > 7 and q[7] else set("GERCJ")
                cur = [float(q[2]), {}, {}, {}, consts, set()]
                eps.append(cur)
            elif cur is None:
                continue
            elif k == "C,":
                q = line.rstrip().split(",")
                cur[1][q[1]] = float(q[2])
            elif k == "B,":
                q = line.rstrip().split(",")
                cur[2][(q[1], q[2])] = float(q[3])
            elif k == "P,":
                q = line.rstrip().split(",")
                disc = int(q[6]) if len(q) > 6 and q[6].lstrip("-").isdigit() else None
                cur[3][(q[1], q[2])] = (float(q[3]), disc)
            elif k == "R,":
                cur[5].update(line.rstrip().split(",")[1:])
    return eps


def levels(ep, fam):
    c, p1, p2 = fam["c"], fam["p1"], fam["p2"]
    f1, f2 = fam["f1"], fam["f2"]
    gam = (f1 / f2) ** 2
    out = {}
    for s, clk in ep[1].items():
        if s[0] != c:
            continue
        try:
            P1, P2 = ep[3][(s, p1)][0], ep[3][(s, p2)][0]
            B1, B2 = ep[2][(s, fam["c1"])], ep[2][(s, fam["c2"])]
        except KeyError:
            continue
        x = ((clk - B1) - (clk - B2)) / (1.0 - gam)
        out[s] = ((clk - P1 + x) / (C_M / f1), (clk - P2 + gam * x) / (C_M / f2))
    return out


def median(v):
    v = sorted(v)
    n = len(v)
    return v[n // 2] if n % 2 else 0.5 * (v[n // 2 - 1] + v[n // 2])


def family(text):
    c, sigs = text.split(":")
    p1, p2 = sigs.split("/")
    return {"name": text, "c": c, "p1": p1, "p2": p2, "c1": "C" + p1[1:], "c2": "C" + p2[1:],
            "f1": FREQ[(c, p1[1])], "f2": FREQ[(c, p2[1])]}


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("runs", nargs="+")
    ap.add_argument("--family", action="append", required=True)
    ap.add_argument("--from-h", type=float, default=0.0)
    ap.add_argument("--to-h", type=float, default=99.0)
    ap.add_argument("--tol", type=float, default=0.15)
    ap.add_argument("--list", type=int, default=0)
    a = ap.parse_args()
    fams = [family(f) for f in a.family]
    fam_signals = {(f["c"], f["p1"]) for f in fams} | {(f["c"], f["p2"]) for f in fams}
    for run in a.runs:
        eps = read_stream(os.path.join(resolve(run), "products.txt"))
        if not any(v[1] is not None for e in eps for v in e[3].values()):
            print("== %s: no phase_disc field on the P records (network.serialize_disc_counters off)" % run)
            continue
        t0 = eps[0][0]
        lo, hi = t0 + 3600.0 * a.from_h, t0 + 3600.0 * a.to_h
        lv = [{f["name"]: levels(e, f) for f in fams} for e in eps]
        depth = {}                       # (tow, band, sat) -> depth of the satellite vertex
        ce = os.path.join(resolve(run), "logs", "network_chain_edges.csv")
        if os.path.exists(ce):
            import csv as _csv
            with open(ce, newline="") as fh:
                for r in _csv.DictReader(fh):
                    if r["child"] == r["edge_sat"]:
                        depth[(round(float(r["tow"])), r["band"], r["edge_sat"])] = int(r["depth"])
        wl_iono = collections.defaultdict(list)   # (family, depth class) -> wide-lane moves of iono-like steps
        sat_ep = collections.Counter()            # (family, depth class) -> satellite-epochs classified
        classes = collections.Counter()
        moved = {}                       # (tow, sat, sig) -> (class, family, x1, x2)
        stepinfo = {}                    # (tow, sat, sig) -> class of the signal's step in a family (any)
        classified_epochs = set()
        for i in range(1, len(eps)):
            ta, tb = eps[i - 1][0], eps[i][0]
            if not (lo <= tb < hi) or tb - ta > 45.0:
                continue
            for f in fams:
                A, B = lv[i - 1][f["name"]], lv[i][f["name"]]
                common = [s for s in B if s in A]
                if len(common) < 4:
                    continue
                classified_epochs.add((tb, f["name"]))
                d1 = {s: B[s][0] - A[s][0] for s in common}
                d2 = {s: B[s][1] - A[s][1] for s in common}
                m1, m2 = median(d1.values()), median(d2.values())
                for s in common:
                    x1, x2 = d1[s] - m1, d2[s] - m2
                    dn = (f["f1"] * x1 - f["f2"] * x2) / (f["f1"] - f["f2"])
                    n1, n2 = round(x1), round(x2)
                    if abs(x1) < a.tol and abs(x2) < a.tol:
                        cls, st = "quiet", (False, False)
                    elif abs(x1 - n1) < a.tol and abs(x2 - n2) < a.tol:
                        cls, st = "whole", (n1 != 0, n2 != 0)
                    elif abs(dn) < a.tol:
                        cls, st = "iono-like", (False, False)
                    else:
                        cls, st = "fraction", (abs(x1) >= a.tol, abs(x2) >= a.tol)
                    dd = max(depth.get((round(tb), f["p1"], s), 0), depth.get((round(tb), f["p2"], s), 0))
                    dcls = "depth %d" % dd if 0 < dd <= 5 else ("depth 7 and more" if dd > 5 else "not in the tree")
                    sat_ep[(f["name"], dcls)] += 1
                    if cls == "iono-like":
                        wl_iono[(f["name"], dcls)].append(abs(x1 - x2))
                    classes[(f["name"], cls)] += 1
                    for sig, m in ((f["p1"], st[0]), (f["p2"], st[1])):
                        key = (tb, s, sig)
                        if m:
                            moved[key] = (cls, f["name"], x1, x2)
                        stepinfo.setdefault(key, cls if m else "unmoved " + cls)
        # Increments of the phase counters between consecutive epochs.
        incs = []
        for i in range(1, len(eps)):
            ta, tb = eps[i - 1][0], eps[i][0]
            if not (lo <= tb < hi):
                continue
            for (s, sig), (pb, disc) in eps[i][3].items():
                prev = eps[i - 1][3].get((s, sig))
                if disc is None or prev is None or prev[1] is None or disc <= prev[1]:
                    continue
                incs.append((tb, s, sig, ta))
        print("== %s: families %s, hours %g to %g, tolerance %g cycle" % (run, ", ".join(a.family), a.from_h,
                                                                         a.to_h, a.tol))
        for f in fams:
            row = ", ".join("%s %d" % (c, classes[(f["name"], c)]) for c in ("quiet", "whole", "iono-like", "fraction"))
            print("   %s steps: %s" % (f["name"], row))
        for f in fams:
            rows = []
            for dcls in sorted({k[1] for k in sat_ep if k[0] == f["name"]}):
                hours = sat_ep[(f["name"], dcls)] * 30.0 / 3600.0
                v = wl_iono.get((f["name"], dcls), [])
                big = [x for x in v if x > 0.25]
                rows.append("%s: %.2f per satellite-hour over 0.25 cycle (%d of %d), largest %.3f"
                            % (dcls, len(big) / hours if hours else 0.0, len(big), len(v), max(v) if v else 0.0))
            print("   %s ionosphere-like steps moving the wide lane: %s" % (f["name"], "; ".join(rows)))
        inc_set = {(tb, s, sig) for tb, s, sig, _ in incs}
        missing = [(k, v) for k, v in sorted(moved.items()) if k not in inc_set]
        by_cls = collections.Counter(v[0] for v in moved.values())
        miss_cls = collections.Counter(v[0] for _, v in missing)
        print("   moved signals: whole %d (without an increment %d), fraction %d (without an increment %d)"
              % (by_cls["whole"], miss_cls["whole"], by_cls["fraction"], miss_cls["fraction"]))
        why = collections.Counter()
        unexplained = []
        for tb, s, sig, ta in incs:
            k = (tb, s, sig)
            ep = eps[[e[0] for e in eps].index(tb)]
            if k in moved:
                why["a whole or fraction step of the signal"] += 1
            elif ep[4] is not None and s[0] in ep[4]:
                why["forced: datum flag of the constellation"] += 1
            elif s in ep[5]:
                why["forced: the satellite in the R record"] += 1
            elif (s[0], sig) not in fam_signals:
                why["a signal in no listed family"] += 1
            elif k in stepinfo:
                why["a %s step of the signal" % stepinfo[k].replace("unmoved ", "")] += 1
                unexplained.append((tb, s, sig, stepinfo[k]))
            else:
                why["not classified (no baseline, a gap or too few satellites)"] += 1
        print("   phase increments %d: %s" % (len(incs), "; ".join("%s %d" % (w, n) for w, n in why.most_common())))
        if a.list:
            for (tb, s, sig), (cls, fname, x1, x2) in missing[:a.list]:
                print("      step without an increment: TOW %.0f %s %s %s (%s) x1 %+.3f x2 %+.3f" % (tb, s, sig, cls,
                                                                                               fname, x1, x2))
            for tb, s, sig, cls in unexplained[:a.list]:
                print("      increment without a step: TOW %.0f %s %s (%s)" % (tb, s, sig, cls))
    return 0


if __name__ == "__main__":
    sys.exit(main())

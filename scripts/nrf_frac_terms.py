#!/usr/bin/env python3
"""Card NRF stage G0: are the chord fractions of a ring-fix run one term per receiver plus one per satellite?

    py -3.14 scripts/nrf_frac_terms.py <run dir or tag> [--min-links 4] [--seed 1] [--json out.json]

From logs/network_ring_fix.csv, per epoch and pair family, the chords not held with a float: the signed N1 residual
d = n_if - round(n_if) and the signed wide-lane residual w = (f1 - f2) - wl (cycles).  For each, a fit of one term per
receiver and one per satellite, d_ij = a_i + b_j, by alternating medians of the wrapped residuals (robust and
circular; ten passes); then the residuals after the terms.  A shuffled null fits the same graph with the epoch's
values permuted among its links.  Printed per family: p50 |d| before, after the terms, and after the terms on the
null; the same for w; and of the rows the decision refused for the fraction (refused = fraction), the share whose
N1 residual after the terms is within the fraction bound (0.20 cycle).  Only receivers and satellites with at least
--min-links chords at the epoch are fitted; other chords are left out of the after-terms reads.
"""
import argparse
import collections
import csv
import json
import os
import random
import statistics
import sys

RUNS = os.environ.get("RAPID_RUNS_ROOT") or "D:/GnssProcessorSupport/runs_nom"
FRAC_BOUND = 0.20


def resolve(run):
    return os.path.abspath(run) if os.path.isdir(run) else os.path.join(RUNS, "_rap_" + run)


def wrap(x):
    return x - round(x)


def fit(links, values, passes=10):
    """Alternating wrapped medians: values[k] ~ a[i] + b[j] for links[k] = (i, j); residuals wrapped."""
    a = collections.defaultdict(float)
    b = collections.defaultdict(float)
    by_i, by_j = collections.defaultdict(list), collections.defaultdict(list)
    for k, (i, j) in enumerate(links):
        by_i[i].append(k)
        by_j[j].append(k)
    for _ in range(passes):
        for i, ks in by_i.items():
            a[i] = statistics.median(wrap(values[k] - b[links[k][1]]) for k in ks)
        for j, ks in by_j.items():
            b[j] = statistics.median(wrap(values[k] - a[links[k][0]]) for k in ks)
    return [wrap(values[k] - a[i] - b[j]) for k, (i, j) in enumerate(links)]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("run")
    ap.add_argument("--min-links", type=int, default=4)
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--json")
    a = ap.parse_args()
    rng = random.Random(a.seed)
    epochs = collections.defaultdict(list)
    with open(os.path.join(resolve(a.run), "logs", "network_ring_fix.csv"), newline="") as fh:
        for r in csv.DictReader(fh):
            if r["state"] == "held" or r["f1"] == "" or r["n_if"] == "" or r["wl"] == "":
                continue
            fam = "%s:%s/%s" % (r["sat"][:1], r["sig1"], r["sig2"])
            d = wrap(float(r["n_if"]))
            w = float(r["f1"]) - float(r["f2"]) - int(r["wl"])
            epochs[(r["tow"], fam)].append((r["station"], r["sat"], d, w, r["state"] == "refused"
                                            and r["refused"] == "fraction"))
    acc = collections.defaultdict(lambda: collections.defaultdict(list))
    for (tow, fam), rows in epochs.items():
        ci = collections.Counter(x[0] for x in rows)
        cj = collections.Counter(x[1] for x in rows)
        rows = [x for x in rows if ci[x[0]] >= a.min_links and cj[x[1]] >= a.min_links]
        if len(rows) < 10:
            continue
        links = [(x[0], x[1]) for x in rows]
        for name, col in (("n1", 2), ("wl", 3)):
            vals = [x[col] for x in rows]
            res = fit(links, vals)
            shuf = vals[:]
            rng.shuffle(shuf)
            res0 = fit(links, shuf)
            acc[fam][name + "_before"] += [abs(v) for v in vals]
            acc[fam][name + "_after"] += [abs(v) for v in res]
            acc[fam][name + "_null"] += [abs(v) for v in res0]
            if name == "n1":
                for x, rv in zip(rows, res):
                    if x[4]:
                        acc[fam]["frac_refused_after"].append(abs(rv))
    out = {}
    print("== %s (chords not held, receivers and satellites with at least %d chords at the epoch)" % (
        resolve(a.run), a.min_links))
    for fam in sorted(acc):
        A = acc[fam]
        med = {k: statistics.median(v) for k, v in A.items() if v}
        fr = A["frac_refused_after"]
        passing = sum(1 for v in fr if v <= FRAC_BOUND)
        out[fam] = {"p50": med, "n_rows": len(A["n1_before"]), "fraction_refused": len(fr),
                    "fraction_refused_within_bound_after_terms": passing}
        print("  %s: %d chord-epochs" % (fam, len(A["n1_before"])))
        print("    N1 residual |d|  p50 before %.3f, after the receiver and satellite terms %.3f (shuffled null %.3f)" % (
            med["n1_before"], med["n1_after"], med["n1_null"]))
        print("    wide lane |w|    p50 before %.3f, after the terms %.3f (shuffled null %.3f)" % (
            med["wl_before"], med["wl_after"], med["wl_null"]))
        if fr:
            print("    rows refused for the fraction: %d; within %.2f cycle after the terms: %d (%.0f %%)" % (
                len(fr), FRAC_BOUND, passing, 100.0 * passing / len(fr)))
    if a.json:
        with open(a.json, "w") as fh:
            json.dump(out, fh, indent=1)
    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""Card IRDU section 14: the phase step declaration on what a user sees, checked from a run's own files.

    py -3.14 scripts/irdu_pv_audit.py replay <network run> [--rule pv|legacy] [--to-min 40]
    py -3.14 scripts/irdu_pv_audit.py audit  <network run> [--from-min 0]

replay  an independent replay of the emitter's phase discontinuity rule over the run's products.txt, and the
        comparison with the counters the producer itself kept (logs/network_solution.csv, column disc_counter of the
        PB rows: a key's counter rising between two epochs is a declared step).
        rule pv (network.disc_phase_visible; the S record's discpv=<n>): a key is declared when the change of its
        clock less phase bias since its last emission with a clock, less the median of that change over the keys of
        its constellation and signal that vote (a baseline at the previous epoch; at least n of them; the mean of
        the two middle values for an even count), exceeds discfrac x wavelength (or the flat gate); below n voters
        each key is tested on its own change; a key without a clock now or at its previous emission takes the
        legacy test.  rule legacy: the phase bias alone against its last emission.  Forced bumps (the E record's
        datum flag, an R record naming the satellite) are declared whatever the rule, and do not vote.  Printed:
        the declared steps by the rule and forced, by 5 minutes; the time of the last; the producer's counter
        increments; the keys where the two differ.
audit   for every epoch, signal and pair of satellites both emitted at that epoch and at the previous one, the jump
        of the pair's difference of clock less phase bias (what a user of between-satellite differences sees),
        and whether either satellite was declared at that epoch (the producer's counters).  Printed: the pair
        jumps above the bar and above twice the bar with neither satellite declared, by 15 minutes, and the
        largest; the bar is the larger of the two satellites' bars.
"""
import argparse
import collections
import csv
import os
import statistics as st

C0 = 299792458.0
FREQ = {("G", "L1C"): 1575.42e6, ("G", "L1W"): 1575.42e6, ("G", "L2W"): 1227.60e6, ("G", "L2L"): 1227.60e6,
        ("G", "L5Q"): 1176.45e6, ("E", "L1C"): 1575.42e6, ("E", "L1X"): 1575.42e6, ("E", "L5Q"): 1176.45e6,
        ("E", "L5X"): 1176.45e6, ("E", "L7Q"): 1207.14e6}


def kt(x):
    return round(float(x), 3)


def read_products(path):
    """Epochs; per epoch {sat: clock}, {(sat, sig): pb}, forced constellations, retro sats; the S fields."""
    ep, C, P, forced, retro = [], {}, {}, {}, {}
    s_fields = {"discfrac": 0.0, "discpv": 0, "flat": 0.05, "stale": 0.0}
    t = None
    with open(path, encoding="utf-8") as fh:
        for ln in fh:
            f = ln.rstrip("\n").split(",")
            if f[0] == "S":
                try:
                    s_fields["flat"] = float(f[8])
                except (IndexError, ValueError):
                    pass
                for tok in f:
                    if tok.startswith("discfrac="):
                        s_fields["discfrac"] = float(tok[9:])
                    elif tok.startswith("discpv="):
                        s_fields["discpv"] = int(tok[7:])
                    elif tok.startswith("stale="):
                        s_fields["stale"] = float(tok[6:])
            elif f[0] == "E":
                t = kt(f[2])
                ep.append(t)
                C[t], P[t], retro[t] = {}, {}, set()
                forced[t] = (set(f[7]) if len(f) > 7 and f[7] else {"*"}) if len(f) > 6 and f[6] == "1" else set()
            elif f[0] == "C" and t is not None:
                C[t][f[1]] = float(f[2])
            elif f[0] == "P" and t is not None:
                P[t][(f[1], f[2])] = float(f[3])
            elif f[0] == "R" and t is not None:
                retro[t].update(x for x in f[1:] if x)
    return ep, C, P, forced, retro, s_fields


def bar_of(sat, sig, s):
    f = FREQ.get((sat[0], sig))
    if s["discfrac"] > 0.0 and f:
        return s["discfrac"] * C0 / f
    return s["flat"]


def median(v):
    v = sorted(v)
    n = len(v)
    return v[n // 2] if n % 2 else 0.5 * (v[n // 2 - 1] + v[n // 2])


def replay_rule(ep, C, P, forced, retro, s, rule):
    """Declared steps: list of (t, sat, sig, kind) with kind in {value, forced}."""
    last_pb, last_pv, last_seen = {}, {}, {}
    out = []
    prev_t = None
    minsats = (s["discpv"] or 4) if rule == "pv" else 0   # a header without discpv=: the built minimum, 4
    for t in ep:
        is_forced = lambda sat: ("*" in forced[t]) or (sat[0] in forced[t]) or (sat in retro[t])
        verdict = {}
        if minsats > 0:
            groups = collections.defaultdict(list)
            for (sat, sig), pb in P[t].items():
                if sat not in C[t]:
                    continue
                k = (sat, sig)
                b = last_pv.get(k)
                stale = s["stale"] > 0.0 and k in last_seen and (t - last_seen[k]) > s["stale"]
                if b is None or stale or is_forced(sat):
                    continue
                change = (C[t][sat] - pb) - b[0]
                votes = prev_t is not None and b[1] == prev_t
                groups[(sat[0], sig)].append((k, change, votes))
            for g, items in groups.items():
                vv = [c for _, c, v in items if v]
                if len(vv) >= minsats:
                    m = median(vv)
                    for k, c, _ in items:
                        verdict[k] = abs(c - m) > bar_of(k[0], k[1], s)
                else:
                    for k, c, _ in items:
                        verdict[k] = abs(c) > bar_of(k[0], k[1], s)
        for (sat, sig), pb in P[t].items():
            k = (sat, sig)
            have = k in last_pb
            stale = s["stale"] > 0.0 and k in last_seen and (t - last_seen[k]) > s["stale"]
            fresh = have and not stale
            jump = False
            if fresh:
                jump = abs(pb - last_pb[k]) > bar_of(sat, sig, s)
                if k in verdict:
                    jump = verdict[k]
            if have and is_forced(sat):
                out.append((t, sat, sig, "forced"))
            elif jump:
                out.append((t, sat, sig, "value"))
            last_pb[k] = pb
            last_seen[k] = t
            if minsats > 0:
                if sat in C[t]:
                    last_pv[k] = (C[t][sat] - pb, t)
                else:
                    last_pv.pop(k, None)
        prev_t = t
    return out


def producer_steps(run):
    """(t, sat, sig) where the producer's PB counter rose (logs/network_solution.csv)."""
    last, out = {}, set()
    with open(os.path.join(run, "logs", "network_solution.csv"), newline="") as fh:
        for r in csv.DictReader(ln for ln in fh if not ln.startswith("#")):
            if r["kind"] != "PB":
                continue
            k = (r["sat"], r["signal"])
            v = int(r["disc_counter"])
            if k in last and v != last[k]:
                out.add((kt(r["tow"]), r["sat"], r["signal"]))
            last[k] = v
    return out


def cmd_replay(a):
    ep, C, P, forced, retro, s = read_products(os.path.join(a.run, "products.txt"))
    t0 = ep[0]
    rule = a.rule or ("pv" if s["discpv"] > 0 else "legacy")
    steps = replay_rule(ep, C, P, forced, retro, s, rule)
    val = [x for x in steps if x[3] == "value"]
    frc = [x for x in steps if x[3] == "forced"]
    early = [x for x in val if (x[0] - t0) / 60.0 <= a.to_min]
    bins = collections.Counter(int((x[0] - t0) / 60.0 // 5) * 5 for x in val)
    print("%s: rule %s (S record: discfrac %g, discpv %d, flat %g m, stale %g s)" % (
        os.path.basename(a.run.rstrip("/\\")), rule, s["discfrac"], s["discpv"], s["flat"], s["stale"]))
    print("  declared value steps %d (%d in the first %g min, the last at %.1f min), forced %d" % (
        len(val), len(early), a.to_min, (val[-1][0] - t0) / 60.0 if val else float("nan"), len(frc)))
    print("  by 5 min: " + ", ".join("%d: %d" % kv for kv in sorted(bins.items())))
    prod = producer_steps(a.run)
    mine = {(x[0], x[1], x[2]) for x in steps}
    print("  the producer's counter increments %d; this replay %d; in both %d; only the producer %d; only the replay %d"
          % (len(prod), len(mine), len(prod & mine), len(prod - mine), len(mine - prod)))
    for x in sorted(prod ^ mine)[:10]:
        print("    differ: %.1f min %s %s (%s)" % ((x[0] - t0) / 60.0, x[1], x[2], "producer" if x in prod else "replay"))


def cmd_audit(a):
    ep, C, P, forced, retro, s = read_products(os.path.join(a.run, "products.txt"))
    t0 = ep[0]
    declared = producer_steps(a.run)
    over1 = collections.Counter()
    over2 = collections.Counter()
    pairs = collections.Counter()
    worst = (0.0, None)
    for prev, t in zip(ep, ep[1:]):
        if (t - t0) / 60.0 < a.from_min:
            continue
        by = collections.defaultdict(dict)
        for (sat, sig), pb in P[t].items():
            k = (sat, sig)
            if k in P[prev] and sat in C[t] and sat in C[prev]:
                by[(sat[0], sig)][sat] = (C[t][sat] - pb) - (C[prev][sat] - P[prev][k])
        b15 = int((t - t0) / 60.0 // 15) * 15
        for (cst, sig), ch in by.items():
            sats = sorted(ch)
            for i in range(len(sats)):
                for j in range(i + 1, len(sats)):
                    si, sj = sats[i], sats[j]
                    jump = abs(ch[si] - ch[sj])
                    bar = max(bar_of(si, sig, s), bar_of(sj, sig, s))
                    pairs[b15] += 1
                    if (t, si, sig) in declared or (t, sj, sig) in declared:
                        continue
                    if jump > bar:
                        over1[b15] += 1
                        if jump > worst[0]:
                            worst = (jump, ((t - t0) / 60.0, si, sj, sig))
                    if jump > 2 * bar:
                        over2[b15] += 1
    print("%s: pair jumps of the difference of clock less phase bias, neither satellite declared (from %g min)" % (
        os.path.basename(a.run.rstrip("/\\")), a.from_min))
    print("  above the bar: %d; above twice the bar: %d; pair-epochs %d" % (
        sum(over1.values()), sum(over2.values()), sum(pairs.values())))
    print("  by 15 min (above the bar / above twice): " + ", ".join(
        "%d: %d/%d" % (b, over1.get(b, 0), over2.get(b, 0)) for b in sorted(pairs)))
    if worst[1]:
        print("  largest: %.1f mm at %.1f min, %s-%s %s" % (1000 * worst[0], worst[1][0], worst[1][1], worst[1][2], worst[1][3]))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = ap.add_subparsers(dest="cmd", required=True)
    p = sp.add_parser("replay")
    p.add_argument("run")
    p.add_argument("--rule", choices=("pv", "legacy"), default="")
    p.add_argument("--to-min", type=float, default=40.0)
    p = sp.add_parser("audit")
    p.add_argument("run")
    p.add_argument("--from-min", type=float, default=0.0)
    a = ap.parse_args()
    {"replay": cmd_replay, "audit": cmd_audit}[a.cmd](a)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Card IRDU section 12.8: the users' ambiguity resets at declared phase-bias discontinuities, per case.

    py -3.14 scripts/irdu_user_resets.py <net tag> [...] [--starts 0,30] [--variant obs] [--user-set SET]

Each user run's logs/closed_loop_sat_trace.csv marks, per satellite and signal, the user's reaction to the stream's
phase-bias discontinuity counter (column ev_pb: none, reset_disc, or a carry).  Printed per case: the reactions summed
over the five users, after the first 5 min of each user's run and in total, and the satellites concerned.
"""
import argparse
import csv
import os
import sys
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import irdu_users as IU  # noqa: E402


def reactions(run):
    p = os.path.join(str(run), "logs", "closed_loop_sat_trace.csv")
    if not os.path.exists(p):
        return None
    out, late, sats = Counter(), Counter(), set()
    t0 = None
    with open(p, newline="") as fh:
        for r in csv.DictReader(fh):
            t = float(r["tow"])
            t0 = t if t0 is None else t0
            ev = r["ev_pb"]
            if ev and ev != "none":
                out[ev] += 1
                sats.add(r["sat"])
                if t - t0 >= 300.0:
                    late[ev] += 1
    return out, late, sats


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("tags", nargs="+")
    ap.add_argument("--starts", default="30")
    ap.add_argument("--variant", default="obs")
    ap.add_argument("--user-set", default="")
    a = ap.parse_args()
    for tag in a.tags:
        for s in (int(x) for x in a.starts.split(",")):
            tot, late, sats = Counter(), Counter(), set()
            n = 0
            for u in IU.USERS:
                r = reactions(IU.user_dir(tag, a.variant, u, s, a.user_set))
                if r is None:
                    continue
                n += 1
                tot.update(r[0])
                late.update(r[1])
                sats |= r[2]
            print("%-16s start %2d set %-3s %s | %d users: reactions %s; after the first 5 min %s; satellites %s" % (
                tag, s, a.user_set or "-", a.variant, n, dict(tot) or "none", dict(late) or "none",
                ",".join(sorted(sats)) or "-"))


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Card IRDU section 12.10: byte identity of user replays between two builds (the key off).

    py -3.14 scripts/irdu_build_identity.py --a fp2 --b ur1 <net tag> [...] [--starts 30] [--users ...] [--user-set SET]

For every user run made under IRDU_USER_BUILD=<a> and <b> (scripts/irdu_users.py; folder suffix _b<tag>), the files
that carry the run's results are compared byte for byte: logs/closed_loop_trace.csv, logs/closed_loop_sat_trace.csv,
logs/consumer_replay_hourly.csv, logs/rt_engine.log and logs/ambiguity_resolver.log (both stamped with GPS time; the backlog warning, which prints the wall clock, is left out).
"""
import argparse
import filecmp
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

FILES = ("closed_loop_trace.csv", "closed_loop_sat_trace.csv", "consumer_replay_hourly.csv", "rt_engine.log",
         "ambiguity_resolver.log")
# The engine's backlog warning prints the replayed epoch's lag behind the wall clock of the run, which differs between
# any two runs made at different times; those lines are left out of the comparison of the logs.
WALL_CLOCK = "behind wall-clock GPS"


def same(fa, fb):
    if fa.endswith(".log"):
        with open(fa, encoding="utf-8", errors="replace") as ha, open(fb, encoding="utf-8", errors="replace") as hb:
            return [ln for ln in ha if WALL_CLOCK not in ln] == [ln for ln in hb if WALL_CLOCK not in ln]
    return filecmp.cmp(fa, fb, shallow=False)


def run_dir(tag, variant, user, start, build, uset=""):
    os.environ["IRDU_USER_BUILD"] = build
    import importlib
    import irdu_users as IU
    importlib.reload(IU)
    return IU.user_dir(tag, variant, user, start, uset)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("tags", nargs="+")
    ap.add_argument("--a", required=True)
    ap.add_argument("--b", required=True)
    ap.add_argument("--starts", default="30")
    ap.add_argument("--users", default="SZZ000SIM,S48000SIM,S40000SIM,S27000SIM,S32000SIM")
    ap.add_argument("--user-set", default="", help="the user configuration set of the runs (card IRDU 12.6), '' = the recipe")
    a = ap.parse_args()
    n = n_same = 0
    for tag in a.tags:
        for s in (int(x) for x in a.starts.split(",")):
            for v in ("obs", "fix"):
                for u in a.users.split(","):
                    da, db = run_dir(tag, v, u, s, a.a, a.user_set), run_dir(tag, v, u, s, a.b, a.user_set)
                    if not (os.path.isdir(da) and os.path.isdir(db)):
                        continue
                    diff = [f for f in FILES
                            if os.path.exists(os.path.join(da, "logs", f)) or os.path.exists(os.path.join(db, "logs", f))
                            if not (os.path.exists(os.path.join(da, "logs", f)) and os.path.exists(os.path.join(db, "logs", f))
                                    and same(os.path.join(da, "logs", f), os.path.join(db, "logs", f)))]
                    n += 1
                    n_same += not diff
                    print("%-46s %s" % (os.path.basename(str(db)), "IDENTICAL" if not diff else "DIFFERS: " + ", ".join(diff)))
    print("identical %d of %d run pairs" % (n_same, n))
    return 0 if n_same == n and n > 0 else 1


if __name__ == "__main__":
    sys.exit(main())

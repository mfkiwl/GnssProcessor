#!/usr/bin/env python3
"""Card IRDU section 12.4: the late-start users, read from each user's own start.  Measure only.

    py -3.14 scripts/irdu_late_start.py <net tag> [<net tag> ...] [--starts 0,30,45] [--users ...] [--json out.json]

For each network run (tag, folder _rap_<tag>) and each start (minutes after the network's first epoch; 0 is the
early start of section 12.1's users, the folders scripts/irdu_users.py makes with --start-min), every user's
logs/closed_loop_trace.csv (pos_err_3d_m per epoch) of the float (obs) and fixing (fix) runs:

  bins     the 3D error median of each user per 15 min from the user's own first epoch, and the median of those over
           the users (mm)
  to 5 cm  the time from the user's first epoch to the first epoch of 10 consecutive epochs at or below 5 cm (card
           IRD's late-start consumer K-c measure), per user; "-" when never within the run
"""
import argparse
import csv
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import irdu_users as IU  # noqa: E402

BIN_MIN = 15.0


def trace(run):
    p = Path(run) / "logs" / "closed_loop_trace.csv"
    if not p.exists():
        return []
    out = []
    with open(p, newline="") as fh:
        for r in csv.DictReader(ln for ln in fh if not ln.startswith("#")):
            try:
                out.append((float(r["tow"]), float(r["pos_err_3d_m"])))
            except (TypeError, ValueError):
                continue
    return out


def median(v):
    v = sorted(v)
    if not v:
        return float("nan")
    n = len(v)
    return v[n // 2] if n % 2 else 0.5 * (v[n // 2 - 1] + v[n // 2])


def to_bar(tr, bar=0.05, run_len=10):
    if not tr:
        return None
    t0 = tr[0][0]
    k = 0
    for i, (t, e) in enumerate(tr):
        k = k + 1 if e <= bar else 0
        if k == run_len:
            return (tr[i - run_len + 1][0] - t0) / 60.0
    return None


def bins(tr):
    if not tr:
        return {}
    t0 = tr[0][0]
    out = {}
    for t, e in tr:
        b = int((t - t0) // (60.0 * BIN_MIN))
        out.setdefault(b, []).append(e)
    return {b: median(v) for b, v in out.items()}


def analyse(tags, starts, users):
    res = {}
    for tag in tags:
        for s in starts:
            for var in ("obs", "fix"):
                per_user = {}
                for u in users:
                    tr = trace(IU.user_dir(tag, var, u, s))
                    per_user[u] = {"n": len(tr), "bins": bins(tr), "to5cm": to_bar(tr)}
                nb = max((max(v["bins"]) for v in per_user.values() if v["bins"]), default=-1) + 1
                over = {}
                for b in range(nb):
                    vals = [v["bins"][b] for v in per_user.values() if b in v["bins"]]
                    if vals:
                        over["%d-%d" % (BIN_MIN * b, BIN_MIN * (b + 1))] = median(vals)
                t5 = [v["to5cm"] for v in per_user.values()]
                res["%s|%d|%s" % (tag, s, var)] = {
                    "users": {u: {"n": v["n"], "to5cm": v["to5cm"]} for u, v in per_user.items()},
                    "median_by_bin": over,
                    "to5cm_p50": median([x for x in t5 if x is not None]) if any(x is not None for x in t5) else None,
                    "never": sum(1 for x in t5 if x is None)}
    return res


def print_result(res):
    for key, r in res.items():
        tag, s, var = key.split("|")
        bins_s = " ".join("%s %.0f" % (b, 1000 * m) for b, m in r["median_by_bin"].items())
        t5 = " ".join("%s %s" % (u[:3].lower(), "-" if v["to5cm"] is None else "%.1f" % v["to5cm"])
                      for u, v in r["users"].items())
        print("%-8s start %2s %-3s | median over users by 15 min from start (mm): %s | to 5 cm (min): %s" % (
            tag, s, var, bins_s, t5))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("tags", nargs="+")
    ap.add_argument("--starts", default="0,30,45")
    ap.add_argument("--users", default=",".join(IU.USERS))
    ap.add_argument("--json")
    a = ap.parse_args()
    res = analyse(a.tags, [int(x) for x in a.starts.split(",")], a.users.split(","))
    print_result(res)
    if a.json:
        with open(a.json, "w") as fh:
            json.dump(res, fh, indent=1)


if __name__ == "__main__":
    main()

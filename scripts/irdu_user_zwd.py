#!/usr/bin/env python3
"""Card IRDU section 12.6, candidate 3: the user's own wet delay against the simulator's truth, beside the network's.

    py -3.14 scripts/irdu_user_zwd.py users <net tag> [--starts 0,30] [--variant obs] [--user-set SET]
    py -3.14 scripts/irdu_user_zwd.py network <net tag> [<net tag> ...]

users: each user's zenith wet delay (the "zwd=" of logs/rt_engine.log, the absolute estimate at each epoch) minus the
truth (truth_tropo.csv of the user's station in the fixture), its median per 15 min from the user's own start, per user
and the median over the users (mm).  network: each station's estimate (logs/network_zwd.csv) minus its truth, the mean
and the median over the stations per 15 min from the run's first epoch (mm).
"""
import argparse
import csv
import json
import os
import re
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import irdu_users as IU  # noqa: E402

RT = re.compile(r"^\[\s*(\d+),\s*([\d.]+).*\[RT\] Epoch \d+: .* zwd=([-\d.]+) sats=(\d+)")


def truth_zwd(fixture, sta):
    out = {}
    with open(Path(fixture) / sta / "truth_tropo.csv", newline="") as fh:
        for r in csv.DictReader(fh):
            out[round(float(r["tow_s"]), 3)] = float(r["zwd_m"])
    return out


def median(v):
    v = sorted(v)
    if not v:
        return float("nan")
    n = len(v)
    return v[n // 2] if n % 2 else 0.5 * (v[n // 2 - 1] + v[n // 2])


def user_series(run, fixture, user):
    tz = truth_zwd(fixture, user)
    out = []
    p = Path(run) / "logs" / "rt_engine.log"
    if not p.exists():
        return out
    with open(p, encoding="utf-8", errors="replace") as fh:
        for ln in fh:
            m = RT.match(ln)
            if m:
                t = round(float(m.group(2)), 3)
                if t in tz:
                    out.append((t, float(m.group(3)) - tz[t], int(m.group(4))))
    return out


def binned(series, t0=None):
    if not series:
        return {}
    t0 = series[0][0] if t0 is None else t0
    b = defaultdict(list)
    for t, e, *_ in series:
        b[int((t - t0) // 900)].append(e)
    return {"%d-%d" % (15 * k, 15 * (k + 1)): median(v) for k, v in sorted(b.items())}


def users(tag, starts, variant, uset):
    net = IU.net_dir(tag)
    fixture = IU.fixture_of(net)
    res = {}
    for s in starts:
        per = {}
        for u in IU.USERS:
            per[u] = binned(user_series(IU.user_dir(tag, variant, u, s, uset), fixture, u))
        keys = sorted({k for v in per.values() for k in v}, key=lambda k: int(k.split("-")[0]))
        res[str(s)] = {"per_user": per, "median": {k: median([v[k] for v in per.values() if k in v]) for k in keys}}
    return res


def network(tag):
    net = IU.net_dir(tag)
    fixture = IU.fixture_of(net)
    est = defaultdict(dict)
    with open(net / "logs" / "network_zwd.csv", newline="") as fh:
        for r in csv.DictReader(fh):
            est[r["station"]][round(float(r["tow"]), 3)] = float(r["zwd_m"])
    t0 = min(min(v) for v in est.values())
    b = defaultdict(list)
    for sta, ser in est.items():
        if not (Path(fixture) / sta / "truth_tropo.csv").exists():
            continue
        tz = truth_zwd(fixture, sta)
        for t, z in ser.items():
            if t in tz:
                b[int((t - t0) // 900)].append(z - tz[t])
    return {"%d-%d" % (15 * k, 15 * (k + 1)): {"mean": sum(v) / len(v), "median": median(v), "n": len(v)}
            for k, v in sorted(b.items())}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("action", choices=("users", "network"))
    ap.add_argument("tags", nargs="+")
    ap.add_argument("--starts", default="0,30")
    ap.add_argument("--variant", default="obs")
    ap.add_argument("--user-set", default="")
    ap.add_argument("--json")
    a = ap.parse_args()
    out = {}
    for tag in a.tags:
        if a.action == "users":
            r = users(tag, [int(x) for x in a.starts.split(",")], a.variant, a.user_set)
            for s, v in r.items():
                print("%-10s start %2s %s | user ZWD error median over users by 15 min (mm): %s" % (
                    tag, s, a.variant, " ".join("%s %.0f" % (k, 1000 * m) for k, m in v["median"].items())))
        else:
            r = network(tag)
            print("%-10s network ZWD error by 15 min, mean / median over stations (mm): %s" % (
                tag, " ".join("%s %.0f/%.0f" % (k, 1000 * v["mean"], 1000 * v["median"]) for k, v in r.items())))
        out[tag] = r
    if a.json:
        with open(a.json, "w") as fh:
            json.dump(out, fh, indent=1)


if __name__ == "__main__":
    main()

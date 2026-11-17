#!/usr/bin/env python3
"""Card IRDU: one table row per graded cell, from the JSON files scripts/irdu_user_grade.py writes.

    py -3.14 scripts/irdu_table.py <grade.json> [<grade.json> ...]

Columns: settled FRAC (WL, N_1), the 30 to 120 min FRAC, settled PAIRS within 0.10, pooled HELD, WRONG / UNRESOLVED
(compared pair-epochs), consensus steps (undeclared of all), the users' median of the float (obs) and fixed 3D error
medians per hour (mm).
"""
import json
import sys


def med(v):
    v = sorted(x for x in v if x is not None)
    return None if not v else (v[len(v) // 2] if len(v) % 2 else 0.5 * (v[len(v) // 2 - 1] + v[len(v) // 2]))


def hour_median(res, key, h):
    return med([dict(r.get(key, [])).get(h) for r in res["users"].values()])


def f3(x):
    return "-" if x is None else "%.3f" % x


def mm(x):
    return "-" if x is None else "%.0f" % (1000 * x)


def pc(x):
    return "-" if x is None else "%.1f" % (100 * x)


def main():
    print("| cell | FRAC settled WL, N_1 | FRAC 30-120 WL, N_1 | PAIRS settled | HELD | WRONG, UNRES (cmp) | consensus "
          "steps (undeclared) | float 3D h1, h2 (mm) | fixed 3D h1, h2 (mm) |")
    print("| --- | --- | --- | --- | --- | --- | --- | --- | --- |")
    for p in sys.argv[1:]:
        r = json.load(open(p))
        q = r["pooled"]
        w = q.get("wrong", {})
        cs = r.get("consensus_steps") or []
        print("| %s | %s, %s | %s, %s | %s %% of %d | %s %% | %d, %d (%d) | %d (%d) | %s, %s | %s, %s |" % (
            r["tag"], f3(q["frac_wl_s"].get("mean")), f3(q["frac_n1_s"].get("mean")), f3(q["frac_wl"].get("mean")),
            f3(q["frac_n1"].get("mean")), pc(q["pairs_s"].get("w010")), q["pairs_s"].get("pairs", 0),
            pc(q.get("held", {}).get("held")), w.get("wrong", 0), w.get("unresolved", 0), w.get("compared", 0),
            len(cs), sum(1 for c in cs if not c[6]), mm(hour_median(r, "pos_obs", 0)), mm(hour_median(r, "pos_obs", 1)),
            mm(hour_median(r, "pos_fix", 0)), mm(hour_median(r, "pos_fix", 1))))
    return 0


if __name__ == "__main__":
    sys.exit(main())

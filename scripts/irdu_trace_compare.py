#!/usr/bin/env python3
"""Card IRDU section 12.10: two user configuration sets on the same stream and build, epoch by epoch.

    py -3.14 scripts/irdu_trace_compare.py <net tag> --a SET --b SET [--starts 30] [--build TAG]

For each user and variant (scripts/irdu_users.py folders; an empty set is written '-'), logs/closed_loop_trace.csv of
the two runs: identical bytes, or the number of epochs whose 3D error differs and the largest difference (mm).
"""
import argparse
import csv
import filecmp
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def trace(path):
    out = {}
    with open(path, newline="") as fh:
        for r in csv.DictReader(ln for ln in fh if not ln.startswith("#")):
            out[r["tow"]] = (float(r["pos_err_3d_m"]), r["num_fixed"])
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("tag")
    ap.add_argument("--a", required=True)
    ap.add_argument("--b", required=True)
    ap.add_argument("--starts", default="30")
    ap.add_argument("--build", default=os.environ.get("IRDU_USER_BUILD", ""))
    a = ap.parse_args()
    os.environ["IRDU_USER_BUILD"] = a.build
    import irdu_users as IU
    sa = "" if a.a == "-" else a.a
    sb = "" if a.b == "-" else a.b
    for s in (int(x) for x in a.starts.split(",")):
        for v in ("obs", "fix"):
            for u in IU.USERS:
                pa = os.path.join(str(IU.user_dir(a.tag, v, u, s, sa)), "logs", "closed_loop_trace.csv")
                pb = os.path.join(str(IU.user_dir(a.tag, v, u, s, sb)), "logs", "closed_loop_trace.csv")
                if not (os.path.exists(pa) and os.path.exists(pb)):
                    print("%s start %d %s %s: missing" % (a.tag, s, v, u))
                    continue
                if filecmp.cmp(pa, pb, shallow=False):
                    print("%s start %2d %s %s: %s and %s IDENTICAL" % (a.tag, s, v, u, a.a, a.b))
                    continue
                ta, tb = trace(pa), trace(pb)
                common = sorted(set(ta) & set(tb), key=float)
                d = [abs(ta[t][0] - tb[t][0]) for t in common]
                nd = sum(1 for x in d if x > 0.0)
                print("%s start %2d %s %s: %s and %s differ at %d of %d epochs, largest 3D difference %.3f mm" % (
                    a.tag, s, v, u, a.a, a.b, nd, len(common), 1000 * max(d) if d else float("nan")))


if __name__ == "__main__":
    main()

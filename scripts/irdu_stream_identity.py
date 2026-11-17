#!/usr/bin/env python3
"""Card IRDU section 13: are two network runs' streams the same, record by record?

    py -3.14 scripts/irdu_stream_identity.py <run A> <run B>

Compares the two runs' products.txt: the whole files byte for byte first; then, record type by record type (E, C, B,
P, R, U, H; the S contract record compared with its discfrac= token removed and reported apart), the number of records,
the records present in one file only, the records whose fields differ, and for C, B and P the largest difference of
the value field (metres).  Comment lines are ignored.
"""
import argparse
import collections
import filecmp
import os


def records(path):
    out = collections.defaultdict(dict)       # type -> {(epoch index, key...): fields}
    s_rec = []
    ep = -1
    with open(path, encoding="utf-8") as fh:
        for ln in fh:
            if ln.startswith("#"):
                continue
            f = ln.rstrip("\n").split(",")
            t = f[0]
            if t == "S":
                s_rec.append(f)
                continue
            if t == "E":
                ep += 1
                out["E"][(ep,)] = f
            elif t in ("C", "U"):
                out[t][(ep, f[1])] = f
            elif t in ("B", "P"):
                out[t][(ep, f[1], f[2])] = f
            else:
                out[t][(ep, len(out[t]))] = f
    return out, s_rec


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("a")
    ap.add_argument("b")
    a = ap.parse_args()
    pa, pb = os.path.join(a.a, "products.txt"), os.path.join(a.b, "products.txt")
    if filecmp.cmp(pa, pb, shallow=False):
        print("%s and %s: products.txt byte-identical" % (a.a, a.b))
        return
    ra, sa = records(pa)
    rb, sb = records(pb)

    def strip_disc(rec):
        return [x for x in rec if not x.startswith("discfrac=")]
    s_same = [strip_disc(x) for x in sa] == [strip_disc(x) for x in sb]
    disc = sorted({x for r in sa + sb for x in r if x.startswith("discfrac=")})
    print("%s and %s: products.txt differ; S record %s apart from discfrac (%s)" % (
        a.a, a.b, "identical" if s_same else "DIFFERENT", ", ".join(disc) or "none"))
    for t in sorted(set(ra) | set(rb)):
        A, B = ra.get(t, {}), rb.get(t, {})
        only_a = len(set(A) - set(B))
        only_b = len(set(B) - set(A))
        common = set(A) & set(B)
        diff = [k for k in common if A[k] != B[k]]
        mx = 0.0
        if t in ("C", "B", "P"):
            vi = 2 if t == "C" else 3
            for k in diff:
                try:
                    mx = max(mx, abs(float(A[k][vi]) - float(B[k][vi])))
                except (ValueError, IndexError):
                    pass
        print("  %s: %d and %d records, only in A %d, only in B %d, differing %d%s" % (
            t, len(A), len(B), only_a, only_b, len(diff), (", largest value difference %.3e m" % mx) if t in ("C", "B", "P") else ""))


if __name__ == "__main__":
    main()

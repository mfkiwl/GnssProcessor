#!/usr/bin/env python3
"""Card IRDU section 12.10: a copy of a product stream with one satellite's records removed over a window, to drive
the consumer's unrecorded-satellite rule through both edges (a record lost, then returned).

    py -3.14 scripts/irdu_record_gap.py <products.txt> --out <products.txt> --sat G05 --from-min 60 --to-min 70

Every C, B, P and U record of the satellite at the epochs from --from-min to --to-min (minutes from the stream's first
epoch, the end excluded) is dropped; every other line is copied unchanged.
"""
import argparse
import os


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("src")
    ap.add_argument("--out", required=True)
    ap.add_argument("--sat", required=True)
    ap.add_argument("--from-min", type=float, required=True)
    ap.add_argument("--to-min", type=float, required=True)
    a = ap.parse_args()
    t0 = tow = None
    dropped = kept = 0
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    with open(a.src, encoding="utf-8") as fh, open(a.out, "w", encoding="utf-8", newline="\n") as out:
        for ln in fh:
            if ln.startswith("E,"):
                tow = round(float(ln.split(",")[2]), 3)
                t0 = tow if t0 is None else t0
            f = ln.split(",")
            if (tow is not None and f[0] in ("C", "B", "P", "U") and len(f) > 1 and f[1] == a.sat
                    and t0 + 60 * a.from_min - 1e-3 <= tow < t0 + 60 * a.to_min - 1e-3):
                dropped += 1
                continue
            kept += 1
            out.write(ln)
    print("%s -> %s: %d records of %s dropped (%.0f to %.0f min), %d lines kept" % (
        a.src, a.out, dropped, a.sat, a.from_min, a.to_min, kept))


if __name__ == "__main__":
    main()

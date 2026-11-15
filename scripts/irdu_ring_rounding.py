#!/usr/bin/env python3
"""Card IRDU section 12 Q3: would plain rounding of the next ring's floats be right, at each stage of ring-by-ring
fixing?  Measure only.

    python scripts/irdu_ring_rounding.py <stage run> --all FILE --pinned FILE|none --next-ring K
        [--minutes 5,10,20,30,60] [--json out.json]
    python scripts/irdu_ring_rounding.py --selftest

<stage run> is a run of the bed without re-seats with some rings held at their true integers (the oracle pin in the
chain's frame) or none.  --all is the frame-target file with every link (scripts/irdu_frame_targets.py --all): it gives
each chord's frame integers N~1, N~2 and its ring.  --pinned is the stage's own frame file (the chords it held), or
`none`.  At each time (minutes after the run's first epoch) every chord row of the chord table
(logs/network_chain_frame.csv: floats n1, n2 and their covariance) is graded against its frame integers:

  WL       round(n1 - n2) = N~1 - N~2
  N1(IF)   the wide lane right and round((f1 n1 - f2 n2 - f2 round(n1 - n2)) / (f1 - f2)) = N~1 (the ionosphere-free
           row with the wide lane rounded, card IRDU section 2)
  bands    round(n1) = N~1 and round(n2) = N~2 (band by band)

with the formal sigma of the wide lane and of the ionosphere-free N_1, and |e| / sigma (e of the ionosphere-free row
taken with the true wide lane).  Two sets of chords, each counted with its wrong would-be integers:

  depth    the chords of ring K not held by the stage (strict depth order)
  best     as many chords as the depth set has, among all the chords not held by the stage, ranked by the number of links
           already at integers at the chord's receiver (its tree links and the stage's held chords), ties by the same
           count at its satellite, then by name (best connected first)
"""
import argparse
import csv
import json
import math
import os
import sys
from collections import defaultdict

F1, F2 = 1575.42e6, 1227.60e6


def read_frame(path):
    """{(sta, sat): {'z1', 'z2', 'ring', 'role'}} from a frame-target file (L1C and L2W rows)."""
    out = defaultdict(dict)
    with open(path, newline="") as fh:
        for r in csv.DictReader(fh):
            k = (r["station"], r["sat"])
            out[k]["z1" if r["signal"] == "L1C" else "z2"] = int(r["frame_int"])
            out[k]["role"] = r["role"]
            out[k]["ring"] = int(r["ring"]) if r.get("ring") not in (None, "", "None") else None
    return {k: v for k, v in out.items() if "z1" in v and "z2" in v}


def grade_row(f1, f2, q11, q12, q22, z1, z2):
    w = f1 - f2
    wl_ok = round(w) == z1 - z2
    n_card = (F1 * f1 - F2 * f2 - F2 * round(w)) / (F1 - F2)
    nl_ok = wl_ok and round(n_card) == z1
    bands_ok = round(f1) == z1 and round(f2) == z2
    s_wl = math.sqrt(max(q11 + q22 - 2.0 * q12, 0.0))
    s_nl = math.sqrt(max(F1 * F1 * q11 - 2.0 * F1 * F2 * q12 + F2 * F2 * q22, 0.0)) / (F1 - F2)
    e_wl = w - (z1 - z2)
    e_nl = (F1 * f1 - F2 * f2 - F2 * (z1 - z2)) / (F1 - F2) - z1
    return {"wl_ok": wl_ok, "nl_ok": nl_ok, "bands_ok": bands_ok, "s_wl": s_wl, "s_nl": s_nl,
            "z_wl": abs(e_wl) / s_wl if s_wl > 0 else float("nan"),
            "z_nl": abs(e_nl) / s_nl if s_nl > 0 else float("nan"),
            "frac_nl": abs(n_card - round(n_card)), "e_nl": e_nl}


def gated(rows, sigma_max, frac_max=0.20):
    """Card IRDU 12.4 (b): accept a link's N_1 (the ionosphere-free row with the wide lane rounded) only when its
    formal sigma is at most sigma_max and its fraction at most frac_max; (accepted, wrong among accepted)."""
    acc = [r for r in rows if r["s_nl"] <= sigma_max and r["frac_nl"] <= frac_max]
    return len(acc), sum(not r["nl_ok"] for r in acc)


def p50(v):
    v = sorted(x for x in v if not math.isnan(x))
    return v[len(v) // 2] if v else float("nan")


def summarize(rows):
    n = len(rows)
    if not n:
        return {"n": 0}
    return {"n": n,
            "wl_right": sum(r["wl_ok"] for r in rows), "nl_right": sum(r["nl_ok"] for r in rows),
            "bands_right": sum(r["bands_ok"] for r in rows),
            "wl_wrong": sum(not r["wl_ok"] for r in rows), "nl_wrong": sum(not r["nl_ok"] for r in rows),
            "bands_wrong": sum(not r["bands_ok"] for r in rows),
            "s_wl_p50": p50([r["s_wl"] for r in rows]), "s_nl_p50": p50([r["s_nl"] for r in rows]),
            "z_wl_p50": p50([r["z_wl"] for r in rows]), "z_nl_p50": p50([r["z_nl"] for r in rows])}


def connectivity(frame, held):
    """Per receiver and per satellite: the number of links at integers (tree links of the frame file and held chords)."""
    rx, sv = defaultdict(int), defaultdict(int)
    for (sta, sat), v in frame.items():
        if v["role"] == "tree" or (sta, sat) in held:
            rx[sta] += 1
            sv[sat] += 1
    return rx, sv


def analyse(run, all_path, pinned_path, next_ring, minutes):
    frame = read_frame(all_path)
    held = set() if pinned_path in (None, "none") else {k for k, v in read_frame(pinned_path).items()
                                                          if v["role"] == "chord"}
    chords = {k for k, v in frame.items() if v["role"] == "chord" and k not in held}
    depth_set = {k for k in chords if frame[k]["ring"] == next_ring}
    rx, sv = connectivity(frame, held)
    ranked = sorted(chords, key=lambda k: (-rx[k[0]], -sv[k[1]], k))
    best_set = set(ranked[:len(depth_set)])
    rows = defaultdict(dict)                              # tow -> (sta, sat) -> chord row
    t0 = None
    with open(os.path.join(run, "logs", "network_chain_edges.csv"), newline="") as fh:
        for r in csv.DictReader(fh):
            t0 = float(r["tow"]) if t0 is None else min(t0, float(r["tow"]))
    want = {round(t0 + 60.0 * m, 3): m for m in minutes}
    with open(os.path.join(run, "logs", "network_chain_frame.csv"), newline="") as fh:
        for r in csv.DictReader(ln for ln in fh if not ln.startswith("#")):
            t = round(float(r["tow"]), 3)
            if t in want:
                rows[t][(r["arc_sta"], r["arc_sat"])] = r
    res = {"run": run, "next_ring": next_ring, "held_chords": len(held), "depth_set": len(depth_set),
           "best_set": len(best_set), "overlap": len(depth_set & best_set),
           "best_rx_links_p50": p50([rx[k[0]] for k in best_set]),
           "depth_rx_links_p50": p50([rx[k[0]] for k in depth_set]), "by_minute": {}}
    for t, m in sorted(want.items(), key=lambda kv: kv[1]):
        out = {}
        for name, sel in (("depth", depth_set), ("best", best_set), ("unheld", chords)):
            graded = []
            for k in sel:
                r = rows.get(t, {}).get(k)
                if r is None:
                    continue
                v = frame[k]
                graded.append(grade_row(float(r["float_cyc_1"]), float(r["float_cyc_2"]), float(r["q11"]),
                                        float(r["q12"]), float(r["q22"]), v["z1"], v["z2"]))
            out[name] = summarize(graded)
            out[name]["gated"] = {"%.2f" % g: gated(graded, g) for g in GATES}
        res["by_minute"][str(m)] = out
    return res


GATES = (0.10, 0.15)


def print_gated(res, label):
    print("== %s, gated rounding of N_1 (sigma at most the gate, fraction at most 0.20): accepted / wrong among "
          "accepted, of n" % label)
    for m, out in res["by_minute"].items():
        parts = []
        for name in ("depth", "unheld"):
            s = out[name]
            if not s.get("n"):
                continue
            gs = "; ".join("gate %s: %d/%d" % (g, a, w) for g, (a, w) in s["gated"].items())
            parts.append("%s n %d: %s" % ("next ring" if name == "depth" else "all not held", s["n"], gs))
        print("   %4s min  %s" % (m, " | ".join(parts)))


def print_result(res, label):
    print("== %s: next ring %d (%d chords not held; best-connected set %d, overlap %d; integer links at the receiver "
          "p50: depth set %s, best set %s; held chords %d)" % (
              label, res["next_ring"], res["depth_set"], res["best_set"], res["overlap"], res["depth_rx_links_p50"],
              res["best_rx_links_p50"], res["held_chords"]))
    for m, out in res["by_minute"].items():
        for name in ("depth", "best"):
            s = out[name]
            if not s.get("n"):
                print("   %3s min %-5s n 0" % (m, name))
                continue
            print("   %3s min %-5s n %3d | WL right %3d (wrong %3d) | N1(IF) right %3d (wrong %3d) | bands right %3d "
                  "(wrong %3d) | sigma WL %.3f N1 %.3f | |e|/sigma WL %.2f N1 %.2f" % (
                      m, name, s["n"], s["wl_right"], s["wl_wrong"], s["nl_right"], s["nl_wrong"], s["bands_right"],
                      s["bands_wrong"], s["s_wl_p50"], s["s_nl_p50"], s["z_wl_p50"], s["z_nl_p50"]))


def selftest():
    ok = True

    def chk(c, msg):
        nonlocal ok
        print(("PASS " if c else "FAIL ") + msg)
        ok &= bool(c)

    g = grade_row(10.2, 7.1, 0.01, 0.0, 0.01, 10, 7)
    chk(g["wl_ok"] and g["bands_ok"], "a float near its integers rounds right on the wide lane and on both bands")
    e1 = 0.4
    g = grade_row(10 + e1, 7 + e1 * F1 / F2, 0.04, 0.04, 0.04, 10, 7)
    chk(g["wl_ok"] and g["nl_ok"] and not g["bands_ok"],
        "an ionosphere-like error passes the ionosphere-free row and fails band by band")
    g = grade_row(10.6, 7.0, 0.01, 0.0, 0.01, 10, 7)
    chk(not g["wl_ok"] and not g["nl_ok"], "a wrong wide lane makes the ionosphere-free N_1 wrong")
    rx, sv = connectivity({("R1", "G1"): {"role": "tree"}, ("R1", "G2"): {"role": "chord"},
                           ("R2", "G2"): {"role": "chord"}}, {("R1", "G2")})
    chk(rx["R1"] == 2 and rx["R2"] == 0 and sv["G2"] == 1, "links at integers count tree links and held chords")
    return ok


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("run", nargs="?")
    ap.add_argument("--all")
    ap.add_argument("--pinned", default="none")
    ap.add_argument("--next-ring", type=int)
    ap.add_argument("--minutes", default="5,10,20,30,60")
    ap.add_argument("--label", default=None)
    ap.add_argument("--json")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        sys.exit(0 if selftest() else 1)
    res = analyse(os.path.abspath(a.run), a.all, a.pinned, a.next_ring, [float(x) for x in a.minutes.split(",")])
    print_result(res, a.label or os.path.basename(a.run))
    print_gated(res, a.label or os.path.basename(a.run))
    if a.json:
        with open(a.json, "w") as fh:
            json.dump(res, fh, indent=1)


if __name__ == "__main__":
    main()

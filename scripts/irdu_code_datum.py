#!/usr/bin/env python3
"""Card IRDU section 12.6, candidate 1: a product stream moved onto the simulator's truth code datum, consistently.

    py -3.14 scripts/irdu_code_datum.py terms <products.txt> [<products.txt> ...] [--fixture DIR]
    py -3.14 scripts/irdu_code_datum.py move <products.txt> --out <products.txt> [--remove x,r,frac] [--fixture DIR]
    py -3.14 scripts/irdu_code_datum.py check <original> <moved> [--remove x,r,frac] [--fixture DIR]
    py -3.14 scripts/irdu_code_datum.py observed <broadcast navigation file> <CODE OSB .BIA file>
    py -3.14 scripts/irdu_code_datum.py --selftest

--remove (default x) also takes r, the range-like code term (B'_b = B_b + r on both bands: the code then equals the
truth's but for x), and frac, the fractional part of what the user's float absorbs (P'_b = P_b + lambda_b (E_b -
round(E_b)): each E_b left at its integer, the frame's offset).  x, r and frac together leave a stream whose code
corrections are the truth's and whose phase corrections are the truth's plus whole cycles.

The stream algebra of card IRD section 8 (scripts/simnet_wire_integer_consistency.py): with dX = emitted - truth,
Wc_b = dC - dB_b and Wp_b = dC - dP_b (metres), the code-implied ionosphere-like term of a satellite is

    x = (Wc_1 - Wc_2) / (mu_1 - mu_2),   mu_b = (f_1 / f_b)^2

(the clock cancels: x depends on the code biases alone), the range-like code term r = Wc_1 - mu_1 x, and what a user's
float absorbs on band b is E_b = (Wp_b + mu_b x) / lambda_b.  A stream whose geometry-free code biases sit at the
broadcast T_GD while the truth sits elsewhere is self-consistent only through x.  The move removes x from both halves:

    B'_b = B_b + mu_b x,   P'_b = P_b - mu_b x

so that x' = 0 (the code biases' geometry-free part is the truth's), r' = r and E'_b = E_b (every satellite pair keeps
its integers and fractions); the clocks and every other field are unchanged.  GPS L1C / L2W phase and C1C / C2W code.

terms prints, per stream, x per satellite (its value over the run and its change from the first epoch) and the
satellite mean of r against the epoch's median over satellites.  check verifies a moved stream against its original:
x' = 0, r' = r and E'_b = E_b at every satellite and epoch (largest deviation printed).
"""
import argparse
import os
import sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import simnet_wire_integer_consistency as WIC  # noqa: E402

F1, F2 = 1575.42e6, 1227.60e6
MU = {"1": 1.0, "2": (F1 / F2) ** 2}
PHASE = {"1": "L1C", "2": "L2W"}
CODE = {"1": "C1C", "2": "C2W"}


def truth_osb(fixture):
    osb, disagree = WIC.load_osb_truth(WIC.station_dirs(fixture))
    if disagree:
        raise SystemExit("refused: %d truth OSB values disagree across stations" % disagree)
    return osb


def x_of(b1, b2, osb, sat):
    """The ionosphere-like term x (m) of a satellite from its two emitted code biases and the truth OSB."""
    wc1_minus_wc2 = -(b1 - osb[(sat, CODE["1"])]) + (b2 - osb[(sat, CODE["2"])])
    return wc1_minus_wc2 / (MU["1"] - MU["2"])


def read_code_biases(path):
    """{(tow, sat): {band: B}} of the C1C and C2W code biases."""
    out = defaultdict(dict)
    tow = None
    with open(path, encoding="utf-8") as fh:
        for ln in fh:
            if ln.startswith("#") or not ln.strip():
                continue
            f = ln.rstrip("\n").split(",")
            if f[0] == "E":
                tow = round(float(f[2]), 1)
            elif f[0] == "B" and tow is not None and f[1].startswith("G"):
                for band, sig in CODE.items():
                    if f[2] == sig:
                        out[(tow, f[1])][band] = float(f[3])
    return out


LAMBDA = {"1": 299792458.0 / F1, "2": 299792458.0 / F2}
REMOVABLE = ("x", "r", "frac", "fracc", "cm")
CM_WINDOW_MIN = (30.0, 120.0)


def constant_integers(vals):
    """{(sat, band): n} one integer per satellite and band: the rounded median of E_b over CM_WINDOW_MIN (over every
    epoch for a satellite with none in the window).  fracc removes everything but these (section 12.6's addendum:
    rounding each epoch on its own flips the integer wherever the fraction crosses half a cycle)."""
    t0 = min(t for t, _ in vals)
    lo, hi = t0 + 60.0 * CM_WINDOW_MIN[0], t0 + 60.0 * CM_WINDOW_MIN[1]
    win, every = defaultdict(list), defaultdict(list)
    for (t, s), v in vals.items():
        for b in ("1", "2"):
            every[(s, b)].append(v["E" + b])
            if lo <= t < hi:
                win[(s, b)].append(v["E" + b])
    out = {}
    for k, xs in every.items():
        ys = sorted(win.get(k) or xs)
        out[k] = int(round(ys[len(ys) // 2]))
    return out


def phase_common_mode(vals):
    """{(tow, band): cm} the common mode of each band's phase error across satellites (section 12.6's addendum): each
    satellite's lambda_b E_b less its own mean over CM_WINDOW_MIN (minutes from the stream's first epoch), averaged
    over the satellites of the epoch that have a window mean."""
    t0 = min(t for t, _ in vals)
    lo, hi = t0 + 60.0 * CM_WINDOW_MIN[0], t0 + 60.0 * CM_WINDOW_MIN[1]
    means = defaultdict(list)
    for (t, s), v in vals.items():
        if lo <= t < hi:
            for b in ("1", "2"):
                means[(s, b)].append(LAMBDA[b] * v["E" + b])
    mean = {k: sum(x) / len(x) for k, x in means.items()}
    acc = defaultdict(list)
    for (t, s), v in vals.items():
        for b in ("1", "2"):
            if (s, b) in mean:
                acc[(t, b)].append(LAMBDA[b] * v["E" + b] - mean[(s, b)])
    return {k: sum(x) / len(x) for k, x in acc.items()}


def move(src, dst, fixture, remove=("x",)):
    """Rewrite the B and P values of a stream to remove, per satellite and epoch, any of: x (B'_b = B_b + mu_b x,
    P'_b = P_b - mu_b x), r (B'_b = B_b + r on both bands, which leaves x), frac (P'_b = P_b + lambda_b (E_b -
    round(E_b)), which leaves each E_b at its integer).  Every other field and record is copied unchanged."""
    vals = sat_values(src, fixture)
    cm = phase_common_mode(vals) if "cm" in remove else {}
    ints = constant_integers(vals) if "fracc" in remove else {}
    n = defaultdict(int)
    tow = None
    os.makedirs(os.path.dirname(os.path.abspath(dst)), exist_ok=True)
    with open(src, encoding="utf-8") as fh, open(dst, "w", encoding="utf-8", newline="\n") as out:
        for ln in fh:
            if ln.startswith("#") or not ln.strip():
                out.write(ln)
                continue
            f = ln.rstrip("\n").split(",")
            if f[0] == "E":
                tow = round(float(f[2]), 3)
            elif f[0] in ("B", "P") and tow is not None and f[1].startswith("G"):
                sigs = CODE if f[0] == "B" else PHASE
                band = next((b for b, s in sigs.items() if s == f[2]), None)
                v = vals.get((tow, f[1]))
                if band is not None and v is not None:
                    shift = 0.0
                    if f[0] == "B":
                        if "x" in remove:
                            shift += MU[band] * v["x"]
                        if "r" in remove:
                            shift += v["r"]
                    else:
                        if "x" in remove:
                            shift -= MU[band] * v["x"]
                        if "frac" in remove:
                            e = v["E" + band]
                            shift += LAMBDA[band] * (e - round(e))
                        if "fracc" in remove:
                            shift += LAMBDA[band] * (v["E" + band] - ints[(f[1], band)])
                        if "cm" in remove:
                            shift += cm.get((tow, band), 0.0)
                    f[3] = repr(float(f[3]) + shift)
                    n[f[0] + " moved"] += 1
                elif band is not None:
                    n[f[0] + " left (no value)"] += 1
            out.write(",".join(f) + "\n")
    return dict(n), len(vals)


def sat_values(path, fixture):
    osb, sc_truth, epochs, _ = WIC.dual_load(fixture, os.path.dirname(os.path.abspath(path))
                                             if os.path.basename(path) == "products.txt" else path)
    out = {}
    for ep in epochs:
        for s, v in WIC.dual_sat_values(ep, osb, sc_truth, ("L1C", "L2W")).items():
            if s.startswith("G"):
                out[(ep["tow"], s)] = v
    return out


def check(orig, moved, fixture, remove=("x",)):
    """Largest deviation of the moved stream from what the move promises: x' = 0 or x, r' = 0 or r, E'_b = round(E_b)
    or E_b, per the removed set."""
    a, b = sat_values(orig, fixture), sat_values(moved, fixture)
    cm = phase_common_mode(a) if "cm" in remove else {}
    ints = constant_integers(a) if "fracc" in remove else {}
    common = set(a) & set(b)
    dev = {"x": 0.0, "r": 0.0, "E1": 0.0, "E2": 0.0}
    for k in common:
        dev["x"] = max(dev["x"], abs(b[k]["x"] - (0.0 if "x" in remove else a[k]["x"])))
        dev["r"] = max(dev["r"], abs(b[k]["r"] - (0.0 if "r" in remove else a[k]["r"])))
        for e in ("E1", "E2"):
            if "fracc" in remove:
                want = float(ints[(k[1], e[1])])
            else:
                want = round(a[k][e]) if "frac" in remove else a[k][e]
            want -= cm.get((k[0], e[1]), 0.0) / LAMBDA[e[1]]
            dev[e] = max(dev[e], abs(b[k][e] - want))
    if cm:
        left = phase_common_mode(b)
        dev["cm left (m)"] = max(abs(v) for v in left.values())
    return len(common), len(set(a) ^ set(b)), dev


def terms(path, fixture):
    v = sat_values(path, fixture)
    by_sat = defaultdict(list)
    by_tow = defaultdict(dict)
    for (t, s), d in v.items():
        by_sat[s].append((t, d["x"]))
        by_tow[t][s] = d["r"]
    xs = {s: sorted(vals) for s, vals in by_sat.items()}
    xabs = sorted(abs(sum(x for _, x in vals) / len(vals)) for vals in xs.values())
    xchg = sorted(max(abs(x - vals[0][1]) for _, x in vals) for vals in xs.values())
    rdev = defaultdict(list)
    for t, rs in by_tow.items():
        med = sorted(rs.values())[len(rs) // 2]
        for s, r in rs.items():
            rdev[s].append(r - med)
    rmean = sorted(abs(sum(d) / len(d)) for d in rdev.values())

    def q(v, p):
        return v[min(len(v) - 1, int(p * (len(v) - 1) + 0.5))] if v else float("nan")
    return {"sats": len(xs), "x_abs_p50": q(xabs, 0.5), "x_abs_max": xabs[-1] if xabs else float("nan"),
            "x_change_max": xchg[-1] if xchg else float("nan"), "r_satmean_abs_p50": q(rmean, 0.5),
            "r_satmean_abs_max": rmean[-1] if rmean else float("nan"),
            "x_by_sat": {s: sum(x for _, x in vals) / len(vals) for s, vals in sorted(xs.items())}}


def observed_x(nav_path, bia_path):
    """x per GPS satellite on observed data: a stream whose C1C-C2W geometry-free code bias sits at the broadcast T_GD
    (B_1 = c T_GD, B_2 = mu_2 c T_GD, the stream's convention) against CODE's observable-specific biases (C1C, C2W)
    standing in for the truth.  The first T_GD of each satellite in the navigation file."""
    c = 299792458.0
    tgd = {}
    with open(nav_path, encoding="utf-8", errors="replace") as fh:
        lines = fh.readlines()
    i = next(k for k, ln in enumerate(lines) if "END OF HEADER" in ln) + 1
    while i < len(lines):
        ln = lines[i]
        if ln.startswith("G") and len(ln) > 3 and ln[1:3].isdigit():
            sat = ln[:3]
            if sat not in tgd and i + 6 < len(lines):
                f6 = lines[i + 6].replace("D", "E")
                tgd[sat] = float(f6[42:61])
            i += 8
        elif ln[:1].isalpha():
            i += 1
        else:
            i += 1
    osb = {}
    with open(bia_path, encoding="utf-8", errors="replace") as fh:
        for ln in fh:
            p = ln.split()
            if len(p) >= 9 and p[0] == "OSB" and p[2].startswith("G") and p[3] in ("C1C", "C2W") and p[6] == "ns":
                osb[(p[2], p[3])] = float(p[7]) * 1e-9 * c
    out = {}
    for sat, t in sorted(tgd.items()):
        if (sat, "C1C") in osb and (sat, "C2W") in osb:
            b1, b2 = c * t, MU["2"] * c * t
            out[sat] = ((b2 - b1) - (osb[(sat, "C2W")] - osb[(sat, "C1C")])) / (MU["1"] - MU["2"])
    return out


def selftest():
    ok = True

    def chk(c, msg):
        nonlocal ok
        print(("PASS " if c else "FAIL ") + msg)
        ok &= bool(c)

    osb = {("G01", "C1C"): 0.3, ("G01", "C2W"): -0.4}
    b1, b2 = 0.3 + 0.2, -0.4 + 0.2 * MU["2"] - 0.0     # an ionosphere-like shift of the code biases plus nothing else
    # dB_b = mu_b * d with d = 0.2 -> Wc_b = dC - mu_b d -> x = -d
    x = x_of(b1, b2, osb, "G01")
    chk(abs(x + 0.2) < 1e-12, "a pure ionosphere-like code shift reads as x = -0.2 m")
    b1m, b2m = b1 + MU["1"] * x, b2 + MU["2"] * x
    chk(abs(x_of(b1m, b2m, osb, "G01")) < 1e-12, "after the move the code biases carry no x")
    # E_b unchanged: Wp_b + mu_b x before equals Wp'_b + mu_b x' after, with P'_b = P_b - mu_b x
    dc, p1, p2, t1, t2 = 0.05, 1.0, 2.0, 0.9, 1.7
    e_before = [(dc - (p - t)) + MU[b] * x for b, p, t in (("1", p1, t1), ("2", p2, t2))]
    e_after = [(dc - (p - MU[b] * x - t)) + 0.0 for b, p, t in (("1", p1, t1), ("2", p2, t2))]
    chk(max(abs(u - v) for u, v in zip(e_before, e_after)) < 1e-12, "the phase move keeps E_b on both bands")
    return ok


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("action", nargs="?", choices=("terms", "move", "check", "observed"))
    ap.add_argument("paths", nargs="*")
    ap.add_argument("--out")
    ap.add_argument("--remove", default="x", help="comma list of x, r, frac (move and check)")
    ap.add_argument("--fixture", default="C:/GnssProcessor/runs/simarl_r3c")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        sys.exit(0 if selftest() else 1)
    if a.action == "terms":
        for p in a.paths:
            t = terms(p, a.fixture)
            print("== %s: %d satellites; |x| (satellite mean) p50 %.3f m, max %.3f m; largest change of x over the run "
                  "%.2e m; |mean r - epoch median| p50 %.3f m, max %.3f m" % (
                      p, t["sats"], t["x_abs_p50"], t["x_abs_max"], t["x_change_max"], t["r_satmean_abs_p50"],
                      t["r_satmean_abs_max"]))
            print("   x by satellite (m): " + ", ".join("%s %.3f" % kv for kv in t["x_by_sat"].items()))
    elif a.action == "move":
        rm = tuple(s for s in a.remove.split(",") if s)
        if any(s not in REMOVABLE for s in rm):
            raise SystemExit("--remove takes %s" % ",".join(REMOVABLE))
        n, nv = move(a.paths[0], a.out, a.fixture, rm)
        print("moved %s -> %s, removed %s: %s (values for %d satellite-epochs)" % (a.paths[0], a.out, rm, n, nv))
    elif a.action == "observed":
        xo = observed_x(a.paths[0], a.paths[1])
        vals = sorted(xo.values())
        mean = sum(vals) / len(vals)
        dev = sorted(abs(v - mean) for v in vals)
        print("observed x (broadcast T_GD against CODE OSB): %d satellites, mean %.3f m, |x - mean| p50 %.3f m, max "
              "%.3f m" % (len(vals), mean, dev[len(dev) // 2], dev[-1]))
        print("   " + ", ".join("%s %.3f" % kv for kv in xo.items()))
    elif a.action == "check":
        rm = tuple(s for s in a.remove.split(",") if s)
        nc, nx, dev = check(a.paths[0], a.paths[1], a.fixture, rm)
        print("check (removed %s): %d satellite-epochs in both, %d in one only; largest deviation from the promise: "
              "x %.2e m, r %.2e m, E1 %.2e cyc, E2 %.2e cyc%s" % (
                  rm, nc, nx, dev["x"], dev["r"], dev["E1"], dev["E2"],
                  "; common mode left %.2e m" % dev["cm left (m)"] if "cm left (m)" in dev else ""))


if __name__ == "__main__":
    main()

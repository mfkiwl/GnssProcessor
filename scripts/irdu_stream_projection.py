#!/usr/bin/env python3
"""Card IRDU section 12.6: what a stream's errors do to one user's wet delay and position, by least squares alone.

    py -3.14 scripts/irdu_stream_projection.py <run or products.txt> [...] --user SZZ000SIM [--from-min 30]
        [--to-min 120] [--fixture DIR]

For each satellite of the user's sky and each epoch of the window, the stream's error in the user's ionosphere-free
phase correction (metres; x cancels in this combination) and in its ionosphere-free code correction, both against truth
(scripts/simnet_wire_integer_consistency.py's algebra: lambda_b E_b on the phase, r on the code).  Each is fitted by
weighted least squares (weight sin^2 of the elevation, the elevation model) to what a static float user estimates:

    phase:  e_s(t) = a_s + c(t) + d_zwd * m_w(el_s(t)) - u_s(t) . dx       (a_s an ambiguity, c(t) a clock)
    code:   e_s(t) =       c(t) + d_zwd * m_w(el_s(t)) - u_s(t) . dx

with m_w = 1/sin(el) and u the unit vector to the satellite in east, north, up.  Printed: d_zwd and dx (east, north,
up) in mm, the share of the error variance the fit explains, and n.  The user's geometry (elevation, azimuth) is the
simulator's (truth_atmo.csv of the user's station).  A truth stream reads 0.
"""
import argparse
import csv
import math
import os
import sys
from collections import defaultdict

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import simnet_wire_integer_consistency as WIC  # noqa: E402

F1, F2 = 1575.42e6, 1227.60e6
C = 299792458.0
L1, L2 = C / F1, C / F2
G1 = F1 * F1 / (F1 * F1 - F2 * F2)
G2 = F2 * F2 / (F1 * F1 - F2 * F2)


def geometry(fixture, user):
    out = {}
    with open(os.path.join(fixture, user, "truth_atmo.csv"), newline="") as fh:
        for r in csv.DictReader(fh):
            out[(round(float(r["tow_s"]), 3), r["satellite"])] = (float(r["elev_deg"]), float(r["az_deg"]))
    return out


def errors(run, fixture):
    path = run if os.path.isdir(run) else os.path.dirname(os.path.abspath(run))
    osb, sc_truth, epochs, _ = WIC.dual_load(fixture, path)
    out = {}
    for ep in epochs:
        for s, v in WIC.dual_sat_values(ep, osb, sc_truth, ("L1C", "L2W")).items():
            if s.startswith("G"):
                phase_if = G1 * L1 * v["E1"] - G2 * L2 * v["E2"]
                out[(ep["tow"], s)] = (phase_if, v["r"])
    return out


def fit(rows, with_amb):
    """rows: (tow, sat, el, az, e). Weighted LS with per-epoch clocks, optional per-satellite ambiguities."""
    tows = sorted({r[0] for r in rows})
    sats = sorted({r[1] for r in rows})
    ti = {t: i for i, t in enumerate(tows)}
    si = {s: i for i, s in enumerate(sats)}
    nc = len(tows)
    na = len(sats) - 1 if with_amb else 0          # one ambiguity is in the clocks' datum
    npar = nc + na + 4
    A = np.zeros((len(rows), npar))
    y = np.zeros(len(rows))
    w = np.zeros(len(rows))
    for k, (t, s, el, az, e) in enumerate(rows):
        e_r, a_r = math.radians(el), math.radians(az)
        A[k, ti[t]] = 1.0
        if with_amb and si[s] > 0:
            A[k, nc + si[s] - 1] = 1.0
        A[k, nc + na] = 1.0 / math.sin(e_r)
        u = (math.cos(e_r) * math.sin(a_r), math.cos(e_r) * math.cos(a_r), math.sin(e_r))
        A[k, nc + na + 1:nc + na + 4] = [-u[0], -u[1], -u[2]]
        y[k] = e
        w[k] = math.sin(e_r) ** 2
    sw = np.sqrt(w)
    sol, *_ = np.linalg.lstsq(A * sw[:, None], y * sw, rcond=None)
    res = y - A @ sol
    var_y = np.sum(w * (y - np.sum(w * y) / np.sum(w)) ** 2)
    expl = 1.0 - np.sum(w * res ** 2) / var_y if var_y > 0 else float("nan")
    return {"zwd_mm": 1000 * sol[nc + na], "dx_mm": [1000 * x for x in sol[nc + na + 1:]], "explained": expl,
            "n": len(rows)}


def analyse(run, fixture, user, from_min, to_min, mask_deg=10.0):
    geo = geometry(fixture, user)
    err = errors(run, fixture)
    t0 = min(t for t, _ in err)
    rows_p, rows_c = [], []
    for (t, s), (ep, ec) in err.items():
        if not (t0 + 60 * from_min <= t < t0 + 60 * to_min):
            continue
        g = geo.get((t, s))
        if g is None or g[0] < mask_deg:
            continue
        rows_p.append((t, s, g[0], g[1], ep))
        rows_c.append((t, s, g[0], g[1], ec))
    return {"phase": fit(rows_p, True), "code": fit(rows_c, False)}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("runs", nargs="+")
    ap.add_argument("--user", default="SZZ000SIM")
    ap.add_argument("--from-min", type=float, default=30.0)
    ap.add_argument("--to-min", type=float, default=120.0)
    ap.add_argument("--fixture", default="C:/GnssProcessor/runs/simarl_r3c")
    a = ap.parse_args()
    for run in a.runs:
        r = analyse(run, a.fixture, a.user, a.from_min, a.to_min)
        for k in ("phase", "code"):
            f = r[k]
            print("%-34s %s %-5s | wet delay %+.1f mm | east %+.1f north %+.1f up %+.1f mm | explained %.2f | n %d" % (
                os.path.basename(run.rstrip("/\\")), a.user, k, f["zwd_mm"], f["dx_mm"][0], f["dx_mm"][1],
                f["dx_mm"][2], f["explained"], f["n"]))


if __name__ == "__main__":
    main()

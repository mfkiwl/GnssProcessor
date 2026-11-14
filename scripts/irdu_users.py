#!/usr/bin/env python3
"""Simulated users on a network run's product stream (card IRDU): the fixing control's resolver replayed at
several stations of the bed.

    py -3.14 scripts/irdu_users.py make <net tag> [--users SZZ000SIM,...] [--variants obs,fix] [--flip auto]
    py -3.14 scripts/irdu_users.py run  <net tag> [--users ...] [--variants obs,fix] [--jobs 4]
    py -3.14 scripts/irdu_users.py list <net tag>

<net tag> is the network run's tag (folder _rap_<net tag> under RAPID_RUNS_ROOT, default
D:/GnssProcessorSupport/runs_nom).  One user run per user and variant, folder
_rap_irdu_u_<net tag less its irdu_ prefix>_<variant>_<user, lower case, first three characters>.

Each user run is a consumer replay (network.closed_loop.replay_products_path = the network run's products.txt) of
the network run's own arm.json with the recipe of the fixing control (card ARN; the field tool nw_arms.py):

  network.closed_loop.consumer_undifferenced false, ar_mode 1, ar_wl_only false (the closed-loop wrapper overlays
  its own wide-lane-only flag, default on, otherwise), the station = the user (its fixture RINEX, never a RINEX the
  network arm rewrote, and its true position), pb_hold_presence_flip = the network run's emission hold (true with the
  hold, false without it, unless --flip says otherwise); network.trace_consumer_sat true;
  estimation.ambiguity_resolution = the b12 block below; filter.process_noise.position_q 0 (static user);
  logging.enable_ambiguity_resolver true at level debug; processing.eigen_threads 1 (a run setting, the same on
  every user run).

Variants: obs = the block with ratio_threshold 1e9 (no fix is ever accepted: the float user and its fractions);
fix = the block with wl_branch_check true (the fixing control's fixing arm).

The executable is environment IRDU_USER_EXE (card IRDU: the renamed copy of the fixing control's
gnss_processor_rscb3.exe, sha256[:16] 5ecf8e1c765fafe3), launched through scripts/ev_launch.ps1 (cwd = run folder).
"""
import argparse
import json
import os
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RUNS = Path(os.environ.get("RAPID_RUNS_ROOT") or "D:/GnssProcessorSupport/runs_nom")
LAUNCH = ROOT / "scripts" / "ev_launch.ps1"
USERS = ["SZZ000SIM", "S48000SIM", "S40000SIM", "S27000SIM", "S32000SIM"]
AR = {"mode": 1, "ratio_threshold": 5.0, "ratio_upper_bound": 10000.0, "elevation_mask": 20.0, "min_epochs": 10,
      "max_position_sigma_m": 0.05, "enable_partial_ar": True, "hold_variance": 1e-07, "wl_from_float": True,
      "nl_sigma_floor_cyc": 0.04, "nl_iono_free_row": True, "hold_release_cyc": 0.25, "refloat_partner_signal": True}
VARIANT = {"obs": {"ratio_threshold": 1e9}, "fix": {"wl_branch_check": True}}


def net_dir(tag):
    return RUNS / ("_rap_" + tag)


def user_dir(tag, variant, user):
    short = tag[5:] if tag.startswith("irdu_") else tag
    return RUNS / ("_rap_irdu_u_%s_%s_%s" % (short, variant, user[:3].lower()))


def fixture_of(net):
    """The bed's fixture directory (absolute) from the network run's rapid.json."""
    prov = json.load(open(net / "rapid.json"))
    fx = prov.get("ird", {}).get("fixture")
    if not fx:
        raise SystemExit("%s: no ird.fixture in rapid.json" % net)
    p = Path(fx)
    return p if p.is_absolute() else Path("C:/GnssProcessor") / p


def station_entry(fixture, user):
    """The user's fixture RINEX and true position (network_fixture.json of the fixture)."""
    fj = json.load(open(fixture / "network_fixture.json"))
    for s in fj["stations"]:
        if s["name"] == user:
            rnx = sorted((fixture / user).glob(user + "_R_*_MO.rnx"))
            if len(rnx) != 1:
                raise SystemExit("%s: %d RINEX files for %s" % (fixture, len(rnx), user))
            return {"name": user, "rinex_path": rnx[0].as_posix(), "position_ecef": s["position_ecef"]}
    raise SystemExit("%s: station %s not in network_fixture.json" % (fixture, user))


def make_one(tag, variant, user, flip):
    net = net_dir(tag)
    dst = user_dir(tag, variant, user)
    if dst.exists():
        print("exists", dst.name)
        return
    if not (net / "products.txt").exists():
        raise SystemExit("%s: no products.txt" % net)
    cfg = json.loads((net / "arm.json").read_text(encoding="utf-8"))
    fixture = fixture_of(net)
    n = cfg["network"]
    cl = n["closed_loop"]
    hold = bool(n.get("emit_pb_hold", False))
    cl["replay_products_path"] = (net / "products.txt").as_posix()
    cl["consumer_undifferenced"] = False
    cl["ar_mode"] = 1
    cl["ar_wl_only"] = False
    cl["station"] = station_entry(fixture, user)
    cl["pb_hold_presence_flip"] = hold if flip == "auto" else (flip == "true")
    n["trace_consumer_sat"] = True
    cfg["estimation"]["ambiguity_resolution"] = dict(AR, **VARIANT[variant])
    cfg.setdefault("filter", {}).setdefault("process_noise", {})["position_q"] = 0.0
    lg = cfg.setdefault("logging", {})
    lg["enable_ambiguity_resolver"] = True
    lg.setdefault("levels", {})["ambiguity_resolver"] = "debug"
    cfg["processing"]["eigen_threads"] = 1
    dst.mkdir(parents=True)
    (dst / "arm.json").write_text(json.dumps(cfg, indent=2), encoding="utf-8")
    meta = {"net_tag": tag, "net_dir": net.as_posix(), "fixture": fixture.as_posix(), "user": user,
            "variant": variant, "emit_pb_hold": hold, "pb_hold_presence_flip": cl["pb_hold_presence_flip"],
            "ambiguity_resolution": cfg["estimation"]["ambiguity_resolution"]}
    (dst / "irdu_user.json").write_text(json.dumps(meta, indent=1), encoding="utf-8")
    print("made", dst.name)


def launch(rd):
    exe = os.environ["IRDU_USER_EXE"]
    t0 = time.time()
    subprocess.run(["pwsh", "-NoProfile", "-File", str(LAUNCH), "-Exe", exe, "-Config", (rd / "arm.json").as_posix(),
                    "-RunDir", rd.as_posix()], check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    f = rd / "exitcode.txt"
    print("end %s: exit %s, %.0f s" % (rd.name, f.read_text().split()[0] if f.exists() else None, time.time() - t0),
          flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("action", choices=("make", "run", "list"))
    ap.add_argument("tag")
    ap.add_argument("--users", default=",".join(USERS))
    ap.add_argument("--variants", default="obs,fix")
    ap.add_argument("--flip", default="auto", choices=("auto", "true", "false"))
    ap.add_argument("--jobs", type=int, default=4)
    a = ap.parse_args()
    items = [(v, u) for v in a.variants.split(",") for u in a.users.split(",")]
    if a.action == "make":
        for v, u in items:
            make_one(a.tag, v, u, a.flip)
        return 0
    if a.action == "list":
        for v, u in items:
            d = user_dir(a.tag, v, u)
            ec = (d / "exitcode.txt").read_text().split() if (d / "exitcode.txt").exists() else None
            print(d.name, ec)
        return 0
    todo = [user_dir(a.tag, v, u) for v, u in items if not (user_dir(a.tag, v, u) / "exitcode.txt").exists()]
    print("exe", os.environ["IRDU_USER_EXE"], "runs", len(todo), flush=True)
    with ThreadPoolExecutor(a.jobs) as ex:
        list(ex.map(launch, todo))
    return 0


if __name__ == "__main__":
    sys.exit(main())

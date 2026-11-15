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
# User configuration sets (card IRDU section 12.6), one change each, applied to the user's config on top of the recipe;
# a run made with a set has the folder suffix _<set>.
USER_SETS = {
    # A slant ionosphere free at every epoch with no prior: initial sigma 1000 m, random walk 100 m^2/s (55 m per 30 s).
    "fi": {"filter.initial_std.ionosphere": 1000.0, "filter.process_noise.ionosphere_q": 100.0},
    # Card IRDU section 12.8: the undifferenced user (no between-satellite differencing in the filter).
    "ud": {"network.closed_loop.consumer_undifferenced": True},
    # Card IRDU section 12.8: carry the float ambiguity across a declared phase-bias step instead of resetting it.
    "pc": {"network.closed_loop.pb_disc_carry": True},
    # Card IRDU section 12.8's addendum: exclude the satellites the thin bed's stream does not correct.
    "xs": {"processing.excluded_satellites": ["G12", "G20", "G25"]},
    # Card IRDU section 12.10: the consumer's rule for satellites without a stream record (default-off key).
    "du": {"network.closed_loop.drop_unrecorded": True},
    # Card IRDU section 15: the rule extended to the phase biases (default-off key).
    "dp": {"network.closed_loop.drop_unrecorded_phase_bias": True},
    # Card IRDU section 15: the recipe on a filtered observation file (the path is set by make --rinex-dir).
    "fr": {},
}
# Card IRDU section 12.10: runs of another executable than the users' build keep their own folders, suffix _b<tag>
# (environment IRDU_USER_BUILD, read by every grader through user_dir).
BUILD = os.environ.get("IRDU_USER_BUILD", "")


def net_dir(tag):
    return RUNS / ("_rap_" + tag)


def user_dir(tag, variant, user, start_min=0, uset=""):
    """A user run's folder; a late start (card IRDU section 12.4) adds the suffix _s<minutes>, a user configuration
    set (section 12.6) the suffix _<set>."""
    short = tag[5:] if tag.startswith("irdu_") else tag
    late = "_s%d" % start_min if start_min else ""
    us = "_%s" % uset if uset else ""
    bd = "_b%s" % BUILD if BUILD else ""
    return RUNS / ("_rap_irdu_u_%s_%s_%s%s%s%s" % (short, variant, user[:3].lower(), late, us, bd))


def apply_set(cfg, uset):
    """Apply a user configuration set (dotted keys) to a config dict; returns the applied keys."""
    if not uset:
        return {}
    for key, val in USER_SETS[uset].items():
        node = cfg
        parts = key.split(".")
        for p in parts[:-1]:
            node = node.setdefault(p, {})
        node[parts[-1]] = val
    return dict(USER_SETS[uset])


def fixture_of(net):
    """The bed's fixture directory (absolute) from the network run's rapid.json."""
    prov = json.load(open(net / "rapid.json"))
    fx = prov.get("ird", {}).get("fixture")
    if not fx:
        # A bed that keeps the golden's own fixture (card NRF stage N3: the golden sim bed) names none: the fixture
        # is the folder of the network's held-out consumer's RINEX, which holds network_fixture.json.
        cfg = json.loads((net / "arm.json").read_text(encoding="utf-8"))
        rnx = cfg.get("network", {}).get("closed_loop", {}).get("station", {}).get("rinex_path", "")
        p = Path(rnx).parent.parent if rnx else None
        if p is None or not (p / "network_fixture.json").exists():
            raise SystemExit("%s: no ird.fixture in rapid.json and no fixture at the consumer's RINEX" % net)
        return p
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


def make_one(tag, variant, user, flip, start_min=0, uset="", rinex_dir=""):
    net = net_dir(tag)
    dst = user_dir(tag, variant, user, start_min, uset)
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
    if rinex_dir:
        # Card IRDU section 15: the user's own observation file replaced by its filtered copy (same file name).
        cl["station"]["rinex_path"] = (Path(rinex_dir) / Path(cl["station"]["rinex_path"]).name).as_posix()
    cl["pb_hold_presence_flip"] = hold if flip == "auto" else (flip == "true")
    n["trace_consumer_sat"] = True
    cfg["estimation"]["ambiguity_resolution"] = dict(AR, **VARIANT[variant])
    cfg.setdefault("filter", {}).setdefault("process_noise", {})["position_q"] = 0.0
    lg = cfg.setdefault("logging", {})
    lg["enable_ambiguity_resolver"] = True
    lg.setdefault("levels", {})["ambiguity_resolver"] = "debug"
    cfg["processing"]["eigen_threads"] = 1
    if start_min or n.get("start_offset_hours"):
        # A late start (card IRDU section 12.4): the user starts cold this many minutes after the product stream's
        # first epoch; the replay anchors the offset there (ApplicationConsumerReplay), so the network's own offset
        # into its observation files (the golden sim bed's 00:30:15) is not added, and a user without a late start
        # on such a bed starts with the stream.
        n["start_offset_hours"] = start_min / 60.0
    applied = apply_set(cfg, uset)
    dst.mkdir(parents=True)
    (dst / "arm.json").write_text(json.dumps(cfg, indent=2), encoding="utf-8")
    meta = {"net_tag": tag, "net_dir": net.as_posix(), "fixture": fixture.as_posix(), "user": user,
            "variant": variant, "emit_pb_hold": hold, "pb_hold_presence_flip": cl["pb_hold_presence_flip"],
            "start_min": start_min, "user_set": uset, "user_set_keys": applied, "build": BUILD,
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
    ap.add_argument("--start-min", type=int, default=0,
                    help="a late start: the user starts this many minutes after the network (card IRDU 12.4)")
    ap.add_argument("--user-set", default="", choices=[""] + sorted(USER_SETS),
                    help="a user configuration set applied on top of the recipe (card IRDU 12.6)")
    ap.add_argument("--rinex-dir", default="",
                    help="make only: take each user's observation file from this folder (card IRDU 15)")
    a = ap.parse_args()
    items = [(v, u) for v in a.variants.split(",") for u in a.users.split(",")]
    s, us = a.start_min, a.user_set
    if a.action == "make":
        for v, u in items:
            make_one(a.tag, v, u, a.flip, s, us, a.rinex_dir)
        return 0
    if a.action == "list":
        for v, u in items:
            d = user_dir(a.tag, v, u, s, us)
            ec = (d / "exitcode.txt").read_text().split() if (d / "exitcode.txt").exists() else None
            print(d.name, ec)
        return 0
    todo = [user_dir(a.tag, v, u, s, us) for v, u in items
            if not (user_dir(a.tag, v, u, s, us) / "exitcode.txt").exists()]
    print("exe", os.environ["IRDU_USER_EXE"], "runs", len(todo), flush=True)
    with ThreadPoolExecutor(a.jobs) as ex:
        list(ex.map(launch, todo))
    return 0


if __name__ == "__main__":
    sys.exit(main())

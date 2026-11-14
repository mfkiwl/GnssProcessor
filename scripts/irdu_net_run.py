#!/usr/bin/env python3
"""Run card IRDU's network arms (folders _rap_<tag> made by scripts/ird_make_arms.py) a few at a time.

    py -3.14 scripts/irdu_net_run.py <tag> [<tag> ...] [--jobs 2]

The executable is environment IRDU_NET_EXE (a renamed copy of this branch's Release build), launched through
scripts/ev_launch.ps1 (cwd = the run folder, exitcode.txt = exit code and wall seconds).  A folder that already has
an exitcode.txt is skipped.
"""
import argparse
import os
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RUNS = Path(os.environ.get("RAPID_RUNS_ROOT") or "D:/GnssProcessorSupport/runs_nom")


def launch(tag):
    rd = RUNS / ("_rap_" + tag)
    t0 = time.time()
    subprocess.run(["pwsh", "-NoProfile", "-File", str(ROOT / "scripts" / "ev_launch.ps1"), "-Exe",
                    os.environ["IRDU_NET_EXE"], "-Config", (rd / "arm.json").as_posix(), "-RunDir", rd.as_posix()],
                   check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    f = rd / "exitcode.txt"
    print("end %s: %s, %.0f s" % (tag, " ".join(f.read_text().split()) if f.exists() else None, time.time() - t0),
          flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("tags", nargs="+")
    ap.add_argument("--jobs", type=int, default=2)
    a = ap.parse_args()
    todo = [t for t in a.tags if not (RUNS / ("_rap_" + t) / "exitcode.txt").exists()]
    print("exe", os.environ["IRDU_NET_EXE"], "runs", len(todo), flush=True)
    with ThreadPoolExecutor(a.jobs) as ex:
        list(ex.map(launch, todo))
    return 0


if __name__ == "__main__":
    sys.exit(main())

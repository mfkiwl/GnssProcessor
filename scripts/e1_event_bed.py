#!/usr/bin/env python3
"""Card BER, stage E1 (bad-epoch response): an event bed, a simulator fixture with one flagged slip at one receiver.

    py -3.14 scripts/e1_event_bed.py --base runs/simnet60_quiet_col_24h --out D:/GnssProcessorSupport/runs_nom/sime1_a \\
        --station S12000SIM --sat G20 --tow 265230 --l1 288 [--code-m 1.0]

The bed holds the event receiver's directory, copied and edited: its L1C phase of the satellite shifted by --l1 cycles
from the epoch on, the loss-of-lock indicator of that L1C set at the epoch (L2W untouched), optionally a code error of
--code-m metres on C1C and C2W at the epoch only, and one row appended to its truth_slips.csv (flagged 1). Every other
receiver contributes only the truth files the ring fix's audit reads (truth_ambiguities.csv, truth_slips.csv,
truth_windup.csv), so the bed can serve as network.ring_fix.truth_root; their RINEX stays in the base fixture, and an
arm points only the event receiver at the bed.  GENERATED.txt records the command and the edited files' sha256.
"""
import argparse
import csv
import glob
import os
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from nrf_slip_bed import elevation, epoch_tow, fixture_dir, obs_types, sha256, shift_rinex  # noqa: E402

TRUTH = ("truth_ambiguities.csv", "truth_slips.csv", "truth_windup.csv")


def mark_epoch(text, sat, tow, lli_codes, code_codes, code_m):
    """Set the LLI digit of `lli_codes` and add `code_m` to `code_codes` of `sat` at the epoch `tow` only."""
    lines = text.split("\n")
    codes = obs_types(lines, sat[0])
    in_body, now, edits = False, None, 0
    for i, ln in enumerate(lines):
        if not in_body:
            in_body = ln[60:].startswith("END OF HEADER")
            continue
        if ln.startswith(">"):
            now = epoch_tow(ln)
            continue
        if now is None or abs(now - tow) > 1e-6 or not ln.startswith(sat):
            continue
        body = ln[3:].ljust(16 * len(codes))
        for c in lli_codes:
            k = codes.index(c)
            body = body[:16 * k + 14] + "1" + body[16 * k + 15:]
            edits += 1
        for c in (code_codes if code_m else ()):
            k = codes.index(c)
            field = body[16 * k:16 * k + 14]
            if field.strip():
                body = body[:16 * k] + "%14.3f" % (float(field) + code_m) + body[16 * k + 14:]
                edits += 1
        lines[i] = (ln[:3] + body).rstrip()
    return "\n".join(lines), edits


def main():
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("--base", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--station", required=True)
    p.add_argument("--sat", required=True)
    p.add_argument("--tow", type=float, required=True)
    p.add_argument("--l1", type=int, required=True)
    p.add_argument("--code-m", type=float, default=0.0)
    a = p.parse_args()
    base, out = fixture_dir(a.base), fixture_dir(a.out)
    if os.path.exists(out):
        raise SystemExit("%s exists" % out)
    stations = sorted(d for d in os.listdir(base) if os.path.isdir(os.path.join(base, d)) and d.endswith("SIM"))
    os.makedirs(out)
    for d in stations:
        if d == a.station:
            shutil.copytree(os.path.join(base, d), os.path.join(out, d), ignore=shutil.ignore_patterns("logs"))
        else:
            os.makedirs(os.path.join(out, d))
            for f in TRUTH:
                shutil.copy2(os.path.join(base, d, f), os.path.join(out, d, f))
    for f in os.listdir(base):
        if os.path.isfile(os.path.join(base, f)):
            shutil.copy2(os.path.join(base, f), os.path.join(out, f))
    sdir = os.path.join(out, a.station)
    rinex = glob.glob(os.path.join(sdir, "%s_R_*.rnx" % a.station))[0]
    raw = open(rinex, "rb").read().decode("ascii")
    crlf = "\r\n" in raw
    text, n1 = shift_rinex(raw.replace("\r\n", "\n"), a.sat, a.tow, {"L1C": a.l1, "L2W": 0})
    text, n2 = mark_epoch(text, a.sat, a.tow, ["L1C"], ["C1C", "C2W"], a.code_m)
    if n1 == 0 or n2 == 0:
        raise SystemExit("no edit made (phase %d, epoch %d)" % (n1, n2))
    open(rinex, "wb").write((text.replace("\n", "\r\n") if crlf else text).encode("ascii"))
    elev = elevation(sdir, a.sat, a.tow)
    slips = os.path.join(sdir, "truth_slips.csv")
    with open(os.path.join(sdir, "truth_tropo.csv"), newline="") as fh:
        week = next(csv.DictReader(fh))["week"]
    raw_s = open(slips, "rb").read().decode("ascii")
    nl = "\r\n" if "\r\n" in raw_s else "\n"
    source = ",scripted" if raw_s.split(nl)[0].rstrip().endswith(",source") else ""
    if not raw_s.endswith(nl):
        raw_s += nl
    open(slips, "wb").write((raw_s + "%s,%.3f,%s,L1C,%d,1,%.2f%s%s" % (week, a.tow, a.sat, a.l1, elev, source, nl))
                            .encode("ascii"))
    with open(os.path.join(out, "GENERATED.txt"), "w", newline="\n") as fh:
        fh.write("Event bed of card BER (stage E1): %s plus one flagged slip.\n\n" % a.base)
        fh.write("Event: %s %s at TOW %.0f (elevation %.2f deg): L1C %+d cycles from the epoch on, L1C loss of lock set "
                 "at the epoch, L2W untouched, code error %.3f m on C1C and C2W at the epoch only.\n"
                 % (a.station, a.sat, a.tow, elev, a.l1, a.code_m))
        fh.write("Made by: py -3.14 scripts/e1_event_bed.py --base %s --out %s --station %s --sat %s --tow %.0f "
                 "--l1 %d --code-m %.3f\n" % (a.base, a.out, a.station, a.sat, a.tow, a.l1, a.code_m))
        fh.write("Fields edited: %d phase, %d at the epoch.  Other receivers: truth files only (%s).\n"
                 % (n1, n2, ", ".join(TRUTH)))
        fh.write("sha256 %s %s\n" % (sha256(rinex), os.path.basename(rinex)))
    print("bed: %s %s TOW %.0f elev %.2f, %d phase and %d epoch edits; %s" % (a.station, a.sat, a.tow, elev, n1, n2, out))
    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""Card BER, stage E1 (bad-epoch response): an event bed, a simulator fixture with one flagged slip at one receiver,
or one return after a tracking gap (order 1).

    py -3.14 scripts/e1_event_bed.py --base runs/simnet60_quiet_col_24h --out D:/GnssProcessorSupport/runs_nom/sime1_a \\
        --station S12000SIM --sat G20 --tow 265230 --l1 288 [--code-m 1.0]
    py -3.14 scripts/e1_event_bed.py ... --sat G04 --tow 265230 --l1 63 --gap 4 --gap-band L1 --no-lli
    py -3.14 scripts/e1_event_bed.py ... --sat G19 --tow 265230 --l1 63 --l2 49 --l5 47 --gap 4 --gap-band all --no-lli

With --gap N the band (--gap-band L1: every L1 observation of the satellite; all: every observation, a whole-arc
gap) is blanked for the N epochs before --tow and returns at --tow with its phases shifted; the other bands track
through.  --no-lli leaves the loss-of-lock indicator unset at the return, so only the gap instrument sees it.

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


def blank_epochs(text, sat, tows, band):
    """Blank `sat`'s fields of `band` ("L1": the codes whose band digit is 1; "all": every code) at the epochs `tows`."""
    lines = text.split("\n")
    codes = obs_types(lines, sat[0])
    cols = [k for k, c in enumerate(codes) if band == "all" or c[1] == "1"]
    in_body, now, edits = False, None, 0
    for i, ln in enumerate(lines):
        if not in_body:
            in_body = ln[60:].startswith("END OF HEADER")
            continue
        if ln.startswith(">"):
            now = epoch_tow(ln)
            continue
        if now is None or not any(abs(now - t) < 1e-6 for t in tows) or not ln.startswith(sat):
            continue
        body = ln[3:].ljust(16 * len(codes))
        for k in cols:
            if body[16 * k:16 * k + 16].strip():
                body = body[:16 * k] + " " * 16 + body[16 * k + 16:]
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
    p.add_argument("--l2", type=int, default=0)
    p.add_argument("--l5", type=int, default=0)
    p.add_argument("--gap", type=int, default=0, help="epochs blanked before --tow (0: a slip, no gap)")
    p.add_argument("--gap-band", choices=("L1", "all"), default="L1")
    p.add_argument("--no-lli", action="store_true")
    p.add_argument("--interval", type=float, default=30.0)
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
    text, n1 = shift_rinex(raw.replace("\r\n", "\n"), a.sat, a.tow, {"L1C": a.l1, "L2W": a.l2, "L5Q": a.l5})
    n_gap = 0
    if a.gap > 0:
        text, n_gap = blank_epochs(text, a.sat, [a.tow - a.interval * k for k in range(1, a.gap + 1)], a.gap_band)
        if n_gap == 0:
            raise SystemExit("no gap made")
    text, n2 = mark_epoch(text, a.sat, a.tow, [] if a.no_lli else ["L1C"], ["C1C", "C2W"], a.code_m)
    # A flag with no slip (every shift 0, loss of lock set) edits only the epoch's LLI digit; a gap with no shift only blanks.
    shifted = bool(a.l1 or a.l2 or a.l5)
    if (shifted and n1 == 0) or (not a.no_lli and n2 == 0) or not (shifted or not a.no_lli or a.gap > 0):
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
    flagged = 0 if a.no_lli else 1
    rows = "".join("%s,%.3f,%s,%s,%d,%d,%.2f%s%s" % (week, a.tow, a.sat, sig, n, flagged, elev, source, nl)
                   for sig, n in (("L1C", a.l1), ("L2W", a.l2), ("L5Q", a.l5)) if n)
    open(slips, "wb").write((raw_s + rows).encode("ascii"))
    with open(os.path.join(out, "GENERATED.txt"), "w", newline="\n") as fh:
        fh.write("Event bed of card BER (stage E1): %s plus one flagged slip.\n\n" % a.base)
        gap_txt = ("the %s observations blanked for the %d epochs before" % (
            "L1" if a.gap_band == "L1" else "satellite's", a.gap)) if a.gap else "no gap"
        fh.write("Event: %s %s at TOW %.0f (elevation %.2f deg): L1C %+d, L2W %+d, L5Q %+d cycles from the epoch on, "
                 "L1C loss of lock %s at the epoch, code error %.3f m on C1C and C2W at the epoch only; %s.\n"
                 % (a.station, a.sat, a.tow, elev, a.l1, a.l2, a.l5, "not set" if a.no_lli else "set", a.code_m, gap_txt))
        fh.write("Made by: py -3.14 scripts/e1_event_bed.py %s\n" % " ".join(sys.argv[1:]))
        fh.write("Fields edited: %d phase, %d at the epoch, %d blanked.  Other receivers: truth files only (%s).\n"
                 % (n1, n2, n_gap, ", ".join(TRUTH)))
        fh.write("sha256 %s %s\n" % (sha256(rinex), os.path.basename(rinex)))
    print("bed: %s %s TOW %.0f elev %.2f, %d phase, %d epoch and %d blanked edits; %s"
          % (a.station, a.sat, a.tow, elev, n1, n2, n_gap, out))
    return 0


if __name__ == "__main__":
    sys.exit(main())

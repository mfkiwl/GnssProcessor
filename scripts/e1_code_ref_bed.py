#!/usr/bin/env python3
"""Card NRF, the code-reference move: a simulator bed in which one Galileo satellite's code reference moves for an hour.

    py -3.14 scripts/e1_code_ref_bed.py --base C:/GnssProcessor/runs/simnet60_quiet_col_24h \\
        --out D:/GnssProcessorSupport/runs_nom/sime1_cra --sat E02 --tow 264630 --seconds 3600
    py -3.14 scripts/e1_code_ref_bed.py ... --out .../sime1_crb --thin --keep-x 1 --born-x 2 --fault-m 0.4

Every receiver of the fixture is copied.  The receivers with an odd number (S01000SIM, S03000SIM, ...) report Galileo
on the X signals (the header's C1C/L1C, C5Q/L5Q, C7Q/L7Q relabelled C1X/L1X, C5X/L5X, C7X/L7X, and the signal names of
their truth_ambiguities.csv and truth_slips.csv with them; the values unchanged), the others on C/Q, so the network
carries both Galileo families as observed data does.  A satellite's code-bias column is shared only from two receivers,
and its ionosphere-free code pin takes the bias product's reference pair (C1C+C5Q) when both are shared.  For --seconds
from --tow the satellite is blanked at every C/Q receiver, so C1C/C5Q fall below two receivers, the pin moves to
C1X+C5X at the window's start and back at its end.

--thin also thins the X family as on DOY 145 (TOW 94830, E18): --keep-x receivers keep the satellite through the window
(those tracking it longest in the window), --born-x more acquire it --born-delay s after the window opens (arcs born
inside the window, whose wide-lane decisions rest on the satellite's X level), and every other X receiver loses it for
the window.  --fault-m adds a constant offset (m) to the C5X code of the --keep-x receivers for the satellite from
--fault-lead s before the window to its end (a receiver-by-satellite code error on the arcs that hold the level).
GENERATED.txt records the command, the receivers of each role and the files' sha256.
"""
import argparse
import os
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from nrf_slip_bed import epoch_tow, fixture_dir, obs_types, sha256  # noqa: E402

RELABEL = {"C1C": "C1X", "L1C": "L1X", "C5Q": "C5X", "L5Q": "L5X", "C7Q": "C7X", "L7Q": "L7X",
           "S1C": "S1X", "S5Q": "S5X", "S7Q": "S7X", "D1C": "D1X", "D5Q": "D5X", "D7Q": "D7X"}
SIGNAL_COLUMN = {"truth_ambiguities.csv": (0, 1), "truth_slips.csv": (2, 3)}   # (satellite, signal) columns
TRUTH = ("truth_ambiguities.csv", "truth_slips.csv", "truth_windup.csv")


def is_x(station):
    """Odd-numbered fixture receivers report Galileo on X; the held-out consumer (SZZ000SIM) stays on C/Q."""
    return station[1:3].isdigit() and int(station[1:3]) % 2 == 1


def header_end(lines):
    for k, ln in enumerate(lines):
        if ln[60:].startswith("END OF HEADER"):
            return k + 1
    raise SystemExit("no END OF HEADER")


def relabel_header(lines):
    """Relabel the Galileo observation types of a RINEX 3 header in place (the E line and its continuations)."""
    in_e = False
    for k in range(header_end(lines)):
        ln = lines[k]
        if ln[60:].startswith("SYS / # / OBS TYPES"):
            in_e = ln[0] == "E" or (ln[0] == " " and in_e)
            if in_e:
                body = ln[:60]
                for old, new in RELABEL.items():
                    body = body.replace(" " + old, " " + new)
                lines[k] = body + ln[60:]
        else:
            in_e = False


def window_epochs(lines, sat, t0, t1):
    n, now = 0, None
    for ln in lines[header_end(lines):]:
        if ln.startswith(">"):
            now = epoch_tow(ln)
        elif now is not None and t0 <= now < t1 and ln.startswith(sat):
            n += 1
    return n


def edit_body(lines, sat, blank, offset):
    """Drop `sat`'s lines inside any [a, b) of `blank` (fixing each epoch line's satellite count) and add offset[2]
    metres to the code column offset[3] inside [offset[0], offset[1]).  Returns (lines, epochs blanked, values offset)."""
    out = lines[:header_end(lines)]
    k, n_blank, n_off = len(out), 0, 0
    while k < len(lines):
        ln = lines[k]
        if not ln.startswith(">"):
            out.append(ln)
            k += 1
            continue
        now = epoch_tow(ln)
        n = int(ln[32:35])
        block = lines[k + 1:k + 1 + n]
        if any(a <= now < b for a, b in blank):
            kept = [b_ for b_ in block if not b_.startswith(sat)]
            if len(kept) != len(block):
                n_blank += 1
                ln = ln[:32] + "%3d" % len(kept) + ln[35:]
                block = kept
        if offset and offset[0] <= now < offset[1]:
            col = offset[3]
            for j, b_ in enumerate(block):
                if not b_.startswith(sat):
                    continue
                field = b_[3 + 16 * col:3 + 16 * col + 16]
                if len(field) >= 14 and field[:14].strip():
                    new = "%14.3f" % (float(field[:14]) + offset[2])
                    block[j] = b_[:3 + 16 * col] + new + b_[3 + 16 * col + 14:]
                    n_off += 1
        out.append(ln)
        out.extend(block)
        k += 1 + n
    return out, n_blank, n_off


def relabel_truth(text, name):
    if name not in SIGNAL_COLUMN:
        return text
    ks, kg = SIGNAL_COLUMN[name]
    rows = text.split("\n")
    for i in range(1, len(rows)):
        f = rows[i].split(",")
        if len(f) > max(ks, kg) and f[ks].startswith("E"):
            f[kg] = RELABEL.get(f[kg], f[kg])
            rows[i] = ",".join(f)
    return "\n".join(rows)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--base", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--sat", required=True)
    ap.add_argument("--tow", type=float, required=True)
    ap.add_argument("--seconds", type=float, default=3600.0)
    ap.add_argument("--thin", action="store_true")
    ap.add_argument("--keep-x", type=int, default=1)
    ap.add_argument("--born-x", type=int, default=2)
    ap.add_argument("--born-delay", type=float, default=300.0)
    ap.add_argument("--fault-m", type=float, default=0.0)
    ap.add_argument("--fault-lead", type=float, default=1800.0)
    a = ap.parse_args()
    base, out = fixture_dir(a.base), fixture_dir(a.out)
    if os.path.exists(out):
        raise SystemExit("%s exists" % out)
    t0, t1 = a.tow, a.tow + a.seconds
    stations = sorted(d for d in os.listdir(base) if os.path.isdir(os.path.join(base, d)) and d.endswith("SIM"))
    texts, counts = {}, {}
    for d in stations:
        rin = [f for f in os.listdir(os.path.join(base, d)) if f.startswith(d + "_R_") and f.endswith(".rnx")]
        if not rin:
            continue
        raw = open(os.path.join(base, d, rin[0]), "rb").read().decode("ascii")
        texts[d] = (rin[0], "\r\n" in raw, raw.replace("\r\n", "\n").split("\n"))
        counts[d] = window_epochs(texts[d][2], a.sat, t0, t1)
    full = int(a.seconds / 30.0)
    xs = sorted((d for d in texts if is_x(d) and counts[d] >= full - 2), key=lambda d: (-counts[d], d))
    keep = set(xs[:a.keep_x]) if a.thin else set()
    born = set(xs[a.keep_x:a.keep_x + a.born_x]) if a.thin else set()
    if a.thin and (len(keep) < a.keep_x or len(born) < a.born_x):
        raise SystemExit("only %d X receivers track %s through the window" % (len(xs), a.sat))
    os.makedirs(out)
    for f in os.listdir(base):
        if os.path.isfile(os.path.join(base, f)):
            shutil.copy2(os.path.join(base, f), os.path.join(out, f))
    report = []
    for d in stations:
        os.makedirs(os.path.join(out, d))
        for f in os.listdir(os.path.join(base, d)):
            src = os.path.join(base, d, f)
            if os.path.isfile(src) and f not in TRUTH and not f.endswith(".rnx"):
                shutil.copy2(src, os.path.join(out, d, f))
        if d not in texts:
            continue
        name, crlf, lines = texts[d]
        lines = list(lines)
        role = "C/Q"
        blank, offset = [], None
        if is_x(d):
            relabel_header(lines)
            role = "X"
            if a.thin:
                if d in keep:
                    role = "X kept"
                    if a.fault_m:
                        col = obs_types(lines, "E").index("C5X")
                        offset = (t0 - a.fault_lead, t1, a.fault_m, col)
                elif d in born:
                    role = "X born"
                    blank = [(t0, t0 + a.born_delay)]
                else:
                    role = "X blanked"
                    blank = [(t0, t1)]
        else:
            blank = [(t0, t1)]
        lines, n_blank, n_off = edit_body(lines, a.sat, blank, offset)
        text = "\n".join(lines)
        open(os.path.join(out, d, name), "wb").write((text.replace("\n", "\r\n") if crlf else text).encode("ascii"))
        for f in TRUTH:
            src = os.path.join(base, d, f)
            if os.path.exists(src):
                s = open(src, "rb").read().decode("ascii")
                open(os.path.join(out, d, f), "wb").write((relabel_truth(s, f) if is_x(d) else s).encode("ascii"))
        report.append((d, role, counts[d], n_blank, n_off, sha256(os.path.join(out, d, name))))
    with open(os.path.join(out, "GENERATED.txt"), "w", newline="\n") as fh:
        fh.write("Code-reference bed (card NRF): %s with the odd-numbered receivers on Galileo X; %s blanked from TOW %.0f "
                 "for %.0f s at every C/Q receiver.\n" % (a.base, a.sat, t0, a.seconds))
        if a.thin:
            fh.write("Thin X family: kept %s; born %.0f s into the window %s; every other X receiver blanked for the "
                     "window.  C5X offset %.3f m at the kept receivers from TOW %.0f to %.0f.\n"
                     % (", ".join(sorted(keep)), a.born_delay, ", ".join(sorted(born)), a.fault_m, t0 - a.fault_lead, t1))
        fh.write("\nMade by: py -3.14 scripts/e1_code_ref_bed.py %s\n\n" % " ".join(sys.argv[1:]))
        for d, role, n, nb, no, h in report:
            fh.write("%s %-9s: %3d epochs of %s in the window, %3d blanked, %3d code values offset; sha256 %s\n"
                     % (d, role, n, a.sat, nb, no, h))
    print("bed %s: kept %s, born %s; %d receivers written"
          % (out, ", ".join(sorted(keep)) or "-", ", ".join(sorted(born)) or "-", len(report)))
    return 0


if __name__ == "__main__":
    sys.exit(main())

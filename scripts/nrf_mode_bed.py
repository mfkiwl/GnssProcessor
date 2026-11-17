#!/usr/bin/env python3
"""Card NRF section 99, the simulator step: a simulator fixture in which half the receivers track Galileo in the
combined mode (C1X/L1X, C5X/L5X) and the other half in the pilot mode (C1C/L1C, C5Q/L5Q), as observed receivers do.

    py -3.14 scripts/nrf_mode_bed.py make --base C:/GnssProcessor/runs/simnet60_quiet_col_24h \\
        --out D:/GnssProcessorSupport/runs_nom/simb_mode1 --label mode1
    py -3.14 scripts/nrf_mode_bed.py verify --base C:/GnssProcessor/runs/simnet60_quiet_col_24h \\
        --out D:/GnssProcessorSupport/runs_nom/simb_mode1
    py -3.14 scripts/nrf_mode_bed.py --selftest

The model is the fixture's own bias product (scenario_summary.json, signal_bias.file; CODE's OSB carries both modes
for every Galileo satellite): the simulator adds a satellite's OSB to its code (`code = P + ... + bias_code + ...`,
src/sim/main.cpp) and folds the phase OSB into the phase, so a receiver that tracks the combined mode sees each E1
and E5a code moved by OSB(C1X) - OSB(C1C) and OSB(C5X) - OSB(C5Q) of its satellite, and each phase by
(OSB(L1X) - OSB(L1C)) / lambda1 and (OSB(L5X) - OSB(L5Q)) / lambda5 (zero in CODE's product, whose phase OSBs are
equal between the modes).  A receiver's own tracking also differs between the modes: each converted receiver gets a
code offset per band drawn from N(0, --rx-code-sigma-m) and a phase offset per band drawn uniformly in
[-0.5, 0.5) cycle, seeded by (--seed, receiver, band), so a draw does not depend on which others exist.

`make` copies the base fixture and converts every --every-th network receiver in sorted order, starting with the
--first (the held-out receivers named by --keep stay in the pilot mode): in its RINEX the Galileo observation types
C1C L1C D1C S1C C5Q L5Q D5Q S5Q become C1X L1X D1X S1X C5X L5X D5X S5X (the header only; columns keep their places),
each E1 and E5a code moves by its satellite's code offset plus the receiver's, each phase by the satellite's phase
offset plus the receiver's; E5b and GPS are untouched.  Truth: the converted receiver's truth_mode.csv lists every
offset; its truth_ambiguities.csv and truth_slips.csv carry the renamed phase signals with the same integers and
slips; its truth_rx_bias.csv gains the combined mode's receiver biases; every receiver's truth_bias.csv gains the
combined mode's satellite biases (C1X and C5X with the synthetic part of C1C and C5Q, L1X and L5X likewise).
GENERATED.txt records the command, the converted receivers and the edited files' sha256.  `verify` reads each
RINEX field by field against the base and proves that only the converted receivers' Galileo E1 and E5a fields
moved, each by its table entry, that the headers were renamed and nothing else, and that every other file is the
base's (the truth files as described).
"""
import argparse
import glob
import hashlib
import json
import math
import os
import random
import re
import shutil
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))).replace(os.sep, "/")
DATA = next((p for p in (ROOT + "/data", "C:/GnssProcessor/data") if os.path.isdir(p)), ROOT + "/data")
C_LIGHT = 299792458.0
F = {"1": 1575.42e6, "5": 1176.45e6}
LAM = {b: C_LIGHT / f for b, f in F.items()}
# pilot -> combined, per band, for the four observation kinds
RENAME = {k + b + p: k + b + "X" for b, p in (("1", "C"), ("5", "Q")) for k in "CLDS"}
OSB_PAIRS = {"C1X": "C1C", "C5X": "C5Q", "L1X": "L1C", "L5X": "L5Q"}


def fixture_dir(path):
    return path.replace("\\", "/") if os.path.isabs(path) else ROOT + "/" + path


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def obs_types(lines, system):
    """The observation codes of one system from a RINEX 3 header."""
    codes, want = [], 0
    for ln in lines:
        if ln[60:].startswith("END OF HEADER"):
            break
        if ln[60:].startswith("SYS / # / OBS TYPES"):
            if ln[0] == system:
                want = int(ln[3:6])
                codes += ln[7:58].split()
            elif ln[0] == " " and want and len(codes) < want:
                codes += ln[7:58].split()
    return codes


def read_osb(path):
    """Galileo OSB values (ns) of the satellite records of a SINEX BIAS file: {(sat, signal): ns}."""
    pat = re.compile(r"^ OSB\s+\S+\s+(E\d\d)\s+([CL][15][CQX])\s+\S+\s+\S+\s+ns\s+(-?[\d.]+)")
    out = {}
    for ln in open(path, encoding="utf-8", errors="replace"):
        m = pat.match(ln)
        if m:
            out[(m.group(1), m.group(2))] = float(m.group(3))
    return out


def sat_offsets(osb, sats):
    """Per satellite the combined mode's offset from the pilot mode: {sat: {"C1X": m, "C5X": m, "L1X": cyc, "L5X": cyc}}.
    A satellite without both modes in the product gets no entry (its observations are left as they are)."""
    out = {}
    for s in sats:
        try:
            out[s] = {
                "C1X": round((osb[(s, "C1X")] - osb[(s, "C1C")]) * C_LIGHT * 1e-9, 3),
                "C5X": round((osb[(s, "C5X")] - osb[(s, "C5Q")]) * C_LIGHT * 1e-9, 3),
                "L1X": round((osb[(s, "L1X")] - osb[(s, "L1C")]) * C_LIGHT * 1e-9 / LAM["1"], 3),
                "L5X": round((osb[(s, "L5X")] - osb[(s, "L5Q")]) * C_LIGHT * 1e-9 / LAM["5"], 3),
            }
        except KeyError:
            continue
    return out


def rx_offsets(seed, station, code_sigma):
    """The receiver's own offsets of the combined mode: code (m) and phase (cycles) per band."""
    out = {}
    for b in "15":
        out["C%sX" % b] = round(random.Random("%d|%s|code|%s" % (seed, station, b)).gauss(0.0, code_sigma), 3)
        out["L%sX" % b] = round(random.Random("%d|%s|phase|%s" % (seed, station, b)).uniform(-0.5, 0.5), 3)
    return out


def convert_rinex(text, sat_off, rx_off):
    """The RINEX text (LF line ends) with Galileo E1 and E5a in the combined mode; the count of edited fields."""
    lines = text.split("\n")
    codes = obs_types(lines, "E")
    edit_cols = {k: RENAME[c] for k, c in enumerate(codes) if c in RENAME and c[0] in "CL"}
    in_body, in_e, edits = False, False, 0
    for i, ln in enumerate(lines):
        if not in_body:
            if ln[60:].startswith("SYS / # / OBS TYPES"):
                in_e = ln[0] == "E" or (ln[0] == " " and in_e)
                if in_e:
                    slots = [ln[7 + 4 * j:11 + 4 * j] for j in range(13)]
                    slots = [RENAME.get(s[:3], s[:3]) + s[3:] if s.strip() else s for s in slots]
                    lines[i] = ln[:7] + "".join(slots) + ln[59:]
            else:
                in_e = False
            in_body = ln[60:].startswith("END OF HEADER")
            continue
        if not ln.startswith("E") or ln[:3] not in sat_off:
            continue
        sat, body = ln[:3], ln[3:]
        for k, newcode in edit_cols.items():
            field = body[16 * k:16 * k + 16]
            if len(field) < 14 or not field[:14].strip():
                continue
            new = "%14.3f" % (float(field[:14]) + sat_off[sat][newcode] + rx_off[newcode])
            if len(new) != 14:
                raise SystemExit("field out of the F14.3 range after the offset: %s" % new)
            body = body[:16 * k] + new + body[16 * k + 14:]
            edits += 1
        lines[i] = sat + body
    return "\n".join(lines), edits


def rename_rows(text, col_sig, sats_prefix="E"):
    """A truth CSV with the pilot phase signals of Galileo renamed to the combined mode (the signal column col_sig)."""
    rows = text.split("\n")
    hdr = rows[0].split(",")
    j = hdr.index(col_sig)
    isat = hdr.index("satellite")
    out = [rows[0]]
    for r in rows[1:]:
        f = r.split(",")
        if len(f) > j and f[isat].startswith(sats_prefix) and f[j] in RENAME:
            f[j] = RENAME[f[j]]
        out.append(",".join(f))
    return "\n".join(out)


def bias_rows(text, sat_off):
    """truth_bias.csv with the combined mode's satellite rows appended after the base's."""
    rows = [r for r in text.split("\n") if r]
    hdr = rows[0].split(",")
    by = {}
    for r in rows[1:]:
        f = r.split(",")
        by[(f[0], f[1])] = f
    extra = []
    for s in sorted(sat_off):
        for xsig, psig in sorted(OSB_PAIRS.items()):
            base = by.get((s, psig))
            if base is None:
                continue
            osb_m, prod_m, synth_m = float(base[3]), float(base[4]), float(base[5])
            band = xsig[1]
            d_m = sat_off[s][xsig] if xsig[0] == "C" else sat_off[s][xsig] * LAM[band]
            prod_x, osb_x = prod_m + d_m, osb_m + d_m
            src = "product+synth" if synth_m != 0.0 else "product"
            extra.append("%s,%s,%.6f,%.6f,%.6f,%.6f,%s" % (s, xsig, osb_x / (C_LIGHT * 1e-9), osb_x, prod_x, synth_m, src))
    return "\n".join(rows + extra) + "\n"


def rx_bias_rows(text, station, rx_off):
    rows = [r for r in text.split("\n") if r]
    have = {}
    for r in rows[1:]:
        f = r.split(",")
        have[(f[1], f[2])] = float(f[3])
    extra = []
    for xsig, psig in sorted(OSB_PAIRS.items()):
        kind = "code" if xsig[0] == "C" else "phase"
        base = have.get((kind, psig), 0.0)
        d_m = rx_off[xsig] if kind == "code" else rx_off[xsig] * LAM[xsig[1]]
        extra.append("%s,%s,%s,%.6f" % (station, kind, xsig, base + d_m))
    return "\n".join(rows + extra) + "\n"


def stations(base):
    out = {}
    for d in sorted(os.listdir(base)):
        if os.path.isdir(os.path.join(base, d)):
            r = glob.glob(os.path.join(base, d, "%s_R_*.rnx" % d))
            if len(r) == 1:
                out[d] = r[0]
    return out


def bia_path(base):
    summ = json.load(open(os.path.join(base, "S01000SIM", "scenario_summary.json")))
    name = summ["signal_bias"]["file"]
    date = summ["date"].split()[0]          # "2024-129"
    tried = [os.path.join(d, date, "products", name) for d in (ROOT + "/data", "C:/GnssProcessor/data")]
    for p in tried:
        if os.path.exists(p):
            return p
    raise SystemExit("the fixture's bias product %s is not at %s" % (name, " or ".join(tried)))


def plan(base, a):
    st = stations(base)
    keep = set(a.keep.split(",")) if a.keep else set()
    net = [s for s in st if s not in keep]
    conv = net[a.first::a.every]
    return st, conv


def read_text(path):
    raw = open(path, "rb").read().decode("ascii")
    return raw.replace("\r\n", "\n"), "\r\n" in raw


def write_text(path, text, crlf):
    open(path, "wb").write((text.replace("\n", "\r\n") if crlf else text).encode("ascii"))


def galileo_sats(text):
    return sorted({ln[:3] for ln in text.split("END OF HEADER", 1)[1].split("\n") if ln[:1] == "E"})


def make(a):
    base, out = fixture_dir(a.base), fixture_dir(a.out)
    if os.path.exists(out):
        raise SystemExit("%s exists: a bed is made once (remove it first to remake it)" % out)
    st, conv = plan(base, a)
    osb = read_osb(bia_path(base))
    os.makedirs(out)
    for d in sorted(os.listdir(base)):
        src = os.path.join(base, d)
        if os.path.isdir(src):
            if d == "logs":
                continue
            shutil.copytree(src, os.path.join(out, d))
        else:
            shutil.copy2(src, os.path.join(out, d))
    all_sats, lines, total = set(), [], 0
    for s, rinex in st.items():
        text, _ = read_text(rinex)
        all_sats |= set(galileo_sats(text))
    sat_off = sat_offsets(osb, sorted(all_sats))
    for s, rinex in st.items():
        d = os.path.join(out, s)
        tb, crlf_b = read_text(os.path.join(base, s, "truth_bias.csv"))
        write_text(os.path.join(d, "truth_bias.csv"), bias_rows(tb, sat_off), crlf_b)
        lines.append("sha256 %s %s/truth_bias.csv" % (sha256(os.path.join(d, "truth_bias.csv")), s))
        if s not in conv:
            continue
        rx = rx_offsets(a.seed, s, a.rx_code_sigma_m)
        text, crlf = read_text(rinex)
        new, edits = convert_rinex(text, sat_off, rx)
        total += edits
        dst = os.path.join(d, os.path.basename(rinex))
        write_text(dst, new, crlf)
        for name, col in (("truth_ambiguities.csv", "signal"), ("truth_slips.csv", "signal")):
            t, c = read_text(os.path.join(base, s, name))
            write_text(os.path.join(d, name), rename_rows(t, col), c)
        t, c = read_text(os.path.join(base, s, "truth_rx_bias.csv"))
        write_text(os.path.join(d, "truth_rx_bias.csv"), rx_bias_rows(t, s, rx), c)
        with open(os.path.join(d, "truth_mode.csv"), "w", newline="\n") as fh:
            fh.write("kind,satellite,signal,value,unit\n")
            for sat in sorted(sat_off):
                for sig in ("C1X", "C5X", "L1X", "L5X"):
                    fh.write("sat,%s,%s,%.3f,%s\n" % (sat, sig, sat_off[sat][sig], "m" if sig[0] == "C" else "cycle"))
            for sig in ("C1X", "C5X", "L1X", "L5X"):
                fh.write("rx,*,%s,%.3f,%s\n" % (sig, rx[sig], "m" if sig[0] == "C" else "cycle"))
        for name in (os.path.basename(rinex), "truth_ambiguities.csv", "truth_slips.csv", "truth_rx_bias.csv",
                     "truth_mode.csv"):
            lines.append("sha256 %s %s/%s" % (sha256(os.path.join(d, name)), s, name))
    cmd = ("py -3.14 scripts/nrf_mode_bed.py make --base %s --out %s --every %d --first %d --keep %s --seed %d "
           "--rx-code-sigma-m %g --label %s" % (a.base, a.out, a.every, a.first, a.keep, a.seed, a.rx_code_sigma_m,
                                                 a.label))
    with open(os.path.join(out, "GENERATED.txt"), "w", newline="\n") as fh:
        keep = set(a.keep.split(",")) if a.keep else set()
        n_net = len([s for s in st if s not in keep])
        fh.write("Two-mode bed %s of card NRF (section 99, the simulator step): %s with %d of its %d network receivers "
                 "tracking Galileo E1 and E5a in the combined mode (C1X/L1X, C5X/L5X).\n\n"
                 % (a.label, a.base, len(conv), n_net))
        fh.write("Satellite offsets: the fixture's bias product %s (OSB of the combined mode less the pilot's).\n"
                 % os.path.basename(bia_path(base)))
        fh.write("Receiver offsets: code N(0, %g m) and phase U[-0.5, 0.5) cycle per (receiver, band), seed %d.\n"
                 % (a.rx_code_sigma_m, a.seed))
        fh.write("Converted: %s\n" % ",".join(conv))
        fh.write("Made by: %s\n" % cmd)
        fh.write("Galileo fields edited: %d (scripts/nrf_mode_bed.py verify).\n" % total)
        fh.write("\n".join(lines) + "\n")
    print("bed %s: %d receivers converted, %d Galileo E1/E5a fields edited, %d satellites with offsets; %s"
          % (a.label, len(conv), total, len(sat_off), out))


def fields(text):
    """{(epoch line index, sat): line} of the body, the header lines, and the Galileo codes."""
    lines = text.split("\n")
    end = next(i for i, ln in enumerate(lines) if ln[60:].startswith("END OF HEADER"))
    return lines[:end + 1], lines[end + 1:], obs_types(lines, "E")


def verify(a):
    base, out = fixture_dir(a.base), fixture_dir(a.out)
    gen = open(os.path.join(out, "GENERATED.txt")).read()
    conv = set(re.search(r"^Converted: (.*)$", gen, re.M).group(1).split(","))
    st = stations(base)
    bad, n_moved, n_same = [], 0, 0
    # 1. every file outside the edited set is the base's
    edited = {"truth_bias.csv"}
    edited_conv = {"truth_ambiguities.csv", "truth_slips.csv", "truth_rx_bias.csv", "truth_mode.csv"}
    for d in sorted(os.listdir(base)):
        p = os.path.join(base, d)
        if d == "logs":
            continue
        rels = [os.path.join(d, f) for f in os.listdir(p)] if os.path.isdir(p) else [d]
        for rel in rels:
            if os.path.isdir(os.path.join(base, rel)):
                continue
            name = os.path.basename(rel)
            o = os.path.join(out, rel)
            if not os.path.exists(o):
                bad.append("missing " + rel)
                continue
            if name in edited or rel.endswith(".rnx") or (d in conv and name in edited_conv):
                continue
            if open(os.path.join(base, rel), "rb").read() != open(o, "rb").read():
                bad.append("differs " + rel)
    # 2. the RINEX field by field
    for s, rinex in st.items():
        bt, _ = read_text(rinex)
        ot, _ = read_text(os.path.join(out, s, os.path.basename(rinex)))
        if s not in conv:
            if bt != ot:
                bad.append("%s: not converted but its RINEX differs" % s)
            continue
        tab = {}
        for r in open(os.path.join(out, s, "truth_mode.csv")).read().splitlines()[1:]:
            kind, sat, sig, val, _ = r.split(",")
            tab[(kind, sat, sig)] = float(val)
        bh, bb, bcodes = fields(bt)
        oh, ob, ocodes = fields(ot)
        if [RENAME.get(c, c) for c in bcodes] != ocodes:
            bad.append("%s: Galileo codes %s, expected %s" % (s, ocodes, [RENAME.get(c, c) for c in bcodes]))
        hdiff = [(x, y) for x, y in zip(bh, oh) if x != y]
        if len(bh) != len(oh) or any(not x[60:].startswith("SYS / # / OBS TYPES") or x[0] not in "E " for x, _ in hdiff):
            bad.append("%s: a header line other than the Galileo types differs" % s)
        if len(bb) != len(ob):
            bad.append("%s: body length differs" % s)
            continue
        for x, y in zip(bb, ob):
            if x == y:
                if x.startswith("E") and ("sat", x[:3], "C1X") in tab:
                    n_same += 1
                continue
            if not x.startswith("E") or x[:3] != y[:3] or len(x) != len(y):
                bad.append("%s: a line other than a Galileo record differs: %r" % (s, x[:20]))
                break
            sat = x[:3]
            for k, code in enumerate(bcodes):
                fx, fy = x[3 + 16 * k:3 + 16 * k + 16], y[3 + 16 * k:3 + 16 * k + 16]
                if fx == fy:
                    continue
                xc = RENAME.get(code)
                if xc is None or xc[0] not in "CL" or fx[14:] != fy[14:]:
                    bad.append("%s %s: field %s moved" % (s, sat, code))
                    break
                want = tab[("sat", sat, xc)] + tab[("rx", "*", xc)]
                if abs(float(fy[:14]) - float(fx[:14]) - want) > 0.0015:
                    bad.append("%s %s %s: moved by %.3f, table %.3f" % (s, sat, xc, float(fy[:14]) - float(fx[:14]), want))
                    break
                n_moved += 1
    # 3. the truth files: renamed signals and the receivers' biases at the converted receivers, the satellites'
    #    combined-mode rows at every receiver
    sat_off = {}
    for s in sorted(conv):
        for r in open(os.path.join(out, s, "truth_mode.csv")).read().splitlines()[1:]:
            kind, sat, sig, val, _ = r.split(",")
            if kind == "sat":
                sat_off.setdefault(sat, {})[sig] = float(val)
        break
    for s in st:
        bt, _ = read_text(os.path.join(base, s, "truth_bias.csv"))
        ot, _ = read_text(os.path.join(out, s, "truth_bias.csv"))
        if bias_rows(bt, sat_off) != ot:
            bad.append("%s/truth_bias.csv: not the base with the combined mode's satellite rows" % s)
        if s not in conv:
            for name in ("truth_ambiguities.csv", "truth_slips.csv", "truth_rx_bias.csv"):
                if open(os.path.join(base, s, name), "rb").read() != open(os.path.join(out, s, name), "rb").read():
                    bad.append("%s/%s differs at a receiver not converted" % (s, name))
            continue
        for name in ("truth_ambiguities.csv", "truth_slips.csv"):
            b, _ = read_text(os.path.join(base, s, name))
            o, _ = read_text(os.path.join(out, s, name))
            if rename_rows(b, "signal") != o:
                bad.append("%s/%s: not the base with the Galileo pilot signals renamed" % (s, name))
        rx = {}
        for r in open(os.path.join(out, s, "truth_mode.csv")).read().splitlines()[1:]:
            kind, sat, sig, val, _ = r.split(",")
            if kind == "rx":
                rx[sig] = float(val)
        if rx != rx_offsets(int(re.search(r"--seed (\d+)", gen).group(1)), s,
                            float(re.search(r"--rx-code-sigma-m (\S+)", gen).group(1))):
            bad.append("%s: the receiver's offsets are not the seeded draw" % s)
        b, _ = read_text(os.path.join(base, s, "truth_rx_bias.csv"))
        o, _ = read_text(os.path.join(out, s, "truth_rx_bias.csv"))
        if rx_bias_rows(b, s, rx) != o:
            bad.append("%s/truth_rx_bias.csv: not the base with the combined mode's receiver rows" % s)
    print("verify %s: %s (%d Galileo fields moved by their table entries%s)"
          % (out, "PASS" if not bad else "FAIL " + "; ".join(bad[:10]), n_moved,
             "" if not n_same else ", %d unmoved Galileo records" % n_same))
    return 0 if not bad else 1


def selftest():
    hdr = ("     3.04           OBSERVATION DATA    M                   RINEX VERSION / TYPE\n"
           "G    4 C1C L1C C2W L2W                                      SYS / # / OBS TYPES\n"
           "E    6 C1C L1C C5Q L5Q C7Q L7Q                              SYS / # / OBS TYPES\n"
           "                                                            END OF HEADER\n")
    body = ("> 2024 05 08 00 00 30.0000000  0  2\n"
            + "G04" + "".join("%14.3f 8" % v for v in (20000000.0, 105000000.123, 20000001.5, 81000000.456)) + "\n"
            + "E07" + "".join("%14.3f 8" % v for v in (23000000.0, 121000000.0, 23000002.0, 90000000.5,
                                                         23000003.0, 93000000.25)) + "\n")
    so = {"E07": {"C1X": 0.071, "C5X": -0.005, "L1X": 0.0, "L5X": 0.0}}
    ro = {"C1X": 0.25, "C5X": -0.1, "L1X": 0.125, "L5X": -0.3}
    new, n = convert_rinex(hdr + body, so, ro)
    lines = new.split("\n")
    ok = n == 4
    ok = ok and lines[2].startswith("E    6 C1X L1X C5X L5X C7Q L7Q ") and lines[2][60:] == "SYS / # / OBS TYPES"
    ok = ok and lines[1].startswith("G    4 C1C L1C C2W L2W")
    e = lines[6]
    vals = [float(e[3 + 16 * k:3 + 16 * k + 14]) for k in range(6)]
    ok = ok and abs(vals[0] - (23000000.0 + 0.321)) < 1e-6 and abs(vals[1] - (121000000.0 + 0.125)) < 1e-6
    ok = ok and abs(vals[2] - (23000002.0 - 0.105)) < 1e-6 and abs(vals[3] - (90000000.5 - 0.3)) < 1e-6
    ok = ok and vals[4] == 23000003.0 and vals[5] == 93000000.25
    ok = ok and lines[5] == ("G04" + "".join("%14.3f 8" % v for v in (20000000.0, 105000000.123, 20000001.5, 81000000.456)))
    ok = ok and rx_offsets(1, "S01000SIM", 0.3) == rx_offsets(1, "S01000SIM", 0.3) != rx_offsets(2, "S01000SIM", 0.3)
    t = "satellite,signal,N_int,wavelength_m\nE07,L1C,3,0.19\nE07,L5Q,-2,0.25\nE07,L7Q,5,0.248\nG04,L1C,1,0.19"
    ok = ok and rename_rows(t, "signal").split("\n")[1:] == ["E07,L1X,3,0.19", "E07,L5X,-2,0.25", "E07,L7Q,5,0.248",
                                                             "G04,L1C,1,0.19"]
    osb = {("E07", "C1C"): -10.0, ("E07", "C1X"): -9.5, ("E07", "C5Q"): -20.0, ("E07", "C5X"): -20.2,
           ("E07", "L1C"): -0.3, ("E07", "L1X"): -0.3, ("E07", "L5Q"): -0.6, ("E07", "L5X"): -0.6}
    off = sat_offsets(osb, ["E07", "E99"])
    ok = ok and set(off) == {"E07"} and off["E07"]["C1X"] == round(0.5 * C_LIGHT * 1e-9, 3)
    ok = ok and off["E07"]["C5X"] == round(-0.2 * C_LIGHT * 1e-9, 3) and off["E07"]["L1X"] == 0.0
    print("selftest: %s" % ("PASS" if ok else "FAIL"))
    return 0 if ok else 1


def main():
    if "--selftest" in sys.argv:
        return selftest()
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    m = sub.add_parser("make")
    m.add_argument("--base", required=True)
    m.add_argument("--out", required=True)
    m.add_argument("--every", type=int, default=2)
    m.add_argument("--first", type=int, default=0)
    m.add_argument("--keep", default="SZZ000SIM", help="receivers left in the pilot mode and out of the count")
    m.add_argument("--seed", type=int, default=1)
    m.add_argument("--rx-code-sigma-m", type=float, default=0.3)
    m.add_argument("--label", required=True)
    v = sub.add_parser("verify")
    v.add_argument("--base", required=True)
    v.add_argument("--out", required=True)
    a = ap.parse_args()
    return make(a) if a.cmd == "make" else verify(a)


if __name__ == "__main__":
    sys.exit(main())

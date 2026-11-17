#!/usr/bin/env python3
"""Card IRDU section 12.2: a hybrid product stream, one stream's phase clocks with another stream's clocks and code
biases, to split a float user's error between the phase half and the code half of a stream.

    python scripts/irdu_hybrid_products.py --phase <products.txt> --code <products.txt> --out <products.txt>
    python scripts/irdu_hybrid_products.py --retoken <base products.txt> <token products.txt> --out <products.txt>
    python scripts/irdu_hybrid_products.py --selftest

--retoken (card IRDU section 12.2's addendum) keeps every value of the base stream and takes each P record's fields after
the bias (signal_integer, wide_lane_integer, a phase discontinuity counter, gen=, cmp=) from the token donor.

A user's phase correction is the stream's clock minus its phase bias, and its code correction the clock minus the code
bias (the wire algebra of card IRD section 8: w_b = dC - dP_b, wc_b = dC - dB_b).  The output keeps every line of the
code donor (its header S line, the H, E, C, B and U records, the comments) and replaces each P record by the phase
donor's record for the same epoch, satellite and signal, with the bias rewritten as

    P_hybrid = P_phase-donor + C_code-donor - C_phase-donor

so that the clock minus the phase bias the user reads is exactly the phase donor's, and the clock minus each code bias
exactly the code donor's.  The P record keeps the phase donor's other fields (signal_integer, wide_lane_integer and
any tokens).  A P record of the code donor with no counterpart in the phase donor, or at an epoch where either clock is
missing, is dropped and counted.  Both streams must hold the same epochs (the H and E lines carry the epoch's TOW).
"""
import argparse
import os
import sys
from collections import Counter


def parse(path):
    """(clock {(tow, sat): c0}, phase {(tow, sat, sig): fields list}) of a products file."""
    clock, phase = {}, {}
    tow = None
    with open(path, encoding="utf-8") as fh:
        for ln in fh:
            if ln.startswith("#") or not ln.strip():
                continue
            f = ln.rstrip("\n").split(",")
            if f[0] in ("H", "E"):
                tow = round(float(f[2]), 1)
            elif f[0] == "C" and tow is not None:
                clock[(tow, f[1])] = float(f[2])
            elif f[0] == "P" and tow is not None:
                phase[(tow, f[1], f[2])] = f
    return clock, phase


def hybrid(phase_path, code_path, out_path):
    pc, pp = parse(phase_path)
    cc, _ = parse(code_path)
    n = Counter()
    tow = None
    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    with open(code_path, encoding="utf-8") as fh, open(out_path, "w", encoding="utf-8", newline="\n") as out:
        for ln in fh:
            if ln.startswith("#") or not ln.strip():
                out.write(ln)
                continue
            f = ln.rstrip("\n").split(",")
            if f[0] in ("H", "E"):
                tow = round(float(f[2]), 1)
            if f[0] != "P":
                out.write(ln)
                continue
            key = (tow, f[1], f[2])
            src = pp.get(key)
            c_code, c_phase = cc.get((tow, f[1])), pc.get((tow, f[1]))
            if src is None or c_code is None or c_phase is None:
                n["P dropped (no counterpart or no clock)"] += 1
                continue
            g = list(src)
            g[3] = repr(float(src[3]) + c_code - c_phase)
            out.write(",".join(g) + "\n")
            n["P rewritten"] += 1
    return n


def retoken(base_path, token_path, out_path):
    """The base stream with every P record's fields after the bias (signal_integer, wide_lane_integer and any tokens)
    taken from the token donor's record for the same epoch, satellite and signal; every other line and every value of
    the base kept.  A P record with no counterpart in the token donor is kept as it is and counted."""
    _, tp = parse(token_path)
    n = Counter()
    tow = None
    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    with open(base_path, encoding="utf-8") as fh, open(out_path, "w", encoding="utf-8", newline="\n") as out:
        for ln in fh:
            if ln.startswith("#") or not ln.strip():
                out.write(ln)
                continue
            f = ln.rstrip("\n").split(",")
            if f[0] in ("H", "E"):
                tow = round(float(f[2]), 1)
            if f[0] != "P":
                out.write(ln)
                continue
            src = tp.get((tow, f[1], f[2]))
            if src is None:
                n["P kept (no counterpart)"] += 1
                out.write(ln)
                continue
            out.write(",".join(f[:4] + src[4:]) + "\n")
            n["P retokened"] += 1
    return n


def selftest():
    import tempfile
    ok = True

    def chk(c, msg):
        nonlocal ok
        print(("PASS " if c else "FAIL ") + msg)
        ok &= bool(c)

    d = tempfile.mkdtemp()
    a = os.path.join(d, "a.txt")
    b = os.path.join(d, "b.txt")
    o = os.path.join(d, "o.txt")
    open(a, "w").write("# head\nS,X\nH,2313,100.0,ok\nE,2313,100.0,0\nC,G01,2.0\nB,G01,C1C,0.5\nP,G01,L1C,1.25,1,0\n")
    open(b, "w").write("# head\nS,Y\nH,2313,100.0,ok\nE,2313,100.0,0\nC,G01,-1.0\nB,G01,C1C,0.25\nP,G01,L1C,9.0,1,1,0,gen=1\n")
    n = hybrid(a, b, o)        # phase from a, code from b
    lines = [ln.rstrip("\n") for ln in open(o) if not ln.startswith("#")]
    p = [ln for ln in lines if ln.startswith("P")][0].split(",")
    c = float([ln for ln in lines if ln.startswith("C")][0].split(",")[2])
    chk(abs((c - float(p[3])) - (2.0 - 1.25)) < 1e-12, "the user's phase clock (C - P) is the phase donor's")
    chk("S,Y" in lines and "B,G01,C1C,0.25" in lines, "the header and the code biases are the code donor's")
    chk(p[4:] == ["1", "0"] and n["P rewritten"] == 1, "the P record keeps the phase donor's other fields")
    n = retoken(a, b, o)       # a's values with b's fields
    p = [ln for ln in open(o) if ln.startswith("P")][0].rstrip("\n").split(",")
    chk(p[3] == "1.25" and p[4:] == ["1", "1", "0", "gen=1"] and n["P retokened"] == 1,
        "retoken keeps the base's value and takes the token donor's fields")
    return ok


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--phase")
    ap.add_argument("--code")
    ap.add_argument("--out")
    ap.add_argument("--retoken", nargs=2, metavar=("BASE", "TOKENS"),
                    help="the BASE stream's values with the P-record fields of TOKENS (card IRDU 12.2 addendum)")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        sys.exit(0 if selftest() else 1)
    if a.retoken:
        n = retoken(a.retoken[0], a.retoken[1], a.out)
        print("%s: the values of %s with the P-record fields of %s; %s" % (a.out, a.retoken[0], a.retoken[1], dict(n)))
        return
    n = hybrid(a.phase, a.code, a.out)
    print("%s: phase clocks of %s with the clocks and code biases of %s; %s" % (a.out, a.phase, a.code, dict(n)))


if __name__ == "__main__":
    main()

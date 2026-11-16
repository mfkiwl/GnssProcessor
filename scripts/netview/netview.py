"""Network view: an interactive page of one network run (links, held whole numbers, parameters over time).

    py -3.14 scripts/netview/netview.py build <run folder> [-o page.html] [--no-compress]
    py -3.14 scripts/netview/netview.py arm <config.json> -o <armed config.json> [--no-map]
    py -3.14 scripts/netview/netview.py compare <page A.html> <page B.html> -o <compare.html>

build   reads the run folder's traces (logs/*.csv and products.txt) and writes one HTML page that opens by
        double-click from file:// (no server, no network access).  Default output: <run folder>/netview.html.
        Parts whose trace is absent are left out and named on the page with the key that writes them.
arm     writes a copy of a run config with the trace keys the page needs switched on (traces only: nothing that
        the estimate reads).  Normal runs leave them off and pay nothing; a run made from the armed copy can be
        viewed.
compare writes a page that shows two built pages side by side (for example the same day from two reference
        receivers); time, signals, layout and the selected link or node follow each other.

The page, the quantities and the cost of the traces: docs/onboarding/network_view.md.
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import nv_arm  # noqa: E402
import nv_build  # noqa: E402
import nv_page  # noqa: E402


def cmd_build(a) -> int:
    run = Path(a.run)
    if not run.is_dir():
        print(f'{run}: not a folder', file=sys.stderr)
        return 2
    out = Path(a.output) if a.output else run / 'netview.html'
    t = time.time()
    print(f'reading {run}')
    header, arrays = nv_build.build_block(run)
    sizes = nv_page.write_page(out, header, arrays, compress=not a.no_compress)
    print(f'wrote {out}: page {sizes["page"] / 1e6:.1f} MB (data block {sizes["raw"] / 1e6:.1f} MB before compression), '
          f'{header["n_ep"]} epochs, {len(header["stations"])} receivers, {len(header["sats"])} satellites, '
          f'{len(header["families"])} signal families, {time.time() - t:.1f} s')
    for m in header['missing']:
        print(f'  not in this run: {m["part"]} ({m["file"]}; key {m["key"]})')
    return 0


def cmd_arm(a) -> int:
    changed, notes = nv_arm.arm(Path(a.config), Path(a.output), with_map=not a.no_map)
    print(f'wrote {a.output}')
    for k, old, new in changed:
        print(f'  {k}: {old} -> {new}')
    if not changed:
        print('  every key the page needs was already on')
    for n in notes:
        print(f'  note: {n}')
    return 0


def cmd_compare(a) -> int:
    pa, pb = Path(a.page_a), Path(a.page_b)
    for p in (pa, pb):
        if not p.is_file():
            print(f'{p}: no such page (build it first)', file=sys.stderr)
            return 2
    nv_page.write_compare(Path(a.output), pa, pb)
    print(f'wrote {a.output}: {pa.name} beside {pb.name} (keep the three files in their folders)')
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    sub = ap.add_subparsers(dest='cmd', required=True)
    b = sub.add_parser('build', help='write the page of one run folder')
    b.add_argument('run')
    b.add_argument('-o', '--output', help='page path (default <run>/netview.html)')
    b.add_argument('--no-compress', action='store_true', help='store the data block uncompressed')
    b.set_defaults(fn=cmd_build)
    r = sub.add_parser('arm', help='copy a run config with the traces the page needs switched on')
    r.add_argument('config')
    r.add_argument('-o', '--output', required=True)
    r.add_argument('--no-map', action='store_true', help='leave the ionosphere trace (satellite positions) as it is')
    r.set_defaults(fn=cmd_arm)
    c = sub.add_parser('compare', help='a page showing two built pages side by side, time and selection linked')
    c.add_argument('page_a')
    c.add_argument('page_b')
    c.add_argument('-o', '--output', required=True)
    c.set_defaults(fn=cmd_compare)
    a = ap.parse_args(argv)
    return a.fn(a)


if __name__ == '__main__':
    sys.exit(main())

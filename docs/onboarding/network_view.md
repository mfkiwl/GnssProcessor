# The network dashboard: one network run on one page

`scripts/netview/netview.py` turns the traces of one network run into a single HTML page laid out as a dashboard:
layers over the whole network (overview, network links, receivers, satellites, cycle slips, stochastic model,
atmosphere, products and user check, events) that lead to the page of one receiver, one satellite and one line of
sight, all on one time cursor. The page opens by double-click (no server, no network access). It is made on request
from a finished run folder, so normal runs pay nothing. The quantities, their sources and the decisions behind the
page: [NETVIEW](../cards/tools/NETVIEW-network-view.md) (the dashboard: section 11).

## Make a page from a finished run

```
py -3.14 scripts\netview\netview.py build <run folder> -o <page.html>
```

Without `-o` the page is written to `<run folder>\netview.html`. The build reads `logs\*.csv`,
`logs\network_run_manifest.json` and `products.txt` (about 40 s for a 6 h run of 56 receivers) and writes a page of
about 22 MB. The overview is ready about a second after the page loads; the other layers decode their data the first
time they are opened (0.1 to 0.3 s). Parts whose trace is absent are left out; the build and each layer name the
file and the key that writes it.

## Make a run that can be viewed

```
py -3.14 scripts\netview\netview.py arm <config.json> -o <armed config.json>
```

`arm` writes a copy of the config with the trace keys of the page switched on and changes nothing else (the
fixing and the chain datum change the estimate and are never switched on by it). The reference configurations
(`config\golden\`) already arm every trace the dashboard reads but two: `network.trace_chain_datum` (the trees and
the links) and `network.trace_rpb_states` (the receiver phase bias); both write only on a run with the chain datum
(`network.phase_datum_eq34`). The run is then made as usual from the armed copy.

| Trace | Key | Size per 6 h, 56 receivers, GPS + Galileo |
| --- | --- | --- |
| `network_chain_edges.csv` | `network.trace_chain_datum` | 49 MB |
| `network_chain_frame.csv` | `network.trace_chain_datum` | 50 MB |
| `network_rpb_states.csv` | `network.trace_rpb_states` | about 14 MB (1.15 MB in the first 30 min of DOY 144) |
| `network_ring_fix.csv` | written by the fixing itself (`network.ring_fix.enable`) | 14 MB (one family held) to 34 MB (two) |
| post-fit rows, carried floats, slip tests and observables, ionosphere, residual test, events and the rest | already armed in `config\golden\` | about 600 MB together |

The two added traces cost about 1 % of the run time and leave `products.txt` byte-identical (measured on 30 min of
DOY 144: [NETVIEW](../cards/tools/NETVIEW-network-view.md), section 5).

## Compare two runs

```
py -3.14 scripts\netview\netview.py compare <page A.html> <page B.html> -o <compare.html>
```

The comparison page shows the two pages side by side; time, the view and its selection follow each other, and each
side keeps its own data (for example the same day from two reference receivers). The three files keep their
relative places.

## Reading the page

1. The rail on the left picks a layer; the badge beside it is its count. The path above the view leads back
   (Overview > Receivers > MBAR00UGA > G05), and so does the browser's back button.
2. The overview's tiles show the cursor epoch with their history; a click on a tile opens the layer behind it. Its
   matrices (receivers x time, satellites x time) take a metric from the buttons above them, worst rows first.
3. A click on a receiver or a satellite (a table row, a point on a map, a cell of a matrix) opens its page at that
   time. On a receiver or satellite page, a click on an arc or on a dot of the sky plot opens the line of sight.
4. The slider, the play button, the arrow keys (Shift: ten epochs) and a click on any chart move the time; every
   view follows. The lanes under the slider count the events of the run; a click on a lane jumps to its nearest
   event and lists the events of that epoch. On an entity page the lane "Selected" holds that entity's events.
5. Event lists name the receiver and the satellite of each row; a click on a row opens its line of sight at that
   time.
6. The network links layer is the first page design: the tree of each signal as rings of hops, held and float
   links, and on the right the detail of a link, satellite or receiver. A double-click on a node or a link opens its
   page.
7. The legend button explains the terms (layers, going deeper, tree link, held link, wide and narrow lane, jump,
   post-fit residual, sigma0, variance factor, MW, GF, wet delay).

## Tests

```
py -3.14 scripts\netview\test_netview.py
```

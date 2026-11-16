# The network view: one network run on one page

`scripts/netview/netview.py` turns the traces of one network run into a single HTML page: the tree of each signal
as rings of hops around its reference receiver, the links held at whole numbers and the float links, the history of
every link, satellite and receiver, an event timeline and summaries over the run. The page opens by double-click
(no server, no network access). It is made on request from a finished run folder, so normal runs pay nothing. The
quantities, their sources and the decisions behind the page: [NETVIEW](../cards/tools/NETVIEW-network-view.md).

## Make a page from a finished run

```
py -3.14 scripts\netview\netview.py build <run folder> -o <page.html>
```

Without `-o` the page is written to `<run folder>\netview.html`. The build reads `logs\*.csv` and `products.txt`
(about 20 s for a 6 h run of 56 receivers) and writes a page of 6 to 7 MB that is ready about half a second after
opening. Parts whose trace is absent are left out; the page and the build both name the file and the key that
writes it.

## Make a run that can be viewed

```
py -3.14 scripts\netview\netview.py arm <config.json> -o <armed config.json>
```

`arm` writes a copy of the config with the trace keys of the page switched on and changes nothing else (the
fixing and the chain datum change the estimate and are never switched on by it). The reference configurations
already arm every key but two: `network.trace_chain_datum` (the tree and the links) and `network.trace_rpb_states`
(the receiver phase bias), and both write only on a run with the chain datum (`network.phase_datum_eq34`). The run
is then made as usual from the armed copy.

| Trace | Key | Size per 6 h, 56 receivers, GPS + Galileo |
| --- | --- | --- |
| `network_chain_edges.csv` | `network.trace_chain_datum` | 49 MB |
| `network_chain_frame.csv` | `network.trace_chain_datum` | 50 MB |
| `network_rpb_states.csv` | `network.trace_rpb_states` | about 14 MB (1.15 MB in the first 30 min of DOY 144) |
| `network_ring_fix.csv` | written by the fixing itself (`network.ring_fix.enable`) | 14 MB (one family held) to 34 MB (two) |
| events, alarms, receivers, wet delay, receiver clock, ionosphere | already armed in `config\golden\` | 68 MB together |

The two added traces cost about 1 % of the run time and leave `products.txt` byte-identical (measured on 30 min of
DOY 144: [NETVIEW](../cards/tools/NETVIEW-network-view.md), section 5).

## Compare two runs

```
py -3.14 scripts\netview\netview.py compare <page A.html> <page B.html> -o <compare.html>
```

The comparison page shows the two pages side by side; time, signals, layout and the selected link or node follow
each other, and each side keeps its own tree (for example the same day from two reference receivers). The three
files keep their relative places.

## Reading the page

1. The top row picks the signal pair, the signal whose tree is drawn, the layout (rings by hops or a world map)
   and which links show.
2. The slider and the play button move in time; the arrow keys step one epoch (ten with Shift).
3. The timeline below the slider has one lane per kind of event (held, released, tree re-formed, slips, gaps,
   alarms, code reference, other checks); a click on a lane jumps to its nearest event and lists the events of
   that epoch.
4. A click on a link, a satellite or a receiver opens its history on the right; the yellow path is the chain of
   tree links from it to the reference receiver.
5. The legend button explains tree link, held link, float link, hop, wide lane, narrow lane and jump.
6. The address of the page records the time, the signals and the selection, so a view can be bookmarked.

## Tests

```
py -3.14 scripts\netview\test_netview.py
```

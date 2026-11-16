# NETVIEW: an interactive page of one network run (links, held whole numbers, parameters over time)

**STATUS**

- **id:** NETVIEW
- **topic:** tools
- **status:** open
- **summary:** A tool that turns the traces of one network run into one self-contained HTML page: the tree of each signal as rings of hops around its reference receiver, the links held at whole numbers and the float links, the history of every link (whole numbers, wide-lane and narrow-lane distance from them with sigma, state, holds and releases), satellite (hops, jumps of the correction level, clock and biases) and receiver (wet delay, clock, receiver phase bias, alarms, links), an event timeline and summaries over the run; a comparison page links two pages in time. Made on request from existing traces, no C++ change; `netview.py arm` writes a config copy with the traces on. Branch `viz/network-view`.
- **dates:** 2026-11-15 (built and first version shown to the author)
- **code:** `scripts/netview/` (`netview.py` with the commands build, arm and compare; readers `nv_read.py`, aggregation `nv_build.py`, page writer `nv_page.py`, the page's sources in `page/`, unit tests `test_netview.py`); how-to [onboarding/network_view.md](../../onboarding/network_view.md)
- **knobs / posture:** none new. `arm` switches on existing trace keys only.
- **run dirs:** pages of `D:\GnssProcessorSupport\runs_nom\_rap_o2s1j_n144`, `_rap_o2s1j_n144r`, `_rap_o2offj_n144`, `_rap_o9_n145`, `_rap_ka_sim` and `_rap_k0_sim` in `D:\GnssProcessorSupport\netview_out\`; the timing pair in `D:\GnssProcessorSupport\netview_out\timing\`
- **source:** the author's request of 2026-11-15 (section 1); the definitions of NRF and BER (branch `irdu/user-integers`, `docs/refound/NRF_network_ring_fixing_2026-11-14*.md`, `BER_bad_epoch_response_2026-11-15.md`) and of ARNF sections 3, 9 and 15 (branch `ar/rx-sat-code-bias`)

**Outcome.** Built. One command makes a page of 6 to 7 MB from a 6 h run of 56 receivers in about 20 s; it is
ready about 0.5 s after opening and redraws in 3 to 7 ms per epoch while scrubbing. The page shows the tree, held
and float links, each link's whole numbers and float distances, satellites' correction-level jumps, receivers' wet
delay and clock, events in lanes, held share and jumps by hops over the run. It degrades to what a run traced and
names the key of each missing part. `arm` adds two traces on a chain run, about 1 % of the run time, products
byte-identical. What it cannot show yet is listed with the export that would provide it.

> Results are appended to this file, below the text, under dated headings.

---

## 1. The request

The author's words, 2026-11-15: "Task another Opus session to build a visualization tool to help me understand
the network information. I mean, links, fixed integers, parameter information. We already have an HTML approach
but it is rather simple and overall basic. I want something more interactive and informative. Default off to save
processing time, but I can re-run on if I want to view network info. Otherwise, only understanding from our chats
becomes hard to manage and follow!"

## 2. What was built

- `netview.py build <run folder> [-o page.html]` reads `logs/*.csv` and `products.txt`, pre-aggregates them into a
  compact binary block (typed arrays, one column per quantity, dense where a quantity is per node and epoch) and
  writes one HTML page. The block is gzip-compressed and base64-encoded into the page; the browser's
  `DecompressionStream` opens it and the page takes typed-array views of it, so nothing large is parsed as text.
  The page draws on canvas with its own short script: no library, no server, no network access.
- `netview.py arm <config> -o <copy>` switches on the trace keys of the page in a copy of a run config and prints
  a note when the run lacks the chain datum or the fixing (it never switches those on: they change the estimate).
- `netview.py compare <page A> <page B> -o <page>` writes a page with the two side by side; each page tells the
  frame its time, signals, layout and selection, and the frame passes them to the other.
- Dependencies: Python 3.14 with numpy; the colour maps are the viridis and vik tables of
  `pyviz/gnssviz/colormaps.py`, the world coastline the Natural Earth table of `pyviz/gnssviz/assets/`.

`scripts/netview/` rather than `pyviz/`: the tool is a command over run folders, as `scripts/qc_dashboard.py` and
`scripts/simnet_report.py` are; its page has its own drawing code and none of pyviz's figure or backend layers, and
it borrows only the two pyviz tables above.

## 3. The page

| Part | What it shows |
| --- | --- |
| Network | One signal pair at a time. The tree of the chosen signal as a radial tree: the reference receiver at the centre, every node on the ring of its hops, each subtree in a wedge as wide as its leaves, children ordered by their direction from the reference receiver. Tree links black, tree links of the other signal only dashed, held links blue, links not yet held orange, links of a pair without fixing grey. Node colour (viridis): the share of the node's links towards the reference that are whole numbers. A red ring marks an alarm in the last minute, a cross a release at this epoch. A world-map layout places receivers at their positions and satellites at their sub-satellite points. |
| Link | State over the run (tree link of both signals or of one, held, decided, not yet held, float); now: the whole numbers (held or nearest) per signal and the wide lane, both floats with their distance from the whole numbers and sigma, the ring, the residual; charts of the wide-lane and narrow-lane distance with a one-sigma band and the gate's limits, the post-fit residual while held with the release bound, the whole number of the tree link per signal, the elevation; the link's events. |
| Satellite | Hops on both signals over time and its parent; its links towards the reference and whether all are whole numbers; the correction level (its own steps added up, narrow lane and wide lane) with each jump marked by class; the emitted clock, phase and code biases (each less its median); its events. |
| Receiver | Hops and parent; its links by state; wet delay with sigma, clock, receiver phase bias where traced; its alarms and events. |
| Timeline | One lane per kind of event with a mark per epoch (height by count): held, released, tree re-formed, slips, gaps and returns, alarms, code reference, other checks, and a lane of the selected link or node; the held share below. A click jumps to the nearest event of the lane and lists the events of that epoch. |
| Over the run | Share of the links that are not tree links held, per family; the counts of tree, held, not-yet-held and float links; jumps of the corrections per satellite-hour by hour and hops class (1, 3, 5, 7+) and class; releases by cause and alarms and slips per 10 min. |

The page's address records time, signals, layout and selection, so a view can be bookmarked and sent.

## 4. The quantities and where they come from

| Quantity | Trace | How |
| --- | --- | --- |
| tree, hops, parent, whole number of a tree link | `network_chain_edges.csv` | per epoch and signal: `child`, `parent`, `depth`, `target_cyc`, `row`; the reference receiver is `r1` of its component (no row of its own) |
| links that are not tree links, their floats and covariance | `network_chain_frame.csv` | per epoch and pair family: `float_cyc_1`, `float_cyc_2`, `q11`, `q12`, `q22` |
| wide lane and narrow lane of a link | the two above | the gate's algebra of `ringFixGate` (`src/core/network/ar/RingFix.cpp`): wl = f1 - f2, rounded; with r = F1 / F2, n = (r f1 - f2 - round(wl)) / (r - 1), sigma(n)² = a² q11 + 2 a b q12 + b² q22 with a = r / (r - 1), b = -1 / (r - 1); checked against `network_ring_fix.csv` on a row of `_rap_o2s1j_n144` (n and its sigma to 1e-3 cycle) |
| fixing state, held whole numbers, ring, residual | `network_ring_fix.csv` | `state` and `refused` (the first test failed), `n1`, `n2`, `ring`, `resid_if_m`; the audit column where a simulator truth is armed |
| held share | `network_ring_fix.csv` | held rows over all rows of the family at the epoch (the definition of `nrf_reads_mine.py`) |
| links towards the reference | tree and links | links of a node to nodes of fewer hops on the drawn signal's tree; whole when a tree link of that signal or held |
| jumps of the correction level | `products.txt` | the definition of `stream_jumps.py` (ARNF section 3): E_b = (C - P_b + mu_b x) / lambda_b with x = ((C - B_1) - (C - B_2)) / (1 - gamma); the step between consecutive epochs less the constellation's median step; classes with a tolerance of 0.15 cycle: whole (both signals within it of whole numbers), ionosphere-like (ionosphere-free part within it), fraction; the hops class is the larger depth of the satellite on the two trees |
| events | `network_events.csv`, `network_raim.csv` | every row but `PRIORRES` (one diagnostic row per prior and epoch, counted and dropped); lanes by tier and event; the RAIM rows become alarms |
| wet delay, receiver clock, receiver phase bias | `network_zwd.csv`, `network_rx_states.csv` (kind CLK), `network_rpb_states.csv` | as written |
| elevation, sub-satellite point | `network_ionosphere.csv` | azimuth and elevation of each line of sight; the line from the receiver met with the nominal orbit sphere, averaged over the receivers |
| clock, phase and code biases | `products.txt` | the C, P and B records |

## 5. What the traces cost

Sizes for the 6 h runs of 56 receivers (GPS and Galileo, two families each): `network_chain_edges.csv` 49 MB,
`network_chain_frame.csv` 50 MB, `network_ring_fix.csv` 14 MB with one family held and 34 MB with two.
`network_rpb_states.csv` was not written by these runs; on the timing pair below it wrote 1.15 MB in 30 min, about
14 MB per 6 h. The traces the reference configurations already arm (events, alarms, receivers, wet delay, receiver
clock, ionosphere) total 68 MB.

**Run time, measured 2026-11-15.** The first 30 min of DOY 144 on the config of `_rap_o2offj_n144` (the chain
datum, no fixing), exe `gnss_processor.exe` of branch `irdu/user-integers` at `8f3b554` (sha256[:16]
`6cc0823967615e00`) copied as `gnss_processor_netview_timing.exe`, one process at a time, in the order A B B A,
on a machine shared with up to four other runs:

| Arm | `trace_chain_datum`, `trace_rpb_states` | Wall time |
| --- | --- | --- |
| A1 | on | 108.5 s |
| B1 | off | 106.3 s |
| B2 | off | 106.4 s |
| A2 | on | 106.7 s (four other runs had started) |

The traces cost about 1 % of the run time (1.3 s on 106 s on the means; the two traced runs differ by 1.8 s from
each other). `products.txt` is byte-identical with the traces on and off (A1 against B1, and B1 against B2): the
traces do not touch the estimate. In 30 min they wrote 4.0 MB (`network_chain_edges.csv`), 4.0 MB
(`network_chain_frame.csv`) and 1.15 MB (`network_rpb_states.csv`).

## 6. Size and speed of the page

| Run | Build | Traces read | Page (block before compression) |
| --- | --- | --- | --- |
| `_rap_o2s1j_n144` (6 h, 56 receivers, one family held) | 18.0 s | 193 MB | 6.8 MB (25.1 MB) |
| `_rap_o2s1j_n144r` (the same from GOPE00CZE) | 18.2 s | | 6.9 MB |
| `_rap_o2offj_n144` (no fixing) | 16.6 s | | 7.0 MB |
| `_rap_o9_n145` (two families held) | 20.3 s | | 6.6 MB |
| `_rap_ka_sim`, `_rap_k0_sim` (simulator, 3 h, 60 receivers) | 11.6 s, 11.2 s | | 3.7 MB, 3.8 MB |

In Chrome the page of `_rap_o2s1j_n144` is ready about 0.5 s after it is opened (0.24 s for the document, 0.23 s
to unpack the block and draw); a step in time redraws the network, the timeline, the detail panel and its charts
in 3 to 7 ms; the page holds about 35 MB of memory. The block is compressed about 3.7 times; most of what remains
is the per-epoch fractions of the floats (two 16-bit numbers per link and epoch) and the per-satellite series.

## 7. What the page cannot show yet, and the export that would provide it

No C++ was changed. Each item names the smallest default-off export that would close it; none is built.

1. **Floats of a link that is a tree link of one signal only.** `network_chain_frame.csv` lists the links that
   are not tree links of either signal, so such a link shows its whole number on the one signal and no float on
   the other. Export: the same row for these links, behind a key such as `network.trace_chain_frame_one_signal`.
2. **The carried float of every link and its re-levels** (`network_amb_state.csv`, 151 MB per 6 h) is not read:
   the size would double the page for little that the chord table does not already give. A build option could
   read it for one link or receiver on request.
3. **Residuals of links that are not held.** `resid_if_m` is written for held links only. Export: the post-fit
   ionosphere-free phase residual of every link of a fixed family in `network_ring_fix.csv`.
4. **Receiver phase bias on the observed-data runs.** Not traced in the sample runs; `arm` switches on
   `network.trace_rpb_states`, which exists.
5. **Whether a held whole number is right** is known only on the simulator (the audit column).
6. **Satellite positions** are from the lines of sight and nominal orbit radii, good to a few tenths of a degree;
   exact positions would need the orbit product.
7. **A run in progress or the real-time engine.** The page reads a finished post-processing run folder.

## 8. Verification

- `py -3.14 scripts/netview/test_netview.py`: 18 tests on a synthetic run folder (readers, the gate algebra
  against the trace row of section 4, the held whole numbers decoded from the block, jump classes on synthetic
  products, the sub-satellite point of a satellite overhead, the binary layout round trip, the missing and empty
  parts, `arm`, the comparison page, and the page's text against the author's list of words to avoid).
- Pages built for the six sample runs; read in a browser at 1500 by 950 pixels and from `file://` (both frames of
  the comparison page load and follow each other in time and selection).
- A run folder stripped to `products.txt`, the events, the receivers and the wet delay: the page shows those and
  names each missing trace with its key.
- `arm` on `config/golden/golden_field_refound.json` changes exactly `network.trace_chain_datum` and
  `network.trace_rpb_states` and notes that the chain datum and the fixing are off; on the config of
  `_rap_o2s1j_n144` it changes `network.trace_rpb_states` only.

## 9. Decisions made in the author's absence, for review

1. Location `scripts/netview/` (section 2); default output `<run folder>/netview.html`.
2. The radial tree layout, ordered by direction from the reference receiver so that the picture keeps its
   geography as the tree changes; rings compressed outward (radius as the 0.6 power of the hops) and the outer
   hop ring at the depth 99 % of the run's nodes do not exceed.
3. Lanes of the timeline as in section 4; `PRIORRES` rows dropped (26 501 of 49 888 rows on `_rap_o2s1j_n144`).
4. One display substitution in raw trace text (a word of the author's list, in three rows of one tier).
5. Colours: viridis for the share of whole links; a fixed colour per link kind and per event lane.

## 10. 2026-11-15: further choices made without the author, and the open questions

Recorded at the end of the build, for the author to read later; no answer was waited for.

**Choices.**

1. "Tied to the reference only through held links" is read as: every link of the node to a node of fewer hops on
   the drawn signal's tree is a tree link or a held link. The satellite and receiver panels say yes or no with the
   count; the node colour is the same share.
2. The held share is the held rows over all rows of the family in `network_ring_fix.csv` at the epoch, which are
   the links that are not tree links (the definition of `nrf_reads_mine.py`).
3. While a link is held, the float in `network_chain_frame.csv` is the solve's value under the hold's tight prior,
   so its distance from the whole number and its sigma read near zero; the panel marks it "pinned by the hold".
   The informative part of the narrow-lane chart is the stretch before each decision.
4. Jumps keep the tolerance (0.15 cycle) and the hops classes (1, 3, 5, 7 and more) of `stream_jumps.py`.
5. Satellite positions come from the lines of sight and nominal orbit radii; the world map draws straight lines in
   longitude and latitude (a link across the date line crosses the map).
6. Event lists hide the lane "other checks" (outlier tests, bookkeeping, the wet-delay carry) behind a link that
   shows them.
7. The page draws with its own short script on canvas; no library is vendored. The data block is binary, gzip in
   base64, opened by the browser's `DecompressionStream` (Chrome, Edge, Firefox and Safari of the last three years).
8. The timing pair used the config without fixing: the loader refuses the fixing without the tree trace, so the
   trace cannot be switched off on a fixing run.

**Open questions.**

1. Node colour: the share of whole links towards the reference (as built), or another quantity (the time since the
   node last moved, alarms, wet delay)?
2. Build one of the exports of section 7 (floats of a link that is a tree link of one signal only; residuals of
   links that are not held), or read `network_amb_state.csv` for one link or receiver on request?
3. Should `arm` stay limited to trace keys? It never switches on the chain datum or the fixing, which change the
   estimate.
4. Default output path: `<run folder>/netview.html` (as built) or a separate folder?
5. BeiDou: the frequency table includes it, but no sample run has a BeiDou tree, so a BeiDou page is untested.
6. Merging the branch to `main` (no C++, the tool and its documentation only) is the author's call.

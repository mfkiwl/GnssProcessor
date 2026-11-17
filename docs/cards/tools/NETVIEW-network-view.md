# NETVIEW: an interactive page of one network run (links, held whole numbers, parameters over time)

**STATUS**

- **id:** NETVIEW
- **topic:** tools
- **status:** open
- **summary:** A tool that turns the traces of one network run into one self-contained HTML page. Since 2026-11-17 the page is a dashboard of layers a reader clicks through (section 11): overview, network links (the trees, held and float links, each link's whole numbers), receivers, satellites, cycle slips, stochastic model, atmosphere, products and the held-out user check, events; and pages of one receiver, one satellite and one line of sight, all on one time cursor. Made on request from existing traces, no C++ change; `netview.py arm` writes a config copy with the two traces the reference configurations lack. Branch `viz/network-view`.
- **dates:** 2026-11-15 (built and first version shown to the author); 2026-11-17 (the dashboard)
- **code:** `scripts/netview/` (`netview.py` with the commands build, arm and compare; readers `nv_read.py` and `nv_tables.py`, aggregation `nv_build.py` (core block) and `layers/` (the other blocks), page writer `nv_page.py`, the page's sources in `page/`, unit tests `test_netview.py`); how-to [onboarding/network_view.md](../../onboarding/network_view.md)
- **knobs / posture:** none new. `arm` switches on existing trace keys only.
- **run dirs:** pages of `D:\GnssProcessorSupport\runs_nom\_rap_o2s1j_n144`, `_rap_o2s1j_n144r`, `_rap_o2offj_n144`, `_rap_o9_n145`, `_rap_ka_sim` and `_rap_k0_sim` in `D:\GnssProcessorSupport\netview_out\` (the first page design); the dashboard of `_rap_l12_n144` as `D:\GnssProcessorSupport\netview_out\l12_n144.html`; the timing pair in `D:\GnssProcessorSupport\netview_out\timing\`
- **source:** the author's request of 2026-11-15 (section 1); the definitions of NRF and BER (branch `irdu/user-integers`, `docs/refound/NRF_network_ring_fixing_2026-11-14*.md`, `BER_bad_epoch_response_2026-11-15.md`) and of ARNF sections 3, 9 and 15 (branch `ar/rx-sat-code-bias`)

**Outcome.** Built, then rebuilt as a dashboard (section 11). One command makes a 22 MB page from a 6 h run of 56
receivers in about 40 s. The overview is ready about 0.9 s after the page loads, a layer opens in 0.01 to 0.2 s and
a time step redraws in about 4 ms. Nine layers (overview, network links, receivers, satellites, cycle slips,
stochastic model, atmosphere, products and user check, events) lead to pages of one receiver, one satellite and one
line of sight. The page degrades to what a run traced and names the key of each missing part. `arm` adds two
traces, about 1 % of the run time, products byte-identical.

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

## 11. 2026-11-17: the dashboard (layers a reader clicks through)

**The request.** The author's words, 2026-11-17: "The interactive network viewer is a good attempt. I want something
like a dashboard. Interactive selectable layers that I can click through to get more detail at each level. What I
envision is almost like a network management visual tool. Network information, receiver information, stochastic
model, cycle slips, satellite health, etc. We have an incredible amount of data to view and we need a fast,
efficient, organized structure that is intuitive to help me follow along."

**Structure.** The time bar and its event lanes stay on top. A rail on the left lists the layers, each with a badge
(its count), and a path above the view names where the reader is (Overview > Receivers > MBAR00UGA > G05). The
address is `#/layer/argument?t=epoch`, so the browser's back button walks the views and a view can be bookmarked.
Every receiver and satellite name is a link to its page, and one time cursor drives every view. Three levels: the
layers over the whole network, the page of one receiver or one satellite, the page of one line of sight (receiver x
satellite).

| Layer | What it shows | Traces |
| --- | --- | --- |
| Overview | key figures with their history (epochs emitted, post-fit sigma0, receivers and satellites in the solution, held share per family, slips per hour, quality-test flags, held-out user 3D error, time per epoch); receivers x time and satellites x time for a chosen metric; the receivers and satellites worth a look | epoch status, solve health, run summary, held-out user, post-fit rows and pools, events, links |
| Network links | the first page design (sections 2 and 3), with links to the pages below and a double-click that opens them | chain edges and frame, ring fix, events, products |
| Receivers, and the page of one | a map and a table; receivers x time; per receiver a sky plot, the arcs of its satellites with slips, gaps, holds and releases, post-fit code and phase residuals, normalized scales, satellites, wet delay, clock, code biases and inter-system bias, the coordinate test, the residual test, its held links | post-fit rows and pools, receiver states, coordinate test, residual test, wet delay, ionosphere (azimuths) |
| Satellites, and the page of one | sub-satellite points on a map and a table; satellites x time; per satellite the receivers tracking it (arcs), its ground track, the emitted clock and phase biases with their discontinuity steps, code-bias states with sigma, the clock anchor guard, its residuals, hops and correction-level jumps | products and their counters, code-bias states, anchor guard, post-fit rows and pools |
| Line of sight | elevation; the post-fit residual of every signal with its a priori sigma; Melbourne-Wubbena, geometry-free and phase minus code with the loss-of-lock flags; the time-difference test against its threshold; slant ionosphere; the residual test; carried float ambiguities with births and drops; the link's whole numbers | post-fit rows, raw slip observables, time-difference test, ionosphere, residual test, carried floats, ring fix, chain frame |
| Cycle slips | slips per 10 minutes by detector (loss of lock, Melbourne-Wubbena, geometry-free, time-difference test); receivers x time; by receiver (also per satellite-hour of tracking) and by satellite; by elevation with the rate per hour of tracking; how often each test flags and the false-alarm rate its threshold implies; the list | events, flag rates, post-fit rows (tracking) |
| Stochastic model | sigma0 over time; variance factors per class of observation; residuals and normalized residuals by elevation and by hour; histograms of the normalized residuals against the normal curve; the block outlier test, smallest detectable errors, carried-prior tests, attribution of large residuals; parameters as modelled and responses to events (run manifest); measured floors of the carried priors | epoch status, variance factors, post-fit rows, block outlier test, detectability, carried-prior test, attribution, run manifest, carried-prior variance |
| Atmosphere | wet delay on a map and receivers x time; slant ionosphere at the pierce points on a shell 350 km high; the vertical-equivalent ionosphere per receiver over time | wet delay, ionosphere |
| Products and user check | epochs emitted, discontinuity steps, datum per constellation, time per epoch; the held-out user receiver's position error by hour, satellites and fixing, inter-system bias | epoch status, solve health, products' counters, datum graph, service health, held-out user |
| Events | events per 10 minutes by family; the list with filters (family, check, name, time window) | events |

**Data.** The page holds six blocks: the core block of the first design (decoded at open) and five more (epoch,
receivers, satellites, quality, line of sight), each a gzip and base64 container decoded the first time a view needs
it. The new blocks are read with pyarrow and reduced with numpy (`nv_tables.py`, `layers/`). Line-of-sight series
are dense [line of sight, epoch] arrays of small integers (code residuals in cm, phase residuals in 0.2 mm, a
sentinel where absent); the smooth ones (slant ionosphere, geometry-free, carried floats) are stored as steps between
epochs and added back when the block opens. pyarrow's conversions of arrays with empty fields import pandas, which
took 74 s on the loaded machine; the readers take the values from the arrays' buffers instead.

**Size and speed** (`_rap_l12_n144`, 6 h, 56 receivers, 62 satellites; Chromium, page served locally):

| Quantity | Value |
| --- | --- |
| build | 39 s |
| page | 22.1 MB: core 6.3, line of sight 10.1, satellites 2.7, receivers 2.2, quality 0.3, epoch 0.1 |
| overview ready | 0.9 s after the page loads (the epoch, receivers and satellites blocks decode in 0.12 s) |
| line-of-sight block | decodes in 0.24 s the first time a line of sight or the atmosphere is opened |
| a layer drawn | overview 0.19 s, satellites 0.15 s, atmosphere 0.14 s, receivers and slips 0.08 s, stochastic model 0.04 s, the rest below 0.03 s |
| a time step | about 4 ms |
| memory | about 44 MB |

**Verification.** 27 unit tests pass, 7 of them new (the table reader, the round trip of the step coding, receiver
residuals, line-of-sight slots and steps, the epoch and satellite blocks, the quality block, missing parts named per
layer). Every view of `_rap_l12_n144` was drawn in headless Chrome with no error. The plain-word check covers every
page file.

**Limits.**
1. The receiver phase bias needs `network.trace_rpb_states` (not traced in `_rap_l12_n144`).
2. The line-of-sight block grows with the run: about 10 MB per 6 h, so a 24 h page would be about 60 MB. Nothing is
   thinned yet.
3. The items of section 7 remain.

**Decisions, for review.**
1. One file per run with its data in blocks decoded on first use, so a page still opens by double-click and can be
   sent; a folder of files or a local server was not taken.
2. Event families: cycle slips and gaps, signals and channels, whole numbers, tree and datum, quality tests,
   atmosphere, satellites and clocks, other. A slip counts once per response (the rows of the loss-of-lock,
   Melbourne-Wubbena, geometry-free and time-difference tests, without the repeated and diagnostic geometry-free
   rows), so the slips of the layers differ from the Slips lane of the time bar, which also holds wind-up restarts.
3. Matrices order their rows worst first by the run median (by the total for counts); the receivers layer offers
   name order.
4. Colours: viridis for magnitudes and counts, vik for signed values (wet delay, offsets, variance factors on a log
   scale), one colour per constellation for tracks.
5. `arm` is unchanged: the reference configurations already switch on every trace the new layers read.

**Open questions.**
1. Which metrics the overview's matrices should open with (now: post-fit code residual RMS for both).
2. Whether runs over 6 h should get a thinned line-of-sight block (every second or fourth epoch).
3. Whether the first page design should remain a separate output (it lives on as the network links layer).

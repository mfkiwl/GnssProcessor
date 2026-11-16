# NRF part 5: the formal-sigma pairs with the bad-epoch response on (sections 27 onwards of card NRF)

**STATUS**

- **id:** NRF-part5
- **topic:** network-vehicle
- **status:** open
- **summary:** Sections 27 onwards of card NRF (2026-11-15). Section 27: stage O2's formal-sigma pairs (Galileo L1X/L5X held on DOY 144 with the odds at the formal sigma) re-run with the bad-epoch response of card BER on, pre-registered, with the bars of stage O2 unchanged; a holding run with the response on is added for the user replays. 2026-11-15, results (section 28): with the response on, the formal-sigma pairs agree on every held integer (0 failing of 155 633 checks between two receivers, 0 of 131 369 between two starts, against 13 008 and 13 344 without it), every epoch emitted, RAIM 7 against 7 (15 to 17 without the response), the holding share unchanged (82 to 87 % from hour 2). Section 29: what a cut-release row is (one cut of one band's tree edge) and how much the releases erase (about 2 300 carried arc entries per hour on DOY 144, about every carried entry once per hour), for remedy (a). Section 30: the second day (DOY 145) at the formal sigma with the response, pre-registered, with the author's rule of 2026-11-15: adopt the faster setting if it passes. 2026-11-15, its results (section 31): the second day FAILS the same-start audit on one wide-lane decision (Galileo E18 at STHL00GBR and LMMF00MTQ in the GOPE00CZE run, decided at wide-lane fractions of 0.16 to 0.17; 271 failing of 134 717 checks, GPS 0 of 90 261), the two-start audit, emission, releases and RAIM pass; nothing is adopted and twice the formal sigma stays; the same pair with the slip response alone fails identically. Section 32: the failure is one start-up pin pair of the chain (BOGT00COL-E18, an uncertified re-host 15.5 min after the cold start, against STHL00GBR-E18 held), not the gate; section 31.4's reading is corrected; `network.ring_fix.sigma_scale` is not adopted, the formal sigma with the full response is the run setting. Section 33: the departing arc pair holds but not its cause: the start-up pin renewed E18's frame (a gauge); the slant ionosphere at the pinned arc parts by about one lane between the two reference receivers' runs from TOW 94560 to 96540 (key-off runs too), and STHL00GBR-E18 is born and held inside that window; pins set from floats counted against their lane on DOY 144 and 145; the remedy for the mechanism found is proposed, not built.
- **source:** [NRF part 4](NRF_network_ring_fixing_2026-11-14_part4.md) sections 21 to 23 (stage O2, its bars and the formal-sigma failures); [BER](BER_bad_epoch_response_2026-11-15.md) (the response, `network.amb_float_drop_jump_k`); the requesting session's review of 2026-11-15

**Outcome.** Question: the formal-sigma runs of stage O2 failed the agreement audit (13 008 of 151 698 checks between two reference receivers, 13 344 of 92 547 between two starts), and the requesting session traced 13 of the 18 departing links to wet-delay recoveries after slips at CPVG00CPV (TOW 3990) and MRO100AUS (TOW 7800). Card BER's response removes the spread of the MRO100AUS slip. With it on, do the formal-sigma pairs agree, with every epoch emitted and no RAIM excess? Yes on this bed: 0 failing checks between receivers and between starts, every epoch emitted, RAIM 7 rows in every run, while the formal sigma keeps its holding share (82 to 87 % from hour 2, against 33 to 65 % at twice the formal sigma). Standing: one bed, `sigma_scale` 2 unchanged.

## 27. 2026-11-15: the formal-sigma pairs with the response on (pre-registered)

**Why.** The requesting session's review of stage O2: most formal-sigma failures are not the sigma; they sit inside a wet-delay recovery after a slip, and a wrong hold then keeps the wet delay wrong for hours. Card BER found that the slip's spread comes from the float vehicle's drop and built a response that removes it at MRO100AUS on this bed (BER section 9). The CPVG00CPV case (a slip on G20 at TOW 3990 with a chain re-host and a cut release of 26 arcs) is open: the response acts only where a band's measured step exceeds the birth variance.

**Arms** (exe nrf12, branch `irdu/user-integers`): copies of stage O2's arms with only `network.amb_float_drop_jump_k` 1 added: `o2s1j_n144` (default receiver, start 0), `o2s1j_n144r` (GOPE00CZE, start 0), `o2s1j_n144b` (default receiver, +1 h), each against a key-off run with the response on (`o2offj_n144`, `o2offj_n144r`, `o2offj_n144b`). For the user replays, `o2gj_n144`: the arm `o2g_n144` (Galileo L1X/L5X and GPS L1C/L2W held at twice the formal sigma) with the response on; its product file is kept.

**Bars (as stage O2, frozen).**
1. The same-start audit (`o2s1j_n144` against `o2s1j_n144r`) and the two-start audit (`o2s1j_n144` against `o2s1j_n144b`, the wind-up branches removed with the trace) on held integers and tree pins over every common arc: 0 failing checks, with the sizes of any failing closure; the audit on the arcs both runs start together beside the two-start one.
2. Every epoch emitted.
3. Every release named.
4. RAIM rows not above the key-off run of the same receiver and start by more than a tenth.
5. Every release by the residual monitor listed with its link and time.

**Reads.** Decisions and held shares by ring against `o2s1` and `o2s2`; the 18 departing links of section 23 (CPVG00CPV, MRO100AUS and the rest) with the response; the wet delay of CPVG00CPV and MRO100AUS across their slips.

## 28. 2026-11-15: results of section 27 (the formal-sigma pairs with the response on)

The seven arms of section 27 ran on exe nrf12 (`67ee6e666ada4c9e`), all exit 0; the same-start pair's wind-up traces are byte-identical. Grades: `_irdu_grades/nrf_o2j_*`, script `_irdu_grades/scripts_s20/grade_o2j.sh`.

### 28.1 The bars

| bar | formal sigma without the response (sections 22, 23) | formal sigma with the response |
|---|---|---|
| 1. same-start audit, default receiver against GOPE00CZE, every common arc | 13 008 failing of 151 698: FAIL | **0 of 155 633: PASS** |
| 1. two-start audit, wind-up branches removed with the trace | 13 344 of 92 547: FAIL | **0 of 131 369: PASS** |
| the same on the arcs both runs start together | 1 015 of 26 048 | 0 of 42 584 |
| held links against the tree-tree potentials (same start) | 1 failing link (CPVG00CPV-E04) | 0 |
| 2. every epoch emitted (default, GOPE00CZE, +1 h) | 720, 720, 600 | 720, 720, 600: PASS |
| 3. every release named | 109, 121, 64 | 109 (17 slip, 92 gap), 122 (24 slip, 98 gap), 98 (17 slip, 80 gap, 1 monitor): PASS |
| 4. RAIM rows against the key-off run of the same receiver and start | 15, 17, 8 against 15, 17, 8 | 7, 7, 7 against 7, 7, 7: PASS |
| 5. monitor releases | LMMF00MTQ-E28 at TOW 21150 (+1 h) | the same link at the same epoch (+1 h) |

### 28.2 Reads

- **Held share.** With the response (default receiver, start 0) by hour 20.8, 82.1, 84.4, 82.0, 86.9, 85.7 % against 21.4, 81.5, 84.3, 81.9, 87.0, 85.4 % without it and 0.5, 33.4, 60.0, 59.3, 64.8, 61.1 % at twice the formal sigma; decisions by ring unchanged (59, 62, 131, 58, 36, 10 at rings 2 to 7). The response does not change how much the formal sigma holds; it changes whether the holds agree.
- **The departing link.** CPVG00CPV-E04, decided without the response at TOW 4560 at `sigma_if` 0.166 inside the wet-delay recovery after the slip at TOW 3990 (section 23), is decided with it at TOW 4470 (default) and 5790 (GOPE00CZE), in agreement. CPVG00CPV's wet delay at TOW 3960, 3990, 4200, 4560, 5400, 7200 and 9000 in the key-off runs: 0.215, 0.128, 0.089, 0.099, 0.120, 0.153, 0.169 m without the response; 0.213, 0.212, 0.214, 0.208, 0.196, 0.186, 0.181 m with it.
- **RAIM over 6 h:** 7 rows in every run with the response against 15, 17 and 8 without it.
- **The user-replay run** `o2gj_n144` (Galileo L1X/L5X and GPS L1C/L2W held at twice the formal sigma, the response on): 720 epochs emitted, RAIM 6, 94 releases named; its product file is kept at `runs_nom/_rap_o2gj_n144/products.txt`.

### 28.3 What section 27 says

With the response on, the formal sigma's held integers agree between the two receivers and the two starts on this bed, every epoch is emitted and RAIM falls to 7 rows in every run (15, 17 and 8 without the response), while the formal sigma keeps its holding share (82 to 87 % of the links from hour 2, against 33 to 65 % at twice the formal sigma). The formal-sigma failures of stage O2 came from the slip response's spread (card BER), not from the sigma. One bed and one day; `sigma_scale` 2 stays the setting until the author decides.

## 29. 2026-11-15: what a cut-release row is, for remedy (a) (asked by the requesting session)

Remedy (a) of section 24.3 (part 4) proposes rebasing instead of releasing the carries at a cut of known step. The requesting session asked what one `CHAIN cut_release` event row is and how many carried entries the releases erase. One row is one cut of one band's tree edge (a receiver and satellite leaving the tree on one signal), written with the count of carried arc entries it erases (`arcs=`), the receiver phase biases (`rpb=`) and the satellite phase biases (`pb=`). On DOY 144 from TOW 1800 to 9000: 313 rows at the default receiver (230 distinct cuts by epoch, receiver and satellite, the two bands counted apart) erase 4 605 carried arc entries, about 2 300 per hour, with 401 receiver and 457 satellite phase biases; at GOPE00CZE 318 rows erase 4 767 entries (about 2 380 per hour). The bad-epoch response changes none of it (the same counts without it). With about 2 240 carried entries in the network at a time (56 receivers, about 20 satellites, two bands), cut releases erase about every carried entry once per hour. A worked case on the simulator (card BER section 13.4): a re-host of one tree edge at S12000SIM (G17, TOW 265170) erases every GPS carry of that receiver, after which the arcs are re-born.

## 30. 2026-11-15: the second day at the formal sigma with the response, and the adoption rule (pre-registered)

**The author's words** (2026-11-15, verbatim, as relayed by the requesting session): "Yes, adopt the faster setting if DOY 145 passes. An improvement should be adopted/enabled. If more verification is needed, then we can work on that later, just add a simple note: this was done on [date], verified by [one run, basic], [todo: check more stations and days eventually]."

**Why.** Section 28: on DOY 144 the formal sigma with the bad-epoch response holds 82 to 87 % of the links from hour 2 and its held integers agree between receivers and starts. A second day decides whether the formal sigma with the response becomes the working setting on observed data.

**Arms** (exe nrf14 `17ec434ffd3ce88c`, commit 65d4086). DOY 145, copies of stage O3's arms (`_rap_o3g_n145[r]`, `_rap_o3off_n145[r]`) with the response as it now stands: `network.amb_float_drop_jump_k` 1, `network.amb_float_drop_gap_cover` free and `network.zwd_event_inflate_m` 0.02 (card BER sections 6 and 13). Holding runs, Galileo L1X/L5X at the formal sigma (`sigma_scale` 1): `o5s1j_n145` (default receiver, start 0), `o5s1j_n145r` (GOPE00CZE, start 0), `o5s1j_n145b` (default receiver, start 1 h later); GPS L1C/L2W held beside Galileo L1X/L5X at the formal sigma: `o5gj_n145`, `o5gj_n145r` (both receivers, start 0). Key-off runs with the response: `o5offj_n145`, `o5offj_n145r`, `o5offj_n145b`. A 10-epoch smoke passed (`o5smoke_n145`).

**Bars (as section 27, unchanged).**
1. The same-start audit (`o5s1j_n145` against `o5s1j_n145r`; `o5gj_n145` against `o5gj_n145r`, per pair family) and the two-start audit (`o5s1j_n145` against `o5s1j_n145b`, the wind-up branches removed with the trace) on held integers and tree pins over every common arc: 0 failing checks, with the sizes of any failing closure; the audit on the arcs both runs start together beside the two-start one.
2. Every epoch emitted.
3. Every release named.
4. RAIM rows not above the key-off run of the same receiver and start by more than a tenth.
5. Every release by the residual monitor listed with its link and time.

**The rule, as relayed.** If every bar passes, the formal sigma with the response is adopted in the same commit as the graded result: the working setting of every later observed-data run is the formal sigma with the response on, twice the formal sigma stays the fallback, used only when named; the ledger rows of `network.ring_fix.sigma_scale` and `network.amb_float_drop_jump_k` move from UNVALIDATED to the scoped class, in the regime of the chain posture with network integer fixing (not the regime of the goldens, which stay as they are), each with the note: "Adopted 2026-11-15 on the author's instruction. Verified by: DOY 144 and DOY 145, one network of 56 receivers, two reference receivers and two starts each (basic). To do: more stations and days; the main posture without the chain." If a bar fails, the failing links are reported as in section 23 and nothing is adopted.

## 31. 2026-11-15: results of section 30, the second day fails on one wide-lane decision

The eight arms of section 30 ran on exe nrf14 (`17ec434ffd3ce88c`), all exit 0; the same-start pairs' wind-up traces are byte-identical. Grades: `_irdu_grades/nrf_o5_*`, script `_irdu_grades/scripts_s20/grade_o5.sh`.

### 31.1 The bars

| bar | result |
|---|---|
| 1. same-start audit, Galileo L1X/L5X held (default receiver against GOPE00CZE) | **271 failing of 134 717 checks: FAIL** (closures L1X +3 at 116, L5X +4 at 155) |
| 1. same-start audit, GPS L1C/L2W held beside Galileo | **279 failing of 224 288: FAIL** (Galileo L1X +3 at 120, L5X +4 at 159; GPS 0 of 90 261) |
| 1. two-start audit, wind-up branches removed with the trace | 0 of 89 689: PASS |
| the same on the arcs both runs start together | 0 of 17 312 |
| held links against their own run's tree potentials | 0 failing in every run |
| 2. every epoch emitted | 720, 720, 600, 720, 720: PASS |
| 3. every release named | 128, 149, 80, 221, 258, each with its cause: PASS |
| 4. RAIM rows against the key-off run of the same receiver and start | 1, 1, 0, 1, 1 against 1, 1, 0: PASS |
| 5. monitor releases | LMMF00MTQ-E30 at TOW 96450 (default, GOPE00CZE, both GPS runs); LMMF00MTQ-E27 at TOW 105630 (GOPE00CZE runs); LMMF00MTQ-G13 at TOW 92610 and 92580 and KIT300UZB-G24 at TOW 99360 (GPS runs) |

Alarm families against the key-off runs (block-Baarda, MDB, congruence, anchors decoupled): 3082, 2968, 158, 2 against 3095, 2968, 166, 2 (default); 3100, 2969, 162, 2 against 3124, 2976, 167, 2 (GOPE00CZE); 2672, 2439, 114, 0 against 2693, 2432, 112, 0 (start 1 h later: MDB +7 and congruence +2).

### 31.2 The failing links, as in section 23

Every failing check is on Galileo E18 at two receivers, STHL00GBR from TOW 97290 and LMMF00MTQ from TOW 97440 to 97560, to TOW 99270 (and, for its last nine epochs, STHL00GBR's other L5X links that close through E18). No held link disagrees with its own run's tree; 173 of the 271 failing checks close through a tree link, so the two runs' frames differ at E18 by one wide-lane cycle (closures +3 on L1X and +4 on L5X: on E1/E5a one wide-lane cycle moves N1 by 3 and N5 by 4 behind a small N1 fraction). In both GOPE00CZE runs, LMMF00MTQ-E18 is decided at TOW 97080 (N1 fraction 0.056 to 0.063, wide-lane fraction 0.160 to 0.162, log-odds 37.5 to 38.4 on N1 and 31.7 to 31.8 on the wide lane) and STHL00GBR-E18 at TOW 97260 (N1 fraction 0.134 to 0.137, wide-lane fraction 0.171 to 0.172, log-odds 29.3 to 29.5 and 21.2 to 21.3). The default receiver decides STHL00GBR-E18 at TOW 96390 (N1 fraction 0.027, wide-lane fraction 0.108) and LMMF00MTQ-E18 at TOW 97410 to 97530. The default run and the run started 1 h later agree on every common arc, so the GOPE00CZE run is the odd one by the vote of three (truth is not available on observed data). At twice the formal sigma the log-odds of these decisions fall to about a quarter (5 to 10), below the gate of 13.8; stage O3, at twice the sigma, held this day with no failing check (part 4, section 26).

### 31.3 Reads

- Held share with the formal sigma and the response, Galileo L1X/L5X, default receiver, by hour: 18.3, 80.6, 87.4, 86.2, 72.6, 66.7 %; with GPS held beside it, Galileo 16.8, 80.4, 87.3, 86.3, 72.8, 66.8 % and both families together 12.3, 50.6, 52.2, 53.5, 48.2, 44.7 %.
- Decisions by ring (Galileo, default): 45, 58, 116, 72, 17, 7 and 2 at rings 2 to 9.

### 31.4 What section 30 says

The second day fails bar 1 on one wide-lane decision taken at the formal sigma, deterministic between the Galileo-only and the two-system pairs of the GOPE00CZE receiver. Under the rule of section 30 nothing is adopted: twice the formal sigma stays the setting, and `network.ring_fix.sigma_scale` and `network.amb_float_drop_jump_k` stay UNVALIDATED. The failing decision is a wide-lane decision at a fraction of about 0.17, admitted by the formal sigma's log-odds and refused at twice the sigma: the formal sigma's margin on Galileo's wide lane is thin on this day. Whether the gap cover took part is read in section 31.5, on the same pair with the slip response alone.

### 31.5 The gap cover takes no part

The same pair with the slip response alone (`o5s1k_n145[r]`: the gap cover and the inflate key removed, nothing else changed) fails identically: 271 failing checks of 134 657 on the same links, with the same decisions in the GOPE00CZE run (LMMF00MTQ-E18 at TOW 97080, STHL00GBR-E18 at TOW 97260, wide-lane fractions 0.160 and 0.173). The order 1 setting (card BER sections 13 and 15) neither causes nor prevents the failure; beside it, RAIM gives 5 rows in each run with the slip response alone against 1 with the gap cover.

## 32. 2026-11-15: the second day's failure is a start-up pin pair, not the gate (correction of section 31.4)

**The requesting session's re-grade** (its outputs in `presentation/agu26/fixing_control/grades_arnd/o5/`): two starts with the wind-up branches removed, L1X 0 of 45 430 and L5X 0 of 44 745 (arcs born together 0 of 9 258 and 0 of 8 188); GPS L1C/L2W held beside Galileo, same start, L1C 0 of 45 426 and L2W 0 of 45 367, with 48 765 and 49 742 held link-epochs (GPS agrees); Galileo L1X/L5X same start, L1X 428 failing of 67 667 and L5X 476 of 67 675 by its walk, all in the fourth hour, closures -3 / +3 on L1X and -4 on L5X. Its attribution tool, which does not depend on the walk (potentials by majority, then the arcs that depart), finds ONE arc pair, 68 epochs per band from TOW 97260 to 99270: BOGT00COL-E18 against STHL00GBR-E18, closure (+3, +4).

**Checked against this card's traces, the attribution holds.** BOGT00COL-E18 is a tree pin in both start-0 runs, set at TOW 87330, 15.5 min after the cold start, by an uncertified re-host carrying its float (`rehost_carry`, row `RehostUncertified`), at (-6, 17) in the default run and (23, 42) in the GOPE00CZE run; the same pins stand in the key-off runs (`o5offj_n145[r]`), so they are the chain's own, not the fixing's. In the run started 1 h later the arc enters as a birth (target 0), with no start-up rounding. No held link disagrees with its own run's tree (section 31.1), and 173 of the 271 failing checks of this card's walk close through a tree link. Each run's decision on STHL00GBR-E18 sits inside its own lane (wide-lane fraction 0.108 in the default run, 0.172 in the GOPE00CZE run); the departure starts when the second run holds the arc and closes the loop through the two pins. One of the two start-up pins was rounded onto the neighbouring (3, 4) lane of Galileo E1/E5a (one wide-lane cycle with N1 moved by 3, which keeps the ionosphere-free phase within 5.6 mm and moves the ionosphere 0.565 m on L1); the requesting session's reading is that 15 min after a cold start the float's ionosphere-like uncertainty is comparable to half that spacing, which the next order counts. By the vote of three (the later start agrees with the default run on every common arc) the GOPE00CZE pin is the one on the neighbouring lane; without truth this stays a vote.

**Correction.** Section 31.4 read the failure as the gate's margin ("admitted by the formal sigma's log-odds and refused at twice the sigma"). That reading is wrong: the failing quantity is a start-up pin of the chain, and twice the formal sigma would only leave the loop open (STHL00GBR-E18 not held in one run), with the two pins still a lane apart. Section 31 stands as written and is read with this correction.

**Decision (the requesting session's).** Bar 1 fails by the letter, so `network.ring_fix.sigma_scale` is not adopted in the ledger; that judgment goes to the author. The working setting of every later observed-data run is the formal sigma with the full response, as a run setting, not a ledger change; twice the formal sigma is the fallback when named. Recorded result of section 30: bar 1 fails on one start-up pin pair; the other audits read zero; GPS agrees. The pin's lane is the next order.

## 33. 2026-11-15: the pin lane (the requesting session's order 1), the attribution re-read and the counts

### 33.1 The attribution, re-read against this card's traces

The departing arc pair of section 32 holds (BOGT00COL-E18 against STHL00GBR-E18, closure (+3, +4)), but the traces do not support the start-up rounding as its cause:

- **The pin at TOW 87330 is a fresh frame for E18.** The uncertified re-host that set it (E18 leaving KOKV00USA for BOGT00COL) released E18's satellite phase bias with its one carried arc (`cut_release ... arcs=1 rpb=0 pb=1 n_rx=0 n_sat=1`) and declared E18's keys moved (`declared_keys E18 ... cause=rehost`), the same in all four start-0 runs. A pin on a vertex whose frame is renewed is a gauge choice: integer shifts of one satellite's phase biases per band leave every observation unchanged, so its lane alone cannot change a double-difference closure.
- **What parts the runs is physical.** The slant ionosphere at the pinned arc BOGT00COL-E18 (`iono_total_m`, frame-free) is the same in the four runs to within 0.02 m until TOW 94560; the two reference receivers' runs then part, gradually, by 0.42 m at TOW 94950 and 0.61 to 0.67 m by TOW 96540 (default 5.46 m, GOPE00CZE 4.86 m), and rejoin by TOW 102180 (difference 0.03 m). The key-off runs part identically, so this is the chain's estimation, not the fixing. No chain event touches E18 or BOGT00COL-E18 between TOW 92550 and 96540 (the events at TOW 90090 and 92550 are the same in both runs). At STHL00GBR-E18 and LMMF00MTQ-E18 the two runs stay within 0.05 and 0.2 m before their holds.
- **The hold falls inside the window.** STHL00GBR-E18 is born at TOW 94890, inside the window, and is held at TOW 96390 (default) and 97260 (GOPE00CZE), each inside its own lane but with the pinned arc's ionosphere-like level of its run about one lane apart: with BOGT00COL-E18's integers fixed, a drift of E18's ionosphere-like level moves the pinned arc's slant ionosphere and the new arc's float, and the hold freezes the drift into a (3, 4) closure. The (3, 4) lane is 0.565 m of L1 ionosphere, the size of the drift.
- A lead, not a conclusion: block-Baarda flags the block (BOGT00COL, E18) in all four runs from TOW 92100 (the requesting session's read), which a code fault on that arc would explain; with the arc's integers pinned, only its code ties its slant ionosphere to the data.

So the departing quantity is the ionosphere-like level of E18 at its pinned arc while E18's ionosphere-like information is thin, not the start-up rounding; twice the formal sigma would only delay or avoid the hold.

### 33.2 The counts: pins set from a float against their lane

`scripts/nrf_pin_lane.py` (new): at every pin the chain sets by rounding a float (row `RehostUncertified`), the arc's chord row at the last epoch before it (`network_chain_frame.csv`: the two floats and their conditional covariance) gives the float's standard deviation along the family's near-degenerate lane pair, in units of the lane spacing (s = sqrt(d' Q d)/(d' d)). The lane pairs: Galileo E1/E5a (3, 4), ionosphere-free cost 5.6 mm, one wide-lane cycle, 0.565 m of L1 ionosphere; GPS L1/L2 (7, 9), ionosphere-free cost 6.3 mm, two wide-lane cycles, 1.338 m of L1 ionosphere (the exact GPS pair is (60, 77); (4, 5) costs 5 cm on the ionosphere-free phase and is caught by it).

| run | family | pins | s p50 | s p90 | s above 0.25 | s above 0.125 |
|---|---|---|---|---|---|---|
| DOY 144, default (`o2s1j_n144`) | Galileo L1C/L5Q | 124 | 0.174 | 0.472 | 31 | 78 |
| | Galileo L1X/L5X (held) | 126 | 0.000 | 0.000 | 9 | 11 |
| | GPS L1C/L2W | 240 | 0.068 | 0.160 | 8 | 46 |
| | GPS L1W/L2W | 191 | 0.051 | 0.149 | 7 | 24 |
| DOY 144, GOPE00CZE | Galileo L1C/L5Q | 124 | 0.174 | 0.472 | 31 | 78 |
| | Galileo L1X/L5X (held) | 119 | 0.000 | 0.149 | 9 | 14 |
| | GPS L1C/L2W | 243 | 0.069 | 0.174 | 9 | 65 |
| | GPS L1W/L2W | 184 | 0.048 | 0.129 | 7 | 21 |
| DOY 145, default (`o5s1j_n145`) | Galileo L1C/L5Q | 174 | 0.162 | 0.356 | 42 | 116 |
| | Galileo L1X/L5X (held) | 122 | 0.000 | 0.129 | 7 | 14 |
| | GPS L1C/L2W | 251 | 0.063 | 0.181 | 15 | 52 |
| | GPS L1W/L2W | 179 | 0.050 | 0.129 | 5 | 22 |
| DOY 145, GOPE00CZE | Galileo L1C/L5Q | 174 | 0.162 | 0.355 | 42 | 116 |
| | Galileo L1X/L5X (held) | 98 | 0.000 | 0.360 | 12 | 16 |
| | GPS L1C/L2W | 248 | 0.067 | 0.190 | 13 | 62 |
| | GPS L1W/L2W | 178 | 0.049 | 0.142 | 7 | 23 |

A held family's pins mostly re-host onto held chords (s about 0); a family not held re-hosts onto floats whose spread along the lane is a sizeable part of the spacing, most on Galileo E1/E5a (a quarter of its pins with the neighbouring lane within two sigmas). BOGT00COL-E18's own pin at TOW 87330 had s = 0.44 (default) and 0.37 (GOPE00CZE), each float within 0.06 spacings of its rounded lane. The simulator's fixing control shows the same early in its cold start (`e1chj13`: Galileo L1C/L5Q 10 of 45 pins above 0.25, GPS 6 of 68).

### 33.3 The remedy, not built

The two remedies of the order (a pin not rounded while its ionosphere-like sigma exceeds a part of the lane spacing; a pin contradicted by held links moved by the lane pair) act on the start-up rounding, which section 33.1 does not find at fault: the pin renewed E18's frame. The narrowest remedy for the mechanism found is an event, as standing invariant 7 asks: a vertex whose ionosphere-like level at a pinned arc moves by more than a set part of its family's lane spacing within the window (here 0.6 m in about 30 min against a spacing of 0.565 m) opens the window of every link of that vertex, so no decision is taken while the level moves. A simulator test needs a bed whose code drives one satellite's ionosphere-like level (a code fault on one pinned arc). Not built: the requesting session chooses, given the re-read.

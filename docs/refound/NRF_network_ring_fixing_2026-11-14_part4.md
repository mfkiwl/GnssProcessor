# NRF part 4: stage O2, integers held on observed data (sections 21 onwards of card NRF)

**STATUS**

- **id:** NRF-part4
- **topic:** network-vehicle
- **status:** open
- **summary:** Sections 21 onwards of card NRF (2026-11-15). Section 21: stage O2 pre-registered, the first runs that hold integers on observed data (Galileo L1X/L5X, the bed of DOY 144, two starts, the odds computed with one and with two times the formal sigma), with the build it needs: `network.ring_fix.sigma_scale` and the wind-up arc trace `network.trace_windup_arcs`, which lets the two-start audit cover every common arc. Section 22: the results. With the odds at twice the formal sigma the two starts agree on every held integer (0 failing of 78 588 checks over every common arc), every epoch emitted, RAIM unchanged, about 60 % of the chord link-epochs held from hour 3; with the formal sigma (the rule as pre-registered) the audit fails (13 344 of 92 547; 7 held links: three young-network decisions, four L5X closures after a re-seat). The wind-up trace matches truth exactly on the simulator. The audit's failing counts depend on its walk (fixed to a sorted walk; earlier raw counts re-read), its verdicts do not. Section 21.1: amended on the requesting session's word (same-start pairs with another reference receiver, a GPS and Galileo arm). Section 23: with twice the formal sigma every pairing agrees on every held integer (two receivers at one start, 0 of 82 972; GPS L1C/L2W held beside Galileo, 0 of 126 238); with the formal sigma the late run and the GOPE00CZE run depart from the others (early decisions, one a wrong wide lane behind a perfect N1 fraction), and 22.4's attribution to run A is corrected to run B. Section 24: stage G0 (reads): deep GPS links open their event window twice as often as Galileo links, often at cut releases of known step 0, and their fractions are one term per receiver plus one per satellite (the frame carries each tree arc's own error); remedies proposed. Section 26: O3 on DOY 145 agrees across two receivers (0 of 122 609); O4, every family held, does not pass (Galileo L1C/L5Q departs after an uncertified re-host of E14, GPS L1C/L2W departs in one run, GPS L1W/L2W cannot hold beside L1C/L2W on one L2W root); RAIM rows exceed the key off in three holding runs; a third frequency assessed.
- **source:** [NRF part 3](NRF_network_ring_fixing_2026-11-14_part3.md) sections 19 and 20; the requesting session's messages of 2026-11-15 (its log-only pilot on the same bed, exe nrf7, four starts)

**Outcome.** Question: on observed data, does the ring fix hold only integers that two runs with different starts agree on, with every epoch emitted and no RAIM excess? With the odds at twice the formal sigma, yes on Galileo L1X/L5X over 6 h of DOY 144: 0 failing of 78 588 checks over every common arc, the wind-up branches removed from a new trace of the stations' accumulators, every epoch emitted, RAIM unchanged. Also between two reference receivers at one start, and with GPS L1C/L2W held beside Galileo (0 of 126 238). With the formal sigma, no. A second day (DOY 145) agrees too; holding all four pair families on DOY 144 does not, and holds raise RAIM rows at stations with re-entering arcs. Standing: default off; Galileo L1X/L5X and GPS L1C/L2W at twice the formal sigma on two days of observed data.

Sections 1 to 12 are in [NRF](NRF_network_ring_fixing_2026-11-14.md), 13 to 16.1 in [part 2](NRF_network_ring_fixing_2026-11-14_part2.md), 17 to 20 in [part 3](NRF_network_ring_fixing_2026-11-14_part3.md). Results are appended below, each under its dated heading.

## 21. 2026-11-15: stage O2 pre-registered (integers held on observed data, Galileo L1X/L5X)

Assigned by the requesting session after its log-only pilot (its words condensed; decided in the author's absence and listed for review). The go for holding runs on observed data is its word.

**Why, from the pilot.** The requesting session ran the log rule on the bed of DOY 144 from four starts (0, +0.5, +1 and +2 h; exe nrf7) and audited the would-be integers between the six pairs of runs. Over every common arc the audit failed, mostly by one N1 cycle on both bands; with the arcs restricted to those both runs start together (section 19.5), the rule as built passes on Galileo L1X/L5X: 0 failing of 12 756 checks over all rings (0 of 4 457 with the odds at twice the formal sigma). Galileo L1C/L5Q: 6 failing of 8 770, all wide-lane cycles of one pair of runs (0 of 3 819 at twice the formal sigma). GPS: too few would-be decisions on common young arcs to judge. What stays real from the all-arc audit is the closures of size (3, 4) on L1X/L5X, a wide-lane cycle of E1/E5a that no wind-up branch can make: 41 over the six pairs with the rule as built, all in a young network's first hour on arcs alive at the later start, none with the odds at twice the formal sigma. The requesting session withdrew its interim reading (a ring cap, ring 2 only) once the branches were understood.

**Build (exe nrf9; default off, byte-identical off; ledger rows UNVALIDATED).**
1. `network.ring_fix.sigma_scale` (default 1; in [1, 100]; needs gate `odds`): the log-odds of N1 and of the wide lane are computed with this factor times their formal sigmas. The trace keeps the formal sigmas; the frozen sigma gate is unchanged.
2. `network.trace_windup_arcs` (default false): `network_windup_arcs.csv`, each station's wind-up accumulator per (station, satellite) arc: a row at the arc's start (the seed, or a restart after a gap) and a row at every epoch whose time of week is a multiple of 300 s, with the accumulated angle in cycles (an epoch observer, `network/diag/WindupArcs`; the accumulator itself gains a read-only arc-start stamp, GnssCorrections::windUpArcs). The producer starts an arc from the raw angle, in (-0.5, 0.5] cycle, so it holds no absolute branch to write; what two runs share is the angle itself: at an anchor epoch common to an arc in both runs, round(cycles_A - cycles_B) is the whole number of cycles between their integers of that arc, the same on every band, for the arc's whole common life. `scripts/nrf_two_run_audit.py --windup-trace` removes it link by link, so the audit covers every common arc that reaches an anchor in both runs.
3. Not built: the ring cap (withdrawn); keys for the 600 s event window and the 10-epoch persistence (asked in the first message, not repeated after the correction).

**Gates (simulation).** The new keys at their defaults: `nrf9_ol_nr3` against `nrf8_ol_nr3` and `nrf9_hf_r3c` against `nrf8_hf_r3c`, byte-identical. The trace checked against truth: held first on r3c from two starts with the trace on (`nrf9_hfw_r3c`, and `nrf9_hfw_r3cb` from `start_offset_hours` 0.504167 to the same end); per common link, round(cycles_A - cycles_B) equals the difference of the two runs' truth branches, and the audit with `--windup-trace` reads as it does with `--windup` (truth).

**Runs (Release, observed data: the bed of `_rap_nwa1nh_n144`; every arm with `network.trace_windup_arcs`; a 10-epoch smoke first).**
- `o2off_n144`: the key off. `o2off_n144b`: the key off from the later start (added here: the RAIM reference of the later start).
- `o2s2_n144`, `o2s2_n144b`: holding; rule gated, order certain, gate odds, `sigma_scale` 2, `wl_frac_max` 0.25, `held_first` true, pairs `["E:L1X/L5X"]`; starts 0 and +1 h (`start_offset_hours` 1.004167, the same end).
- `o2s1_n144`, `o2s1_n144b`: the same with `sigma_scale` 1 (the rule as pre-registered).
- `nrf9_log_n144`: the log rule, pairs `["E:L1X/L5X"]`, `wl_frac_max` 0.25, start 0; **gate: products byte-identical to `o2off_n144`**.

**Bars (frozen, the requesting session's).**
1. The two-start audit on held integers and tree pins, with the wind-up branches removed (`--windup-trace`): 0 failing checks for each pair (`o2s2`, `o2s1`), reported with the sizes of any failing closure; the audit on the arcs both runs start together (`--born-after`) beside it.
2. Every epoch emitted.
3. Every release named.
4. RAIM rows not above the key-off run's by more than a tenth (each start against the key-off run of that start).
5. Every release by the residual monitor listed with its link and time.

**Reads.** Held share by hour and by ring (held link-epochs over the pair family's chord link-epochs); decisions and releases by cause; re-attachments through held links; minutes from an arc's birth to its hold (`scripts/nrf_hold_reads.py`, new). A failure is traced, not explained away.

**Known limits.** An error both runs share passes the audit; the wide-lane bound is the guard there, and a slip of equal cycles on both bands does not move the wide lane (section 20.2), the residual monitor is its guard. An arc whose common life in the two runs holds no anchor epoch is not audited (counted). No truth on observed data; no users in O2.

## 22. 2026-11-15: stage O2 results

**What ran.** Exe `gnss_processor_irdu_nrf9.exe` (sha256[:16] `a18324f2ed30a1c5`, commit `5747848`: the build and section 21, committed before the observed-data runs). Grades `runs_nom/_irdu_grades/nrf_o2_*`; the scratch reads of this section in `runs_nom/_irdu_grades/scripts_s20/`. All seven observed-data runs exit 0.

### 22.1 The build's gates and the trace on the simulator

- `nrf9_hf_r3c` against `nrf8_hf_r3c`: IDENTICAL (`scripts/nom_td_gate.py`, 50 items). `nrf9_ol_nr3` against `nrf8_ol_nr3`: products, every trace, the run manifest, the run-end block, `rt_engine.log` and the exit code identical; the arm file differs only in the bed's RINEX paths (the bed's files live in the base run's folder and were read from there).
- Smoke `o2smoke_n144`: 11 epochs emitted, every arming line present, the trace writing arc starts and anchors.
- The trace against truth (`nrf9_hfw_r3c`, and `nrf9_hfw_r3cb` from +0.5 h): every traced arc start equals the truth model's raw angle, wu - floor(wu + 0.5) (1 391 starts, max 1e-6 cycle); for each of the 654 arcs common to both runs at an anchor, round(cycles_A - cycles_B) equals the difference of the truth branches (-1 at 6 arcs, 0 at 639, +1 at 9). The audit on held integers and tree pins: raw 2 274 failing of 36 208 checks; with the truth branches removed 0; with the trace 0 (16 links without a common anchor, dropped); on the arcs both runs start together 0 of 744.
- Tests: the 179 tests of the affected suites pass, the four new ones among them; `scripts/nom_epoch_lint.py` and `scripts/nom_n4_verify.py --whole` pass. The Debug suite of the previous build (`f3e1a1c`): 4 296 passed, 37 skipped (fixture-gated), 0 failed.

### 22.2 The bars

The byte-identity gate: `nrf9_log_n144` against `o2off_n144`, products byte-identical (389 291 lines): PASS; and the products of `o2off_n144` equal those of `nrf8off_n144` (the trace changes no product).

| bar | o2s2 (odds at 2 sigma) | o2s1 (formal sigma, as pre-registered) |
|---|---|---|
| 1. two-start audit, wind-up removed with the trace | **0 failing of 78 588 checks: PASS** | **13 344 failing of 92 547: FAIL** |
| the same on the arcs both runs start together | 0 of 21 684 | 1 015 of 26 048 |
| 2. every epoch emitted (start 0 / start +1 h) | 720 / 600: PASS | 720 / 600: PASS |
| 3. every release named | 54 / 47, each with its cause, both closures closed: PASS | 109 / 64: PASS |
| 4. RAIM rows against the key off of the same start (15 / 8) | 15 / 8: PASS | 15 / 8: PASS |
| 5. monitor releases | none / LMMF00MTQ-E28 at TOW 21150 | none / the same link at the same epoch |

Both pairs drop 56 link-band-epochs without a common anchor; no two common anchors of an arc disagree. The failing closures of o2s1, by band and size: L1X -1 at 4 355, +1 at 447, +3 at 264; L5X -1 at 7 767, +1 at 247, +4 at 264.

**The failing counts depend on the walk.** With failures, the number of failing checks depends on the spanning tree the breadth-first walk takes. The first version of `scripts/nrf_two_run_audit.py` walked in the set order of Python, which changes from process to process (o2s1 read 13 225, 9 034, 10 824 and 8 047 failing on the same files); it now walks in sorted order, and the counts here are that walk's. A count of 0 does not depend on the walk, so every verdict of sections 19.5 and 20 stands, but their raw failing counts do: with the sorted walk, the raw audit of N3b reads 67 540 failing of 512 298 (section 20.1: 125 386), that of O1 1 878 of 30 908 (section 20.4: 3 456) and the simulation check 2 274 (first walk 7 844). A count of the failures that does not depend on the walk is the attribution of 22.4.

### 22.3 Reads

Held share by hour of the bed (held link-epochs over the Galileo L1X/L5X chord link-epochs, %):

| hour of the bed | 1 | 2 | 3 | 4 | 5 | 6 |
|---|---|---|---|---|---|---|
| o2s2, start 0 | 0.5 | 33.4 | 60.0 | 59.3 | 64.8 | 61.1 |
| o2s2, start +1 h | not run | 0.7 | 33.9 | 55.5 | 63.9 | 60.8 |
| o2s1, start 0 | 21.4 | 81.5 | 84.3 | 81.9 | 87.0 | 85.4 |
| o2s1, start +1 h | not run | 16.5 | 49.3 | 47.9 | 65.6 | 70.8 |

- **By ring** (start 0): o2s2 ring 2 63.6 %, ring 3 50.0, ring 4 49.3, ring 5 35.6, ring 6 33.4, ring 7 26.2; o2s1 82.1, 70.7, 73.5, 77.8, 64.3, 74.3.
- **Decisions** (start 0 / +1 h): o2s2 244 / 211 (238 / 210 links), the first at TOW 2910 (48.5 min after the start) / 5880 (37.5 min); o2s1 356 / 269 (331 / 262 links), the first at 1050 (17.5 min) / 4710 (18 min).
- **Releases by cause** (start 0 / +1 h): o2s2 gap 48, slip 6 / gap 44, slip 2, monitor 1; o2s1 gap 92, slip 17 / gap 54, slip 8, refloat 1, monitor 1.
- **Re-attachments through held links**: o2s2 93 keeping 731 held links / 64 keeping 487; o2s1 114 keeping 1 117 / 83 keeping 834. Every held-first cut had a step of 0 (161, 114, 196 and 146 cuts); no usable held link was released across an unknown step.
- **Minutes from an arc's birth to its first hold** (from the tracking arc's start, p50 and p90): o2s2 73.5 and 120.5 / 70.5 and 111.5; o2s1 30.0 and 62.5 / 39.0 and 149.0. Arcs that start inside the run: o2s2 64.0 and 105.5 / 63.0 and 107.5; o2s1 22.5 and 52.5 / 37.0 and 147.5.
- **The monitor release** (both late starts): LMMF00MTQ-E28, held at -13, -96 since TOW 7650 (o2s2) and 5640 (o2s1), released by the residual monitor at TOW 21150. Its ionosphere-free residual rose smoothly, 0.014, 0.020, 0.031, 0.032, 0.033 and 0.036 m from TOW 20970, while E28 set through 16 degrees of elevation with no step in the MW or the GF combination; at TOW 21030 block-Baarda flags E28 and E31 at LMMF00MTQ and the congruence test a coordinate offset there, in the log run of O1 as well (nothing held). A disturbance of the observed data at that station, seen by the monitor; after the release the float N1 of the link sits near -12.5 (no integer), and the arc ends at TOW 21270.

### 22.4 The failures of o2s1, traced

- **Attribution, independent of the walk** (scratch `o2_fail_trace.py`): per epoch and band, the potentials of the two frames from the links that are tree links in both runs (a forest, so the potentials are unique), and every link held in either run checked against them. 7 held links fail, of 25 290 link-band-epochs checked; o2s2: 0 of 43 115.
  - GAMB00PYF-E12: 264 epochs, bed hours 2.4 to 4.6, closure (-3, -4), a wide-lane cycle of E1/E5a. Run A decided it at TOW 1800 (30 min after its start) at frac_if 0.152, sigma_if 0.126 cycle, log-odds 22.1; run B at TOW 4980 at frac_if 0.005, sigma_if 0.109, log-odds 41.9.
  - LMMF00MTQ-E10: 218 epochs, hours 2.4 to 4.2, closure (+1, +1), one N1 cycle. Run A at TOW 1560 (26 min) at frac_if 0.170, log-odds 29.6; run B at 5010 at frac_if 0.155, log-odds 15.6.
  - LMMF00MTQ-E11: 150 epochs, hours 3.0 to 4.3, (+1, +1). Run A at TOW 1530 (25.5 min), frac_if 0.092, log-odds 21.8; run B at 7350, frac_if 0.150, log-odds 84.0.
  - CPVG00CPV-E31, -E28 and -E16 (114, 86 and 33 epochs) and WIND00NAM-E28 (28): hours 6.0 to 7.0, closures on L5X alone (+1, +1, +1, -1).
- **Reading.** The three failures on both bands are decisions of a young network: run A took them in its first 30 min, where the formal-sigma odds pass links at fractions of 0.09 to 0.17 cycle (the finding of the requesting session's pilot, that the formal sigma of N1 is too small on observed data, holds in a holding run). The failures on L5X alone cannot be decisions: the gate fixes the wide lane before N1, so a decided link differs on both bands at once. They begin at TOW 18180, when a loss-of-lock slip on CPVG00CPV-E19 (L5X, then L1X an epoch later) de-seated the tree link of CPVG00CPV in run A and the chain re-attached CPVG00CPV through the held link CPVG00CPV-E04, while in run B E19 hung below CPVG00CPV and re-hosted to POVE00BRA and YKRO00CIV. With twice the formal sigma CPVG00CPV-E19 was a held link, released by that slip, and no closure failed. Which frame is wrong at CPVG00CPV after the re-seat is not traced.

### 22.5 What O2 says, and decisions for the author's review

1. On observed data, with the odds at twice the formal sigma, the ring fix held only integers that two starts agree on: Galileo L1X/L5X, 0 failing of 78 588 checks over every common arc, 238 links held in 6 h, about 60 % of the chord link-epochs held from hour 3, every epoch emitted, RAIM unchanged. With the formal sigma (the rule as pre-registered) the two starts disagree on 7 held links: three young-network decisions and four L5X closures after a re-seat.
2. The wind-up arc trace makes the two-start audit cover every common arc on observed data (78 588 checks against 21 684 on the arcs born together), and it matches truth exactly on the simulator.
3. The setting that passed (sigma_scale 2) is a candidate, not a verdict: one bed, one pair of starts. Decided here, for review: the RAIM reference run of the late start (`o2off_n144b`) was added; the walk of the audit was fixed after the first reads and the counts read again.
4. Still open: the event-text defect of section 20.4 (`ring=-1` in `would_hold` events); keys for the event window and the persistence, not built.
5. Asked for an opinion, not a build: a chain that takes the most mature candidate as a new tree link. A near equivalent exists as default-off keys, `network.eq34_anchor_min_arc_ep` (a minimum arc age for a re-host candidate; first sightings never gated) and `network.eq34_fresh_pin_sigma_scale` (a softer pin on a young host), both UNVALIDATED on this posture, so a test is an arm, not a build. The caution of the record: the longevity election and the slip-aware election (`network.phase_datum_eq34_longevity_election` and `network.phase_datum_eq34_slip_aware_election`, both KEEP_OFF, measured harmful) changed which edge the chain takes and did harm. With held first armed, held links (mature by construction) are already taken first, so such a gate acts only on unheld choices; the L5X closures of 22.4 followed a re-attachment through a held link, which a maturity gate would not change.

### 21.1 2026-11-15: O2 amended (the requesting session's word): same-start pairs, and the first GPS and Galileo holding run

Received after section 22's runs (its words condensed). Two runs from the same start with different reference receivers share every arc's wind-up branch, so their audit covers every arc without a trace; the requesting session's same-start log pilot (`_rap_mgr_log_n144` against `_rap_mgr_log_n144r`, `network.phase_datum_eq34_receiver` GOPE00CZE, exe nrf7, the rule as built, the wide-lane bound applied offline) reads 0 failing of 25 771 checks on Galileo L1X/L5X over every common arc and epoch, 45 of 12 428 on GPS L1C/L2W (one link, SGOC00LKA-G13, wide lanes one cycle apart; 0 of 8 577 with twice the formal sigma) and 225 of 28 790 on Galileo L1C/L5Q (the links of E03 at DARW00AUS, SOLO00SLB and PARK00AUS, one cycle on both bands from 2.12 h).

**The E03 case and the wind-up branch, read before these runs.** In the trace of `o2off_n144` (same bed, same start), the accumulators of DARW00AUS-E03, SOLO00SLB-E03 and PARK00AUS-E03 start at TOW 0 and never restart (DARW00AUS-E03 moves smoothly from 0.018 to 0.071 cycle between TOW 6600 and 8700). The accumulator restarts only at a gap of at least its horizon or an epoch out of order (GnssCorrections::computePhaseWindUp); nothing in a refloat, a re-host or the datum touches it. Two runs from one start therefore carry the same branch on every arc, and the one-cycle step of E03 is not a wind-up branch: it is a frame move in one run or a real step.

**Added runs (exe nrf9, Release, observed data, every arm with the trace; the +1 h runs of section 22 are kept).**
- `o2s2_n144r`, `o2s1_n144r`: the holding arms of section 21 (Galileo L1X/L5X, sigma_scale 2 and 1) from start 0 with `network.phase_datum_eq34_receiver` GOPE00CZE. Audit pairs: `o2s2_n144` with `o2s2_n144r` and `o2s1_n144` with `o2s1_n144r`, on every common arc.
- `o2off_n144r`: the key off with the same receiver (the RAIM reference of the `r` runs).
- Optional, after the Galileo arms: `o2g_n144` and `o2g_n144r`, the first holding runs on two systems: sigma_scale 2, `wl_frac_max` 0.25, held first, pairs `["E:L1X/L5X", "G:L1C/L2W"]`, from start 0 with the default receiver and with GOPE00CZE. Why now: in log mode GPS L1C/L2W decides little beyond ring 2 (would-hold share by ring 27, 9, 2 and 1 %); whether holds at ring 2 let deeper rings follow under held first only a holding run shows.

**Bars (as section 21, frozen).** The audit of each same-start pair on held integers and tree pins over every common arc: 0 failing checks, reported per band with the sizes of any failing closure (the trace-corrected audit beside it, which must find a whole-cycle difference of 0 on every arc); every epoch emitted; every release named; RAIM rows not above the key off of the same receiver by more than a tenth; every release by the residual monitor listed. **Reads** as section 21, per pair family for `o2g`.

## 23. 2026-11-15: O2's added runs (amendment 21.1) and a correction to 22.4

**What ran.** Exe nrf9 (`a18324f2ed30a1c5`, commit `5747848`; the amendment committed as `f938457` before these runs): `o2s2_n144r`, `o2s1_n144r`, `o2off_n144r`, `o2g_n144`, `o2g_n144r`, all exit 0, 720 epochs each. Roots: the default receiver gives Galileo L1X/L5X at BOGT00COL and GPS L1C/L2W at BOR100POL; `network.phase_datum_eq34_receiver` GOPE00CZE gives both at GOPE00CZE. Grades `runs_nom/_irdu_grades/nrf_o2r_*`.

**The wind-up branch belongs to the receiver and the satellite, not to the datum.** In each same-start pair the two runs' wind-up traces are byte-identical, and the trace-corrected audit finds a whole-cycle difference of 0 on every arc (no link dropped): two runs from one start compare every arc as they stand.

### 23.1 The bars of the same-start pairs (receivers default and GOPE00CZE, start 0)

| bar | o2s2 pair (2 sigma) | o2s1 pair (formal sigma) | o2g pair (2 sigma, GPS and Galileo) |
|---|---|---|---|
| 1. audit over every common arc | **0 failing of 82 972: PASS** | **13 008 of 151 698: FAIL** | **0 of 126 238: PASS** |
| by band | L1X 0 of 41 500, L5X 0 of 41 472 | L1X 4 803 of 75 626, L5X 8 205 of 76 072 | E L1X 0 of 42 918, E L5X 0 of 42 960, G L1C 0 of 20 180, G L2W 0 of 20 180 |
| 2. every epoch emitted | 720 / 720 | 720 / 720 | 720 / 720 |
| 3. every release named, closures closed | yes | yes | yes |
| 4. RAIM rows (key off: 15 default, 17 GOPE00CZE) | 15 / 17: PASS | 15 / 17: PASS | 13 / 16: PASS |
| 5. monitor releases | none | BOGT00COL-E11 at TOW 17550 (GOPE00CZE run) | none |

### 23.2 Which run is the odd one: the formal-sigma runs against the 2-sigma runs of the same start and receiver

The audit between the two rules at one start and one receiver says which run of a failing pair departs from the others:

| pair (same start, same receiver) | checks | failing | failing held links (attribution of 22.4) |
|---|---|---|---|
| `o2s1_n144` against `o2s2_n144` (start 0, default) | 104 457 | 0 | 0 of 56 069 link-band-epochs |
| `o2s1_n144b` against `o2s2_n144b` (start +1 h, default) | 62 335 | 7 316 | 11 |
| `o2s1_n144r` against `o2s2_n144r` (start 0, GOPE00CZE) | 99 309 | 11 867 | 7 |

The start-0 formal-sigma run with the default receiver agrees with every 2-sigma run (directly with `o2s2_n144`, and through it with `o2s2_n144b` and `o2s2_n144r`, whose pairs pass). The odd runs are the late formal-sigma run and the formal-sigma run with GOPE00CZE:
- `o2s1_n144b` (start +1 h): 11 links depart, among them GAMB00PYF-E12, a wide-lane cycle (+3, +4), decided 22 min after the run's start (TOW 4980) at frac_if 0.005, sigma_if 0.109 and log-odds 41.9: an N1 fraction that looks perfect over a wrong wide lane, the E1/E5a case of section 19.3; LMMF00MTQ-E10 (-1, -1), decided 23 min after the start at log-odds 15.6; and a cluster at CPVG00CPV (E31, E28, E19, E23, one N1 cycle each, from TOW 8460).
- `o2s1_n144r` (GOPE00CZE): 7 links depart, a cluster at CPVG00CPV (E04, E31, E06, E09, one N1 cycle, from TOW 7380; E28 and E23 after TOW 18180) and MRO100AUS-E27. Its CPVG00CPV-E04 was decided at TOW 4560 at sigma_if 0.166 and log-odds 15.5, which twice the formal sigma refuses (log-odds 3.9); the 2-sigma run held that link at 7350, consistently with both default-receiver runs.

**Correction to 22.4.** Its reading named run A's first 30 min as the source of the three failures on both bands; the audit against the 2-sigma runs shows run A's holds of GAMB00PYF-E12, LMMF00MTQ-E10 and LMMF00MTQ-E11 agree with three other runs, and the departing integers are run B's, decided in run B's first 23 min. The reading's substance stands with the runs exchanged: the failures are early decisions of the younger network under the formal sigma. The L5X-only closures of 22.4 at CPVG00CPV are the comparison of run A with run B's CPVG00CPV cluster after run A re-attached CPVG00CPV at TOW 18180 through two different held links (CPVG00CPV-E04 on L5X, CPVG00CPV-E06 on L1X at 18210), not an error introduced by that re-attachment.

### 23.3 Reads

Held share by hour (Galileo L1X/L5X chord link-epochs, %):

| run | 1 | 2 | 3 | 4 | 5 | 6 |
|---|---|---|---|---|---|---|
| o2s2_n144r (2 sigma, GOPE00CZE) | 3.6 | 28.0 | 48.4 | 56.7 | 57.9 | 63.3 |
| o2s1_n144r (formal sigma, GOPE00CZE) | 22.2 | 74.6 | 83.7 | 81.7 | 86.2 | 79.7 |
| o2g_n144, Galileo L1X/L5X | 0.5 | 33.0 | 60.2 | 60.0 | 65.0 | 61.2 |
| o2g_n144, GPS L1C/L2W | 0.7 | 8.8 | 12.0 | 16.6 | 25.2 | 21.0 |
| o2g_n144r, Galileo L1X/L5X | 3.6 | 29.5 | 51.7 | 58.9 | 59.1 | 65.3 |
| o2g_n144r, GPS L1C/L2W | 1.2 | 13.1 | 16.3 | 18.9 | 25.0 | 16.5 |

- **GPS L1C/L2W by ring** (held share, default / GOPE00CZE): ring 2 31.4 / 40.6 %, ring 3 25.3 / 16.0, ring 4 10.2 / 8.9, ring 5 3.6 / 3.6, ring 6 2.8 / 2.7, deeper rings 0 to 3. The requesting session's log pilot (formal sigma, exe nrf7) read would-hold shares of 27, 9, 2 and 1 % at rings 2 to 5: holding with held first raises rings 3 and 4, and GPS beyond ring 4 stays near zero. The two counts differ in rule and build, so the comparison is indicative.
- **Links held**: o2s2_n144r 223; o2s1_n144r 319; o2g_n144 370 (Galileo 237, GPS 133); o2g_n144r 363 (231, 132). The Galileo shares of `o2g` match the Galileo-only runs within 1 point: holding GPS beside Galileo did not change the Galileo holds.
- **Releases** (all named): o2s2_n144r gap 51, slip 3; o2s1_n144r gap 96, slip 21, refloat 3, monitor 1; o2g_n144 gap 87, slip 10, refloat 3; o2g_n144r gap 94, slip 10, refloat 1. Re-attachments through held links: 63, 97, 141 and 120, keeping 507, 1 026, 946 and 791 held links.
- **Minutes from an arc's birth to its first hold** (p50 / p90): o2s2_n144r 63.5 / 127.5; o2s1_n144r 31.0 / 65.5; o2g_n144 76.5 / 142.5; o2g_n144r 68.5 / 138.5.

### 23.4 What the amendment says

1. With twice the formal sigma, every pairing of O2 agrees on every held integer over every common arc: two starts (0 of 78 588), two reference receivers at one start (0 of 82 972), and two receivers with GPS L1C/L2W held beside Galileo L1X/L5X (0 of 126 238, of them 40 360 GPS checks). Every epoch was emitted and RAIM stayed at the key-off level.
2. With the formal sigma, a run can be right (the start-0 default run agrees with all 2-sigma runs) or wrong (the late run and the GOPE00CZE run hold early, low-odds or wrong-wide-lane decisions that propagate to a station's other links); the rule as pre-registered is not safe on observed data.
3. GPS L1C/L2W under holds: 132 to 133 links held, a quarter to two fifths of ring 2, a sixth to a quarter of ring 3, a tenth of ring 4, almost nothing deeper.
4. The E03 case of the requesting session's pilot is no wind-up branch (21.1): a frame move in one run or a real step, still not traced; Galileo L1C/L5Q stays out of holding.

## 24. 2026-11-15: stage G0, why GPS stops at ring 4 (reads of existing runs)

Assigned by the requesting session (its words condensed; decided in the author's absence and listed for review). Its read of `o2g_n144` from hour 2, the share of chord rows per ring by refusal: GPS ring 2 held 52 % (fraction 21, odds 13, window 11), ring 4 held 15 % (window 39, odds 27, fraction 18), ring 6 and deeper held 3 % (window 61, fraction 20, odds 16); Galileo L1X/L5X ring 5 held 42 % (window 27, odds 25, fraction 3). Run read here: `o2g_n144` (Galileo L1X/L5X and GPS L1C/L2W held, sigma_scale 2). New scripts: `scripts/nrf_window_causes.py`, `scripts/nrf_frac_terms.py`. Grades `runs_nom/_irdu_grades/nrf_g0_*`.

### 24.1 What opens the window of a deep link

**In the code.** The decision's window test reads only the link's own state: both carried entries present and not latched, their re-level stamps at least 600 s old, the link a chord for at least 600 s, no tree tenure and no release within 600 s. Upstream events reach it through the carried entries: every chain cut (a re-host, a slip de-seat, a return, a merge) issues a cut release that re-opens the carried entries of the arcs on its moved side and the moved receiver's phase bias (`CHAIN cut_release ... arcs= rpb= pb=`), so every unheld chord with an end on the moved side starts its window again. This happens also when the moved side re-attaches through a held link at a known step of 0 under held first: the held links keep their integers, and the unheld chords below them lose their carry and their window.

**Measured.** An episode is a run of epochs on which a link is refused for the window; its cause is read at its first epoch (the first that applies: left the tree, chord start, own release, own arc event, station event, a cut release whose moved side holds the link's receiver or satellite, with or without a held-first re-attachment at step 0, else unattributed).

| ring | GPS L1C/L2W window share | GPS episodes per link-hour | Galileo L1X/L5X window share | Galileo episodes per link-hour |
|---|---|---|---|---|
| 2 | 17.5 % | 0.99 | 8.5 % | 0.52 |
| 3 | 34.1 % | 1.72 | 16.0 % | 0.93 |
| 4 | 46.2 % | 2.14 | 19.3 % | 1.06 |
| 5 | 46.7 % | 2.13 | 28.6 % | 1.48 |
| 6 | 63.6 % | 2.45 | 26.9 % | 1.13 |
| 7 | 60.4 % | 2.56 | 30.0 % | 1.41 |
| 8 | 61.0 % | 2.72 | 18.9 % | 1.03 |

- Causes, all rings (GPS 2 449 episodes / Galileo 938): a chord's start, new or after a gap, 790 / 403; a cut release of unknown step upstream 800 / 108; a cut release through a held link at step 0, 353 / 283; unattributed 653 / 102; own arc events 20 / 16; leaving the tree 17 / 20; own release 6 / 6. Upstream cuts make up a growing share with depth (GPS ring 5: 364 of 728 episodes, 102 of them at step 0).
- A GPS link opens its window about twice as often as a Galileo link at the same ring. The unattributed GPS episodes (653, a quarter) are not traced: a re-level of the carry from another source, a cut outside the two epochs read, or a moved side reconstructed incompletely.

**Does a step-0 re-attachment need to reset the windows below it? No.** When the moved side re-attaches through a held link whose integer is kept, its frame is unchanged (a step of 0, or any known step), so the carried entries of its arcs stay valid after a rebase by that step; re-opening them throws their convergence away and restarts every unheld chord's window for no event of their own. In this run that is 353 GPS and 283 Galileo episodes, 14 % and 30 % of all.

### 24.2 The fraction refusals: one term per receiver plus one per satellite

Per epoch and family, the chords not held with a float: the signed N1 residual d = n_if - round(n_if) and the signed wide-lane residual w = (f1 - f2) - wl, fitted as one term per receiver plus one per satellite by alternating wrapped medians (receivers and satellites with at least 4 chords at the epoch); a shuffled null fits the same graph with the values permuted.

| family | chord-epochs | N1 p50 before | after the terms | null | wide lane p50 before | after | null | fraction refusals within 0.20 after the terms |
|---|---|---|---|---|---|---|---|---|
| GPS L1C/L2W | 121 620 | 0.214 | 0.046 | 0.099 | 0.186 | 0.034 | 0.093 | 25 849 of 32 423 (80 %) |
| Galileo L1X/L5X | 23 760 | 0.128 | 0.025 | 0.056 | 0.101 | 0.024 | 0.044 | 4 712 of 5 399 (87 %) |

**Reading.** Yes: most of a GPS chord's fraction is shared with the other chords of its receiver and of its satellite at the epoch, well beyond what a fit of that many terms takes from shuffled values, and with the terms removed the GPS residuals fall below Galileo's raw ones. That is the frame: each tree arc is pinned at its own rounded float, so its own error becomes a potential of every vertex below it, and a chord carries the difference of its two vertices' potentials. On GPS the tree arcs' own errors are large (a receiver-by-satellite code bias leaks into the floats), on Galileo small. This agrees with the requesting session's look-ahead on the key-off run (per-arc wide-lane offsets p50 0.119 to 0.038, N1 0.195 to 0.029, nulls 0.092 and 0.098).

### 24.3 The remedy, proposed (not built)

1. **(a) A cut of known step keeps the moved side's carry.** When a held-first re-attachment gives the moved side a known step, its carried entries and receiver phase bias are rebased by that step instead of released. Narrow, no change of frame or decision; removes the step-0 window episodes (14 % on GPS, 30 % on Galileo here) and keeps the moved floats converged. The same episodes occur on the simulator, so the existing beds test it (held share, 0 wrong, the truth audit); standing invariant 1 holds (a known step is no jump to respond to). Do first: cheap and safe, though it does not touch the fraction.
2. **(b) Decide against the consensus, done as a datum.** The fraction is the binding refusal at depth once the window opens, and 80 % of GPS fraction refusals fall within the bound against the consensus of the link's receiver and satellite. But a decision taken against the consensus while holds stay in the tree-pinned frame would hold integers whose fractional misfit is the frame error, as tension in the solve. The consistent form is a phase datum set by the consensus of all arcs (receiver and satellite phase biases from a robust fit over every arc, with the tree pins becoming integers measured against it), and the ring fix deciding in it. That is a change of the datum, not of the decision: it needs a design and the simulator first. Recommended second, as the remedy for GPS depth.
3. **(c) Fewer GPS tree-link changes.** Default-off keys exist (`network.eq34_anchor_min_arc_ep`, a minimum arc age for a re-host candidate; `network.eq34_fresh_pin_sigma_scale`), so this is an arm, not a build. It reduces window openings and frame steps, but the fraction structure stays: whichever arc carries the tree, its own bias becomes the potential. The longevity and slip-aware elections are KEEP_OFF as measured harmful.
4. **What the simulator needs.** Its GPS has receiver code biases per station and observable (`biases.rx_code_bias`, the same for every satellite, absorbed by the receiver code-bias states) and satellite biases (the same at every receiver); neither makes the frame signature. Needed: a constant code bias per (receiver, satellite) and code observable, from a per-station table or a seeded draw, about 0.10 to 0.15 m (an observed per-arc wide-lane offset of about 0.12 cycle p50 corresponds to about 0.10 m on both codes), applied to code only and written to a truth file, with Galileo unbiased as the control. With it the fixture's GPS would read like observed GPS, and (a), (b) and (c) can be graded against truth.

## 25. 2026-11-15: stages O3 and O4 pre-registered

Assigned by the requesting session with G0 (its words condensed; decided in the author's absence and listed for review). Its decision, recorded as its own: sigma_scale 2 is the setting on observed data from here on; the rule on the formal sigma is not used again there. Exe nrf9 (`a18324f2ed30a1c5`); every arm with `network.trace_windup_arcs`; a 10-epoch smoke of each stage first; Release; product files left in place for the requesting session's user replays.

**O3: a second day at the setting that passed.** DOY 145 (its inputs are complete: the 56 receivers and the five products, as for DOY 143; 145 is the requesting session's first choice). Base: `_rap_nwa1nh_n144/arm.json` with every DOY-144 path moved to DOY 145 and `data_download.doy` 145 (holds off posture, 6 h from start 0).
- `o3off_n145` and `o3off_n145r`: the key off with the default receiver and with `network.phase_datum_eq34_receiver` GOPE00CZE.
- `o3g_n145` and `o3g_n145r`: holding, rule gated, order certain, gate odds, sigma_scale 2, `wl_frac_max` 0.25, held first, pairs `["E:L1X/L5X", "G:L1C/L2W"]`, with the two receivers.

**O4: DOY 144, every pair family held.** Pairs `["E:L1X/L5X", "E:L1C/L5Q", "G:L1C/L2W", "G:L1W/L2W"]`, sigma_scale 2, `wl_frac_max` 0.25, held first. No receiver is in all four families' trees (Galileo X 28 receivers, Galileo C/Q 28, GPS L1C 39, GPS L1W 17), so two receivers move the roots:
- `o4_n144`: the default roots (Galileo X BOGT00COL, Galileo C/Q COCO00AUS, GPS L1C and L2W BOR100POL, GPS L1W LEIJ00DEU).
- `o4_n144r`: GOPE00CZE (moves the Galileo X and GPS L1C roots).
- `o4_n144r2`: CHUR00CAN (tracks Galileo L1C/L5Q and GPS L1W/L2W; moves those roots).
- `o4_n144b`: the default roots from +1 h (`start_offset_hours` 1.004167, the same end).
- `o4off_n144r2`: the key off with CHUR00CAN (the other key-off references exist: `o2off_n144`, `o2off_n144r`, `o2off_n144b`).
- Audit pairs: `o4_n144` with `o4_n144r` and with `o4_n144r2` (every common arc), and with `o4_n144b` (`--windup-trace`).
- This is the test of the E03 case under holding: in log mode nothing keeps the frame through a tree change, with held first something does. If L1C/L5Q fails, it is traced first (which run steps, and which chain event at 2.12 h on the links of E03).

**Bars (as O2, frozen; per family).** The audit over every common arc, 0 failing checks, with the sizes of any failing closure; every epoch emitted; every release named; RAIM rows not above the key off of the same receiver and start by more than a tenth; every release by the residual monitor listed. **Reads** as O2, per family.

### 24.4 2026-11-15: G0 on a second run, and a precision about the cut release

- **The same reads on `o2g_n144r`** (receiver GOPE00CZE). Fractions: GPS L1C/L2W N1 p50 0.207 before the receiver and satellite terms, 0.050 after (shuffled null 0.095), wide lane 0.212, 0.035 (0.096), 22 092 of 29 110 fraction refusals within the bound after the terms (76 %); Galileo L1X/L5X N1 0.115, 0.026 (0.045), wide lane 0.123, 0.024 (0.048), 83 %. Window: GPS episodes per link-hour at rings 4 to 8 2.24, 2.20, 2.39, 2.93 and 2.54 (Galileo 1.03 to 1.80); causes of the GPS episodes (2 615): a chord's start 792, a cut release of unknown step upstream 667, a cut release through a held link at step 0 494, unattributed 620, own arc events 21, leaving the tree 17, own release 4; Galileo (994): 403, 191, 171, 184, 16, 15, 6. Both reads of 24.1 and 24.2 hold on the second run.
- **What a cut release erases** (`ChainReleaseObs` in `network/solve/ChainFrame.hpp`): every leveling carry of a satellite of the moved side at any station, every carry of a receiver of the moved side on the band, and the moved receivers' phase-bias carries. Section 24.1's "the carried entries of the arcs on its moved side" understates it in the first point: the carries of a moved satellite are erased at every station, inside the moved side or not. The window read of 24.1 used exactly this rule (a link is touched when its receiver or its satellite is in the moved side).

## 26. 2026-11-15: stages O3 and O4 results, and a third frequency assessed

**What ran.** Exe nrf9 (`a18324f2ed30a1c5`); the pre-registration committed as `ade435e` before these runs; smokes of both stages clean (11 epochs each, the trace written, every arming line present); all nine runs exit 0. Grades `runs_nom/_irdu_grades/nrf_o34_*`; scratch reads in `runs_nom/_irdu_grades/scripts_s20/`.

### 26.1 O3: DOY 145, Galileo L1X/L5X and GPS L1C/L2W held, two receivers from one start

Roots: the default receiver gives Galileo L1X/L5X at STHL00GBR and GPS L1C/L2W at BOR100POL; GOPE00CZE gives both at GOPE00CZE. The two runs' wind-up traces are byte-identical.

| bar | default receiver | GOPE00CZE |
|---|---|---|
| 1. audit over every common arc | **0 failing of 122 609 checks: PASS** (Galileo L1X 40 159, L5X 40 172; GPS L1C 21 139, L2W 21 139); with the trace, a whole-cycle difference of 0 on every arc; held links against the common tree: 0 failing of 9 624 | (the same pair) |
| 2. every epoch emitted | 720: PASS | 720: PASS |
| 3. every release named, closure closed | 106: PASS | 135: PASS |
| 4. RAIM rows against the key off of the same receiver | 3 against 3: PASS | **6 against 2: FAIL** |
| 5. monitor releases | none | LMMF00MTQ-E30 at TOW 96450, KIT300UZB-G24 at 99360, LMMF00MTQ-E27 at 105630 |

The four extra RAIM rows of the GOPE00CZE run are isolated rows on arcs not held at the time (s 6 to 16, no refloat): KIT300UZB-G22 at TOW 95730 and 96090, just after its held link was released by a slip at 94590; CUSV00THA-G06 at 105390, a row the default receiver's key off also has; WARK00NZL-E33 at 107370, at a re-entry with a GF step of 5.6 m. **Reads** (default / GOPE00CZE): Galileo L1X/L5X 195 / 227 links held, held share by hour 0.6, 30.4, 44.6, 61.5, 56.4, 59.0 / 7.7, 43.8, 57.6, 74.3, 60.1, 56.7 %; GPS L1C/L2W 117 / 121 links, 0.4, 10.6, 13.4, 20.3, 24.6, 15.4 / 0.9, 14.2, 15.9, 20.9, 24.3, 13.5 %, by ring 42.1 / 43.3 % at ring 2, 6.4 / 8.0 at ring 3, 4.5 / 6.3 at ring 4, at most 5 deeper; re-attachments through held links 99 / 121 keeping 659 / 720; minutes from an arc's birth to its first hold p50 75.0 / 67.0.

### 26.2 O4: DOY 144, the four pair families held

Roots: default Galileo L1X/L5X BOGT00COL, Galileo L1C/L5Q COCO00AUS, GPS L1C and L2W BOR100POL, GPS L1W LEIJ00DEU; GOPE00CZE moves Galileo X and GPS L1C and L2W to GOPE00CZE; CHUR00CAN moves Galileo C/Q and GPS L1W and L2W to CHUR00CAN; the late start (default receiver) elects GPS L1W and L2W at MBAR00UGA and Galileo C/Q at MRC100USA. Wind-up traces byte-identical in the same-start pairs.

| audit pair | checks | failing | by family |
|---|---|---|---|
| default against GOPE00CZE (start 0) | 196 419 | **2 169: FAIL** | Galileo X 0 of 86 987; Galileo C/Q 711 and 767 of 69 494 (closures +1 and -1); GPS L1C/L2W 328 and 363 of 39 652 (closures of +4/+5, -4/-5 and one N1 cycle); GPS L1W/L2W 0 of 286 |
| default against CHUR00CAN (start 0) | 106 505 | 0 | Galileo X 0 of 93 734; Galileo C/Q 0 of 12 771; GPS none (the CHUR00CAN run holds 1 GPS L1C/L2W link) |
| default against the late start (wind-up removed) | 119 814 | 0 | Galileo C/Q 0 of 34 952; Galileo X 0 of 80 030; GPS L1C/L2W 0 of 4 832 (on the arcs born together: 0 of 26 797) |

**Which run departs.** Held links against the tree common to the default and GOPE00CZE runs: 6 fail.
- **Galileo L1C/L5Q, E14** (DARW00AUS from TOW 8400; SOLO00SLB, MAJU00MHL, MAC100AUS and PARK00AUS from 17940 to 19170, one N1 cycle each). At TOW 7860 the chain re-hosted E14 away from NYA200NOR in both runs by an uncertified re-host from the carried floats (`rehost_carry`, step unknown), erasing E14's carries at every station; DARW00AUS-E14 then re-converged and was decided at (56, 83) in the default run and (55, 82) in the GOPE00CZE run, while MAJU00MHL-E14 holds (36, 15) in both. The late-start run agrees with the default run over 17 478 C/Q checks (it holds DARW00AUS-E14 from TOW 10950), so the departing integers are the GOPE00CZE run's.
- **GPS L1C/L2W.** The default four-family run departs from the default two-family run `o2g_n144` (427 failing of 20 467 checks per band), while the GOPE00CZE four-family run agrees with its two-family run `o2g_n144r` (0 of 25 632): the odd run is the default four-family run. HKSL00HKG-G12, the failing link the attribution names, carries the same integers (318, 164) in both default-receiver runs, so the departure is in the four-family run's GPS frame, not in that link's decision; not traced further.
- **Two families on one band.** GPS L1C/L2W and L1W/L2W share the L2W band, which has one tree and one root. A family holds only when its first band's tree has the same root as the L2W tree: with the default roots (L1C and L2W at BOR100POL, L1W at LEIJ00DEU) L1C/L2W held 124 links and L1W/L2W 5; in the late start (L1W and L2W at MBAR00UGA) L1W/L2W held 52 and L1C/L2W 27; with CHUR00CAN (L1W and L2W there) L1C/L2W held 1. This is the shared-band problem of a third frequency, already present with two GPS families.
- **The E03 case under holding.** E03's L1C/L5Q links carry identical integers in the default and GOPE00CZE runs: SOLO00SLB (-300, -387), PARK00AUS (-251, -312) and DARW00AUS (-160, -156), held from TOW 6060 to 6510 and kept through 2.12 h, with no audit failure. The step of the requesting session's log pilot (DARW00AUS-E03 to (-161, -157) at 2.12 h) does not recur under holding.

**The other bars.** Every epoch emitted (720, and 600 in the late start); every release named and every closure closed. RAIM rows against the key off of the same receiver and start: default 24 against 15, **FAIL**; GOPE00CZE 12 against 17, PASS; CHUR00CAN 25 against 22, **FAIL** (the bar is 24.2); late start 5 against 8, PASS. The default run's excess is one burst at KIT300UZB from TOW 15960 to 16140: E27 lost L1C at 15810 and came back at 15960 with a GF step of 2.25 m, an arc not held, attributed and refloated by RAIM every epoch in every run; with the four families held its statistic reaches 90 and six other satellites of the station join at 16080 (key off: 16; GOPE00CZE: 20, decaying). Monitor releases: GOPE00CZE DARW00AUS-E15 at TOW 7920; late start GUAM00GUM-E14 at 17850 and LMMF00MTQ-E28 at 21150 (the O2 event). Held links released at a chain cut across an unknown step (cause chain): 7, 6, 5 and 2, none in O2.

**Reads (default receiver, start 0).** Galileo L1C/L5Q 179 links held, held share by hour 1.4, 18.0, 43.8, 46.2, 46.6, 49.8 %, by ring 52.8 % at ring 2 to 20.9 at ring 6; Galileo L1X/L5X 237 links, as in O2; GPS L1C/L2W 124; GPS L1W/L2W 5. Late start: Galileo C/Q 182, Galileo X 225, GPS L1C/L2W 27, GPS L1W/L2W 52.

### 26.3 What O3 and O4 say

1. A second day agrees: on DOY 145 the two receivers' held integers agree on every common arc (0 of 122 609, a third of the checks GPS). Its RAIM bar fails in one run by four isolated rows on arcs that were not held.
2. Holding every family on DOY 144 does not pass. Galileo L1X/L5X agrees in every pairing; Galileo L1C/L5Q departs in one run after an uncertified re-host of E14 (an unknown step: a known-step remedy such as 24.3 (a) would not cover it); GPS L1C/L2W departs in the four-family run with the default receiver; and GPS L1W/L2W cannot be held beside L1C/L2W while the shared L2W band has one root.
3. A RAIM pattern of holding: on a stiffer network, the error of a re-entering arc that is not held shows as RAIM rows at its station (KIT300UZB on DOY 144: s 90 and six satellites; DOY 145: isolated rows); RAIM refloats nothing, and every epoch is emitted.

### 26.4 A third frequency, assessed (asked by the requesting session; no build)

- **What exists.** The simulator's golden fixture already carries a third band on both systems (GPS C5Q/L5Q; Galileo C5Q/L5Q and C7Q/L7Q). The network has the band-5 pieces of card L5B, all default off and UNVALIDATED: a free band-5 code column (`network.sat_gf_extra_band_free`), the receiver's extra-band code delay (`network.estimate_rx_extra_band_code_delay`) and a shared verdict for signals that resume together (`network.cycle_slip.gap_reentry_coresumed_share`); second-band admission (`network.second_band_admission`) and per-signal records (`network.n3c_wire_per_signal`) are armed in the BeiDou lineage. The chain builds one tree per signal band, and the ring fix decides pair families named by two signals.
- **What is known to break.** On the simulator the settled three-band posture diverged (the extra-wide-lane share fell from 74.7 to 5.0 %, root unknown; not armed), and the third band hurt the clock and the wet delay there. On observed data GPS L5 reproduces the MAJU00MHL G08 event on the GPS and Galileo golden (a phase-datum anchor's weak three-band level coupling to the phase biases its pins define; card ALD's local pin row derived, not built); the band-5 code deweight is KEEP_OFF. GPS L5 is SEQUENCED, never closed.
- **What the ring fix lacks**, now seen on observed data (26.2): two pair families that share a band decide its integer twice, and with one tree root per band only one of them holds. A third frequency (E1/E5a and E1/E5b share E1) needs a cascade: the third signal's integer from the held pair and the extra-wide lane (E5a/E5b, 9.8 m), decided after the pair, not beside it; the same cascade would let GPS L1W/L2W follow L1C/L2W through the shared L2W.
- **The smallest simulator step.** No build and no new fixture: on the simulator golden bed, the posture of card L5B's simulator runs that admitted every tracking channel (stable there over 2 h), with the ring fix in log mode on two Galileo families that share E1 (pairs `E:L1C/L5Q` and `E:L1C/L7Q`) and the truth audit. Read: the share of right integers in each family, whether the two families' E1 integers agree, and how the shared band's root election treats the two families. If both families agree with truth, the next step is the cascade, built and held on the simulator.

# NRF part 4: stage O2, integers held on observed data (sections 21 onwards of card NRF)

**STATUS**

- **id:** NRF-part4
- **topic:** network-vehicle
- **status:** open
- **summary:** Sections 21 onwards of card NRF (2026-11-15). Section 21: stage O2 pre-registered, the first runs that hold integers on observed data (Galileo L1X/L5X, the bed of DOY 144, two starts, the odds computed with one and with two times the formal sigma), with the build it needs: `network.ring_fix.sigma_scale` and the wind-up arc trace `network.trace_windup_arcs`, which lets the two-start audit cover every common arc. Section 22: the results. With the odds at twice the formal sigma the two starts agree on every held integer (0 failing of 78 588 checks over every common arc), every epoch emitted, RAIM unchanged, about 60 % of the chord link-epochs held from hour 3; with the formal sigma (the rule as pre-registered) the audit fails (13 344 of 92 547; 7 held links: three young-network decisions, four L5X closures after a re-seat). The wind-up trace matches truth exactly on the simulator. The audit's failing counts depend on its walk (fixed to a sorted walk; earlier raw counts re-read), its verdicts do not.
- **source:** [NRF part 3](NRF_network_ring_fixing_2026-11-14_part3.md) sections 19 and 20; the requesting session's messages of 2026-11-15 (its log-only pilot on the same bed, exe nrf7, four starts)

**Outcome.** Question: on observed data, does the ring fix hold only integers that two runs with different starts agree on, with every epoch emitted and no RAIM excess? With the odds at twice the formal sigma, yes on Galileo L1X/L5X over 6 h of DOY 144: 0 failing of 78 588 checks over every common arc, the wind-up branches removed from a new trace of the stations' accumulators, every epoch emitted, RAIM unchanged. With the formal sigma, no: three young-network decisions and four L5X closures after a re-seat disagree between the starts. Standing: default off; one bed, one pair of starts.

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

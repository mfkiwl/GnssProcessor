# NRF part 6: remedy (a) and the stream's step declaration (sections 41 onwards of card NRF)

**STATUS**

- **id:** NRF-part6
- **topic:** network-vehicle
- **status:** open
- **summary:** Sections 41 onwards of card NRF (2026-11-15), continued from [part 5](NRF_network_ring_fixing_2026-11-14_part5.md). Section 41: the results of section 39, remedy (a) (`network.ring_fix.rehost_keep_carry`: a chain re-host onto a held link keeps the moved side's carries): every bar passes on the golden simulator bed, bed B of section 36 and the DOY 145 holding pair (same-start audit 0 of 147 280, E18's level within 0.015 m between two reference receivers); why Galileo at S45000SIM holds fewer link-epochs (the per-epoch decision cap); the kept steps (micrometres, now a step of 0 under 1e-4 cycle, exe nrf18); what resets a kept receiver phase bias (no field-blocking gap found); the remedy and the formal sigma adopted in the chain posture. Section 42: the adopted set on DOY 144 and DOY 145 with GPS beside Galileo, pre-registered. Section 43: the stream's step declaration on that stream, pre-registered. Section 42.1: the first batch fails on DOY 144 through a defect of remedy (a) as built (a fractional step carried into the moved side moved held chords off their integers); fixed to keep a re-host only at a step of 0 (exe nrf20). Sections 44 and 45: the per-epoch decision cap as a key and the settled flags, pre-registered. Section 46: the re-runs on the fixed code pass every bar (the simulator pair, DOY 144 and DOY 145 with two reference receivers, DOY 145 with two starts) and the adoption stands. Section 47: the step declaration leaves the estimates unchanged and marks every whole and fraction step; its cause-side check fails (a release does not always raise an increment, and a freed level creeps unsignalled); ionosphere-like steps move a held family's wide lane in the first hour and twice after it on GPS. Section 48: the decision cap passes at 3, 6, 12 and no cap on the simulator (12 holds 36 % more link-epochs than 3, within 0.3 % of no cap) and at 12 on DOY 144 (audit zero, held link-epochs within 0.5 %: the cap of 3 binds there in the first hour only); adopted at 12 in the chain posture. Section 49: the settled flags: the check found two defects of the build (a wire-fill copy carried its source's flags; a held link in a tracking gap settled its satellite), fixed in exe nrf22; the stream as fixed (`f11_n144`) equals the rule at every epoch.
- **source:** [part 5](NRF_network_ring_fixing_2026-11-14_part5.md) sections 35 (the code-reference window of DOY 145), 38 to 40 (the window's results) and 39 (remedy (a), pre-registered); [part 4](NRF_network_ring_fixing_2026-11-14_part4.md) section 24.3 (the remedy proposed); the requesting session's review of 2026-11-15 (four requests for the write-ups).

**Outcome.** Question: does remedy (a), a chain re-host onto a link the ring fix holds keeping the moved side's carries, cure the DOY 145 departure without harm? Yes, as fixed: the code first adopted also carried a fractional step into the moved side and broke DOY 144's held chords; kept only at a step of 0, the re-runs read 0 failing on the simulator pair, on both days with two reference receivers and on DOY 145 with two starts. The remedy, the formal sigma and a decision cap of 12 are adopted in the chain posture (sections 41.6, 46 and 48). The settled flags pass after two fixes (section 49); the step declaration's cause-side check fails (section 47).

## 41. 2026-11-15: results of section 39, remedy (a): every bar passes

Every arm on exe nrf17 (`a1b4d87801bfb5b5`, commit fc43724) unless named, all exit 0, every epoch emitted (360 of 360 on the simulator beds, 720 of 720 on DOY 145). Grades: `_irdu_grades/nrf_ka_*`, script `_irdu_grades/scripts_s20/grade_ka.sh`; re-hosts and their old edges by `scripts/nrf_rehost_causes.py`.

### 41.1 The golden simulator bed (3 h from 00:30:15; the ring fix on GPS L1C/L2W and Galileo L1C/L5Q at the formal sigma with the full response)

| arm | (a) | decisions wrong | held link-epochs (wrong) | held share h1, h2, h3 (%) | cut releases | carried entries erased (per hour) | receiver / satellite phase biases dropped | re-hosts kept |
|---|---|---|---|---|---|---|---|---|
| `k0_sim` | off | 0 | 121 541 (0) | 12.5, 54.4, 77.2 | 372 | 10 024 (3 341) | 920 / 428 | |
| `ka_sim` | on | 0 | 127 151 (0) | 12.5, 54.5, 83.7 | 166 | 2 704 (901) | 188 / 114 | 212 |
| `k0_sim_r` | off | 0 | 119 395 (0) | 10.4, 51.3, 79.8 | 282 | 7 998 (2 666) | 734 / 336 | |
| `ka_sim_r` | on | 0 | 121 358 (0) | 10.5, 51.8, 81.5 | 130 | 2 350 (783) | 192 / 84 | 154 |

Two-reference audits: 0 failing of 174 366 checks without (a), 0 of 191 104 with it. Bars: held share not below the arm without (a) (held link-epochs +4.6 % and +1.6 %), 0 wrong against truth (decisions and held link-epochs, the truth taken per epoch through the re-seats), every epoch emitted: PASS. Keys absent identical: `k0_sim15` (exe nrf15) against `k0_sim15b` (exe nrf17), 1.5 h with the ring fix and no key of (a) or of the step declaration: the products, the solution and the ring-fix, chain-edge, event and epoch-status traces byte-identical.

**Galileo at S45000SIM holds fewer link-epochs with (a)** (the requesting session's count: 58 755 to 53 131, while GPS goes from 60 640 to 68 227). The cause is the ring fix's cap of 3 decisions per epoch over all families, taken in order of the log-odds (`kRingFixMaxDecisionsPerEpoch`), not a kept carry that delays a decision. With (a) more links pass every test: Galileo's window refusals fall from 2 092 to 1 373 link-epochs and its fraction refusals from 545 to 421 in the third half-hour, while its refusals by the cap (a link that passed every test and was passed over) rise from 976 to 3 379, and GPS's from 3 543 to 4 416. In the second and third half-hours GPS takes the slots first (decisions 114 and 61 without (a), 125 and 86 with it; Galileo 65 and 119, 55 and 94); Galileo's decisions come later (half-hours 4 and 5: 76 and 28 without, 93 and 48 with), and its held share by the last half-hour is 91 % with (a) against 90 % without. At the default receiver Galileo leads with (a) (75 % to 83 % in the fourth half-hour).

**The kept re-hosts.** Run-end counters: kept 212 and 154, re-targeted 0, released all the same 0; by band (re-hosts with an old edge at the previous epoch) GPS L1C 56 and L2W 56, Galileo L1C 20 and L5Q 50 at the default receiver, 51, 51, 9 and 26 at S45000SIM. The counter "with a non-zero step" read 212 and 154 because it counted any difference between the held integer and the new host's carry. In cycles (the chain trace's pinmove at micrometre resolution): p50 0, p99 0 (default) and 1.2e-5 (S45000SIM), largest 2.6e-5 cycle (5 micrometres) apart from one case: the held link's carry sits on its whole number to within the hold's own tightness. They do not accumulate: along a satellite's level over the 3 h (the shift walk moves every vertex of the moved side, the sign alternating down the tree) the largest running sum is 3.2e-5 cycle (E10 L1C, 3 kept re-hosts). The one case (default receiver, S40000SIM-E34 at TOW 264960): 0.108 cycle on L1C and 0.146 on L5Q (2.1 and 3.7 cm); the link was decided at TOW 264930 and became a tree edge at the next epoch, before the hold had pulled its carry onto the integers (its floats sat at those distances from 14 and 80 at the decision); the shift walk carried that exact displacement into the moved side (a receiver with no satellite below it), and the decision is right against truth. **Change made on this finding** (the requesting session's request): a displacement under 1e-4 cycle is now a step of 0 (`kRehostKeepZeroStepCyc`), so a held link whose carry sits on its integer is kept whether or not the carry shift is armed, and the counter counts real steps only (exe nrf18; section 41.5).

**Why the old edges went** (default receiver, band-edges): the satellite set at the old receiver 125, the old edge still in the tree (re-arranged, flipped or not) 36, a gap of that arc 14, re-arranged while tracked 5, a slip of that arc 2; at S45000SIM 137 kept, none at a receiver with a receiver-wide event (section 41.4).

### 41.2 Bed B of section 36 (the thinned X family with the code error)

| arm | (a) | decisions wrong | held link-epochs (wrong) | carried entries erased per hour | re-hosts kept |
|---|---|---|---|---|---|
| `crb_off` (nrf15) | off | 0 | 117 656 (0) | 3 395 | |
| `kb_crb` | on | 0 | 123 129 (0) | 848 | 242 |
| `crb_off_r` (nrf15) | off | 0 | 114 956 (0) | 2 507 | |
| `kb_crb_r` | on | 0 | 116 769 (0) | 724 | 182 |

Two-reference audit with (a): 0 of 190 668 (0 of 177 752 without). PASS; as section 39 said, bed B departs without (a) neither, so it shows only that (a) does no harm there.

### 41.3 DOY 145, the holding pair (Galileo L1X/L5X at the formal sigma with the full response)

| arms | same-start audit | E18's level at BOGT00COL-E18, TOW 94560 to 99270 | E18 holds (default; GOPE00CZE) | held share h2 to h6, default (%) | GOPE00CZE (%) | carried entries erased per hour | re-hosts kept |
|---|---|---|---|---|---|---|---|
| without (a) (`o5s1j_n145[r]`, nrf14) | 271 failing | largest difference 0.741 m, 153 of 158 epochs over 0.1 m | STHL00GBR 96390, LMMF00MTQ 97530; LMMF00MTQ 97080, STHL00GBR 97260 | 80.6, 87.4, 86.2, 72.6, 66.7 | 83.3, 86.4, 88.0, 81.3, 83.7 | 2 480; 2 532 | |
| with (a) (`o8a_n145[r]`) | **0 of 147 280** (L1X 73 546, L5X 73 734) | **largest difference 0.015 m**, none over 0.1 m | STHL00GBR 96750, LMMF00MTQ 97110; STHL00GBR 97020, LMMF00MTQ 97080 | 81.6, 87.5, 88.3, 85.3, 86.6 | 86.4, 87.6, 88.7, 86.7, 88.5 | 2 121; 2 105 | 154; 148 |

Both bars of section 39 pass. With (a) the re-host of TOW 94560 keeps BOGT00COL's X receiver phase bias and E18's X phase biases; E18's level in the default receiver's run then follows the carried level as the GOPE00CZE run's does (4.743 and 4.742 m at TOW 95580, 5.009 and 5.008 m at TOW 98460), and both runs hold STHL00GBR-E18 and LMMF00MTQ-E18 on the same lane. RAIM rows 1 and 1 (1 and 1 without); releases named (139: slip 26, refloat 1, gap 111, monitor 1; 159: slip 29, refloat 3, gap 125, monitor 2). The held share rises most in hours 5 and 6 (default 72.6 to 85.3 and 66.7 to 86.6 %). Carried entries erased fall by 14 and 17 % only: on DOY 144 and 145 only the X family is held, and the unheld Galileo C/Q and GPS families keep releasing as before. Kept re-hosts by band: L1X 77 and L5X 77 (default), 73 and 75 (GOPE00CZE); old edges: still in the tree 41, set 96, slip 17 (default), 47, 83 and 18 (GOPE00CZE); no re-target; one step of 1e-4 cycle or more on the day (GOPE00CZE, CAS100ATA-E06 at TOW 89610: 0.104 and 0.130 cycle, the link decided at TOW 89580, the epoch before, as the simulator's case); none at a receiver with a receiver-wide event.

### 41.4 What resets a kept receiver phase bias (the requesting session's request 2 (b))

Before (a), a re-host released every receiver phase bias of its moved side whatever had happened, so an event at a moved receiver that came with the re-host was covered by the release. With (a) those receiver phase biases are kept, and what resets them is what resets every carried receiver phase bias, re-host or not (code read in `ChainDatum.cpp`, `RxPhaseBiasCarry.cpp`):

1. **An event on every arc of the receiver** (a receiver-wide slip or jump) puts all its arcs in the free-epoch latch. A held link at that receiver is then refused by (a) (its latch test) and released by the ring fix, and the receiver's own tree edge, on a latched arc, falls to the slip row, which releases it: the walk's step there is unknown and the receiver phase bias is dropped (`ResponseSite::RpbEq34Erase`).
2. **A receiver that returns to the tree after a gap** (absent from the last tree, seen in an earlier one) is the returning row's: its edge is released and its receiver phase bias dropped.
3. **A gap past the horizon** (`network.phase_leveling_max_gap_s`, 900 s in every arm): the carried receiver phase bias is pruned.
4. **A step of the receiver phase bias itself:** in the block route (`network.phase_datum_eq34_rpb_in_block`, armed in every arm) a carried value whose harvest differs from it by more than its step test is erased the epoch after (reset, not repair).

An event at one arc (the old edge's satellite setting, a gap or a slip of that arc alone) does not move the receiver's phase bias, which is what (a) keeps. What no response catches is a receiver-wide phase step that flags no arc and stays under the step test; the release at a re-host caught it only when a re-host happened at that epoch, by coincidence, so (a) removes no designed protection. Measured: of the kept re-hosts, none had an old edge at a receiver whose every arc slipped or went missing at the epoch (simulator: 0 of 182 at the default receiver and 0 of 137 at S45000SIM; DOY 145: 0 of 154 and 0 of 148). No field-blocking gap is found on this evidence.

### 41.5 The zero-step tolerance (exe nrf18, `9ba0d737967bdeb6`)

The four remedy-on arms re-run with the tolerance (`kc_sim`, `kc_sim_r`, `o8c_n145`, `o8c_n145r`) give the integers of exe nrf17 (audits against the nrf17 runs of the same receiver: 0 failing of 254 302, 242 716, 150 148 and 168 980 checks), the same held link-epochs (127 151 and 121 358) and held shares, 0 wrong against truth, the DOY 145 same-start audit 0 of 147 280 and E18's level within 0.015 m. The counter of steps of 1e-4 cycle or more now reads 2, 0, 0 and 2: the two bands of the two links decided one epoch before they became tree edges (S40000SIM-E34 on the simulator, CAS100ATA-E06 on DOY 145, 0.104 and 0.130 cycle). The products are not byte-identical: clocks within 11 micrometres and code biases within 15 micrometres of nrf17's, phase biases within 0.3 mm on the simulator and 7 mm on DOY 145 (E36 L5X, a slow wander from TOW 89640): the float history's sensitivity to the zeroed micrometre steps, with no integer moved.

### 41.6 Adoption (section 39, item 4)

Bars 1 and 2 of section 39 pass. Under the author's rule `network.ring_fix.rehost_keep_carry` (armed when on) and `network.ring_fix.sigma_scale` (armed at 1, the formal sigma) move from UNVALIDATED to RECOMMEND_SCOPED, regime `on("network.ring_fix.enable")` (the chain posture with network integer fixing; the goldens do not run the ring fix and are unchanged), with matching scoped rows in the loader's posture table (`GnssConfigNetworkPosture.cpp`) and these notes:
- `network.ring_fix.rehost_keep_carry`: adopted 2026-11-15 on the author's instruction (an improvement that passes its bars is adopted). Verified by: the golden simulator bed and bed B of section 36 (two reference receivers each, 0 wrong against truth) and DOY 145, one network of 56 receivers, the same start with two reference receivers (basic). To do: DOY 144 and the two-start audit with the remedy; more stations and days; the main posture without the chain.
- `network.ring_fix.sigma_scale`: adopted 2026-11-15 on the author's instruction, with remedy (a): the formal sigma (1). Verified by: DOY 144 without the remedy (same start and two starts, Galileo L1X/L5X and GPS L1C/L2W) and DOY 145 with it (same start, two reference receivers), one network of 56 receivers (basic). To do: DOY 144 and the two-start audit with the remedy; more stations and days; the main posture without the chain.

`config_posture_check.py --verify-loader`: 0 gaps; `make_golden_config.py --verify`: PASS. The window key of section 36 stays UNVALIDATED and off.

## 42. 2026-11-15: the adopted set on both days, GPS beside Galileo (pre-registered)

**Why** (the requesting session's order after section 41): close the to-do of the adoption notes at once. The formal sigma was verified with the remedy only on DOY 145 at the same start and with Galileo alone; DOY 144 and a two-start audit with the remedy are owed.

**Arms** (exe nrf18, `9ba0d737967bdeb6`; the adopted set: the formal sigma, the full bad-epoch response, `network.ring_fix.rehost_keep_carry`; Galileo L1X/L5X and GPS L1C/L2W held; BSHM00ISR out, 55 receivers; the counters serialized):
- DOY 144, one start, two reference receivers: `o9_n144` (default receiver) and `o9_n144r` (GOPE00CZE), from `o6gj_n144[r]` of section 34 with the remedy.
- DOY 145: `o9_n145` (default receiver) and `o9_n145r` (GOPE00CZE), from `o5gj_n145[r]` with the remedy and BSHM00ISR out, and `o9_n145b` (default receiver, start 1 h later, 5 h).

A 10-epoch smoke first.

**Bars.** Every audit zero per family: the same-start audits of both days and the two-start audit of DOY 145 (the wind-up branches removed with the trace), over held integers and tree pins; every epoch emitted; releases named; RAIM rows not above the runs without the remedy by more than a tenth. **Reads:** `stream_jumps.py` by family and depth (hours 3 to 6); held share by family and hour.

## 43. 2026-11-15: the stream signals its steps, on the stream of section 42 (order D.2, pre-registered)

**The declaration** (exe nrf18; keys `network.disc_step_class_pairs` and `network.disc_step_class_tol_cyc`, default 0.15 cycle; off by default, ledger rows UNVALIDATED; commit fc43724). The counter it steps is the P record's `phase_disc`, the per-key phase discontinuity counter: every reaction of the user engine to a phase step (reset, carry, translate) keys on a change of that counter (`RealTimeEngineSsrBreaks.cpp`). Per family and emission, each satellite's step of the level a user's phase reads, (C - P_b + mu_b x) / lambda_b less the family's median step, is classed as the requesting session's stream-step read classes it (quiet, whole, ionosphere-like, fraction), and the signals a whole or fraction step moves carry an increment in place of the value test; quiet and ionosphere-like steps carry none. A key not classified (no previous emission within 45 s, a bias or the clock missing, a family below 4 satellites) and a signal in no family keep the value test; forced marks are unchanged (`products/PhaseStepClassTest.hpp`).

**Why on the emitted step and not on the chain's declared keys.** A chain release does not move a level once: the freed level re-converges over several epochs (section 35.2: 0.15 m at the release of TOW 94560, 0.25 m over the next 4 min, 0.125 m at the code-reference move, then 0.6 m over 12 min), so a declaration at the release epoch alone leaves the later steps unsignalled, and a declared key whose level does not move raises an increment without a step. The emitter sees every step of what it emits, whatever its cause. Because the rule and the checker share one classification, the agreement of steps and counters holds by construction; the cause-side check below is the independent one.

**Arms** (exe nrf18): `d9_n144`, `d9_n144r`, `d9_n145`, `d9_n145r`, `d9_n145b`: the arms of section 42 with the declaration on Galileo L1C/L5Q and L1X/L5X and GPS L1C/L2W and L1W/L2W. Their estimates are those of section 42 (the declaration touches only the counters), which is checked.

**Bars (the order's, with the requesting session's two additions).**
1. On each arm: every step `stream_jumps.py` classes whole or fraction carries an increment at that epoch on each signal it moves; no increment without a step, each one listed with what stands behind it (a forced mark, a key not classified, a signal in no family). Checker: `scripts/stream_disc_check.py`.
2. The cause-side check: every chain event that moves a satellite signal's level (a `cut_release`, a re-pin with a non-zero step) has an increment at that epoch on that satellite signal; the increments with no chain event behind them are listed with what moved the level there.
3. The ionosphere-like steps, which carry no increment: per family and depth, the number per satellite-hour that move the wide lane (d1 - d2) by more than 0.25 cycle, and the largest. If there are any on a held family, a declaration of their own is proposed (a class a user re-levels the wide lane on without dropping the narrow lane), not built.
4. The C, B and P values of each `d9` arm identical to its `o9` twin's.

### 42.1 2026-11-15: the first batch, a defect of remedy (a) at a fractional step, and the fix (amendment, pre-registered)

The first batch of section 42 ran on exe nrf18. **DOY 145 passes:** the same-start audit reads 0 of 239 698 checks (Galileo L1X 73 164, L5X 73 357; GPS L1C 46 573, L2W 46 604). **DOY 144 fails:** 762 of 277 256 (Galileo L1X 508 of 81 659, L5X 254 of 81 639, closures of one cycle on one band; GPS 0 of 113 958), from TOW 12270 to 19740.

**The cause is remedy (a) as built.** At TOW 11970 in the default receiver's run the link SYOG00ATA-E02, decided at TOW 11940 (floats 47.80 and 22.72 against 48 and 23: band fractions 0.20 and 0.28, ionosphere-free 0.04, wide lane 0.08), became E02's L5X tree edge through a kept re-host one epoch after its decision, before the hold had pulled its carry onto the integers. The kept branch took the step, 0.283 cycle, as known, and the shift walk carried it into E02's subtree: the carried L5X floats of E02's three other held links moved by the same amount off their integers (KRGG00ATF 100 to 100.278, CAS100ATA 87 to 87.281, SCTB00ATA -33 to -32.719), all three were released at the next epoch, and E02's later L5X decisions were taken in a frame 0.283 cycle off the other run's. A fractional step moves every chord through the moved side off its integer, held links included, and the ring fix, which sees no cut, cannot re-express them. The two earlier cases (the simulator's S40000SIM-E34, a receiver with no satellite below it, and DOY 145's CAS100ATA-E06) moved no integer; this one did. Section 41.1's reading that the shift walk carries such a step "exactly" holds for the carries and misses what the step does to the held chords; the general known step was a stretch of section 39's remedy, which is a re-host that changes nothing physical.

**The fix** (exe nrf20): remedy (a) keeps a re-host only when the new host's carry sits on the held integer to within 1e-4 cycle (a step of 0); a held link whose carry is off its integer is released as before (counter `rehost_off_integer`). The nrf18 runs of the second batch were stopped.

**Re-runs** (exe nrf20; the bars of sections 39, 42 and 43 unchanged): the golden simulator pair `kd_sim` and `kd_sim_r` (section 41.1's arms with (a) on); section 42's arms as `o10_n144`, `o10_n144r`, `o10_n145`, `o10_n145r`, `o10_n145b`; section 43's as `d10_*`. If they pass, the adoption of section 41.6 stands on the fixed code with its notes revised; if not, the remedy's adoption is withdrawn.

## 44. 2026-11-15: the per-epoch decision cap as a key (pre-registered)

**Why** (the requesting session's order): the ring fix decides at most 3 links per epoch, a value set when a wrong decision was still expected; with remedy (a) it passes over 3 379 Galileo and 4 416 GPS link-epochs in 3 h on the golden simulator bed that had passed every test (section 41.1), and none of the decisions since has been wrong on any bed.

**The key** (commit af34831, exe nrf21): `network.ring_fix.max_decisions_per_epoch`, default 3 (the former constant, identical when absent), 0 for no cap; ledger row UNVALIDATED.

**Arms** (exe nrf21; the golden simulator bed with the adopted set, as `kd_sim[_r]` of section 42.1): `kq6_sim[_r]`, `kq12_sim[_r]`, `kq0_sim[_r]` (cap 6, 12 and none, the default receiver and S45000SIM); the cap of 3 is `kd_sim[_r]`; `ki_sim` (`kd_sim` with the key set to 3) against `kf_sim` (`kd_sim` with no key) for keys absent identical. Then the DOY 144 pair of section 42 at the best value that keeps every bar.

**Bars:** 0 wrong against truth; the two-reference audit zero; every epoch emitted; keys absent identical. **Reads:** held share by half hour per family, refusals by the cap, decisions per epoch (p50, p99, largest), alarms (RAIM rows, monitor releases). If the DOY 144 pair passes, the key is adopted under the author's rule with the three-part note.

## 45. 2026-11-15: the stream says which signals are settled (pre-registered)

**Why** (the requesting session's design question and order): a user that starts with the network fixes on the stream's unsettled first hour and keeps what that hour put into it (its note ARNF section 17); the stream should say which satellite signals are settled, so that a user fixes only on them.

**The flags** (exe nrf21; key `network.ring_fix.settled_flags`, default off, ledger row UNVALIDATED; needs `network.ring_fix.pairs`): on every phase-bias record of a held family (a pair of `network.ring_fix.pairs`), `signal_integer` is 1 only while the satellite is reached from its tree's datum receiver through held links and tree edges that entered the tree as held links (rule B of `scripts/nrf_settled_flags.py`), and `wide_lane_integer` is 1; on a record of no held family both are 0. Computed by the ring fix after its decisions each epoch (`ringFixSettledSats`, the components from the arc graph's disjoint sets) and stamped on the records at the solution's preparation. The read of section 43's design question on `o2s1j_n144` (Galileo L1X/L5X): flagged 21 % of satellite-epochs in hour 1, 92 % in hour 2, 97 to 100 % after, 0.05 flips per satellite-hour after the first hour.

**Arms** (exe nrf21): `f10_n144`, the DOY 144 stream of section 42.1 with the step declaration (`d10_n144`) and the flags; `kf_sim` (`kd_sim` with no new key) for keys absent identical.

**Bars:** keys absent identical (`kf_sim` against `kd_sim`, exe nrf20); on `f10_n144` the emitted flags equal `nrf_settled_flags.py`'s rule B at every epoch, for every satellite signal of a held family; the flips counted; the products otherwise identical to `d10_n144`'s (the step declaration's increments unchanged by the flags).

## 46. 2026-11-15: results of section 42.1, the re-runs on the fixed remedy: every bar passes, the adoption stands

Exe nrf20 (`fa5a0299fa2928cb`, commit af34831), all arms exit 0, every epoch emitted (360 on the simulator, 720 on DOY 144 and DOY 145 from start 0, 600 from the start 1 h later). Grades: `_irdu_grades/nrf_kd_*`, `nrf_o10_*`.

| arms | audit | checks | failing |
|---|---|---|---|
| `kd_sim` against `kd_sim_r` (simulator, two reference receivers) | held integers and tree pins | 190 848 | 0 |
| `o10_n144` against `o10_n144r` (DOY 144, same start) | Galileo L1X 83 287, L5X 83 267; GPS L1C 57 083, L2W 57 374 | 281 011 | 0 (762 on exe nrf18) |
| `o10_n145` against `o10_n145r` (DOY 145, same start) | Galileo L1X 73 240, L5X 73 433; GPS L1C 46 837, L2W 46 821 | 240 331 | 0 |
| `o10_n145` against `o10_n145b` (DOY 145, two starts, wind-up branches removed by the trace) | Galileo L1X 55 418, L5X 55 413; GPS L1C 2 872, L2W 2 872 | 116 575 | 0 |
| the same, arcs born after the later start | | 27 524 | 0 |

- **Truth (simulator):** 0 wrong decisions and 0 wrong held link-epochs in both runs (126 977 and 121 358 held link-epochs).
- **E18's level on BOGT00COL-E18, DOY 145:** largest difference 0.016 m between the two reference receivers from TOW 94560 to 99270, none over 0.1 m.
- **RAIM rows:** 0 and 0 on DOY 144, 1, 1 and 0 on DOY 145 (as without the remedy).
- **`rehost_off_integer`** (re-hosts onto a held link released because the carry was off its integer): simulator 2 and 0, DOY 144 2 and 4, DOY 145 2, 5 and 1, counting band-edges. Each is one link decided the epoch before it became a tree edge, about one per family per run (DOY 144: SYOG00ATA-E02 and NYA200NOR-G21 at the default receiver, SCTB00ATA-E25 and GAMB00PYF-G03 at GOPE00CZE). At one or two a day per family the safe form stays; the other form (the pin takes the held integers, the link's slant ionosphere takes the lag) is not assessed.
- **Held share by family**, hours 2 to 6: Galileo L1X/L5X 81 to 90 % on both days and receivers; GPS L1C/L2W 51 to 62 % (DOY 144, default), 37 to 53 % (GOPE00CZE), 34 to 44 % (DOY 145). **The run started 1 h later holds almost no GPS** (1.5 to 5 %, 37 links against 332 from start 0), which is why the two-start audit has only 2 872 GPS checks: a read for the GPS held share, the next item.

Every bar of the outcome rule on the remedy passes (the simulator pair, both days with the two-start audit, and the step declaration's twins equal to these streams, section 47). The adoption of section 41.6 stands on the fixed code; both ledger notes are revised (the defect, the fix, DOY 144 and the two-start audit now verified with the remedy, and the GPS wording of DOY 144 corrected: its two-start audit covered Galileo L1X/L5X, and GPS beside Galileo was graded from one start with two reference receivers).

## 47. 2026-11-15: results of section 43, the stream signals its steps

The five step-declaration arms ran on exe nrf20, all exit 0. Grades: `scripts/stream_disc_check.py`, `scripts/stream_cause_check.py` (new), timing and drift reads in `_irdu_grades/scripts_s20/`.

**Bar 4, the estimates:** every `d10` arm's products equal its `o10` twin's line for line once the discontinuity counters are dropped (the five pairs: 389 271, 389 271, 391 680, 391 680 and 326 085 lines, 0 differing).

**Bar 1, steps against increments** (all hours, the four families):

| arm | whole steps moved (without an increment) | fraction steps moved (without) | increments behind a whole or fraction step | not classified | forced |
|---|---|---|---|---|---|
| `d10_n144` | 166 (0) | 3 014 (0) | 3 180 | 458 | 214 |
| `d10_n144r` | 157 (0) | 3 257 (0) | 3 414 | 450 | 214 |
| `d10_n145` | 151 (0) | 3 345 (0) | 3 496 | 388 | 130 |
| `d10_n145r` | 154 (0) | 3 285 (0) | 3 439 | 385 | 132 |
| `d10_n145b` | 176 (0) | 3 580 (0) | 3 756 | 290 | 111 |

Every whole and fraction step carries an increment on each moved signal, and no increment stands behind a quiet or ionosphere-like step. The others are listed by cause: keys the class rule could not classify (a satellite back after a gap, a bias missing at the previous epoch), declared by the value test, and the satellites of the R record (forced marks). As section 43 said, this agreement holds by construction (the rule and the checker share one classification); bar 2 is the independent one.

**Bar 2, the cause side** (all five arms; `scripts/stream_cause_check.py`, the breakdown by time in `_irdu_grades/nrf_d10_cause_breakdown.txt`). No known re-pin with a non-zero step remains on any arm (the fixed remedy keeps a re-host only at a step of 0), so the chain events are the releases (declared keys):

| arm | releases | with an increment at that epoch | without | of these, an increment within 10 min | none within 10 min | increments with nothing in the chain at their epoch |
|---|---|---|---|---|---|---|
| `d10_n144` | 733 | 536 | 197 | 80 | 117 | 3 147 |
| `d10_n144r` | 816 | 592 | 224 | 96 | 128 | 3 317 |
| `d10_n145` | 825 | 531 | 294 | 84 | 210 | 3 385 |
| `d10_n145r` | 797 | 549 | 248 | 67 | 181 | 3 307 |
| `d10_n145b` | 975 | 660 | 315 | 101 | 214 | 3 414 |

**The levels released without an increment still move** (DOY 144, `d10_n144`): over the 10 min after the release the satellite's level, less the family's median, moves by a median 0.198 cycle, 0.458 at the 90th percentile and 1.452 at most (E14 on Galileo L1C/L5Q at TOW 17940), more than 0.15 cycle in 75 of the 113 that can be read, by steps each under the tolerance: creep the class rule does not see. They are on the unheld families mostly (Galileo L1C/L5Q 47, GPS L1W/L2W 52, GPS L1C/L2W 11, Galileo L1X/L5X 3). **The increments with nothing in the chain** follow a release or fall in the first hour: on DOY 144, 960 come within 10 min after a release of the same satellite signal (the freed level re-converging), 189 later after one, and 1 998 with no release of that satellite signal before them, 1 973 of these in the first hour (the cold start's convergence of the floats, every family) and 25 after it; the other arms read alike (with no release before and after the first hour: 31, 61, 66 and 53). **The cause side fails by the letter** on every arm: a release does not always raise an increment, and a freed level can creep unsignalled. **Proposed (not built):** the chain's declared keys raise the phase increment of each released satellite signal at the release epoch, in addition to the class rule, so a user drops its ambiguity there and the creep that follows lands on a float; with the settled flag (section 45) the signal is then unflagged until it is held again, so the user does not fix during the creep. This failure concerns the declaration (UNVALIDATED, off), not remedy (a): the estimates are the same with and without it (bar 4).

**Bar 3, ionosphere-like steps that move the wide lane** (the wide lane d1 - d2 by more than 0.25 cycle, per satellite-hour, `d10_n144`): Galileo L1X/L5X (held) depth 1 none (largest 0.134), depth 3 0.05 (4, largest 0.716), depth 5 0.06 (2, largest 0.410), depth 7 and more none; GPS L1C/L2W (held) none at any depth (largest 0.218); Galileo L1C/L5Q (not held) 0.03, 0.06, 0.32 and 1.01 per satellite-hour from depth 1 to 7 and more (largest 0.606); GPS L1W/L2W (not held) 0.03 at depth 3 (2, largest 0.279). All six on the held Galileo family fall in the first 1.5 hours (TOW 30 to 1800: E05 0.716, E27 0.572, E29 0.410, E14 0.385, E19 0.379 and -0.267 cycle), during the cold start. Over the five arms the held families' such steps fall in the first hour but for two, both on GPS L1C/L2W on DOY 145 (G14 at TOW 102060, -0.326 cycle; G27 at TOW 105360 in the run started 1 h later, -0.308); held Galileo has none after the first hour. **Proposed (not built):** a wide-lane step of its own: when an ionosphere-like step moves a satellite's wide lane by 0.25 cycle or more, a per-signal wide-lane counter on the P record (a self-describing token, for instance `wlstep=<n>`, beside the phase counter) increments, and a user re-floats its wide-lane ambiguity on that satellite while keeping its narrow-lane state; on these two days it would fire in the first hour on the held families, where the settled flag already says not to fix, and twice after it on GPS.

**Section 43's design question, which signals are settled:** answered and built as section 45 (the flags); its read on `o2s1j_n144` stands (21 % of satellite-epochs flagged in hour 1 under rule B, 92 % in hour 2, 97 to 100 % after, 0.05 flips per satellite-hour after the first hour), and the wide lane is integer for a user at a network receiver from the first hour (the requesting session's replays), hence `wide_lane_integer` 1 on every satellite of a held family.

## 48. 2026-11-15: results of section 44, the decision cap as a key

The cap arms on exe nrf21 (`6cc0823967615e00`, commit 1c888c1), the cap of 3 on exe nrf20 (`kd_sim[_r]`), all exit 0, 360 of 360 epochs emitted. Grades: `_irdu_grades/nrf_kq_grade.txt` (script `_irdu_grades/scripts_s20/grade_kq.sh` with `kq_reads.py`).

**Keys absent identical:** `kf_sim` (exe nrf21, no new key) against `kd_sim` (exe nrf20) and `ki_sim` (the key at 3) against `kf_sim`: the products and the 42 CSV traces identical apart from three traces' wall-clock columns (section 49); `kg_sim` (exe nrf22) against `kd_sim` the same.

### 48.1 The golden simulator bed (3 h from 00:30:15, the adopted set; the default receiver and S45000SIM)

| cap | arm | decisions wrong | held link-epochs (wrong) | two-reference audit: checks, failing | decisions per epoch: p50, p99, largest | refused by the cap (Galileo, GPS) | RAIM rows | monitor releases |
|---|---|---|---|---|---|---|---|---|
| 3 | `kd_sim` | 0 | 126 977 (0) | 190 848, 0 | 3, 3, 3 | 8 162, 17 012 | 0 | 0 |
| 3 | `kd_sim_r` | 0 | 121 358 (0) | | 3, 3, 3 | 10 251, 16 091 | 0 | 1 |
| 6 | `kq6_sim` | 0 | 164 453 (0) | 291 150, 0 | 2, 6, 6 | 1 522, 2 308 | 0 | 0 |
| 6 | `kq6_sim_r` | 0 | 158 152 (0) | | 2, 6, 6 | 1 498, 2 425 | 0 | 1 |
| 12 | `kq12_sim` | 0 | 172 293 (0) | 314 434, 0 | 2, 12, 12 | 35, 102 | 0 | 0 |
| 12 | `kq12_sim_r` | 0 | 167 618 (0) | | 2, 12, 12 | 28, 72 | 0 | 1 |
| none | `kq0_sim` | 0 | 172 595 (0) | 315 510, 0 | 2, 18, 27 | 0, 0 | 0 | 0 |
| none | `kq0_sim_r` | 0 | 168 145 (0) | | 2, 15, 24 | 0, 0 | 0 | 1 |

(Decisions per epoch over the 354 epochs of the trace; the p50 of 2 is over every epoch, 3 or 2 over the epochs with a decision.)

**Held share by half hour** (% of the chord link-epochs, the default receiver; S45000SIM in the grade file):

| cap | Galileo L1C/L5Q | GPS L1C/L2W |
|---|---|---|
| 3 | 2.6, 28.1, 58.5, 82.6, 85.4, 91.3 | 1.9, 17.0, 34.1, 49.4, 72.0, 87.7 |
| 6 | 3.0, 43.7, 86.5, 92.0, 90.5, 92.2 | 2.5, 26.9, 71.7, 91.0, 90.9, 90.7 |
| 12 | 3.1, 53.3, 91.3, 91.8, 90.6, 92.2 | 2.6, 37.9, 82.1, 91.0, 91.0, 90.8 |
| none | 3.1, 54.1, 91.4, 91.8, 90.6, 92.2 | 2.7, 38.3, 82.2, 91.0, 91.0, 90.8 |

Every bar passes at every value: 0 wrong against truth (decisions and held link-epochs), the two-reference audits zero, every epoch emitted, keys absent identical. The cap of 3 held back the second hour: with 12 the shares reach 91 % (Galileo) and 82 % (GPS) in the third half-hour against 59 % and 34 %, and the held link-epochs rise by 36 % and 38 %. Without a cap the run holds 0.2 % and 0.3 % more link-epochs than with 12 and takes up to 27 decisions in one epoch (the cap of 12 binds in the second half-hour only, 35 and 102 link-epochs refused). **Chosen for DOY 144: 12**, the share of no cap within 0.3 % with a bound kept on a burst of decisions.

### 48.2 DOY 144 at 12 (exe nrf22, `a8444bdbcebf4b6a`)

`q12_n144` and `q12_n144r`: the adopted set of section 42 with the key at 12 (the default receiver and GOPE00CZE), against `o10_n144[r]` (the cap of 3, exe nrf20). Grade `_irdu_grades/nrf_q12_grade.txt` (script `_irdu_grades/scripts_s20/grade_q12.sh`).

| arm | cap | same-start audit: checks, failing | held link-epochs (Galileo L1X/L5X, GPS L1C/L2W) | decisions per epoch: p99, largest | refused by the cap | RAIM rows | releases: gap, slip, refloat, chain, monitor |
|---|---|---|---|---|---|---|---|
| `q12_n144` | 12 | 285 744, 0 | 169 744 (87 420, 82 324) | 8, 12 | 9 | 0 | 237, 39, 1, 0, 1 |
| `q12_n144r` | 12 | | 153 114 (88 606, 64 508) | 9, 12 | 0 | 0 | 214, 41, 1, 0, 0 |
| `o10_n144` | 3 | 281 011, 0 | 170 548 (86 544, 84 004) | 3, 3 | 939 | 0 | 236, 39, 1, 3, 1 |
| `o10_n144r` | 3 | | 152 926 (88 283, 64 643) | 3, 3 | 446 | 0 | 205, 41, 1, 0, 0 |

The audit at 12 by signal: Galileo L1X 83 945 and L5X 83 925 checks, GPS L1C 58 776 and L2W 59 098, 0 failing. Every epoch emitted (720 of 720), every release named, RAIM rows 0 as at 3: **every bar passes.** On observed data the cap of 3 binds in the first hour only (835 of its 939 refusals and 365 of 446 fall in the first 1.5 h); the binding refusals there are the window, the fraction and the odds. So 12 changes little: the held link-epochs differ by -0.5 % and +0.1 %; the start is held sooner (Galileo 37.9 and 82.6 % in the second and third half-hours against 33.0 and 77.0, GPS 32.3 against 27.3 in the second); later the default receiver's GPS share runs 4 to 5 points lower in half-hours 7 to 10 (54.0, 53.2, 54.4 and 60.4 % against 58.1, 58.4, 59.5 and 65.3), GOPE00CZE's within a point of the cap of 3.

**Adopted** under the author's rule (an improvement that passes its bars is adopted): `network.ring_fix.max_decisions_per_epoch` 12 in the chain posture with network integer fixing (RECOMMEND_SCOPED, armed when 12; the loader default stays 3, identical when absent), with the three-part note: done on 2026-11-15; verified by the golden simulator bed at four values with two reference receivers and DOY 144 with two reference receivers (basic); to do: DOY 145 and a two-start audit at 12, more stations and days, the main posture without the chain.

## 49. 2026-11-15: results of section 45, the settled flags: two defects of the build, fixed

**Keys absent identical** (exe nrf21): `kf_sim` (no new key) against `kd_sim` (exe nrf20): the products and the 42 CSV traces identical apart from the wall-clock columns of three (`ms` of the datum graph, `loop_ms` and `ms_per_epoch` of the run summary, `ms_per_epoch_window` of the service health), which are identical once those columns are dropped.

**The first stream, `f10_n144`** (exe nrf21, the DOY 144 stream with the step declaration and the flags). Its products equal `d10_n144`'s once the two flag fields of the P record are masked (389 271 lines, 0 differing): the step declaration's increments are unchanged by the flags. Against rule B (`scripts/nrf_settled_flags.py --check`): of 87 638 records of held families, 156 differ (Galileo L1X/L5X 94, GPS L1C/L2W 62), and 2 390 records of no held family carry a flag. Two defects of the build, both on the path with the key on:

1. **The 2 390 are GPS L1W records copied from L1C.** The wire fill (`network.n3c_wire_per_signal`) copies the record of the same band and channel family into a modelled signal a satellite lacks this epoch (L1W from L1C: the same value), and it runs after the flags were stamped, so the copy carried L1C's flags. **Fixed:** the flags are stamped last, after the fill (`ringFixStampSettledFlags`), so a filled record takes the flags of its own signal, 0 for a signal of no held family; unit test `RingFixSettledFlags.TheStampFlagsHeldFamiliesOnlyAndAFilledCopyTakesItsOwnSignalsFlags`.
2. **The 156 are held links in a tracking gap.** They fall in three spells, every one with the stream flagged and rule B not: E36 from TOW 4950 to 5820, E09 from 6180 to 6660, G15 from 8670 to 9570. Each satellite was reached only through one held link whose receiver had stopped observing it: ULAB00MNG-E36 has no observation from TOW 4950 and is released for the gap at 5850, 3 780 s after its decision. The code counted every held link; the rule reads the trace, which lists the links that are chords this epoch. A held link without an observation carries no information that epoch, so the rule's reading is kept. **Fixed:** the settled graph takes only the held links that are chords this epoch.

Both fixes are confined to the key's path (the stamp and the graph run only with `network.ring_fix.settled_flags`); exe nrf22 (`a8444bdbcebf4b6a`, commit 6ddb293).

**The stream as fixed, `f11_n144`** (exe nrf22): every bar passes. The emitted flags equal rule B at every epoch (87 638 records of held families compared; the 65 168 records of no held family all 0 and 0; no mismatch). The products equal `d10_n144`'s with the two flag fields masked (389 271 lines, 0 differing), so the step declaration's increments are unchanged. Keys absent identical on exe nrf22: `kg_sim` against `kd_sim`, the products and the 42 traces, wall-clock columns aside. **Flips:** 142 changes of a satellite signal's flag in 6 h (run end; a satellite's two signals change together); from hour 2, 0.08 per satellite-hour on Galileo L1X/L5X and 0.22 on GPS L1C/L2W. **Flagged share** by hour from hour 2: Galileo 90, 98, 95, 95 and 100 %; GPS 44, 66, 73, 80 and 84 %.

**For user replays:** `f11_n144` (DOY 144, Galileo L1X/L5X and GPS L1C/L2W held, the step declaration and the flags). `f10_n144` carries the defective flags and is not for replays; the streams with the declaration and no flags are `d10_*`, those with neither `o10_*`.

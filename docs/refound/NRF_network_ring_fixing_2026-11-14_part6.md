# NRF part 6: remedy (a) and the stream's step declaration (sections 41 onwards of card NRF)

**STATUS**

- **id:** NRF-part6
- **topic:** network-vehicle
- **status:** open
- **summary:** Sections 41 onwards of card NRF (2026-11-15), continued from [part 5](NRF_network_ring_fixing_2026-11-14_part5.md). Section 41: the results of section 39, remedy (a) (`network.ring_fix.rehost_keep_carry`: a chain re-host onto a held link keeps the moved side's carries): every bar passes on the golden simulator bed, bed B of section 36 and the DOY 145 holding pair (same-start audit 0 of 147 280, E18's level within 0.015 m between two reference receivers); why Galileo at S45000SIM holds fewer link-epochs (the per-epoch decision cap); the kept steps (micrometres, now a step of 0 under 1e-4 cycle, exe nrf18); what resets a kept receiver phase bias (no field-blocking gap found); the remedy and the formal sigma adopted in the chain posture. Section 42: the adopted set on DOY 144 and DOY 145 with GPS beside Galileo, pre-registered. Section 43: the stream's step declaration on that stream, pre-registered.
- **source:** [part 5](NRF_network_ring_fixing_2026-11-14_part5.md) sections 35 (the code-reference window of DOY 145), 38 to 40 (the window's results) and 39 (remedy (a), pre-registered); [part 4](NRF_network_ring_fixing_2026-11-14_part4.md) section 24.3 (the remedy proposed); the requesting session's review of 2026-11-15 (four requests for the write-ups).

**Outcome.** Question: does remedy (a), a chain re-host onto a link the ring fix holds keeping the moved side's carries instead of releasing them, cure the DOY 145 departure without harm? Yes on this evidence. On the golden simulator bed it keeps 212 and 154 re-hosts, erases about 72 % fewer carried entries, holds more link-epochs and decides nothing wrong against truth; on DOY 145 the same-start audit reads 0 of 147 280 checks (271 failing without) and E18's level agrees within 0.015 m between the two reference receivers (0.741 m without). A held link's carry sits on its integer to micrometres, now counted as a step of 0. Adopted in the chain posture with network integer fixing: the remedy and the formal sigma (section 41.6).

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

# NRF part 8: the flags by the largest tied set, the configured families, the GPS wide lane (sections 61 onwards of card NRF)

**STATUS**

- **id:** NRF-part8
- **topic:** network-vehicle
- **status:** open
- **summary:** Sections 61 onwards of card NRF (2026-11-16), continued from [part 7](NRF_network_ring_fixing_2026-11-14_part7.md). Section 61: rule L of the settled flags built (`network.ring_fix.settled_rule` "largest", default off): the largest set of a family's satellites tied through held links and certified tree edges, whatever receiver roots it, once it holds 4 satellites, the incumbent kept until another holds 2 more; 61.1: every exact bar passes (keys absent identical, values unchanged, the flags equal the script at every record; streams `l12_n144` and `l12_n145`), and the truth bar on the simulator fails under rule B as well, rule L adding 3 GPS pair-epochs above 0.25 cycle in the first 90 min. Section 62: the chord table forms every configured family (`network.ring_fix.form_configured_pairs`, default off); 62.1: the log arm `t3l` on four families decides right against truth and the shared signal agrees. Section 63: GPS's held share is short on the wide lane. Sections 64 to 66 pre-registered: GPS L1C/L5Q held on the simulator; GPS band 1 on L1C before L1W; the unsettled steps of the signals of no held family (`network.ring_fix.unsettled_steps_unheld`, built, default off).
- **source:** [part 7](NRF_network_ring_fixing_2026-11-14_part7.md) sections 58 (rule L proposed) and 60 (the third frequency's plan); the requesting session's orders A, B and C after section 60.

**Outcome.** Rule L of the settled flags is built and passes every exact bar; its streams `l12_n144` and `l12_n145` equal u12's apart from the flags and the counters. On the simulator the truth bar fails under rule B as well (phase moves of flagged satellites), and rule L adds 3 GPS pair-epochs above 0.25 cycle in the first 90 min. The chord table now forms every configured family, and a third band's second family decides right with the shared signal agreeing: the cascade is next. GPS's held share is short on the wide lane; GPS band 1 on L1C, GPS L1C/L5Q and the steps of signals of no held family are running.

## 61. 2026-11-16: the settled flags by the largest tied set (pre-registered)

**Why** (the requesting session's order A after section 60): rule L of section 58 gains the first two hours (Galileo C/Q 61 to 75 points, GPS 45 to 58) with the segment bar as rule B; built with a minimum of 4 satellites and a hysteresis of 2 (section 58's proposal), a key of its own, rule B the default of the flags.

**The build** (exe nrf26; key `network.ring_fix.settled_rule`, "root" by default (rule B) or "largest" (rule L), needs `network.ring_fix.settled_flags`; ledger row UNVALIDATED). `ringFixLargestSettledSet` (`network/ar/RingFix`): the held links of a family that are chords this epoch and its certified tree edges form a graph over receivers and satellites (`arcgraph::Dsu`); the family's first-band tree satellites fall into its components. The incumbent (last epoch's flagged set) is followed into the component holding most of it, which stays flagged, with this epoch's membership, while it holds at least 4 satellites and no other component holds 2 more; otherwise the largest component is flagged when it holds at least 4, and none below. Ties go to the component whose lexically smallest satellite comes first; an epoch without the family's tree clears the incumbent. With `network.ring_fix.unsettled_steps` on, the emitter's rule reads the emitted flags, so a satellite that leaves the set steps at every emission and one that joins takes the settling step. The run-end line adds the changes of identity (another component replacing a non-empty incumbent) and the satellites that changed side at them. Unit test `RingFixSettledFlags.TheLargestSetNeedsFourSatellitesAndKeepsTheIncumbentUntilAnotherLeadsByTwo`.

**Arms** (exe nrf26, `95eea9710201a513`): `l12_n144` and `l12_n145` (`u12_n144` and `u12_n145` with the key: the step declaration, the release increments, the flags by rule L and the unsettled steps), the streams for user replays; `l12_sim` (`kq12_sim` with the step declaration on its two families, the flags, the unsettled steps and rule L); `kl_sim` (`kd_sim`'s configuration) and `u13_n144` (`u12_n144`'s: the flags on, the rule key absent) for keys absent identical; 10-epoch smokes first (`l12smoke`, `t3l26smoke`: exit 0).

**Bars** (the order's): keys absent identical (`kl_sim` against `kd_sim`, exe nrf20; `u13_n144` against `u12_n144`, exe nrf24); with the key on, the C, B and P values of `l12_n144` and `l12_n145` equal `u12_n144`'s and `u12_n145`'s (only the flags and the phase counters move); the emitted flags equal `flag_root.py`'s rule L, with the minimum and the hysteresis, at every record; on the simulator bed with truth, every pair of flagged satellites integer-consistent at every epoch, or not worse than rule B; the run-end line reported.

**The truth audit of flagged pairs** (`_irdu_grades/scripts_s20/flag_truth.py`, measured on `kq12_sim` before the runs). Per satellite the stream error a user's ambiguities absorb is W_b = [C - clk_err_true] - [P_b - osb_true] (`scripts/simnet_wire_integer_consistency.py`). Its per-band fractions against truth are not a test: the network's satellite GF code bias sits at the broadcast T_GD, its error goes into the slant ionosphere, and every user's own slant ionosphere absorbs it alike (with the code's implied ionosphere added back, the band fractions keep a residual with E_2 about (f1/f2) E_1). A user fixes a pair's wide lane through the Melbourne-Wubbena combination and its narrow lane through the ionosphere-free row, so the audit grades each flagged pair's MW (wide-lane cycles) and NL (narrow-lane cycles, the wide lane rounded), wrapped; a pair above 0.25 cycle is inconsistent. On `kq12_sim` over 3 h, with each rule stamped from the run's own traces by `flag_root.py` (whose rule B reproduces the emitted flags of `u12_n144` exactly: 0 of 87 638 records differ):

| flagged set | GPS L1C/L2W pairs | above 0.10 / 0.25 cycle | Galileo L1C/L5Q pairs | above 0.10 / 0.25 cycle |
|---|---|---|---|---|
| every satellite (the stream's null) | 171 218 | 40 204 / 20 885 | 104 112 | 18 888 / 10 240 |
| rule B | 96 979 | 198 / 10 | 79 131 | 180 / 16 |
| rule L | 123 111 | 894 / 13 | 79 656 | 256 / 16 |

Under rule B the pairs above 0.25 cycle are one satellite's MW excursion of one or two epochs (G30 at TOW 268 740, MW 0.30, NL 0.03; E27 at 263 520), a code transient and not a phase inconsistency: the strict bar fails under rule B as well. Rule L adds 3 GPS pair-epochs, G23-G27 at TOW 263 460 to 263 490 (NL 0.257 to 0.259, about 40 min after the start); its larger count above 0.10 is the first hour, where it flags and rule B does not. `l12_sim` carries the same values as `kq12_sim`, so its audit repeats this table unless the build's flags differ from the stamp.

### 61.1 2026-11-16: rule L: the build's bars pass; the truth bar fails under both rules

Exe nrf26 (`95eea9710201a513`, commit c72f652); every arm exits 0 with every epoch emitted; 10-epoch smokes first. Grades `_irdu_grades/nrf_l12_sim_grade.txt`, `nrf_l12_obs_grade.txt` and `nrf_l12_u13_grade.txt` (script `_irdu_grades/scripts_s20/grade_l12_stage.sh`).

- **Keys absent identical:** `kl_sim` (nrf26) against `kd_sim` (nrf20): the products and the 42 CSV traces identical, wall-clock columns aside. `u13_n144` against `u12_n144` (exe nrf24): identical (61.2).
- **Only the flags and the counters move:** `l12_n144` and `l12_n145` equal `u12_n144` and `u12_n145` with the flags and the phase counters masked (389 271 and 391 680 lines, 0 differing); the flags move 4 156 and 11 038 lines, the counters 37 445 and 59 764; of the 39 CSV traces 4 differ, the network's solution trace (its counter column) and the run's own closed-loop consumer's three, which read the flags and the counters (the requesting session's re-check agrees). On the simulator, `l12_sim`'s E, C, B and P values equal `kq12_sim`'s (100 965 records, 0 differing): the step declaration, the flags, the unsettled steps and rule L move no value.
- **The emitted flags equal `flag_root.py`'s rule L** (minimum 4, hysteresis 2) at every record: `l12_sim` 0 of 40 242 family records; `l12_n144` 0 of 87 638 and `l12_n145` 0 of 88 446.
- **Run-end lines:** `l12_sim` 31 688 satellite-signal-epochs flagged, 8 554 not, 120 flips; rule L 0 changes of identity, 0 satellites changed side (`flag_root.py` counts 0 as well); unsettled steps Galileo L1C/L5Q 3 412 while unsettled and 52 at the settling, GPS L1C/L2W 5 028 and 68. `l12_n144` 65 128 flagged, 22 510 not, 150 flips; `l12_n145` 61 148, 27 298 and 174; rule L 0 changes of identity on both days. Unsettled steps with rule L (with rule B, `u12`): DOY 144 Galileo 6 962 and 66 (7 314 and 66), GPS 15 424 and 70 (19 228 and 66); DOY 145 Galileo 6 986 and 72 (14 894 and 68), GPS 20 188 and 72 (23 318 and 72). Flagged share in half hours 1 to 4, rule L (rule B): DOY 144 Galileo 2 43 89 91 % (0 36 89 91), GPS 3 54 64 67 % (0 0 22 67); DOY 145 Galileo 1 39 84 96 % (0 0 0 0), GPS 3 45 59 52 % (0 0 25 52); the same afterwards.
- **Flagged pairs against truth** (`flag_truth.py`, MW and NL wrapped; rule B stamped from the run's own traces): pairs, above 0.10 and above 0.25 cycle, by half hour:

| half hour | GPS rule B | GPS rule L | Galileo rule B | Galileo rule L |
|---|---|---|---|---|
| 1 | none flagged | 232; 28; 0 | none flagged | 415; 55; 0 |
| 2 | none flagged | 14 600; 616; 3 | 11 139; 146; 16 | 11 249; 167; 16 |
| 3 | 14 175; 60; 0 | 25 475; 112; 0 | 16 776; 31; 0 | 16 776; 31; 0 |
| 4 to 6 | 82 804; 138; 10 | the same pairs | 51 216; 3; 0 | the same pairs |

  The bar as written (every flagged pair integer-consistent at every epoch) fails under rule B as well as rule L. From the fourth half hour both rules flag the same pairs. Rule L's additions all fall in the first 90 min: on GPS 26 132 pairs, 696 above 0.10 cycle (2.7 %, against 0.4 % of rule B's own pairs in the third half hour) and 3 above 0.25 (G23-G27 at TOW 263 460 and 263 490, NL 0.257 and 0.259); on Galileo 525 pairs, 76 above 0.10 and none above 0.25. Against rule B, rule L is worse by those 3 GPS pair-epochs above 0.25 cycle and by 772 above 0.10, all where rule B flags fewer satellites or none.
- **Section 61's reading of rule B's pairs above 0.25 cycle is corrected:** they are not a code transient. The satellites' code biases do not move there (every B record steps 0.000 m); the phase biases do. G30's step at TOW 268 740 (-0.181 m on L1C, -0.293 m on L2W, ratio 1.62, ionosphere-like) is declared by the producer's counter (82 to 83); its next move at 268 830 (+0.075 and +0.119 m, ionosphere-like, about 0.11 wide-lane cycle) is not, under the class rule's 0.15 tolerance. E27's phase biases move by 1 to 10 cm per epoch from TOW 263 520, the epoch at which both rules flag it, under a constant counter (82), its MW 0.2 to 0.3 cycle off for a few minutes: the simulator's own case of a flagged level that moves under constant counters, in the first hour, under rule B as under rule L.

### 61.2 2026-11-16: keys absent identical on observed data

`u13_n144` (exe nrf26, `u12_n144`'s configuration: the flags on, the rule key absent) against `u12_n144` (exe nrf24): the products and the 39 CSV traces identical, wall-clock columns aside (grade `_irdu_grades/nrf_l12_u13_grade.txt`). Every bar of section 61 that the build answers passes; the truth bar on the simulator fails under both rules (61.1).

## 62. 2026-11-16: the chord table forms every configured family; the log arm `t3l` (pre-registered in section 60)

**The build** (exe nrf26; key `network.ring_fix.form_configured_pairs`, default false, needs `network.ring_fix.pairs`; ledger row UNVALIDATED). `chainArcFamilies` (`network/solve/ChainChordTable`) gives an arc's pair families: the rule of `chainPairFamilies` (every band-1 signal with the arc's lowest-digit signal of another band) and, with the key, every configured family of the satellite's constellation whose two signals the arc tracks and that the rule does not form. The ring fix's chord rows and its inheritance of old hosts' carries use it. Unit test `ChainArcFamilies.AConfiguredFamilyOfAThirdBandIsFormedBesideTheRule` (a file of its own, `tests/network/test_chain_arc_families.cpp`). The 10-epoch smoke of the log arm (`t3l26smoke`) shows the families formed: Galileo L1C/L7Q 1 521 chord rows (8 in `t3lsmoke` without the key), GPS L1C/L5Q 2 067 (none), Galileo L1C/L5Q and GPS L1C/L2W unchanged (1 513 and 2 067).

**Arms** (exe nrf26): `t3l_sim` and `t3l_sim_r`, section 60's log arms with the key: the three bands of the simulator (card L5B section 11's four keys), the ring fix in log mode on GPS L1C/L2W and L1C/L5Q and Galileo L1C/L5Q and L1C/L7Q, the adopted set at the cap of 12 (`kq12_sim[_r]`), 3 h from 00:30:15, the default receiver and S45000SIM. The results of `t3c` are section 60.1 (part 7).

**Bars** (section 60's): every family's would-be decisions right against truth at 99.9 % or more; on every arc decided by two families the shared signal's integers equal; within a constellation, each band's tree on the same datum receiver. The would-be decisions are graded offline (`_irdu_grades/scripts_s20/t3l_truth.py`): each row in state would_hold against the true integer of its arc in the frame of its epoch (`scripts/ird_frame_census.py`, `frame_integer`, with the producer's wind-up branch per arc), since the producer's truth audit counts held links only. The grader reproduces that audit on `kq12_sim`'s held rows: 79 135 and 94 203 link-epochs right, 0 wrong (the audit: 0 wrong).

### 62.1 2026-11-16: `t3l`: every bar passes

Exe nrf26; both runs exit 0 with every epoch emitted and RAIM rows 0; a 10-epoch smoke first (`t3l26smoke`). Grade `_irdu_grades/nrf_l12_t3l_grade.txt` (script `_irdu_grades/scripts_s20/grade_l12_stage.sh t3l`: `t3l_truth.py`, `scripts/nrf_log_reads.py`, `scripts/nrf_two_run_audit.py`).

- **Every family's would-be decisions right against truth** (bar 99.9 %): `t3l_sim` Galileo L1C/L5Q 30 627 link-epochs and 322 links right, L1C/L7Q 29 603 and 309, GPS L1C/L2W 32 229 and 391, L1C/L5Q 34 235 and 401; `t3l_sim_r` 31 079 and 340, 30 097 and 331, 27 405 and 405, 29 988 and 432; none wrong, none ungradeable.
- **The shared signal's integers equal** wherever two families decide one arc: 61 050 and 56 614 (epoch, station, satellite) rows, none differing.
- **Each band's tree on the same datum receiver** within a constellation at every epoch: `t3l_sim` GPS S13000SIM and Galileo S03000SIM, `t3l_sim_r` S45000SIM for all six bands.
- **The two runs agree:** the same-start audit of the would-be integers fails 0 of 60 045 checks (Galileo L1C 10 558, L5Q 10 295, L7Q 9 465; GPS L1C 10 498, L2W 9 180, L5Q 10 049).
- Reads (`t3l_sim`): 1 423 of 2 502 links reach a would-be decision, the first at p50 48 min (p90 89) after their first chord row; refused link-epochs by cause: window 177 462, odds 92 882, fraction 72 978, persistence 31 382, wide-lane bound 77.

On the simulator a third band's second family decides right and agrees with the first on the shared signal. By section 60's plan the next step is the cascade, built default off and held on the simulator.

## 63. 2026-11-16: what separates GPS's held share from Galileo's: the wide lane

**Why** (the requesting session's order C after section 60): for the GPS L1C/L2W links refused at the odds test and at the fraction bound, against Galileo's: the float's formal sigma, the wide lane's settle time and scatter (the code on L2W), the time since the arc's start, by receiver type; in one line, whether the wide lane (code) or the narrow lane (phase and geometry) is what is not decisive on GPS.

**How** (`_irdu_grades/scripts_s20/gps_wl_nl.py` on `u12_n144` and `u12_n145`, from hour 2; grade `_irdu_grades/nrf_orderC_wl_nl.txt`). Each chord row of the ring-fix trace carries the two bands' floats, the wide lane's fraction, the narrow-lane float of the ionosphere-free row with that wide lane, and its formal sigma (the ionosphere-free combination of the two floats, so a narrow-lane quantity once the wide lane is whole). A refusal counts as wide-lane-limited when the wide lane's fraction exceeds 0.15 cycle, or, on GPS only, when the other wide lane brings N1 within 0.10: a wide lane off by one moves N1 by f2 / (f1 - f2) cycles, 3.53 on GPS L1/L2 (a fraction of 0.47) but 2.95 on Galileo E1/E5a (a fraction of 0.05, which hides it). Per arc of 60 min or more: the wide lane's settle (its fraction below 0.10 for 10 epochs), its scatter after the settle, and the wait from the settle to the arc's first hold.

**Results** (DOY 144; DOY 145):

| | Galileo L1X/L5X | GPS L1C/L2W |
|---|---|---|
| link-epochs refused at the odds test / at the fraction bound | 1 078 / 1 618; 1 232 / 827 | 10 931 / 18 786; 17 091 / 25 015 |
| of them wide-lane-limited (odds / fraction) | 43 / 19 %; 56 / 21 % | 71 / 74 %; 72 / 77 % |
| refusals wide-lane-limited, from 0-15 min to 120 min and more after the arc's start | 32 to 5 %; 42 to 0 % | 63 to 77 %; 68 to 75 % |
| narrow lane's formal sigma, refusals with a wide-lane fraction under 0.10 (p50, cycle) | 0.100; 0.124 | 0.771; 0.668 |
| arcs whose wide lane never settles | 1 of 307; 0 of 285 | 34 of 468; 56 of 468 |
| the wide lane's settle p50; its scatter p50 after the settle (cycle) | 13.0 min, 0.015; 18.0 min, 0.015 | 15.8 min, 0.025; 22.2 min, 0.046 |
| narrow lane at the settle: formal sigma p50 (cycle) | 0.162; 0.146 | 0.276; 0.639 |
| after the settle: first hold within 30 min / never | 79 / 3 %; 81 / 1 % | 59 / 23 %; 41 / 35 % |
| arcs settled and never held: their refused epochs with the wide lane out again (fraction above 0.15) | 3 % of 8 arcs; 29 % of 4 | 53 % of 99 arcs; 59 % of 145 |

By receiver type on GPS, the wide lane's scatter is largest on Trimble Alloy (0.042 and 0.130 cycle) and Septentrio AsteRx4 (0.034 and 0.284), and the arcs that never settle are mostly PolaRx5 (15 and 24) and Alloy (12 and 20); on Galileo every type settles (JAVAD TRE_G3TH latest, 29 and 48 min).

**Answer: the wide lane (code).** Three quarters of the GPS refusals come with a wide lane that is not decisive, at every arc age, while Galileo's fall to 0 to 5 % after the first hour; one GPS arc in eight to fourteen never settles its wide lane, and on arcs that settle but never hold the wide lane leaves again in more than half of the refused epochs. The narrow lane is weaker on GPS as well (formal sigma at the wide lane's settle 0.28 and 0.64 cycle against 0.15), a second factor behind the first. By the requesting session's rule the test is GPS L1C/L5Q as the held pair (its wide lane rests on the L5 code), the simulator first; section 62's key makes that family form.

## 64. 2026-11-16: GPS L1C/L5Q as the held pair, the simulator first (pre-registered)

**Why** (the requesting session's order C, its conditional): section 63's answer is the wide lane, so the test is GPS L1C/L5Q as the held pair, whose wide lane rests on the L5 code, after item 0 (section 62: the family forms only with `network.ring_fix.form_configured_pairs`, since the rule pairs L1C with L2W), the simulator first.

**What the simulator can show.** The fixture draws every code with the same zenith noise (0.3 m) and nearly the same multipath (GPS L1 0.02 m, L2 0.03 m, Galileo 0.015 m), so L2W carries no semi-codeless penalty there: the simulator certifies that the family forms and holds right (the algebra and the machinery), not the observed gain, which only observed data can show (on GPS IIF and III satellites, the ones with L5, at receivers that track L5Q).

**Arms** (exe nrf26): `g5_sim` and `g5_sim_r`, `t3c_sim[_r]` (the three bands, the adopted set at the cap of 12, 3 h from 00:30:15, the default receiver and S45000SIM) with the held pairs GPS L1C/L5Q and Galileo L1C/L5Q and the configured families formed; a 10-epoch smoke first (`g5smoke`).

**Bars.** Every epoch emitted; 0 wrong against truth (the producer's audit) and the same-start audit zero; Galileo L1C/L5Q's held link-epochs within 5 % of `t3c_sim[_r]`'s; RAIM rows not above `t3c_sim[_r]`'s by more than a tenth. Reads: GPS L1C/L5Q's held share by half hour against GPS L1C/L2W's in `t3c_sim[_r]`, and its refusals by cause. If the bars pass, observed data follows (DOY 144 and 145, the u12 configuration with the GPS pair replaced), graded as section 63 grades GPS L1C/L2W.

### 64.1 2026-11-16: GPS L1C/L5Q held on the simulator: every bar passes

Exe nrf26; both runs exit 0 with every epoch emitted; a 10-epoch smoke first (`g5smoke`, exit 0). Grade `_irdu_grades/nrf_g5_grade.txt` (script `_irdu_grades/scripts_s20/grade_g5.sh`).

- **0 wrong against truth:** 174 677 and 172 143 held link-epochs right, decisions wrong 0; the same-start audit of the two runs fails 0 of 317 036 checks (GPS L1C 88 239, L5Q 88 209; Galileo L1C and L5Q 70 294 each).
- **Galileo L1C/L5Q within 5 % of `t3c_sim[_r]`:** 79 724 and 74 346 held link-epochs against 79 654 and 74 115 (+0.1 and +0.3 %).
- **RAIM rows** 0 and 0, as `t3c_sim[_r]`.
- **GPS L1C/L5Q holds as GPS L1C/L2W does:** held share by half hour 3.3 46.7 86.3 90.1 88.8 88.2 % and 2.3 52.1 90.1 90.3 90.2 89.7 % (L1C/L2W in `t3c`: 3.1 44.0 85.3 90.3 88.9 88.5 and 1.8 48.7 90.0 90.6 90.5 89.9); held link-epochs 96 004 and 98 857 against 95 344 and 98 078 (+0.7 and +0.8 %).

On the simulator the family forms, holds right and holds as much as GPS L1C/L2W, as expected where L2W carries no code penalty. The observed-data step of section 64 needs the observed triple-frequency posture for GPS; section 65.1 has since shown that most of section 63's GPS shortfall came from the split of band 1 between L1C and L1W, not from the L2W code, so whether GPS L1C/L5Q still needs the observed test is the requesting session's call.

## 65. 2026-11-16: GPS band 1 on L1C before L1W (pre-registered)

**Why** (the requesting session's order D after its review of section 61): `processing.signal_priorities.GPS` lists C1W and L1W before C1C and L1C, so the 17 roster stations that report both on band 1 (15 JAVAD, 2 Septentrio PolaRx5; every one carries C1C and L1C), and the held-out consumer WTZZ00DEU, are processed on L1W/L2W, outside the GPS L1C/L2W family: their L1W is never flagged nor stepped, and its level moves under constant counters (the requesting session's read: segments of constant counters p50 0.6 and up to 5.8 narrow-lane cycles). Section 63's GPS arcs are the other receivers'.

**The datum without C1W** (read in the code before the run). The ionosphere-free code pin pair of each satellite is chosen by `NetworkSbasis::selectIfPinPair` in band-digit, then name order, C1C before C1W, and no bias product's reference pair is armed (`network.n3c_bia_pin_pair` absent): the pair is (C1C, C2W) now (the S record's `cbpin=G:C1C-C2W`) and stays so. The broadcast T_GD target (`NetworkSbasis::satGfBroadcastTarget`) is applied to that pair's GF combination (bands 1 and 2), as now: a P(Y) group delay already applied to C1C-C2W, each satellite's C1C-C1W difference left in its code biases. The code datum is C1C at all 55 roster stations already (the run-start table 'signals as planned' of `l12_n144`: datum code C1C 55, pinned by C1C on 32 satellites), and every station carries C1C on both days. C1W does not leave: the smoke's table shows it as band 1's companion code at the 38 stations that report it (17 had it as their primary code, 21 already as companion), its satellite code biases estimated and emitted as before. What leaves is the L1W phase (17 stations move to L1C). No second key is needed. Two side effects to read: GPS then tracks exactly two phase signals, so the chain's pair-family mode (`phase_datum_eq34_family` "pair") should grow one forest over GPS L1C and L2W in place of three per-band trees; and the per-signal wire fill (`network.n3c_wire_per_signal`) writes an L1W record only while the roster models L1W.

**Arms** (exe nrf26): `p12_n144` and `p12_n145`, `l12_n144` and `l12_n145` with C1C, L1C, D1C and S1C ahead of their W entries in `processing.signal_priorities.GPS` (one knob); a 10-epoch smoke first (`p12smoke`).

**Bars** (against `l12_n144` and `l12_n145`): every epoch emitted; Galileo's held link-epochs not below l12's by more than 2 %; the truth-free check of an observed arm, the segment drift of the flagged runs not above l12's by more than a tenth. **Reads:** the GPS receivers and arcs in the family, the GPS held and flagged shares by half hour, the refusals by cause as in section 63, the run-end ring line, RAIM rows and withheld epochs, whether L1W leaves the stream. The streams are for the requesting session's user replays.

### 65.1 2026-11-16: GPS on L1C: the GPS family covers every receiver and holds as Galileo does; Galileo slower early at the shared decision cap

Exe nrf26; both runs exit 0, 720 of 720 epochs emitted (none withheld); a 10-epoch smoke first (`p12smoke`, exit 0). Grade `_irdu_grades/nrf_p12_grade.txt` (script `_irdu_grades/scripts_s20/grade_p12.sh`). DOY 144, then DOY 145; `l12` in parentheses.

- **The family and the stream.** GPS L1C/L2W spans all 55 receivers (38), 1 107 and 1 121 arcs (746 and 754); the chain grows one forest over GPS L1C and L2W at every epoch (720 pair-family elections against none). L1W leaves the stream (no P record, against 22 727 and 22 716); C1W stays as the companion code (its B records as before).
- **GPS holds as Galileo does.** Held link-epochs 193 129 and 188 978 (84 453 and 56 229). Held share by half hour: DOY 144 2.1 28.2 61.3 82.8 87.9 86.2 88.7 86.4 89.4 88.5 87.9 88.6 % (1.5 27.3 49.0 53.3 51.7 49.6 58.1 58.4 59.5 65.3 62.0 60.9); DOY 145 2.3 27.1 54.6 80.2 87.7 86.3 87.4 84.9 88.3 86.5 86.1 86.9 % (1.4 17.6 31.6 35.7 34.9 35.1 38.9 37.1 38.2 43.7 45.3 43.6). Flagged share (rule L) from the fourth half hour 98 to 100 % on both days (52 to 85 %); one change of identity (DOY 145, TOW 87 990, 11 satellites).
- **The wide lane that section 63 found lacking is there now.** GPS refusals from hour 2 at the odds test and the fraction bound: 1 268 and 1 995 (10 931 and 18 786) on DOY 144, 1 167 and 3 070 (17 091 and 25 015) on DOY 145; the narrow lane's formal sigma of refusals with a decisive wide lane p50 0.106 and 0.080 cycle (0.771 and 0.668). Per arc of 60 min or more: the wide lane never settles on 4 of 726 and 8 of 713 (34 of 468 and 56 of 468); settle p50 11.0 and 12.5 min (15.8 and 22.2), scatter 0.018 and 0.017 cycle (0.025 and 0.046); after the settle the first hold comes within 30 min on 75 and 74 % of arcs (59 and 41 %) and never on 4 and 5 % (23 and 35 %). Section 63's GPS shortfall was mostly the split of band 1 between L1C and L1W: the family's tree spanned two thirds of the receivers, and three per-band trees shared no pins.
- **Galileo is slower in the first 90 min.** Held link-epochs 84 747 and 73 867 (86 909 and 75 202): -2.5 and -1.8 %. Held share in half hours 2 and 3: 24.9 and 56.5 % (33.0 and 77.0) on DOY 144, 16.8 and 56.3 % (31.5 and 78.6) on DOY 145, equal or above from the fourth. The cause is the decision cap of 3 per epoch that these configurations keep (the adopted 12 is not in the u12 lineage), shared by the families: Galileo's link-epochs refused at the cap in half hours 2 and 3 are 997 and 796 (327 and 61) on DOY 144 and 828 and 826 (546 and 0) on DOY 145, while GPS's are 3 365 and 2 806, 3 292 and 3 474 (424 and 0, 284 and 0).
- **Segment drift of the flagged runs** (`stream_seg_drift.py`, hours 1 to 6, whole segments: p90, largest, share of flagged satellite-epochs in segments over 0.15 narrow-lane cycle): GPS 0.161, 0.264, 28.2 % (0.333, 0.415, 84.1 %) on DOY 144 and 0.167, 0.240, 27.3 % (0.269, 0.317, 84.5 %) on DOY 145; Galileo 0.143, 0.248, 21.8 % (0.146, 0.305, 24.5 %) on DOY 144 and 0.192, 0.254, 37.1 % (0.158, 0.262, 26.6 %) on DOY 145.
- **Alarms and the ring line:** RAIM rows 1 and 1 (0 and 1). Released 482 and 518 (280 and 253), slips 109 and 124 (39 and 43), gaps 370 and 383 (236 and 198), monitor 0 and 5 (1 and 2): in proportion to the links.

**Bars.** Every epoch emitted: passes. Galileo's held link-epochs not below l12's by more than 2 %: DOY 145 passes (-1.8 %), DOY 144 fails by 0.5 point (-2.5 %), the loss all in half hours 2 and 3 at the shared cap. The segment drift not above l12's by more than a tenth: GPS far below on both days; Galileo equal on DOY 144; on DOY 145 Galileo's p90 rises by 0.034 cycle (22 %), within a tenth of a cycle, not within a tenth of l12's value. Both streams are fit for the user replays. The cap of 12 adopted in section 48 (`network.ring_fix.max_decisions_per_epoch`) would lift the early Galileo loss: one knob on p12 and on order G's arms, the requesting session's choice.

## 66. 2026-11-16: the unsettled steps of the signals of no held family (built, pre-registered)

**Why** (the requesting session's order E): a phase signal that belongs to no held family is never settled, so with the unsettled steps its counter should step at every emission (GPS L1W at the receivers processed on it; Galileo L1C and L5Q where only L1X/L5X is held).

**The build** (exe nrf27; key `network.ring_fix.unsettled_steps_unheld`, default off, needs `network.ring_fix.unsettled_steps`; ledger row UNVALIDATED). A second key, so that section 54's rule and the streams built on it stay as they are. The emitter adds every phase signal of an emission that belongs to no family of `network.ring_fix.pairs` of its constellation, filled copies included, to the signals that step at every emission with a baseline, counted per constellation under "no held family" on the run-end line. Unit test `UnsettledSteps.WithTheUnheldKeyASignalOfNoHeldFamilyStepsAtEveryEmission`.

**Arms** (exe nrf27): `e12_n144`, `l12_n144` with the key; `km_sim` (`kd_sim`'s configuration) for keys absent identical. **Bars:** keys absent identical; against `l12_n144`, the values unchanged, the family signals' counters unchanged, and every other phase signal's counter changing at every emission that has a baseline.

## 67. 2026-11-16: a wait on the flag's raise (read H)

**Why** (the requesting session's read H): section 61.1 puts rule L's added pairs above 0.10 cycle in the first 90 min, where flagged levels still move (E27's phase biases moving 1 to 10 cm per epoch after its flag rose), and the requesting session's DOY 144 hour-2 cost at the user has the same address. A wait: a satellite is flagged only from the (N+1)-th consecutive emission at which rule L puts it in the set (the unsettled steps go on during the wait, the settling step comes at the delayed raise). A stamp and the truth audit; no run, no build.

**How.** `_irdu_grades/scripts_s20/flag_root.py --wait N` stamps rule L with the wait from the run's own traces (the count restarts when the satellite leaves the set or the family's tree is absent; `--wait 0` reproduces the emitted flags exactly, 0 of 40 242 records differ) on `l12_sim`, whose values equal `kq12_sim`'s, for N = 10, 20 and 40 epochs (5, 10 and 20 min at 30 s); `flag_truth.py` grades each stamp's flagged pairs through their MW and NL against truth, as in section 61. Grade `_irdu_grades/nrf_readH.txt`.

**Results** (3 h from 00:30:15; flagged pair-epochs; of them above 0.10 cycle; above 0.25 cycle):

| flagged set | GPS L1C/L2W | Galileo L1C/L5Q |
|---|---|---|
| rule B | 96 979; 198; 10 | 79 131; 180; 16 |
| rule L | 123 111; 894; 13 | 79 656; 256; 16 |
| rule L, wait 10 | 117 777; 203; 8 | 76 417; 35; 0 |
| rule L, wait 20 | 112 567; 138; 8 | 73 187; 28; 0 |
| rule L, wait 40 | 102 204; 103; 8 | 66 736; 19; 0 |

- **By half hour,** the pairs above 0.10 cycle (GPS; Galileo): rule L 28 616 112 0 138 0; 55 167 31 0 0 3. Wait 10: 0 98 2 0 103 0; 2 16 14 0 0 3. Wait 20: 0 34 2 0 102 0; 0 11 14 0 0 3. Wait 40: 0 0 1 0 102 0; 0 2 14 0 0 3.
- **Above 0.25 cycle,** every wait keeps only G30's declared step at TOW 268 740 (section 61.1: the producer's counter steps there), which a wait on the raise cannot touch. E27's moving level at TOW 263 520 (16 pairs above 0.25 under both rules) falls out at every wait.
- **Flagged pair-epochs lost against rule L:** GPS 5 334, 10 544 and 20 907 (4.3, 8.6 and 17.0 %), Galileo 3 239, 6 469 and 12 920 (4.1, 8.1 and 16.2 %), most in the second and third half hours. Against rule B, GPS keeps 21, 16 and 5 % more flagged pairs and Galileo 3.4, 7.5 and 15.7 % fewer (rule B's Galileo flags rise in the second half hour and are not delayed).

**Reading.** On the simulator a wait of 10 removes most of rule L's early inconsistency (GPS pairs above 0.10 cycle 894 to 203, about rule B's 198 with 21 % more flagged pairs; Galileo 256 to 35, against rule B's 180) for about 4 % of the flagged pairs; 20 brings them to 138 and 28 for twice that cost; 40 costs a sixth of the pairs for little more. Every wait is better than rule B above 0.25 cycle. The requesting session's N = 20 at the users on both observed days completes the read.

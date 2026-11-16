# NRF part 8: the flags by the largest tied set, the configured families, the GPS wide lane (sections 61 onwards of card NRF)

**STATUS**

- **id:** NRF-part8
- **topic:** network-vehicle
- **status:** open
- **summary:** Sections 61 onwards of card NRF (2026-11-16), continued from [part 7](NRF_network_ring_fixing_2026-11-14_part7.md). Section 61: rule L of the settled flags built (`network.ring_fix.settled_rule` "largest", default off): the largest set of a family's satellites tied through held links and certified tree edges, whatever receiver roots it, once it holds 4 satellites, the incumbent kept until another holds 2 more; streams `l12_n144` and `l12_n145`; a truth audit of flagged pairs on the simulator through their wide and narrow lanes. Section 62: the chord table forms every configured family (`network.ring_fix.form_configured_pairs`, default off) and the log arm `t3l` of section 60 on four families. Section 63: what separates GPS's held share from Galileo's: the wide lane.
- **source:** [part 7](NRF_network_ring_fixing_2026-11-14_part7.md) sections 58 (rule L proposed) and 60 (the third frequency's plan); the requesting session's orders A, B and C after section 60.

**Outcome.** Pending the runs of sections 61 and 62. Section 63 answers order C: the wide lane (code), not the narrow lane, is what GPS L1C/L2W lacks against Galileo L1X/L5X. Three quarters of GPS refusals come with a wide lane that is not decisive, at every arc age; one GPS arc in eight to fourteen never settles its wide lane. The narrow lane is weaker on GPS as well, a second factor. The test the requesting session named follows: GPS L1C/L5Q as the held pair, the simulator first.

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

## 62. 2026-11-16: the chord table forms every configured family; the log arm `t3l` (pre-registered in section 60)

**The build** (exe nrf26; key `network.ring_fix.form_configured_pairs`, default false, needs `network.ring_fix.pairs`; ledger row UNVALIDATED). `chainArcFamilies` (`network/solve/ChainChordTable`) gives an arc's pair families: the rule of `chainPairFamilies` (every band-1 signal with the arc's lowest-digit signal of another band) and, with the key, every configured family of the satellite's constellation whose two signals the arc tracks and that the rule does not form. The ring fix's chord rows and its inheritance of old hosts' carries use it. Unit test `ChainArcFamilies.AConfiguredFamilyOfAThirdBandIsFormedBesideTheRule` (a file of its own, `tests/network/test_chain_arc_families.cpp`). The 10-epoch smoke of the log arm (`t3l26smoke`) shows the families formed: Galileo L1C/L7Q 1 521 chord rows (8 in `t3lsmoke` without the key), GPS L1C/L5Q 2 067 (none), Galileo L1C/L5Q and GPS L1C/L2W unchanged (1 513 and 2 067).

**Arms** (exe nrf26): `t3l_sim` and `t3l_sim_r`, section 60's log arms with the key: the three bands of the simulator (card L5B section 11's four keys), the ring fix in log mode on GPS L1C/L2W and L1C/L5Q and Galileo L1C/L5Q and L1C/L7Q, the adopted set at the cap of 12 (`kq12_sim[_r]`), 3 h from 00:30:15, the default receiver and S45000SIM. The results of `t3c` are section 60.1 (part 7).

**Bars** (section 60's): every family's would-be decisions right against truth at 99.9 % or more; on every arc decided by two families the shared signal's integers equal; within a constellation, each band's tree on the same datum receiver. The would-be decisions are graded offline (`_irdu_grades/scripts_s20/t3l_truth.py`): each row in state would_hold against the true integer of its arc in the frame of its epoch (`scripts/ird_frame_census.py`, `frame_integer`, with the producer's wind-up branch per arc), since the producer's truth audit counts held links only. The grader reproduces that audit on `kq12_sim`'s held rows: 79 135 and 94 203 link-epochs right, 0 wrong (the audit: 0 wrong).

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

# BER: the network's response to a bad epoch (stage E1: one flagged slip on the simulator, then one observed epoch)

**STATUS**

- **id:** BER
- **topic:** network-vehicle
- **status:** open
- **summary:** Opened 2026-11-15 on the author's order, relayed by the requesting session (section 1): the network detects a bad epoch but does not know how to respond; build a response and test it on the simulator, then on one observed epoch. Stage E1 (sections 2 to 9): one flagged L1 slip of 288 cycles on one GPS satellite near 16 degrees at minute 70 of a 2 h simulator bed, then the same event as observed at MRO100AUS on DOY 144 at TOW 7800. The step that spreads the fault is the float vehicle's drop of the slipped arc, which keeps the pre-slip value with the arc's birth variance; the response `network.amb_float_drop_jump_k` (default 0) gives the drop a variance that covers the band's measured phase-minus-code step. With k = 1 every bar passes on the simulator against the same-build control (the faulty receiver's clause against truth fails for the control as well and is read against it) and on the observed epoch at both reference receivers. A flagged slip of one cycle moves other satellites' phase biases up to 35 mm, almost all in the ionosphere-like direction that only code pins; its ionosphere-free reach with the clock is 0.3 to 0.4 mm, the level of the 288-cycle slip with the response (sections 8 and 9, clarified in section 14). A second key, `network.zwd_event_inflate_m`, is built and left off (section 7). Station-level events open no link window today; a proposal is in section 10, not built. 2026-11-15, the requesting session's review (section 12): the response leaves returns after a gap uncovered; three orders follow. Order 1 (section 13): `network.amb_float_drop_gap_cover` `free` frees a band whose return the gap instrument declares shifted; on DOY 144 TOW 1800 to 9000, at both reference receivers, no drop stays more than 3 restored sigmas off (9 and 11 returns before), T4 refloats 15 to 0, RAIM wet-delay erases 9 to 0, KIT300UZB's wet-delay step +8.4 to -1.0 cm (-0.9 cm with `network.zwd_event_inflate_m` 0.02); on the simulator a band return and a whole-arc return pass the bars of stage E1 where the carries bridge the gap. Orders 2 (slip size) and 3 (against the blanket drop floor) are pre-registered in section 12. 2026-11-15, the order 1 setting (the free gap cover and `network.zwd_event_inflate_m`) is adopted on the author's instruction in the regime of the chain posture with network integer fixing (section 15).
- **source:** the requesting session's messages of 2026-11-15 (stage E1; its review of stage O2's formal-sigma failures; its DARW00AUS trace); [NRF part 4](NRF_network_ring_fixing_2026-11-14_part4.md) sections 22 to 26 (the DOY 144 bed and its pairs); standing invariants 1 and 7 of the project instructions; card RF-1 (the float vehicle and its drop, in the record)

**Outcome.** Question: when one epoch carries a fault the network detects, here a flagged slip of 55 m on one band of one line of sight, does the network contain it? It did not. The float vehicle dropped the slipped arc to its birth variance at the pre-slip value, a prior about 80 sigma wrong, and the epoch's solve spread it into the line of sight's ionosphere, the arc's other band, the receiver's wet delay and clock, other receivers' floats and the emitted phase biases (metres); on observed data 13 and 29 satellite clock anchors decoupled. A drop whose variance covers the band's measured step contains it on both beds, and freeing a band whose return after a gap is declared shifted contains the returns that step cannot see. Standing: default off, UNVALIDATED.

## 1. The author's words and the assignment

The author's words, verbatim, as relayed by the requesting session:

- "Have the builder test a bad-epoch response on the simulator."
- "Regardless of the cause of the bad epoch, our network can detect it, but doesn't know how to respond/adapt. This is what Opus should work on to save our weekly tokens!"

The requesting session's reading: the response is the subject, not the forensics; stage E1 comes first, ahead of the formal-sigma re-run of card NRF and the review's remedies (section 11).

## 2. Stage E1 as frozen (pre-registration)

The bars were frozen in the requesting session's message before any run of this stage; this file was written after the runs and records them as relayed.

1. **The event.** On the simulator, one injected event: the L1 phase +288 cycles with the L1 loss-of-lock indicator, L2 untouched, one GPS satellite near 16 degrees, the network settled, minute 70 of a 2 h bed; two reference receivers; about 1 m of code error added if clean code hides the effect.
2. **The reach.** Against truth and against a control: wet delays, receiver clocks, floats, emitted clocks and phase biases, the tests that fire and their responses; the step that spreads the fault named.
3. **The response.** Designed and built default off, byte-identical off, its ledger row UNVALIDATED.
4. **Bars on the simulator.** (a) No other receiver's wet delay differs from the control's by more than 5 mm after the event; the faulty receiver's within 2 cm of truth. (b) The emitted clocks and phase biases of the other satellites within the noise of a control pair, the noise stated. (c) Every epoch emitted. (d) With fixing (held first, `sigma_scale` 2): no wrong held integer, no hold released except on the faulty link, no decision at the faulty receiver inside the event. (e) Defaults byte-identical.
5. **Bars on observed data** (DOY 144, TOW 7800, both reference receivers): one-epoch wet-delay steps below 1 cm at every receiver but MRO100AUS, alarms not above the control's, every epoch emitted.

## 3. Beds, arms and builds

- **Event bed** `runs_nom/sime1_a` (`scripts/e1_event_bed.py`): the golden simulator fixture `runs/simnet60_quiet_col_24h` with S12000SIM G20 at TOW 265230 (elevation 15.9 degrees, 70.25 min after the 00:30:15 start): L1C +288 cycles (54.80 m) from the epoch on, the L1C loss-of-lock indicator at the epoch, L2W untouched. `sime1_b` adds 1 m of code error on C1C and C2W at the epoch. `sime1_d` is the same flagged slip at one cycle (the reference pair of bar (b)). The other receivers keep the fixture's files; their truth files are copied.
- **Arms** (scratch `make_e1_arms.py`): copies of `_rap_nrf6off_g6` (the chain posture on the golden simulator bed, ring fix off), 2 h from 00:30:15, the event receiver pointed at a bed; reference receiver 1 is the elected S03000SIM, reference receiver 2 is S45000SIM (`network.phase_datum_eq34_receiver`). Event arms `e1a`, `e1b` (with code error), `e1a_r`; controls `e1c`, `e1c_r` on the unedited fixture; with the response `e1aj`, `e1aj_r` against `e1cj`, `e1cj_r`; the reference pair `e1dj`, `e1dj_r`; with fixing `e1ahj` against `e1chj` (ring fix held first, `sigma_scale` 2, pairs G:L1C/L2W and E:L1C/L5Q, truth audit in each epoch's frame).
- **Observed pair:** stage O2's arms on DOY 144 with the ring fix off, the default receiver and GOPE00CZE (`_rap_o2off_n144`, `_rap_o2off_n144r`, exe nrf9), against the same arms with the response (`_rap_o2j_n144`, `_rap_o2j_n144r`, to TOW 9000).
- **Builds** (branch `irdu/user-integers`, Release, AVX2): nrf9 `a18324f2ed30a1c5` (before the response), nrf10 `3cab205403a5f983` (the wet-delay inflate key), nrf11 `457ba1858879f38d` (both keys). Every event arm is graded against a control of its own build; the keys-off identity of the builds is bar (e).

## 4. The reach of the event without a response

Event minus control after the event epoch (`scripts/e1_reach.py`): the largest absolute difference over the rest of the 2 h; receiver clocks with the epoch's median over receivers removed, emitted values with the epoch's median over the constellation's satellites removed (a common shift reaches no user). The columns with the response are section 8.

| quantity | ref 1, no response | ref 2, no response | ref 1, response | ref 2, response |
|---|---|---|---|---|
| faulty receiver's wet delay | 3.56 cm | 15.98 cm | 0.43 cm | 0.64 cm |
| other receivers' wet delay (count above 5 mm) | 1.89 cm (3) | 0.99 cm (1) | 0.002 cm (0) | 0.010 cm (0) |
| faulty receiver's clock | 7.9 cm | 23.6 cm | 0.61 cm | 0.91 cm |
| other receivers' clocks | 13.6 cm | 1.6 cm | 0.004 cm | 0.020 cm |
| floats of the faulty receiver's other arcs | 44.3 cycles | 12.2 cycles | 0.023 cycle | 0.040 cycle |
| floats at other receivers | 21.1 cycles | 10.9 cycles | 0.004 cycle | 0.002 cycle |
| event satellite's emitted clock | 1.6 mm | 2.0 mm | 0.03 mm | 0.01 mm |
| other satellites' emitted clocks | 3.8 mm | 9.9 mm | 0.09 mm | 0.23 mm |
| event satellite's phase biases L1C / L2W | 1.22 / 1.98 m | 0.33 / 0.55 m | 0.2 / 0.3 mm | 0.05 / 0.08 mm |
| other satellites' phase biases | 4.20 m (G17 L2W) | 2.13 m (G06 L2W) | 0.92 mm (G17 L2W) | 0.30 mm (G04 L2W) |
| RAIM rows over the run (control 0) | 11 | 12 | 0 | 0 |
| events beyond the control's at the event epoch and the next | 349 | 162 | 7 | 8 |
| epochs emitted | 241 of 241 | 241 of 241 | 241 of 241 | 241 of 241 |

The tests that fire at the event epoch, the same in every event arm: the loss-of-lock flag with the MW step, the ionosphere-free slip test (139.5 against 0.128) and the GF jump (54.80 m), each answered by the slip latch, and the wet-delay erase at the latch. Without the response the next epoch adds a T4 attribution refloat of the arc, a second wet-delay erase at the RAIM attribution, an MDB exceedance and 153 to 340 prior-residual reports. With the response the added events are those at the epoch, a band-scope row and the wet delay's re-coupling 30 s later (and one prior-residual report on ref 2). The code error of `sime1_b` changes no figure of the table by more than 3 %: clean code does not hide the effect, and code is not what spreads it.

On the bed without the event the response is inert: with k = 1 the products of `e1cj` and `e1cj_r` are identical to `e1c` and `e1c_r`.

## 5. The step that spreads the fault

The slipped arc S12000SIM G20 was born at TOW 265170, two epochs before the slip. Its trace in `e1a` (`network_amb_state.csv`, `network_ionosphere.csv`; floats in metres):

| TOW | row | L1C float | L1C variance | L2W float | slant ionosphere (`iono_total_m`) |
|---|---|---|---|---|---|
| 265200 | after the solve | 12.65 | 0.23 m² | 7.20 | 3.53 |
| 265230 | the drop at the slip latch (`drop:relevel_free`) | 12.65 | 0.45 m² (birth) | 7.20 | |
| 265230 | after the solve | 50.87 | 0.11 m² | -20.01 | -5.98 |
| 265230 | the T4 drop (`drop:t4_attrib`) | 50.87 | 0.45 m² | -20.01 | |
| 265260 | after the solve | 54.74 | 0.14 m² | -13.66 | -2.32 |
| 265290 | after the solve | 56.49 | 0.10 m² | | -1.10 |

The control at the same epoch: L1C 12.27, L2W 6.58, slant ionosphere 3.29 m. The data moved +54.80 m on L1 alone.

The step is `networkAmbFloatApplyDrops`, the float vehicle's bounded drop at a latched slip: it restores the arc's variance to max(birth, first, floor) and keeps the value at the pre-slip level. The prior then sits 54.8 m from the data at a sigma of 0.67 m, about 80 sigma. The epoch's solve splits the misfit: the L1C float takes +38.2 m, the L2W float -27.2 m (its data unchanged), the slant ionosphere -9.5 m, and the shared rows carry the rest into the receiver's clock and wet delay. The next epoch's tests (T4 attribution, RAIM) drop the arc again at the damaged values and erase the receiver's wet delay, and the shared solution carries the move to other receivers' floats and to the emitted phase biases. Detection did its part (three tests at the epoch); the response to all three is the latch and this drop, whose variance is sized for an arc's birth, not for the step the tests measured.

## 6. The response

`network.amb_float_drop_jump_k` (default 0, range 0 to 10, read only on the float vehicle): at a slip-latched drop, each band's variance is at least (k times the band's measured phase-minus-code step across the epoch) squared. The steps come from the raw-observable slip screen that PASS A already runs: band 1 |Δ(L1 - C1)|, band 2 |Δ(L1 - C1) - ΔGF + ΔGF_code| (that is |Δ(L2 - C2)|), in metres; a step formed across a signal-pair change, or not measured, gives nothing. The value is kept. A band that moved is freed and re-determined by its own data that epoch, while the untouched band keeps its prior and holds the ionosphere. A one-cycle slip's step sits near code noise, below the birth variance at k = 1, so its drop is unchanged.

The same arc with the response (`e1aj`): the L1C drop takes 3 010.6 m² (the measured step, 54.87 m, squared); after the solve L1C is 67.08 m (the control's 12.27 m plus 54.81 m), L2W 6.579 m against the control's 6.581 m, the slant ionosphere 3.284 m against 3.287 m.

Code: `rawSlipBandJumps` and `networkRawSlipBandJumps` (`network/slip/RawObservables`), filled into `RelevelEpochState::pmc_jump_m` by `passARawObservables` when armed (`network/slip/PassASlipScan`); the covering drop in `networkAmbFloatApplyDrops` (`network/ar/AmbFloat`), with counters `n_amb_drop_jump_cover` and `max_amb_drop_jump_cover_m` and a run-end line; the knob snapshot `amb_drop_jump_k` (`network/driver/Knobs`). Unit tests: `tests/network/test_bad_epoch_response.cpp` (suite `BadEpochResponse`). Ledger row UNVALIDATED.

## 7. A second key, built and left off

`network.zwd_event_inflate_m` (default 0, range 0 to 1 m, read with the float vehicle and `network.carry_zwd_in_block`): at a slip latch, a RAIM arc flag or a RAIM prior flag, the station's carried wet delay is kept with this sigma added in quadrature instead of erased and re-seeded from one epoch (`zwdEventRespond` in `network/carry/ZwdCarry`, counter `n_zwd_event_inflated`, unit test `ZwdCoupleEdgeTest.AnInflatingResponseKeepsTheValueAddsTheSigmaAndOpensTheRecord`). It was built first, on the reading that the wet-delay erase spread the fault. On this event alone it changes nothing (`e1ai` against `e1ci` at 2 cm: the faulty receiver 3.53 cm against 3.56 cm, every other figure within 1 %), because the spreading step is the drop. Beside the response (`e1ajz`, `e1ajz_r` against `e1cjz`, `e1cjz_r`, both keys, nrf11) it trims the faulty receiver's wet-delay difference from 4.3 to 3.6 mm (6.4 to 5.5 mm) and its error against truth by 0.2 to 0.3 mm, every other figure unchanged; it also changes the bed without the event (one natural slip latch there). The faulty receiver's remaining difference is therefore mostly the information the freed band loses, not the erase. Left off; ledger row UNVALIDATED.

## 8. The bars on the simulator

- **(a) Wet delays: PASS for the other receivers**, at most 0.02 mm (ref 1) and 0.10 mm (ref 2) from the control. The faulty receiver's clause against truth fails for the control itself: after minute 70 the control's wet delay at S12000SIM lies -2.47 to +1.03 cm from truth (ref 2: -2.89 to +1.37 cm) and was already -1.8 cm (-2.5 cm) at the epoch before the slip; with the response -2.67 to +1.12 cm (-3.23 to +1.39 cm), the extreme at the same epoch as the control's (TOW 265710). Read against the control, the response's cost at the faulty receiver is 4.3 mm (6.4 mm): the wet-delay erase at the slip latch and its re-coupling 30 s later. The reference pair of bar (b) costs the same there (4.4 mm, 6.1 mm): any flagged slip on that arc costs this much today.
- **(b) Emitted values of the other satellites: PASS.** Two controls of one posture are identical (`e1c` under nrf9, nrf10 and nrf11, and `e1cj`, give identical products), so a pair of controls has no noise; the reference pair is the control against the same flagged slip at one cycle (`e1dj`, `e1dj_r`), the change any flagged slip on that arc makes today: other satellites' clocks up to 0.08 mm (0.21 mm), phase biases up to 35.2 mm (5.1 mm). With the response the 288-cycle slip moves them up to 0.09 mm (0.23 mm) and 0.92 mm (0.30 mm): the clocks at the one-cycle level, the phase biases below it. The one-cycle slip moves the phase biases more because its kept value is wrong by one cycle against the birth sigma and k = 1 does not cover a step that small (section 9).
- **(c) Every epoch emitted: PASS**, 241 of 241 in every arm.
- **(d) Fixing: PASS.** `e1ahj` against `e1chj`: held link-epochs right 13 261 against 13 262, wrong 0 in both, wrong decisions 0; 197 decisions in each with the same ring counts; 8 releases in each, all at data gaps, none added; the faulty link was never held (born two epochs before the slip). At the faulty receiver no decision in the event (the slip epoch and the wet delay's re-coupling 30 s later); its next decision, E19 at +450 s, comes 30 s after the control's.
- **(e) Defaults byte-identical: PASS.** With both keys absent the arm, the products, every trace, the run manifest, the run-end block and the exit code of `e1c` are identical between nrf9 and nrf11 and between nrf9 and nrf10 (`_irdu_grades/e1_gate_default*.txt`).

## 9. The observed epoch

DOY 144, the observed slip at MRO100AUS on G11 at TOW 7800 (elevation 15.7 degrees; the network's own events: loss of lock with the MW step, the ionosphere-free slip test at 139.5 against 0.118, a GF jump of +54.82 m, 288 L1 cycles), each reference receiver's run without the response against the same run with it (scratch `e1_obs_check.py`):

| quantity | default receiver, no response | default receiver, response | GOPE00CZE, no response | GOPE00CZE, response |
|---|---|---|---|---|
| MRO100AUS one-epoch wet-delay step | +10.76 cm | +0.02 cm | +103.13 cm | +0.02 cm |
| other receivers above 1 cm, one epoch (largest) | 3 (DARW00AUS +2.77 cm) | 0 (YKRO00CIV -0.38 cm) | 10 (DARW00AUS +33.50 cm) | 0 (CPVG00CPV -0.31 cm) |
| other receivers above 1 cm, TOW 7800 to 7890 (largest) | 3 (2.98 cm) | 0 (0.62 cm) | 12 (33.82 cm) | 0 (0.57 cm) |
| satellite clock anchors decoupled, TOW 7800 to 8100 | 13 | 0 | 29 | 0 |
| RAIM rows TOW 7800 to 8100; to TOW 9000 | 1; 10 | 0; 4 | 8; 12 | 0; 4 |
| block-Baarda flags; congruence flags, TOW 7800 to 8100 | 111; 11 | 103; 10 | 167; 26 | 104; 10 |
| epochs emitted to TOW 9000 | 301 of 301 | 301 of 301 | 301 of 301 | 301 of 301 |

Every observed bar passes: steps below 1 cm at every receiver but MRO100AUS (largest 0.38 cm), alarms not above the control's on any family (MDB exceedances 76 against 76, 76 against 77; every other family below), every epoch emitted. The runs without the response come from nrf9, whose keys-off output equals nrf11's (bar (e)).

Not covered: a slip on both bands at once (both steps are measured; not run), a flagged slip below the birth variance (the one-cycle case of bar (b): its phase-bias reach of 35 mm is today's behaviour, unchanged by the key at k = 1; a larger k or a floor of a few cycles is untested), an unflagged slip (the residual monitor of card NRF section 20), and the GPS L1C/L2W pair on observed data with fixing on.

## 10. Station-level events and the link window (stage G0's question)

Asked: does a station-level event at either end of a link (a congruence flag, a gross-LOS declaration on any satellite of the station, a step of the station's wet delay or clock beyond its sigma) open the link's window today? No. The window test (`windowOk` in `src/core/network/ar/RingFix.cpp`) reads only the link's own state: its carried entries present and unlatched, its two bands' re-level stamps, its time as a chord, its last time as a tree edge and its last release, each against 600 s. A station event reaches a link only when it erases or re-levels that link's own carried entries (a gross-LOS declaration on that line of sight, a T4 refloat of that arc, a cut release).

Proposal, not built: a station event stamp per receiver, set by a congruence flag at the station, a gross-LOS declaration on any of its lines of sight, a wet-delay erase, or a one-epoch step of its carried wet delay or receiver clock beyond k times the step's sigma; every link with that receiver at either end is refused for the window after the stamp (a refusal of its own), and a held link there is put under the residual monitor rather than released. With the response armed, the E1 event raises none of these at the other receivers on observed data: DARW00AUS's step of +2.77 cm (+33.50 cm) falls to at most 0.16 cm.

Noted for the author, not addressed by this stage: the requesting session's DARW00AUS trace shows the gross-LOS screen's latency and a carried wet delay with no guard of its own between an event and the screen's declaration.

## 11. Next, in the order relayed

1. Stage O2's formal-sigma pairs re-run with the response on (`o2s1` with both reference receivers and the +1 h start), results to card NRF; the product file of a holding run with the response on kept for the user replays.
2. Remedy (a) of the review: why a cut whose new tree arc carries a float releases the carries at all; answered in card NRF before any build, and if the release is not needed, (a) covers every cut with a crossing float, not only step 0.
3. The simulator bed for remedy (b) (consensus re-seat as a discrete event); no build of (a) or (b) before the author chooses.

## 12. 2026-11-15: the requesting session's review, and orders 1 to 3 (pre-registered)

The requesting session re-graded stage E1 and accepted the diagnosis and the response. Its own checks: the numbers reproduce from the traces without the stage's scripts; the comment inside `ambFloatDrop` states the design assumption the fault breaks ("a prior at birth variance is dominated by the epoch's data"), which is false twice: the kept value keeps a real weight (about 30 % in `e1a`), and the restored "birth variance" is the arc's first-stash variance, as small as (0.057 m)^2 on observed data. At MRO100AUS-G11 with the response only L1C is reset and its float returns in the same epoch with the sigma it had before the slip.

**A population the response does not cover.** The review read every drop of DOY 144 from TOW 1800 to 9000 with two scripts of its own (`e1_drop_walk.py`, `e1_cover_gaps.py`): for each drop, |value after the epoch's solve - kept value| over the restored sigma, z. A kept value more than three restored sigmas off is a prior the solve had to fight. Adjacent-epoch slips: 365 and 372 drops (default receiver, GOPE00CZE), 8 and 8 above 3 sigma without the response, 0 and 0 with it. Returns after a gap (tier `T0_gap`): 92 and 94 drops, 9 and 11 above 3 sigma, unchanged by the response, because the raw screen forms a step only from the immediately preceding epoch. The gap instrument measures and declares those returns shifted (GF changes of 8.6 to 23.5 m), and the drop keeps the pre-gap value at the first-stash variance (KIT300UZB-E34 at TOW 8280: 12.48 m against a restored sigma of 0.057 m, z 60, with T4 refloats and wet-delay erases on three epochs and the receiver's wet delay +8.4 cm).

**Order 1, the gap-return cover.** A band whose return the gap instrument declares shifted is freed like a slipped band, either by the band's phase-minus-code step across the gap (per signal; the pair may change across the gap) or outright with a large variance; the choice is made by test. The GF shift must not size the cover of a whole-arc return (a shift common to both bands cancels in GF). One owner: the latch carries the size the detector measured and the drop reads it, whichever detector latched the band. Default off, byte-identical off, counters by class at run end. Bars: on DOY 144 TOW 1800 to 9000, both reference receivers, zero drops with a kept value more than three restored sigmas off in both classes; KIT300UZB's wet-delay step at TOW 8280 below 1 cm; T4 refloats, wet-delay erases by RAIM attribution and alarms not above the present run's; every epoch emitted. On the simulator, one injected return after a gap with a shift (a band missing 4 epochs, back 12 m off, its partner tracked through) and one whole-arc return, with the bars of stage E1.

**Order 2, the slip size**, on the stage E1 bed: a flag with no slip (the yardstick of what any latch costs), 1, 4 and 10 cycles on the E1 arc; the same four on a settled arc with its other band intact; the 288-cycle slip on a tree link and on a held link of a settled receiver (the cut release it triggers, the carried entries erased, the receiver's wet delay against the control). The review's prediction: the kept value's pull is J Vd / (max(Vbirth, k^2 J^2) + Vd), which at k = 1 peaks near J = sigma_birth, so 3 to 5 cycles are worse than one.

**Order 3, against the drop floor the project already has** (`network.amb_float_drop_var_m2`, KEEP_OFF; card RF-3's record: it removes the post-drop walk and missed the hour-1 bars in September; card ICL6's read at 100 m^2 over 24 h on DOY 129 and 132: T4 arcs 422 to 80 and 549 to 176, clock-anchor decouplings 5 and 31 to 0, positions neutral). Three arms on the E1 events and the two observed hours: (i) the response with the gap cover; (ii) the drop floor at 100 m^2 alone; (iii) the response with the gap cover plus a floor on declared slips and declared shifts only (not on T4 or T3 statistical refloats, whose kept value is roughly right). Reads: the population table, the reach table, and the first hour of a cold start on the simulator (hour 1 is why the blanket floor is off). The review expects (iii); no ledger verdict changes.

**Smaller points.** The faulty receiver's clause against truth was badly posed (the control fails it); the reading against the control is accepted. Section 10's station stamp drops the bare wet-delay-erase trigger (slips erase a wet delay 195 times in those two hours; at 600 s a stamp would refuse each receiver's links about a quarter of the time); the measured-step triggers stay; nothing is built before orders 1 to 3. `network.zwd_event_inflate_m` is re-read after order 1.

**Prior art found on the way.** Card ICL6 (2026-11-07, in the record) traced the same mechanism from another symptom: "A slip's freed arc keeps its pre-slip level at birth variance; that prior pushes a receiver's DCB by metres", read there as lone clock-anchor trips, and the 100 m^2 floor removed all of them as an instrument. Card RF-3 (section 6) measured why the blanket floor costs hour 1: drops in hour 1 act on unconverged values, where the restored prior decides how fast an arc re-converges.

## 13. 2026-11-15: order 1 results, the gap-return cover

### 13.1 What was built

One record of a band's measured break replaces the stage E1 table (`BandBreak`, `include/network/slip/BandBreak.hpp`): its step, where it was measured (between adjacent epochs, or across a gap) and, for a return, whether the gap instrument declared it shifted. It is keyed like the latch (`RelevelEpochState::band_break`), written by the raw screen for adjacent epochs (`networkRawSlipBandJumps`) and by the gap instrument for returns (`networkGapBandBreaks`), and read by the drop through one function (`ambDropCoverVar`), whichever detector latched the band. The gap instrument now forms each returning signal's own phase-minus-code step across the gap: in the row-level tier for every signal present on both sides (the pair may change across the gap), in the per-signal tier from the signal's own last-seen phase and code. A shift common to both bands, invisible to GF, is therefore sized per band.

`network.amb_float_drop_gap_cover` (default `off`, read only on the float vehicle): `step` covers (`network.amb_float_drop_jump_k` times the band's step across the gap) squared; `free` gives a band whose return the gap instrument declares shifted a variance of 1e4 m^2. Run-end line by class (returns with a measured break, covered drops, largest covering sigma). Unit tests (suite `BadEpochResponse`): a band returning 63 cycles off after three epochs with its partner tracked through carries its own step (11.99 m, declared shifted; the unshifted band about 0); a whole-arc return with 63 and 49 cycles on the two bands has a GF change of 2 cm, below the GF gate, is declared shifted by MW and carries 11.99 and 11.97 m per band; the cover by kind and form. Exe nrf13 (`450da55a1372864c`).

### 13.2 Identity

With the keys absent, every product, trace, the run manifest and the run-end block of the control are identical between nrf9 and nrf13. With `network.amb_float_drop_jump_k` 1 and the gap cover off, nrf13's products equal nrf11's on the simulator (both reference receivers) and on the observed hours (`o2j13_n144[r]` against `o2j_n144[r]`): the new record changes nothing the stage E1 response did. On the simulator control, both cover forms leave the products identical (no return there has a carried entry to drop).

### 13.3 The observed hours (DOY 144, TOW 1800 to 9000)

Default receiver / GOPE00CZE; the review's scripts on each run; "present" is the response alone (`o2j13_n144[r]`).

| | present | step | free | free and `network.zwd_event_inflate_m` 0.02 |
|---|---|---|---|---|
| returns after a gap, kept value more than 3 restored sigmas off | 9 / 11 | 2 / 1 | **0 / 0** | 0 / 0 |
| adjacent-epoch slips, the same | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 |
| returns whose drop took the cover (of 92 / 94) | 3 / 3 | 51 / 56 | 88 / 90 | 88 / 90 |
| KIT300UZB one-epoch wet-delay step at TOW 8280 | +8.36 / +8.31 cm | -1.02 / -1.03 cm | -1.02 / -1.03 cm | **-0.88 / -0.89 cm** |
| T4 refloats | 15 / 15 | 0 / 0 | 0 / 0 | 0 / 0 |
| wet-delay erases by RAIM attribution | 9 / 9 | 0 / 0 | 0 / 0 | 0 / 0 |
| RAIM rows to TOW 9000 | 4 / 4 | 0 / 0 | 0 / 0 | 0 / 0 |
| clock anchors decoupled | 0 / 2 | 0 / 0 | 0 / 0 | 0 / 0 |
| block-Baarda; MDB; congruence flags | 1106, 1029, 60 / 1101, 1024, 57 | 1103, 1029, 56 / 1097, 1024, 56 | 1101, 1025, 56 / 1093, 1018, 56 | 1101, 1025, 56 / 1093, 1018, 57 |
| one-epoch wet-delay steps of 2 cm or more (5 cm or more) | 14 (7) / 8 (2) | 13 (6) / 6 (1) | 1 (0) / 13 (5) | 1 (0) / 13 (5) |
| epochs emitted | 301 / 301 | 301 / 301 | 301 / 301 | 301 / 301 |

- **The step form fails the population bar** (2 and 1 returns stay more than 3 sigma off): a measured phase-minus-code step carries code noise, so a small shift can be under-covered against a first-stash sigma of a few centimetres.
- **The free form passes every bar but one by itself:** KIT300UZB's step is -1.02 cm against a bar of 1 cm. At that epoch the band is freed (no T4 refloat, no RAIM erase any more); what remains is the receiver's own wet-delay erase at the slip latch, re-seeded from one epoch. With `network.zwd_event_inflate_m` 0.02 (the value kept, 2 cm of sigma added) the step is -0.88 cm, and the receiver's wet delay then moves -0.61, -0.31 and 0.00 cm over the next three epochs (about 1.8 cm in all) against about 0.1 cm per epoch before.
- **The wet-delay steps of 2 cm or more that remain are all BSHM00ISR's** (TOW 2820 to 3210). Its local block is reported not positive definite at every epoch (TOPOLOGY `sta_pd_dropped`), its wet delay has wandered to -0.23 m by TOW 2820 in three of the four runs and to +0.11 m in the fourth, and the steps are its recovery from there: a property of that receiver, which moves with any perturbation, not of the gap cover.

### 13.4 The simulator returns

Two beds on the golden simulator fixture, each with one return at S12000SIM at TOW 265230 and no loss-of-lock flag (`scripts/e1_event_bed.py --gap`): `sime1_g`, G04 (35 degrees, tracked from the run start) with its L1 observations blanked for the 4 epochs before and back 63 cycles (11.99 m) off, L2 and L5 tracked through; `sime1_w`, G19 (45 degrees) absent for 4 epochs and back with 63, 49 and 47 cycles on L1, L2 and L5 (about 12 m on each, GF change 0.07 m). At reference receiver 1 a chain re-host at S12000SIM at TOW 265170 (the tree edge of G17) erases every GPS carry of the receiver in the control as well, so both returns arrive with nothing carried and nothing to drop; the fault exists at reference receiver 2 (S45000SIM), where the carries are bridged across the gap. Event against the control of the same form, reference receiver 2:

| | band return, no cover | step | free | whole-arc return, no cover | step | free |
|---|---|---|---|---|---|---|
| z of the returning band(s) at the drop | 34.5 | 1.0 | 0.1 | 22.2, 4.5 | 1.1, 1.1 | 0.1, 0.1 |
| faulty receiver's wet delay | 3.18 cm | 0.06 cm | 0.06 cm | 2.94 cm | 0.09 cm | 0.09 cm |
| other receivers' wet delay (count above 5 mm) | 2.03 cm (1) | 0.014 cm (0) | 0.012 cm (0) | 1.72 cm (1) | 0.021 cm (0) | 0.022 cm (0) |
| faulty receiver's clock; other receivers' clocks | 8.0; 3.1 cm | 0.79; 0.023 cm | 0.79; 0.022 cm | 15.3; 2.8 cm | 2.25; 0.072 cm | 2.28; 0.074 cm |
| floats at other receivers | 6.6 cycles | 0.006 cycle | 0.003 cycle | 11.5 cycles | 0.019 cycle | 0.004 cycle |
| other satellites' emitted clocks; phase biases | 3.3; 5.4 mm | 0.24; 0.4 mm | 0.24; 0.4 mm | 2.8 mm; 2.41 m | 0.55; 4.9 mm | 0.56; 0.9 mm |
| events beyond the control's at the return and the next epoch | 48 | 2 | 2 | 143 | 4 | 4 |
| RAIM rows over the run (control 0) | 7 | 0 | 0 | 2 | 0 | 0 |
| epochs emitted | 241 | 241 | 241 | 241 | 241 | 241 |

The yardstick of bar (b), the same gap with no shift (beds `sime1_g0`, `sime1_w0`, free form, reference receiver 2): the band gap moves the other satellites' emitted clocks and phase biases by 0.24 and 0.4 mm, exactly what the shifted return costs under either form; the whole-arc gap by 0.67 and 14.4 mm, more than the shifted return under the free form (0.56 and 0.9 mm). With fixing (ring fix held first at twice the formal sigma, reference receiver 2, the free form), the band and whole-arc beds give decisions and releases identical to the control's: 134 decided, 7 842 held link-epochs right, 0 wrong, 2 releases at data gaps, no decision at S12000SIM in the 10 minutes after the return.

### 13.5 The bars

- **Simulator, as stage E1, with the free form:** (a) other receivers' wet delay at most 0.22 mm from the control, the faulty receiver's 0.6 and 0.9 mm: PASS; (b) other satellites' emitted values at or below the same gap with no shift: PASS; (c) every epoch emitted: PASS; (d) fixing unchanged against the control, 0 wrong: PASS; (e) keys absent identical to nrf9, the cover forms inert on the control fixture, `network.amb_float_drop_jump_k` with the cover off identical to nrf11: PASS.
- **Observed hours:** zero returns more than 3 restored sigmas off in both classes: PASS with the free form (0 / 0), FAIL with the step form (2 / 1); KIT300UZB's step at TOW 8280 below 1 cm: -1.02 / -1.03 cm with the free form alone (FAIL by 0.2 mm), -0.88 / -0.89 cm with `network.zwd_event_inflate_m` 0.02 beside it (PASS); T4 refloats, RAIM wet-delay erases and alarms not above the present run's: PASS (T4 15 to 0, RAIM erases 9 to 0, every alarm family at or below); every epoch emitted: PASS.

### 13.6 The choice, and the inflate key re-read

The free form is chosen: a return the gap instrument declares shifted owes nothing to its old level, and freeing it outright leaves no drop more than 3 sigma off, where the step form, carrying code noise, leaves a few. The step form stays in the code as the tested alternative. With the band freed, the only thing still acting on the receiver's wet delay at a latch is its erase and one-epoch re-seed; `network.zwd_event_inflate_m` 0.02 keeps the value with 2 cm of sigma added, which brings KIT300UZB under the bar and changes no other read of the two hours (alarms, population, emission). Both keys stay default off with ledger rows UNVALIDATED; arming is the author's decision.

## 14. 2026-11-15: clarification of sections 8 and 9, the one-cycle slip's reach is ionosphere-like

Sections 8 (bar (b)) and 9 (what is not covered) and the summary line say that a flagged one-cycle slip moves the other satellites' phase biases more than the 288-cycle slip does with the response (35.2 against 0.92 mm). The requesting session split each satellite's phase-bias change (event minus control, the epoch's median over the constellation removed) into the part a slant ionosphere absorbs and the ionosphere-free part: with d1 = I + G and d2 = gamma I + G (gamma = f1^2 / f2^2), I = (d2 - d1)/(gamma - 1) and G = (gamma d1 - d2)/(gamma - 1). `scripts/e1_reach.py` now reports the phase-bias reach in these directions for GPS and Galileo: the ionosphere-free part with the satellite clock's change added (what a user's position and the ring fix's ionosphere-free N1 feel), the ionosphere-like part, and the wide lane in cycles (d1/lambda1 - d2/lambda2). Largest over the run, other GPS satellites, mm (the wide lane in cycles):

| pair | ionosphere-like | ionosphere-free with the clock | wide lane |
|---|---|---|---|
| one cycle, `e1dj` - `e1cj` | 21.21 | 0.41 | 0.031 |
| one cycle, reference receiver 2 | 3.01 | 0.31 | 0.004 |
| 288 cycles with the response, `e1aj` - `e1cj` | 0.55 | 0.12 | 0.001 |
| 288 cycles with the response, reference receiver 2 | 0.18 | 0.30 | 0.000 |
| 288 cycles without the response, `e1a` - `e1c` | 2534 | 481 (G05; 197 at G22) | 3.749 |
| 288 cycles without the response, reference receiver 2 | 1276 | 43 | 1.863 |

The ionosphere-like column reproduces the requesting session's to 0.01 mm; the column with the clock reproduces it on the response arms (0.12, 0.30 mm) and differs where the satellite set differs (its 0.46 mm for the one-cycle slip, its 197 mm for `e1a`, which leaves out G05). Galileo's columns stay below 0.2 mm in every arm with the response. So the one-cycle slip moves what a user's position can feel by 0.3 to 0.4 mm, the level of the large slip with the response; the 35 mm of section 8 is the ionosphere level shared by the phase biases, the slant ionospheres and the floats, which only code pins. Sections 8 and 9 stand as written and are read with this clarification: the one-cycle pair is a fair yardstick in the ionosphere-free direction, and a floor for small slips is not motivated by it (the requesting session's reading). Order 2 is read on the ionosphere-free part with the clock and moves behind order 3.

## 15. 2026-11-15: the order 1 setting adopted, on the author's instruction

**The author's words** (2026-11-15, verbatim, as relayed by the requesting session): "Yes, adopt the faster setting if DOY 145 passes. An improvement should be adopted/enabled. If more verification is needed, then we can work on that later, just add a simple note: this was done on [date], verified by [one run, basic], [todo: check more stations and days eventually]." The requesting session's rule from them: an improvement that passes its bars is adopted in its regime with that three-part note, and the gap cover of order 1 is the next case.

Order 1 passed its bars with the free form and `network.zwd_event_inflate_m` beside it (section 13.5). Ledger rows changed, both from UNVALIDATED to RECOMMEND_SCOPED in the regime of the chain posture with network integer fixing (`on("network.ring_fix.enable")`, false on every golden, so the goldens are unchanged and `make_golden_config.py --verify` passes), with a matching scoped row in the loader's run-start posture table (`src/core/config/GnssConfigNetworkPosture.cpp`):

- `network.amb_float_drop_gap_cover`, armed when `free`;
- `network.zwd_event_inflate_m`, armed when positive (0.02 m as run), the gap cover's companion.

Each row carries the note: "Adopted 2026-11-15 on the author's instruction (an improvement that passes its bars is adopted). Verified by: DOY 144 TOW 1800 to 9000, one network of 56 receivers, two reference receivers, and the simulator's band and whole-arc returns (basic). To do: more stations and days; the main posture without the chain." `network.amb_float_drop_jump_k` and `network.ring_fix.sigma_scale` wait for the second day (card NRF part 5, section 30), as the rule says.

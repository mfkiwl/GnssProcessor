# NRF part 3: stage N3 and what follows (sections 17 onwards of card NRF)

**STATUS**

- **id:** NRF-part3
- **topic:** network-vehicle
- **status:** open
- **summary:** Sections 17 onwards of card NRF (2026-11-15). Section 17: the requesting session's re-grade of stage N2b (every count reproduces; its truth-free two-run audit finds 0 failing checks) and its rulings (B2 means links present at the cut; the root-change rule stays; the receiver's step after a slip on a tree link is no integer matter). Section 18: stage N3 on the 6 h golden sim bed from a cold start, on both constellations: 0 wrong held integers (342 217 held link-epochs with held first, 233 400 with the plain order, by the code's audit and an independent one); held first holds 77 to 88 % of the chords in hours 3 to 6 (predicted at least 90 %: missed) with the stream's NL at most 0.024 cycle at every depth (predicted at most 0.03: met); its users hold integers 48 to 57 % of the time against 8 to 17 % on the plain chain, 0 wrong for every start; card IRD-8's P-a fails on every chain arm, the plain chain included. Section 19: stages N3b, N2c and O1 pre-registered.
- **source:** [NRF](NRF_network_ring_fixing_2026-11-14.md) sections 3, 4 and 6; [NRF part 2](NRF_network_ring_fixing_2026-11-14_part2.md) sections 14 to 16.1; [IRD](IRD_integer_recovering_datum_2026-10-13.md) section 9 (the IRD-8 bars)

**Outcome.** Question: over 6 h on the reference bed, from a cold start, does the ring fix stay at 0 wrong integers, and what do users get? It takes 0 wrong integers on GPS and Galileo; with held-first re-attachment no held link is released at a re-seat, and it holds 77 to 88 % of the network's chords from hour 3 with the stream's narrow lane at the truth-fed level. Its users hold integers half the time, 0 wrong, against a sixth on the plain chain. Standing: default off; simulator only; observed data log-only next (section 19).

Sections 1 to 12 are in [NRF](NRF_network_ring_fixing_2026-11-14.md), sections 13 to 16.1 in [part 2](NRF_network_ring_fixing_2026-11-14_part2.md). Results are appended below, each under its dated heading.

## 17. 2026-11-15: the requesting session's re-grade of stage N2b and its rulings

Recorded as received from the requesting session (its tools `nrf_reads_mine.py` and `nrf_dd_agree.py`, copies and outputs under `D:\GnssProcessorSupport\presentation\agu26\fixing_control\tools\` and `...\fixing_control\grades_arnd\n2b\`).

**Re-grade.** The counts of section 15 reproduce on all 16 bed runs, the ceiling, the steady run and the slip beds: decisions, held link-epochs, releases by cause, re-attachments and kept links, 0 wrong rows in the audit, 0 hold events with `truth=WRONG`, 0 RAIM rows; the held share of the last 30 min on r3c is 83.7 % with held first and 61.0 % on the control. The truth-free audit (two runs must agree on every double difference of their integers; the reference is N1b-OL on the bed without re-seats, itself checked against the file of true integers): held first on the eight beds 16 908 checks per signal, 0 failing; the ceiling 2 979, 0; the steady run 2 081, 0 (N2's steady run: 530 of 1 652 failing). Slip beds, the bed's true slip added to the reference: s1 and s2 0 failing (1 690 checks on the control, 2 423 with held first); without the slip added 34 and 16 checks fail from 96 min, all through S05000SIM-G26, and with the sign reversed 16 fail, so the link is held again at the old integer plus the slip. s3 against `nrf6_hf_r3c` (the same bed without the slip): 18 326 checks (held first) and 13 972 (control), 0 failing with the slip added, 8 and 11 failing on S03000SIM-G25 without it. The stream by depth reproduces (held first, NL over all depths 0.247 0.166 0.060 0.046 0.035 0.016 0.013 0.012; every pair within 0.10 cycle from 75 min).

**Rulings (the requesting session's, open to the author's review).**

- (a) Bar B2 of section 14 means links present at the cut: an absent link cannot carry the moved side, and its release across an unknown step is the safe response. The frozen read stays FAILED on ird_ms and ird_msx in the record, with this ruling beside it.
- (b) The root-change rule stays as built (it releases the links inside a side that re-joins through an unknown step): six links on one bed do not pay for a second rule on the merge path; revisited only if N3 shows it costs holds.
- (c) The receiver's step on s3 is not an integer matter. Traced in `network_rpb_states.csv` and `network_amb_state.csv`: S03000SIM is the parent end of the slipped tree link (depth 2, its own parent link did not slip); its phase-bias pair drifts by about -0.07 m (L1) and -0.10 m (L2) over the four epochs after the slip on every arm; on the held-first arm every held or pinned ambiguity of that receiver is unchanged to 0.000 cycle across the slip. The move sits in parameters that are free per epoch (the receiver's phase bias with its clock and the per-arc ionosphere), a direction the phase data do not see while the per-arc ionosphere is free. No action in the ring fix; not traced to a line of code.
- (d) I-b: noted; N3's users are the test of what the undeclared steps cost.

## 18. 2026-11-15: stage N3 results (the 6 h golden sim bed from a cold start)

**What ran.** Pre-registered in section 16 (`95ec239`), amended in section 16.1 (`f6a2837`) before the re-runs. First runs on exe nrf6 (kept as the record): `nrf6off_g6`, `nrf6_olt_g6`, `nrf6_hf_g6`, `nrf6_G_g6`. Re-runs on exe `gnss_processor_irdu_nrf7.exe` (sha256[:16] `e9ddf9ea14925df0`): `nrf7_olt_g6`, `nrf7_hf_g6`; the gates `nrf7off_r3c` and `nrf7_hf_r3c` against nrf6 are IDENTICAL (one constellation: the fix changes nothing there, so the results of N2b stand on nrf7). Users (the users' build, sha256[:16] `5ecf8e1c765fafe3`): five users, four starts, float and fixing, on the plain stream (`nrf6off_g6`) and the two re-run streams, 120 runs `_rap_irdu_u_<stream>_<obs|fix>_<user>_s<30|120|180|240>`. Every network run exit 0, 720 of 720 epochs emitted, 0 RAIM rows. Grades `runs_nom/_irdu_grades/nrf_n3_*`.

**The ring fix runs on both constellations on this bed.** Section 16 said the chain claims GPS only; that was wrong. On the held-first re-run the trace holds Galileo L1C/L5Q links for 160 229 link-epochs and GPS L1C/L2W links for 181 988; 640 Galileo and 798 GPS decisions; 119 Galileo and 175 GPS re-attachments; the chain's record has 120 228 Galileo and 130 020 GPS tree edges.

**Bars.**
- **N3-B1, 0 wrong held integers over 6 h: PASS.** Held first 342 217 held link-epochs, the plain order 233 400, 0 wrong by the code's truth audit and by `nrf_audit.py --fixture` (both constellations, 0 not listed). The first runs: 332 377 and 138 951, 0 wrong by both.
- **N3-B2, every release named: PASS.** Every RINGFIX release row carries its cause, and the run-end closure is closed (held first 1 438 = 511 released + 294 tree edges + 633 held; plain order 2 022 = 1 459 + 175 + 388).
- **N3-B3, every epoch emitted: PASS** (720 of 720 on every arm).

**By hour (re-runs).**

| arm | hour | held share | decisions | releases by cause | re-attachments (held links kept) | minutes from birth to hold, p50 |
| --- | --- | --- | --- | --- | --- | --- |
| held first | 1 | 12.5 % | 251 | 0 | 6 (35) | 58.5 |
| | 2 | 54.4 % | 357 | gap 37 | 40 (543) | 37.0 |
| | 3 | 76.9 % | 264 | gap 95, slip 1 | 62 (1 430) | 26.0 |
| | 4 | 87.7 % | 205 | gap 125, slip 1 | 37 (1 164) | 25.0 |
| | 5 | 87.4 % | 172 | gap 123, slip 2 | 75 (1 700) | 25.0 |
| | 6 | 83.6 % | 189 | gap 126, slip 1 | 74 (1 733) | 24.5 |
| plain order | 1 | 11.9 % | 251 | chain 41 | 0 | 56.0 |
| | 2 | 45.1 % | 361 | chain 122, gap 34 | 0 | 37.5 |
| | 3 | 50.9 % | 364 | chain 256, gap 42, slip 1 | 0 | 34.0 |
| | 4 | 49.3 % | 347 | chain 276, gap 51, slip 1 | 0 | 42.5 |
| | 5 | 57.1 % | 364 | chain 203, gap 68, monitor 1, slip 1 | 0 | 33.0 |
| | 6 | 60.6 % | 335 | chain 281, gap 78, slip 3 | 0 | 23.0 |

Cuts by kind: held first 758 cuts on a band, 588 taken through a held link first (every one at step 0) and 170 with an unknown step, across which 0 held links were released; the plain order 810 cuts, 350 with a known step (all 0), 460 unknown, 1 179 held links released across them; 2 cuts with a nested release on each; 21 old hosts inherited on the plain order, none with held first; the release floor bound 36 and 29 times. On the first runs the held-first arm released 63 present held links at cuts, all through the constellation defect of section 16.1, and the plain order 1 632 (held share by hour 9.5, 34.2, 25.4, 23.8, 34.0, 37.0 %): the fix lifts the plain order's hours 3 to 6 from 24 to 37 % to 49 to 61 %.

**The stream, NL offset p50 over all depths by 15 min (cycles).**

| stream | hour 1 | hour 2 | hour 3 | hour 4 | hour 5 | hour 6 |
| --- | --- | --- | --- | --- | --- | --- |
| plain chain | 0.233 0.152 0.110 0.146 | 0.084 0.108 0.086 0.121 | 0.114 0.150 0.091 0.065 | 0.072 0.092 0.092 0.065 | 0.066 0.079 0.097 0.089 | 0.061 0.072 0.070 0.067 |
| plain order | 0.233 0.162 0.085 0.095 | 0.045 0.026 0.031 0.060 | 0.044 0.054 0.035 0.029 | 0.030 0.030 0.020 0.016 | 0.017 0.021 0.036 0.020 | 0.021 0.028 0.025 0.020 |
| held first | 0.233 0.162 0.088 0.085 | 0.041 0.024 0.019 0.021 | 0.023 0.022 0.017 0.013 | 0.016 0.014 0.013 0.013 | 0.016 0.018 0.013 0.012 | 0.016 0.014 0.014 0.015 |

With held first the NL offset p50 stays at or below 0.024 cycle at depths 1, 3 and 5 and over all depths in every bin of hours 3 to 6 (depth 5: 0.023 0.022 0.018 0.012, 0.016 0.016 0.014 0.011, 0.016 0.019 0.014 0.011, 0.017 0.013 0.013 0.015). The wide lane over all depths with held first: 0.032 0.028 0.019 0.024 in hour 3, 0.017 to 0.029 after.

**Prediction (the requesting session's).** Held share at least 90 % in hours 3 to 6 with held first: **missed** (76.9, 87.7, 87.4, 83.6 %); no held link is released at a cut, and the shortfall is the gap releases of setting satellites (about 125 an hour) and the 24 to 26 min from a link's birth to its hold. NL offset at most 0.03 cycle at every depth: **met**. The users started at 3 h: see the users' table.

**I-b (card IRD), band 1, undeclared integer steps of the undeclared pair-steps, by class.** Plain chain: cut release 9 051 of 107 740, kept 11 191 of 128 495, non-event 9 450 of 156 496, rehost 8 673 of 104 919, returning 514 of 3 633, slip de-seat 320 of 3 118. Plain order: 7 206, 8 128, 6 500, 6 930, 388, 202. Held first: 3 908 of 113 929, 3 780 of 132 698, 3 256 of 144 645, 3 878 of 112 038, 42 of 3 350, 43 of 3 999. Still FAILED; held first removes more than half of the undeclared integer steps of every class.

**P-a (card IRD-8: the held-out consumer's float 3D p50 by hour against the same-build golden, mm).** Arm G 99.5 32.6 39.8 16.0 18.0 15.2; plain chain 445.6 83.5 55.8 76.0 94.8 42.6; plain order 231.7 100.1 47.4 30.2 83.2 27.2; held first 266.1 115.7 35.9 60.9 118.5 31.9. **FAILED on every chain arm, the plain chain included**: the chain's stream gives the float consumer a worse position than the golden's, with or without the ring fix.

**The two-run audit, rehearsed.** Between `nrf7_hf_g6` and `nrf7_olt_g6` (held links and tree pins, every epoch): 458 948 loop checks over the four bands, 0 failing; both runs are right by truth, so this also checks the tool (`scripts/nrf_two_run_audit.py`, section 19.1).
**Users** (the users' build; five users started 30 min, 2 h, 3 h and 4 h after the stream's first epoch and ending with it, float and fixing; `scripts/irdu_user_grade.py cell --from-min 30`; 120 runs, all exit 0).

| stream | start | HELD | held pair-epochs | compared | WRONG | UNRESOLVED | steps declared / undeclared | 95 % Wilson bound on the wrong share |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| plain chain | 30 min | 15.9 % | 7 968 | 2 384 | 0 | 76 | 33 / 28 | 1.6e-3 |
| | 2 h | 14.7 % | 4 824 | 1 755 | 0 | 0 | 23 / 13 | 2.2e-3 |
| | 3 h | 17.1 % | 3 921 | 1 166 | 0 | 0 | 4 / 8 | 3.3e-3 |
| | 4 h | 7.5 % | 488 | 96 | 0 | 0 | 0 / 2 | 3.9e-2 |
| plain order | 30 min | 21.3 % | 10 089 | 3 875 | 12 | 32 | 21 / 11 | 5.4e-3 |
| | 2 h | 31.5 % | 12 564 | 7 369 | 0 | 0 | 15 / 18 | 5.2e-4 |
| | 3 h | 39.0 % | 9 263 | 4 737 | 0 | 0 | 8 / 18 | 8.1e-4 |
| | 4 h | 35.8 % | 3 968 | 2 033 | 0 | 0 | 0 / 0 | 1.9e-3 |
| held first | 30 min | 50.2 % | 23 488 | 12 886 | 0 | 0 | 18 / 1 | 3.0e-4 |
| | 2 h | 56.9 % | 22 247 | 12 832 | 0 | 0 | 13 / 1 | 3.0e-4 |
| | 3 h | 48.1 % | 14 022 | 7 608 | 0 | 0 | 12 / 1 | 5.1e-4 |
| | 4 h | 50.9 % | 7 306 | 4 042 | 0 | 0 | 0 / 1 | 9.5e-4 |

- **U1, no wrong pair integer on a fixing stream for the users started at 2 h or later: PASS** (0 on every stream; the plain chain's count 0).
- **U2, HELD above the plain chain's for those starts: PASS** (held first 56.9, 48.1, 50.9 % against 14.7, 17.1, 7.5 %; the plain order 31.5, 39.0, 35.8 %).
- The plain order's 12 wrong pair-epochs are one user started at 30 min (S27000SIM, pair G10-G23, one cycle on both bands, 2.5 to 3.5 h after its start); not traced. None on the held-first stream, where the users' consensus offsets change by one undeclared step per start (against 11 to 18 on the plain order and 2 to 28 on the plain chain).
- **Prediction, the users started at 3 h hold at least half the time: missed** (48.1 %; the 4 h start 50.9 %).
- **Card IRD-8's K-a**: 0 wrong everywhere; the 95 % Wilson bound below 3e-4 needs about 12 800 compared pair-epochs, which only the held-first stream's 30 min and 2 h starts reach, pooled over the five users (3.0e-4), not per station as K-a counts.
- **K-c: FAILED.** The fixing users' 3D p50 against the float users' in hours 1 and 2 (started at 30 min): 1.00 and 0.80 on the plain chain, 0.99 and 1.03 on the plain order, 1.00 and 1.02 with held first; the time to 3D below 0.10 m is the same fixing and float. Users started at 3 h reach a sustained 5 cm (10 epochs) sooner fixing on the held-first stream (38, 38, 43, 82, 105 min against 38, 54, 94, 106, 134; median 43 against 94), not on the plain order (median 48 against 48).
- The 3D p50 by 15 min, median over the users (mm), on the held-first stream: started at 2 h, fixing 351 201 74 33 55 42 21 16 8 8 4 8 11 14 13 13 against float 351 201 74 40 55 50 38 28 26 24 27 29 30 24 23 20; started at 3 h, fixing 197 109 70 46 40 43 36 29 23 22 22 22 against float 197 109 80 77 81 71 61 44 43 41 37 32. On the plain chain, started at 2 h: fixing 390 147 138 109 80 62 49 48 34 24 25 21 20 18 18 25 against float 390 147 138 108 92 77 71 61 40 39 40 43 40 36 30 28.

**Verdict.** Every bar of the network passes on both re-run arms (0 wrong held integers over 6 h by two audits, every release named, every epoch emitted), and both user bars pass. Of the requesting session's predictions, the stream's NL at every depth is met, the held share of 90 % and the users at 3 h holding half the time are missed narrowly (77 to 88 %; 48.1 %). Held first is the arm that delivers: no held link released at a re-seat, the stream at the truth-fed level from hour 3, its users holding integers half the time with 0 wrong. Card IRD-8's P-a and K-c fail on every chain arm, and I-b stays failed; those are properties of the chain's stream, which the ring fix improves without passing.

**For the author's decision.** (a) The held share left on the table is the gap releases of setting satellites (about 125 an hour) and the 24 to 26 min from a link's birth to its hold, not cuts. (b) P-a: the chain's float consumer trails the golden's by a factor of 2 to 6 in most hours, with or without the ring fix. (c) The plain order's wrong user integers at one user (not traced). (d) Observed data, log only, next (section 19.3).

**Not verified.** P-b and P-c of card IRD-8 (no census of the held-out stations was run); a per-station K-a.

## 19. 2026-11-15: stages N3b, N2c and O1 pre-registered

Assigned by the requesting session after section 16.1 (its words condensed; decided in the author's absence and listed for review). Order: N3's report first; then N3b and N2c on the simulator and O1 on observed data, log only; then stop and report. No run that holds integers on observed data until the requesting session says so.

### 19.1 N3b: a second, later start of the 6 h bed (the two-run audit rehearsed on the simulator)

**Why.** On observed data the safety check of held integers is the agreement of two runs with different starts; on the simulator truth says whether each run is right, so the audit's verdict can itself be checked.

**Run.** `nrf7_hf_g6b`: N3's held-first arm (exe nrf7) started one hour later (`start_offset_hours` 1.504167) to the same end (`max_duration_s` 18 000), with the truth audit.

**Bars.** 0 wrong held integers in the late start by the code's truth audit; the audit between `nrf7_hf_g6` and `nrf7_hf_g6b` shows 0 failing checks (the requesting session runs it; `scripts/nrf_two_run_audit.py` runs it here too). **Reads.** The number of checks per signal; how many common arcs are held in one run and a tree link in the other.

**The two-run audit of this card** (`scripts/nrf_two_run_audit.py`, new). At every epoch common to two runs and on each band, the links whose integers both runs know (held, or for a log run would-be decided, or a tree link with its pin) give the difference D = N_A - N_B per link. Two frames differ by one potential per receiver and per satellite, so on the graph of common links D must equal x_receiver - y_satellite; a breadth-first walk assigns the potentials and checks every remaining link. Checks = common links - vertices + components, per epoch and band; a failing check is a closed loop whose integers the two runs disagree on. Known limit: an error both runs share (one biased wide lane rounded the same way in both) passes it.

### 19.2 N2c: a slip on a held link that the detectors do not flag (the residual monitor's path)

**Why.** N2b-3's slips were both flagged by the producer's latch, so the monitor's release path stayed unexercised; standing invariant 1 asks for it before any holding run on observed data.

**Build (exe nrf8, simulation only, default off; ledger rows UNVALIDATED).** `network.ring_fix.mask_slip_arc` ("<station>:<satellite>"), `mask_slip_tow` and `mask_slip_epochs` (default 1), armed only with `network.ring_fix.truth_root`: at the masked epochs the arc's carried entries are snapshot before PASS A's slip drains and restored after them, and its phase signals are taken out of the free-epoch latch (with the cause), the slip funnel and the bridge pends, so the phase steps under a hold with no latch. The detectors' own traces and counters keep what they saw; post-fit RAIM is not masked. One RINGFIX `mask_slip` event per masked epoch; run-end counts.

**Bed and arms.** s4 = s2's bed (L1C +1 and L2W +1 on S05000SIM-G26 at TOW 265830, `simnrf_s2`) with the mask on that arc at that epoch. The mask needs the ring fix enabled, so the key-off arm is the log rule with the mask (nothing held, the producer's slip response masked): `nrf8_log_s4`; control `nrf8_olt_s4` (N1b-OL, truth, mask); held first `nrf8_hf_s4`. The flagged bed's key-off arm `nrf6off_s2` is read beside them.

**Bars.** The link is released within the monitor's 4 epochs, or earlier by RAIM's attribution (which one is reported); 0 wrong held link-epochs after the release; no other hold wrong at any epoch (the truth audit); every epoch emitted; RAIM rows reported beside the key-off arm. **Reads.** What released the link; how many other holds went; the stream's step at the satellite in the epochs between the slip and the release; minutes until the link is held again. If the monitor does not release it, that is reported at once, not tuned.

### 19.3 O1: observed data, log only, Galileo L1X/L5X (and a GPS read)

**Why Galileo L1X/L5X first** (the requesting session's reading of the chain run of 13 November, `_rap_nwa1nh_n144`, no fixing): its untied links are integer-like on their own (N_1 fraction 0.057 at ring 2, 0.027 for arcs older than 4 h; per-arc wide-lane offset p50 0.075, p90 0.169, p99 0.284, none above 0.40, close to a Gaussian of sigma 0.11 cycle). GPS is not: 27 % of the GPS L1C/L2W arcs carry a wide-lane offset above 0.25 cycle, by receiver. On Galileo E1/E5a a wide lane wrong by one cycle moves N_1 by 2.949, so the N_1 fraction cannot catch it; the wide lane needs its own bound.

**Build (exe nrf8, default off, byte-identical off; ledger rows UNVALIDATED).**
1. `network.ring_fix.pairs`: the pair families considered (`["E:L1X/L5X"]`); empty is all. A chord of another family is never decided, held or traced: it is skipped before the gate and counted at run end (`Network (ring fix, pairs)`).
2. `network.ring_fix.wl_frac_max`: the wide lane's fraction bound, tested last, after the persistence count, with its own refusal (`wl_fraction`), so a refusal names a link every other test would decide; 0 (default) is no bound.
3. The log rule without a truth root: `would_hold` rows and events with their integers; the audit columns stay empty.
4. The decision on Galileo E1/E5a, checked in the code and on the traces: N_1 of the ionosphere-free row uses the pair's own wavelengths (`chainWavelengthM` per satellite and signal: r = lambda_2 / lambda_1 = 1.3391 on E1/E5a, 1.2833 on GPS L1/L2); the lattice veto applies when the producer's lattice lists the chord; a chord's ring is the larger depth of its two vertices in the first signal's tree. A pair link is in the pair family's graph on both bands, so its two ends lie in one component of each band's forest; whether the two bands' depths agree is read from the run's trees and reported.

**Gates (simulation).** N1b-OL on the bed without re-seats and held first on r3c with the new keys at their defaults, byte-identical to nrf6 (`nrf8_ol_nr3` against `nrf5_ol_nr3`, `nrf8_hf_r3c` against `nrf6_hf_r3c`).

**Runs (Release, observed data: the bed of `_rap_nwa1nh_n144`, DOY 144, 6 h, 56 receivers, GPS and Galileo, holds off; its arm file copied; smoke first).**
- `nrf8off_n144`: the key off. Read (not a bar, the builds differ): whether its products equal `_rap_nwa1nh_n144/products.txt`.
- `nrf8_log_n144`: the ring fix on, rule `log`, order `certain`, gate `odds`, pairs `["E:L1X/L5X"]`, `wl_frac_max` 0.25. **Gate: products byte-identical to `nrf8off_n144`.**
- `nrf8_log_n144b`: the same started one hour later (`start_offset_hours` 1.004167, to the same end), with another datum receiver: no key names a family's root, but `network.phase_datum_eq34_receiver` names the chain's datum receiver for every family, so run B sets it to a receiver other than run A's Galileo root (BOGT); the roots of both runs are reported.
- `nrf8_logg_n144` and `nrf8_logg_n144b`: the same two starts and roots with pairs `["G:L1C/L2W"]` and no wide-lane bound (a read for the multi-system step; nothing held, no bar).

**Reads.** Would-be links and link-epochs by hour and by ring; minutes from an arc's birth to its first would-be decision; the distributions of frac_wl, frac_if and sigma_if at the first would-be decision; refusals by reason; links refused by the wide-lane bound alone. The two-run audit on the would-be integers and tree pins, per epoch: **bar 0 failing checks**, with the number of checks; a failure is traced, not explained away. Known limit: an error both runs share passes it; the wide-lane bound is the guard there. No users in O1 (the log rule leaves the stream unchanged).

### 18.1 2026-11-15: the S27000SIM user failure, traced (asked by the requesting session)

**The failure.** S27000SIM started at 30 min is thrown about 150 m off at its third epoch (TOW 262920: 1.16 m, then 147.8 m, up -111 m, ZWD 15.50 m against 0.13 m, formal 3D sigma 1.8 m) on both ring-fix streams, float and fixing alike, and is fine on the plain stream. It recovers (below 1 m for 5 min) 32 min after its start on the plain-order stream and 142.5 min after it on the held-first stream.

**What differs at that epoch.** The two streams' corrections differ by millimetres to centimetres; neither changes a code bias or marks a phase-bias discontinuity there. The user declares a phase-bias discontinuity itself when a bias moves by more than 0.25 cycle between epochs. At 262920 E24's phase bias moves by -0.26 (L1C) and -0.31 (L5Q) cycle on the plain stream and by -0.24 and -0.28 on the ring-fix streams, so the user resets E24 on both bands on the first and on L5Q alone on the second. E24 is the user's Galileo reference satellite at its second epoch (G05 the GPS one), and the reset hands the reference over (to E11). On the ring-fix streams the filter then diverges into the slant ionosphere (50 to 87 m on most satellites) and its ambiguities (hundreds of metres).

**Replays on edited copies of the stream** (one phase-bias record moved by 3 to 14 mm at 262920, enough to cross the user's threshold one way or the other; `_rap_s27x_*`, 30 min each, the users' build):

| stream | edit | resets of the two reference satellites at 262920 | 3D at epochs 3 and 4 |
| --- | --- | --- | --- |
| ring fix | none | G05 both bands, E24 L5Q | 147.8 m, 148.8 m |
| ring fix | E24 L1C over the threshold | G05 both, E24 both | 147.8 m, 148.8 m |
| ring fix | G05 L1C under it | G05 L2W, E24 L5Q | 147.8 m, 149.4 m |
| ring fix | E24 L5Q under it | G05 both, E24 none | 1.77 m, 0.52 m |
| plain | E24 L1C under it | G05 L2W, E24 L5Q | 1.89 m, 0.59 m |
| plain | G05 L1C over it | G05 both, E24 both | 1.89 m, 0.52 m |

**Reading.** Not a one-band declaration: declaring E24 on both bands leaves the failure, and the plain stream takes an L5Q-only declaration without harm. Not the GPS reference's declaration either. The trigger is the reset of the user's Galileo reference satellite at its third epoch on the ring-fix streams' values: avoided by 1 cm on one record, the same user on the same stream does not diverge, and on the plain stream the same reset is harmless. A cold user re-referencing its Galileo single differences at its third epoch lands, for some inputs, in a state far off with a formal sigma of 1.8 m, and its rows then pull it back slowly (32 to 142 min). That is a user-side defect of the reference handover early in a user's life, which the ring fix's stream happens to trigger here; not traced to a line of code. A user could be made to recover by a consistency check between its code residuals and its formal sigma that re-initializes it (or by not handing the reference over in its first epochs); a user-side change, not made here.

**The 30-min starts with and without S27000SIM** (the other four users):

| stream | HELD with / without | WRONG with / without | 3D p50 by 15 min, float, first 3 h, without S27000SIM (mm) |
| --- | --- | --- | --- |
| plain chain | 15.9 % / 15.1 % | 0 / 0 | 338 176 119 58 41 49 56 28 29 24 22 20 |
| plain order | 21.3 % / 24.2 % | 12 / 0 | 387 152 145 64 32 27 31 25 23 19 17 16 |
| held first | 50.2 % / 49.2 % | 0 / 0 | 389 158 176 86 51 25 22 19 17 21 23 21 |

The plain order's 12 wrong pair-epochs at that start were S27000SIM's. Without it, held first's fixing users read 389 158 176 87 51 25 20 13 13 9 10 7 mm over the first 3 h (float 389 158 176 86 51 25 22 19 17 21 23 21), the plain chain's fixing users 338 176 119 58 44 48 50 37 37 26 21 21.

### 19.4 2026-11-15: O1 amended (the requesting session's word)

The separate GPS L1C/L2W log runs of section 19.3 (`nrf8_logg_n144`, `nrf8_logg_n144b`) are dropped: the requesting session runs a log-only pilot on the same bed with exe nrf7 (all pairs, no wide-lane bound, two starts) that gives those traces. Item D stands as pre-registered (the build with `network.ring_fix.pairs` and `wl_frac_max`, and the Galileo L1X/L5X log runs on it); if the pilot's two-start audit fails on Galileo L1X/L5X, item D changes on its word.

### 19.5 2026-11-15: the two-start audit, amended before O1's runs (from N3b)

N3b's two runs are both right by truth, yet the raw two-run audit fails 125 386 of 512 298 checks: under the accumulated wind-up convention each run gives an arc the wind-up branch floor(wu(t0) + 0.5) at its own start of that arc, so an arc older than the later start carries a different integer in each run, the same on both bands of a link (as a wrong N1 with a right wide lane would). Removing each run's true branch leaves 0 failing of 512 298; comparing only the arcs both runs start together leaves 0 failing of 206 324 (full results in the next results section). O1's audit therefore compares only arcs born after run B's first epoch (`scripts/nrf_two_run_audit.py --born-after`), its bar unchanged (0 failing checks), with the raw audit reported beside it. On observed data the branch can be removed only if the producer traces its accumulated wind-up per arc; that trace does not exist yet.

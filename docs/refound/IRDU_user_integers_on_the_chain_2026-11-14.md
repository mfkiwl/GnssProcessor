# IRDU: the user's integers on the chain's stream, measured on the simulator

**STATUS**

- **id:** IRDU
- **topic:** network-vehicle
- **status:** open
- **summary:** Pre-registered 2026-11-14 before any graded run. A simulated user's float ambiguities and fixed integers on the network's product stream, graded against the fixture's truth and datum-free (the double difference of fixed minus truth between two users is zero; fixed minus truth of a satellite pair at one user is constant except at a declared discontinuity). Stage A: the instrument and its controls (a truth wire, the golden posture). Stage B: the chain on or off by the emission holds on or off on a quiet bed with receiver phase biases. Stage C: one scripted event per bed, ranked by what it costs the user. Stage D: whether the network's own certified integers were available and right at each re-host, then a default-off research switch that takes them. Results are appended below.
- **source:** the author's remarks of 2026-11-14 (section 1); [ARR](../record/refound/ARR_integer_ambiguity_review_2026-11-07.md) sections 2.1, 2.2, 6 and 7; [IRD](IRD_integer_recovering_datum_2026-10-13.md) sections 3, 5 and 8; [IRDC](IRDC_integer_recovering_datum_events_2026-11-02.md) sections 6 and 7 (the hold of the certified branch); [IRDD](IRDD_integer_recovering_datum_rows_2026-11-03.md) sections 2 and 4; [IRDG](../record/refound/IRDG_floor_off_rpb_in_block_2026-11-09.md) sections 7 and 8; the instrument of card ARN (the fixing control's user resolver on a product stream; uncommitted, branch `ar/rx-sat-code-bias`)
- **dates in the text:** 2026-11-14
- **knobs / posture:** the arms of `scripts/ird_make_arms.py` (golden pinned at `a02ccfb`): R1, A1krhRsm and their holds-off twins R1h and A1krhRsmh (new on this branch: `network.emit_pb_hold`, `network.emit_pb_hold_trip_generation` and `network.emit_pb_hold_phase_clock` false), every network run with the run settings `network.parallel_max_threads` 8 and `processing.eigen_threads` 8; the user runs of `scripts/irdu_users.py`; stage D's switch is a new default-off key, ledger UNVALIDATED, never armed in a golden
- **hashes / run dirs:** branch `irdu/user-integers` from main `43ec792` (worktree `D:/GnssProcessorSupport/worktrees/irdu`); network runs on this branch's own Release build (sha256 recorded with the first results); user runs on `D:/GnssProcessorSupport/gates/exe/irdu/gnss_processor_irdu_rscb3.exe`, a renamed copy of the fixing control's `gnss_processor_rscb3.exe` (sha256[:16] `5ecf8e1c765fafe3`); runs `_rap_irdu_*` under `D:/GnssProcessorSupport/runs_nom/`; grader `scripts/irdu_user_grade.py`

**Outcome.** Pre-registered 2026-11-14; no graded run yet. The question is whether a simulated user of the integer-recovering chain's product stream fixes integers that agree with truth, which scripted events break that, and what the network's own certified integers would add at reference changes. The instrument replays the stream at five stations of the bed with the fixing control's resolver and grades the held integers between users and in time, without a datum. Expectations, bars and stopping points are written in sections 3 to 7 before any of their runs.

## 1. The question

The author, 2026-11-14: "It almost seems like the theory is easily testable on the sim. I mean, we can create any scenario under simulation, like satellites dropping, slips (we already did), etc." and "Every satellite's phase bias must tied to one receiver through whole-cycle pins seems much more straightforward if the network is already integer...".

Card ARR (sections 2.1 and 2.2) derived the user's between-satellite single-difference ambiguity on this stream, a_u^{sp} = (N_u^s - N_u^p) + D_sp, and found two breakers on the goldens: each satellite's phase bias is pinned on a float at its own anchor receiver, so D_sp keeps the difference of two network receivers' phase biases, and the emission hold freezes each bias at its cold value. The chain of card IRD replaces the anchors with one receiver frame (D_sp = z^s - z^p, an integer combination of the tree's pins, card IRD section 3); the author's order of 2026-11-09 (card ARR section 7) is the chain first and the replacement of the freeze second. As far as the record shows, the producer's frame (bar I-b) and the float user's position have been graded on the chain, but no user's fixed integers on the chain's stream have been graded against truth. This card measures that at the user.

The author's decisions bound the card. The offline per-satellite offsets of card ARN are a benchmark only; the emission-side transform stays declined; integer constraints or a hold inside the network solve stay a standing do-not-build (card FCF, the wide-lane cascade and Phase-3 re-pin verdict). The author's hold of the certified re-host branch (card IRDC section 7, 2026-11-02) stays in force for everything outside stage D's research arm.

## 2. The instrument

**Users.** Five stations of each bed replay the network run's `products.txt` as users: SZZ000SIM (the fixture's held-out consumer, never in the network) and S48000SIM, S40000SIM, S27000SIM and S32000SIM (network stations, so their data entered the products; the nearest stations to SZZ000SIM that no event fixture scripts, except S48000SIM, which the abrupt cut `ird_msx` blanks). A user reads its own fixture RINEX, never a file the network arm rewrote, so on the cut beds a user sees every satellite it tracks. The user's integer property does not depend on whether its data entered the network: D_sp is the stream's and is common to every user; a network station as a user is an in-sample observer of the float's precision and is reported apart from SZZ000SIM.

**The recipe** (the fixing control of card ARN, `scripts/irdu_users.py`): the network run's own `arm.json` with `network.closed_loop.replay_products_path` = its `products.txt`, `consumer_undifferenced` false, `ar_mode` 1, `ar_wl_only` false, the user's station, `pb_hold_presence_flip` equal to the network run's emission hold (false on a holds-off stream), `network.trace_consumer_sat` true, `filter.process_noise.position_q` 0, the resolver log at debug, `processing.eigen_threads` 1, and `estimation.ambiguity_resolution` = {mode 1, ratio_threshold 5.0, ratio_upper_bound 10000, elevation_mask 20, min_epochs 10, max_position_sigma_m 0.05, enable_partial_ar true, hold_variance 1e-7, wl_from_float true, nl_sigma_floor_cyc 0.04, nl_iono_free_row true, hold_release_cyc 0.25, refloat_partner_signal true}. Two variants per user: **obs** (ratio_threshold 1e9: no fix is ever accepted; the float user) and **fix** (wl_branch_check true; the fixing user).

**Readings** (`scripts/irdu_user_grade.py`, each printing n; the window starts 30 min after the user's first epoch):

| reading | definition |
| --- | --- |
| FRAC | obs runs, every CLFRAC pair and epoch: the wide lane w = n1 - n2 and the N_1 float of the ionosphere-free row with w rounded, n = (f1 n1 - f2 n2 - f2 round(w)) / (f1 - f2); mean \|fraction\| and the shares within 0.10 and 0.15 cycle; the uniform null reads 0.25, 20 % and 30 % |
| PAIRS | obs runs: per satellite pair formed reference-free inside each epoch and seen at least 20 epochs, the circular mean of the N_1 fraction; the share of pairs within 0.10 cycle |
| HELD | fix runs: the share of wide-lane pair-epochs held on integers after the first 30 min of resolver activity (a WLFLOAT line within 0.01 cycle of an integer with sigma below 0.01) and the minute of the first hold |
| WRONG (a) | fix runs: the held integers of an epoch (WLFLOAT held and both signals' CLFRAC lines within 0.01 cycle of an integer), referred to the epoch's largest reference group, minus the truth: E_u(i) = F_u(i, r) - [N_u(i) - N_u(r)] per signal, N = the slip-accumulated truth plus the wind-up branch of the user's own arc (`scripts/consumer_ar_grade.py`). For every satellite pair held by two or more users at one epoch, v_u = E_u(i) - E_u(j) must be equal at every user. A user against a strict majority of three or more is WRONG; a disagreement without a majority is UNRESOLVED |
| WRONG (b) | fix runs: a change of v_u between two consecutive epochs at which the user holds the pair is a STEP, DECLARED when the stream marks a discontinuity of either satellite between them (a P record's phase_disc or gen= field changes, an R record names it, or the E record declares a datum change), else UNDECLARED. The consensus offset (the value the holding users agree on, or the strict majority) is the stream's integer offset of the pair; its changes are listed with the chain event at that epoch |
| POS | 3D error median per hour from `consumer_replay_hourly.csv`, obs and fix runs |

**What the readings cannot see.** A stream with a non-integer D_sp can pass WRONG (a): users with converged floats round the same fraction the same way. FRAC is the reading of the integer property; WRONG is the reading of the user's integers once fixed. A holds-off stream declares no discontinuity at all (its P records carry no phase_disc and no gen=; checked on card IRD's arm `_rap_ird2_a0h_gs`), and the chain's own declarations (`declared_keys` rows of `network_events.csv`) do not reach the wire (card IRD-7 is not built): on such a stream every step of a user's integers is undeclared on the wire, and the card lists each step with the chain event that caused it.

## 3. Stage A: the controls (2026-11-14)

The bed is ARL rung 3c (`runs/simarl_r3c`: receiver phase biases at every station, GIM ionosphere, a time-varying wet delay, phase colour; GPS only), 2 h.

- **A-1, positive control.** A truth wire (`scripts/simnet_truth_wire.py`, the template the products of arm G on r3c): every P record at the truth's OSB, one generation. Bars: pooled FRAC means at most 0.08 cycle on the wide lane and on N_1; HELD at least 50 % pooled; WRONG 0 and UNRESOLVED 0; 0 undeclared steps.
- **A-2, positive control with integer offsets.** The same truth wire with `--integer-gauge 7` (a per-satellite and per-signal integer in [-40, 40]): the integer frame of a chain. Bars as A-1; the consensus offsets are the gauge differences.
- **A-3, negative control.** Arm G on r3c (the golden posture, holds on). Bar: pooled FRAC means at least 0.20 cycle on both the wide lane and N_1, at SZZ000SIM and pooled. WRONG is reported without a bar (section 2).

If A-1 or A-2 fails, the instrument is void and the card stops until it is repaired.

## 4. Stage B: the theory end to end on a quiet bed

A two-by-two on r3c, 2 h, the same build: chain off (arm R1: the golden posture with the slip set, the log-only search and the IRD traces that the chain arm also carries, the record's reference arm) or on (arm A1krhRsm, the in-block key), each with the emission holds on (as the arm defines them) or off (R1h, A1krhRsmh). Supplementary, the holds-off pair on the microscope (r1c with zero-ionosphere rows on the network side; the users estimate their ionosphere freely; the fixture's ionosphere is zero).

**Expectations, written before the runs.** By the theory only the cell chain on and holds off has an integer D_sp; chain off keeps the anchors' receiver frames (card ARR section 2.2), and the hold freezes the cold estimate plus the phase-clock transfer (card ARR section 2.2, card SZE in card ARR section 6). The record names what may still break the theory's cell on r3c: per-band chord floats of about 0.2 cycle with a free ionosphere, so a re-host that rounds its target per band can step the moved side by whole cycles; one re-host every 2.5 min on the ARL beds, each a cut release (card IRDD section 4); the float's quiet-epoch wander (card IRDG section 7.7: the pre-hold wire moves above the fractional bar on a fifth of the pairs between epochs); and steps that do not reach the wire (section 2).

**Bars (the theory's cell, A1krhRsmh on r3c).** PASS when: pooled FRAC means at most max(0.10, the truth wire's + 0.05) cycle on the wide lane and on N_1; at least 90 % of PAIRS within 0.10 cycle; WRONG 0 and UNRESOLVED 0. The other three cells are predicted at the null (pooled N_1 mean at least 0.20). Undeclared consensus steps are reported, each with its chain event; they are the declaration gap of section 2, not a failure of the integer property. On the microscope the theory's cell is predicted to pass with N_1 at most 0.05.

**Stop.** If the theory's cell fails, the card stops after stage B and traces why; that trace is the result.

## 5. Stage C: one injected event per bed, the chain as built

The arm is A1krhRsmh (the chain as built, holds off: the theory's cell of stage B), 2 h, on the existing single-event fixtures of `scripts/ird_make_arms.py`, each beside the quiet r3b control on the same build:

| class | bed | event (epoch; TOW = 261030 + 30 (epoch - 1)) |
| --- | --- | --- |
| a station's return (interior vertex) | `ird_rv16` | S45000SIM blanked from epoch 152, returns at 184 |
| a slip on a satellite-side tree edge | `ird_t1` | L1C +1, S10000SIM G09, epoch 158 |
| a slip on the root's own edge | `ird_tr` | L1C +1, S13000SIM G03, epoch 158 |
| a root handover | `ird_rg` | the root S13000SIM blanked from epoch 152, returns at 172 |
| a split and merge, the root outside | `ird_ms` | split at 158, merge at 178 (control `ird_ms_ctl`) |
| a split and merge, the root inside | `ird_msr` | split at 158, merge at 178 (control `ird_msr_ctl`) |
| an abrupt cut | `ird_msx` | nine stations and six satellites cut from 158 for 10 min |

Natural satellite sets, rises and returns happen on every bed, the quiet control included; a scripted network-wide satellite drop is added (`scripts/ird_fixture_gate.py`) only if the quiet control shows none of its kind.

**Readings per class at the users:** FRAC before (10 min before the event) and after (the 10 min from the event and the 20 min after them); HELD in the same windows; WRONG (a) from the event to the run end; the consensus steps at the event with their chain rows; the time from the event until the users' held share regains 90 % of its pre-event level (three consecutive epochs). **Ranking rule:** by the WRONG count, then the recovery time, then the undeclared consensus steps.

**Expectations from the record.** The rehost row's releases erase converged carries (2 944 in 2 h, card IRDD section 4), so the released side's fractions degrade until the carries return; the root row keeps the frame (card IRDD section 5), so a root handover should cost what its re-hosts cost and no more; the slip and merge rows can step the frame by integers (card IRDE); every step is undeclared on the wire.

## 6. Stage D, census: the network's own integers at each re-host (no code)

At each re-host of stage C's beds and of the quiet control (rows RehostCertified and RehostUncertified of `network_chain_edges.csv`): whether the previous epoch's chord table determined the new edge's integer, and whether that integer is right against truth in the incumbent frame (`scripts/ird_frame_census.py cert`, its `rehost_grade`), by event class and by the time since the last release of the component. Expectation from card IRDG section 7.5 (0 of 3 116 would-be certifications wrong on r3c with the key): most re-hosts on these beds are certified and right; the census counts how many and how fast after a damaging event.

## 7. Stage D: a research switch that takes the certified integer

A default-off key on this branch: a re-host whose new edge the previous chord table certified (the two-band fix, no conflict) takes that integer as its target with a known zero step and keeps its carries; every other re-host keeps the release. Ledger row UNVALIDATED; never armed in a golden; the author's hold of 2026-11-02 stays in force everywhere else. Gate: off identical on the same build (products and every trace byte-identical on r3c and one event bed), a unit test of the decision. Readings on stage C's beds against the switch off: at the users HELD and WRONG; the carries erased; the float user's position by hour (the network run's own held-out consumer, and the obs users).

## 8. Further ideas, each pre-registered as its own section before it runs

(1) Double differences do not depend on the reference: how many of the integers the events of stage C need were determined and right in the quiet stretches before them. (2) A truthful per-key integer declaration read from the chain: how many of stage C's wrong user fixes it would have prevented (measure only).

<!-- Results are appended below this line under dated headings. -->

## 9. 2026-11-14: stage A, the controls

**What ran.** The network runs use this branch's Release build at `f49f2b1` (main `43ec792` plus the scripts of the pre-registration), copied as `build/x64-Release/gnss_processor_irdu_net0.exe` (sha256[:16] `399f1467d34fb82d`), with the run settings of the STATUS block. Smoke first: arms G and A1krhRsmh on r3c for 0.1 h (exit 0, 13 of 13 epochs emitted each), and two users on the second (exit 0, the resolver log writes CLFRAC). Arm G on r3c for 2 h: exit 0, 240 of 240 epochs. The truth wires are `_rap_irdu_tw_r3c` and `_rap_irdu_twg_r3c` (`scripts/simnet_truth_wire.py`, template G's `products.txt`; the second with `--integer-gauge 7`). Every one of the 30 user runs exits 0. Grades: `runs_nom/_irdu_grades/a_*.json`.

| control | FRAC 30 to 120 min: WL, N_1 | FRAC settled (90 to 120 min): WL, N_1 | PAIRS within 0.10: 30 min, settled | HELD pooled (per user) | WRONG, UNRESOLVED (compared pair-epochs) | steps | verdict |
| --- | --- | --- | --- | --- | --- | --- | --- |
| A-1 truth wire | 0.060, **0.160** | 0.057, 0.081 | 32.8 % of 122, 73.6 % of 53 | 86.3 % (72.6 to 97.5) | 0, 0 (3 440) | 0 | **FAILED as written** (the N_1 clause, 0.160 against 0.08); the other clauses pass |
| A-2 truth wire, integer gauge | as A-1 | as A-1 | as A-1 | as A-1 | 0, 0 (3 440) | 0 | as A-1 |
| A-3 golden posture (arm G) | 0.248, 0.249 | 0.304, 0.243 | 18.9 %, 13.2 % | 9.8 % (0.0 to 40.4) | 0, 0 (58) | 0 | PASS |

**Readings.**

1. **The integer readings are exact on an integer stream.** Every held integer at every user minus the truth is the stream's own offset: (0, 0) on all 754 held satellite-epochs of SZZ000SIM on A-1, and on A-2 the gauge differences (for instance (22, 61) and (-31, 63)) with no disagreement between users. A-2 reproduces A-1 in every fraction and held share, as integer offsets must. The truth convention (slip-accumulated integer plus the wind-up branch of the user's arc) needs no correction.
2. **The users' float narrow lane converges slowly on r3c.** On the truth wire the held-out user's N_1 fraction by 15 min bins from its first epoch reads 0.30, 0.20, 0.29, 0.17, 0.12, 0.16, 0.05 and 0.05 (the wide lane 0.09 to 0.02); the settled N_1 per user is 0.051 (SZZ000SIM), 0.056, 0.063, 0.102 and 0.133. No stream can meet a fraction bar of 0.08 over 30 to 120 min on this bed, nor the 90 % PAIRS clause of section 4 (33 % on the truth wire in that window, 74 % settled). The fixing user nonetheless holds 86 % of the wide-lane pair-epochs from minute 42 to 57, all correct: the resolver's wide lane and ionosphere-free row decide sooner than the per-pair float fraction settles.
3. **The golden stream reads at the null and still gets fixes.** Two users hold integers on it (S32000SIM 40.4 %, S27000SIM 6.4 %): the ratio test accepted near-integer floats of a non-integer stream. The fixed position is worse than the float where it held (hour 2: S48000SIM 86 against 18 mm, S32000SIM 81 against 28 mm). WRONG (a) sees nothing there because those pairs are rarely held by two users at once (58 compared pair-epochs): on a non-integer stream the readings that speak are FRAC and the position, as section 2 says.

**Re-registration (2026-11-14, a decision of this session, flagged for the author's review).** By section 3's rule the instrument is void for fraction bars over 30 to 120 min on r3c, and the card stops until it is repaired. The repair re-registers the window and the bars of section 4 against the truth wire on the same bed and window. It is written before any stage-B cell is graded at the user (the stage-B network runs had finished and their user replays were running; nothing of them had been read):

1. FRAC and PAIRS bars are read in the settled window, 90 to 120 min after each user's first epoch; the 30 to 120 min window is reported beside it.
2. The theory's cell passes when its settled pooled WL and N_1 means are at most the truth wire's settled means plus 0.05 cycle (r3c: 0.107 and 0.131), its settled PAIRS share within 0.10 is at least the truth wire's less 15 points (r3c: 58.6 %), its pooled HELD is at least half the truth wire's (r3c: 43.2 %), and WRONG and UNRESOLVED are 0. A null cell reads a settled pooled N_1 mean of at least 0.20.
3. The microscope column is read against its own truth wire (`_rap_irdu_tw_mic`, template the products of `_rap_irdu_ch_mic`, fixture r1c), with bars of the same form.
4. The record keeps A-1's and A-2's fraction clause FAILED as written; their integer clauses PASS, and A-3 PASSES.

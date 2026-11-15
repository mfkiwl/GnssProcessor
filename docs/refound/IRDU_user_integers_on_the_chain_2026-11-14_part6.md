# IRDU part 6: the phase step declaration on what a user sees (section 14 of card IRDU)

**STATUS**

- **id:** IRDU-part6
- **topic:** network-vehicle
- **status:** open
- **summary:** Section 14 of card IRDU, continued from [part 5](IRDU_user_integers_on_the_chain_2026-11-14_part5.md) (2026-11-14): approach 1 of section 13.5, approved by the author, built on the simulator and default off as card IRD's step IRD-7 (emission and declarations). The key `network.disc_phase_visible` declares a phase step of a satellite and signal when the change of its clock less phase bias, less the median of that change over the satellites of its constellation and signal, exceeds the discontinuity threshold; the rule travels in the stream header (`discpv=`) and a replay reproduces the counters. Runs A to E are pre-registered below before any graded run. Results are appended below.
- **source:** [part 5](IRDU_user_integers_on_the_chain_2026-11-14_part5.md) sections 13.2 (the declarations-off arm), 13.3 and 13.5 (the cause, approach 1); [IRD](IRD_integer_recovering_datum_2026-10-13.md) section 11, step IRD-7 and its frozen bars

**Outcome.** Built and unit-tested; the graded runs are pre-registered below. The key declares a phase step only when what a user of between-satellite differences sees moves: a satellite's clock less phase bias, against the median of the other satellites of its signal. On the simulator's control streams an independent replay of the rule gives the counts of the requesting session's offline tool to the step (536, 987 and 1 960 against 1 542, 1 798 and 2 610 for the phase bias alone).

Sections 1 to 10 are in [IRDU](IRDU_user_integers_on_the_chain_2026-11-14.md), section 11 in [part 2](IRDU_user_integers_on_the_chain_2026-11-14_part2.md), sections 12 to 12.5 in [part 3](IRDU_user_integers_on_the_chain_2026-11-14_part3.md), sections 12.6 to 12.11 in [part 4](IRDU_user_integers_on_the_chain_2026-11-14_part4.md), section 13 in [part 5](IRDU_user_integers_on_the_chain_2026-11-14_part5.md). Results are appended below.

### 14 2026-11-14: the step declaration on what a user sees, built (card IRD step IRD-7; the graded runs pre-registered before they run)

**Assigned** by the requesting session after the author's approval. The author was asked "Have the Opus session build step declarations on what a user sees (simulator, default off)?" and answered "Yes, assign it". Nothing else is approved: not the emission hold, not the datum change, not the scaled threshold, and not an extension of the users' rule of 12.11 (that question stays with the author). The requesting session re-graded 13.2 to 13.5 and reproduced them, except the 92 to 95 % share of 13.3, which it did not re-grade. Its offline tool (`D:/GnssProcessorSupport/presentation/agu26/fixing_control/tools/stream_user_view.py`: jumps above 0.25 cycle between consecutive epochs, counted on the phase bias, on the clock less the phase bias, and on the clock less the phase bias less the median over the satellites of the signal, with four or more satellites) gives the reference counts:

| run | phase bias alone | clock less phase bias | less the satellites' median |
| --- | --- | --- | --- |
| `_rap_irdu_q1_nr3` | 1 542 (last 37.0 min) | 1 277 (28.0) | 536 (15.5) |
| `_rap_irdu_zw_nr3` | 1 798 (48.0) | 1 567 (39.5) | 987 (35.0) |
| `_rap_irdu_zw_r3c` | 2 610 | 2 414 | 1 960, through the run |

**Where it sits.** Card IRD section 11, step IRD-7 (emission and declarations). Its frozen bars apply as follows:
- **Off byte-identical with no token:** run A.
- **A replay reproduces the discontinuity counters byte for byte:** the unit test, and run B's producer and replay counts.
- **Every step declared:** here every step of what a user sees, by run D's audit and run E.
- **The W bars on the emitted phase biases:** unchanged by construction, since the key changes no emitted value, only the counters and the header.

The other IRD-7 bars (the settle regeneration, `signal_integer`) do not apply.

**What was built** (this branch; committed with this section, before any graded run):

1. **The rule:** a pure function, `products/PhaseVisibleStepTest` (`decidePhaseVisibleSteps`, `phaseVisibleMedian`). For each key it takes d, the change of the clock less the phase bias since the key's last emission with a clock.
   - Groups are (constellation, signal).
   - A key votes when its change is defined and its baseline is the previous emission (consecutive epochs).
   - The median is the middle value, or the mean of the two middle values for an even count.
   - With at least four voters (`kPhaseVisibleMinSats`), a key is declared when |d less the median| exceeds its threshold (discfrac times the wavelength, or the flat gate).
   - Below four voters, each key is tested on its own change d, so the shared part is then declared with the rest (the safe side).
2. **The emitter** (`NetworkProductEmitter`, eighth construction parameter, the minimum count; 0 is the legacy test).
   - A pre-pass over the epoch forms the groups before the per-satellite loop stamps the counters; a tested key takes the rule's verdict in place of the phase bias alone.
   - These keys are not tested:
     - a key without a clock in this or its previous emission keeps the legacy test;
     - a first record is seeded;
     - a return past the staleness horizon is re-seeded, as the legacy test does;
     - a key under a forced mark is declared by the mark and does not vote.
   - Off, the pre-pass does not run and the legacy code path is unchanged.
   - The state (each key's baseline and the previous emission) is in the snapshot as a version 4 header, written only when armed.
3. **The stream header:** the S record carries `discpv=4` when armed (the legend declares the optional token). `checkContract` compares it, and `makeReplayEmitter` builds the replay's emitter with it, so a replay of the file reproduces the counters. The user's reaction to a counter change is unchanged.
4. **The key:** `network.disc_phase_visible` (default false), a getter with Doxygen, and a ledger row (UNVALIDATED, area DatumSignalling).
   - Under `network.emit_pb_hold` the loader disarms it with a warning, since the hold's generations declare the held steps, and the header then carries no token (item 7).
5. **Both edges** (standing invariant 7). Counters over the emitter's life, printed at the run end of the producer and of a replay:
   - first records, returns tested against an older baseline, returns past the horizon;
   - keys under a forced mark, keys without a clock;
   - vote-set entries and exits;
   - groups entering and leaving the below-minimum state;
   - the legacy test's verdicts on the tested keys, and the keys declared here that the legacy test would not have declared.
6. **Unit tests:** 19 cases in `tests/test_phase_visible_step_test.cpp`, all passing on the Debug build with the 173 tests of the neighbouring emitter, stream-file, mark-scope, hold and snapshot suites.
   - The rule on hand-built epochs: a shared move alone, one satellite's own move, fewer voters than the minimum, untested keys, groups, the even median.
   - The emitter: off is the legacy test; a shared move; an own move; a phase-bias move matched by its clock; below the minimum; a satellite appearing, leaving and returning; a key without a clock; a forced mark; a return past the horizon; the snapshot round trip and its refusal by an unarmed emitter.
   - The header token: off byte-identical; the parse; the replay emitter; the contract check.
   - A file replay reproducing the producer's counters epoch by epoch.
   - The config key and its disarming under the hold.
   - The stream file's legend test (`NetworkProductIoTest`) now arms the token too, so it checks that the legend declares it.

**The shared part (item 3): whom the declaration protects.** The header states the assumption, and the stream does not declare the shared move as a step of its own. A user that differences between satellites the stream corrects loses the shared part in its differences, and the closed-loop consumer differences in that way. A user that does not difference absorbs a move common to every satellite of a signal into its receiver terms. A user that pairs a corrected satellite with one the stream does not correct (12.9) reads the shared part as a between-satellite move and carries it undeclared.

The 12.11 rule (`network.closed_loop.drop_unrecorded`) removes that case at the user. Without the rule, 13.2 measured that such users still end better with no declarations at all after their 45th minute, and are mixed before it. The run-end line counts the epochs whose shared move exceeded the bar: the steps a non-differencing user would have needed.

**The clock's declaration (item 5).** The key does not change the clock's discontinuity counter or the code-bias jump test. When a clock step is declared, the user's engine (`RealTimeEngine::reinflateOnClockDisc`) re-inflates the variances of its inter-system biases (all of them on a step of the reference constellation's clock) and resets no phase ambiguity; the receiver clock, free every epoch, absorbs the common part. A clock step with the clock less phase bias continuous therefore does not re-float the user's phase ambiguities. Finding: none; nothing changed.

**A pair property, stated before the audit.** Each satellite is tested against the median, so two satellites moving apart by just under the threshold each make their pair's difference move by up to twice the threshold with neither declared. The legacy test on the phase bias alone has the same property. Run D's audit therefore counts undeclared pair jumps above twice the threshold, which must be 0 by construction (a check of the implementation), and above the threshold, reported for the key and for the control.

#### 14.1 The runs, pre-registered

**Executables.** Network: the build of this section, copied to `build/x64-Release/gnss_processor_irdu_pv1.exe` (sha256[:16] `cee9504ce1d1424e`); the controls of 13.2 (`gnss_processor_irdu_fp2.exe`) and an r3c control on the same fp2 executable (`irdu_zwc_r3c`). Users: the same build, copied to `D:/GnssProcessorSupport/gates/exe/irdu/gnss_processor_irdu_pv1.exe`, folders with the suffix `_bpv1`. Each network arm is preceded by a 10-epoch smoke, cold start, 2 h, Release. Arms (`scripts/ird_make_arms.py`; knob group `fpin_nr3_all_pv` = Q1's keys plus the key, `--knob` elsewhere):

| tag | bed | base | key |
| --- | --- | --- | --- |
| `irdu_q1k0_nr3`, `irdu_zwk0_nr3`, `irdu_r3k0_r3c` | irdu_nr, irdu_nr, r3c | Q1, the plain chain arm, the plain chain arm | off (the new executable) |
| `irdu_q1pv_nr3`, `irdu_zwpv_nr3`, `irdu_r3pv_r3c` | the same | the same | `network.disc_phase_visible` true |

**A. Key off.**
- The new executable's `products.txt` is byte-identical to the fp2 control's on Q1, the plain chain arm and r3c in every data record. The one `#` legend comment line differs: it declares the new optional token, the codebase's rule for a wire extension. The reader skips it, and byte comparisons of stream files strip the `#` lines.
- The users are byte-identical between the previous user build (`ur1`) and the new one on the control streams, by `scripts/irdu_build_identity.py`:
  - Q1: 30 replays (starts 0, 15 and 30 min, with the recipe and with the rule);
  - the plain chain arm and r3c: 5 each (from 30 min, the recipe).

**B. Q1, key on.**
- **The stream:** every C, B and P value equal to the control's (`scripts/irdu_stream_identity.py`); only the header and the counters differ.
- **The declared value steps:** 536 with the last at 15.5 min (the reference count). A difference is explained key by key from `scripts/irdu_pv_audit.py replay`, the independent replay that already gives 536 on the control stream.
- **The replay:** the producer's run-end counts of the test equal a replay's from the file's first epoch (users starting at 0 min).
- **The users** from 0, 15 and 30 min, with the recipe and with the rule, against the control (13.2) and the declarations-off arm (13.2, arm iii). Bar, PASS when all hold:
  1. For starts 0 and 15 min, in every 15-minute bin from each user's 45th minute, the key's median is at most the declarations-off median plus a quarter of the control's excess over it, or below the declarations-off median, in at least 80 % of those bins (with the recipe and with the rule pooled).
  2. Users from 30 min within 8 mm of the control in every bin from their 45th minute (13.2's spread).
  3. Resets: 0 for users from 30 min (no declared step after 15.5 min).

**C. The plain chain arm, key on.** The same reads, against its own control users and its declarations-off users (`irdu_zwc_nr3`, `irdu_zwdt_nr3`, users on the new executable).
- The declared value steps: 987, the last at 35.0 min.
- The users' bar as in B (1 and 2); its resets after 35 min 0.

**D. r3c, key on: the safety side.**
- **The audit** (`scripts/irdu_pv_audit.py audit`): for every epoch, signal and pair of satellites emitted at that epoch and the previous one, the jump of the pair's clock less phase bias difference, with neither satellite declared.
  - Above twice the threshold: 0, a check of the implementation.
  - Above the threshold: reported for the key and for the control, with the largest.
- **The declared value steps:** 1 960 plus the forced bumps, the reference count.
- **The users** from 0, 15 and 30 min, with the recipe and with the rule, against the r3c control's users: no 15-minute bin from each user's 30th minute worse than the control by more than 10 mm or 10 % of the control's median, whichever is larger.

**E. The negative control.** The fixture's true slip (S43000SIM/G22, L1C, +25 cycles at 15.0 min) is declared on G22 at 15.0 min with the key on: its clock less phase bias moves −90.0 mm on L1C and −136.5 mm on L2W against the median, beyond 47.6 and 61.1 mm. The independent replay on the control stream already declares it there.

**Decisions in the author's absence, for review.**
1. The minimum voter count is fixed at four (the value of the offline tool) and travels as the token's value, not as a second key.
2. Below the minimum, each key is tested on its own change (the shared part declared), not left undeclared.
3. A key without a clock keeps the legacy test.
4. The shared part is not declared as a step of its own; the header states the assumption of between-satellite differences.
5. The pair property is audited at twice the threshold for a zero count, and reported at the threshold.
6. The legend comment line extends with the token, as the codebase requires; run A compares the data records.
7. Run A's user identity covers the controls' streams with the new user build, rather than re-running each key-off network's users: the key-off streams' data records are compared directly.

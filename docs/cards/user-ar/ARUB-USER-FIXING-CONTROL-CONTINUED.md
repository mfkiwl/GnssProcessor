# ARUB: integer fixing at the user, a post-processed control first, continued

**STATUS**

- **id:** ARUB
- **topic:** user-ar
- **status:** open
- **summary:** Card ARU's continuation (that file nears the 60 KB bar), from its section 8.10 on; the bars, set-ups and results of stages A and B stay in card ARU sections 1 to 8. Trace of the WTZZ00DEU height with the SIF tide loading (2026-11-13, section 2, diagnostic, not graded): every pair-arc fixed under both tide sources holds the same integers; the base of the comparison, the EOT20 grid as the engine reads it, has every phase sign reversed (`OceanTideModel::parseEot20Load`; 597 SIF stations, all eight main constituents, M2 RMS phasor difference to the SIF 18.8 mm as read and 3.5 mm with the phase negated), and at WTZZ00DEU, M2 phase -89.7 deg, it applies nearly the opposite of the M2 loading. The 14 user configurations in `config/` that name a tide source all name that grid. Removing the diurnal translation from the SIF values (card OTL section 9) raises the WTZZ00DEU fixed height by 3.5 and 2.4 mm on DOY 143 and 144. With the network's three loading keys (b11; the nodal corrections add at most 0.4 mm) the mean absolute up error over hours 3 to 6 is 3.7 mm fixed and 4.0 mm float (EOT20 as read 6.2 and 7.0), the median 3D error 6.5 against 8.1 mm, B1 908 pair-arcs with none different, and B2 fails on 6 of 15 receiver-days, 4 of them at WTZZ00DEU, where a north error of up to 10.8 mm stays under every tide source (reported only). The EOT20 sign is fixed on the branch, and the rerun of the 15 receiver-days is set up and frozen in section 3. Corrects card ARU section 8.10: its WTZZ00DEU "east" values are north.
- **dates:** 2026-11-13 (registered as the continuation; section 2; section 3, the EOT20 sign fixed and the rerun set up and frozen)
- **knobs / posture:** none new. The runs of section 2 use the existing `model_corrections.otl_from_sif`, `model_corrections.otl_remove_diurnal_translation` and `model_corrections.otl_nodal_corrections` (ledger RECOMMEND_SCOPED, armed in the network's field configuration; off in every user configuration).
- **code:** `src/tools/otl_diag.cpp`, `lookup --phases`: the radial amplitude and phase lag of M2, S2, N2, K2, K1, O1, P1 and Q1 from the SIF record and from the EOT20 synthesis (the default output of `lookup` unchanged). Section 3: `OceanTideModel::parseEot20Load` takes the phase lag as atan2(Im, Re) (a defect fix that moves every run on the EOT20 grid), the matching inverse in `src/sim/OtlField.cpp`, and `tests/test_eot20_phase_convention.cpp`.
- **run dirs:** `D:\GnssProcessorSupport\runs_nom\_rap_aru_{otleot,otlsif,b10fix,b10flt,b11fix,b11late,b11flt}_est_<doy>_<site>`; tools and grades `D:\GnssProcessorSupport\presentation\agu26\fixing_control\` (`tools\`, `otl_phase\`, `grade_b10.json`, `grade_b11.json`)
- **source:** card [ARU](ARU-USER-FIXING-CONTROL.md) section 8.10 (the WTZZ00DEU fixed height worse with the SIF loading on DOY 143 and 144); card [OTL](../../record/refound/OTL_ocean_tide_loading_source_2026-10-16.md) sections 4, 8.4 and 9

**Outcome.** Question: why does the WTZZ00DEU fixed height get worse with the SIF tide loading (card ARU section 8.10)?
Not through the integers: every pair-arc fixed under both sources holds the same integers. The base of the comparison was
defective: the engine reads every EOT20 phase with the wrong sign (597 SIF stations, all eight main constituents), and at
WTZZ00DEU it applied nearly the opposite of the M2 loading. With the diurnal translation removed from the SIF values the
WTZZ00DEU fixed mean absolute up error is 2.9 mm (EOT20 as read 3.4, SIF 4.5). Left: a fixed height 4 to 5 mm low on
DOY 143 and 144 (no integer error in the hours checked) and a north error of up to 10.8 mm on DOY 147 that the float
carries too. Standing: open; the EOT20 sign
is fixed on the branch and its rerun is frozen in section 3.

> Results are appended TO THIS FILE, below the text.

---

## 1. Scope

Card ARU nears the 60 KB bar; its results continue here. The bars B1 to B4 stay as frozen in card ARU sections 5 and
8.5, and nothing is frozen anew in this file. Section 2 is diagnostic: its runs were not set up before a graded run and
grade nothing, and the B1 and B2 values it gives are reported only.

## 2. Trace of the WTZZ00DEU height with the SIF tide loading (2026-11-13, diagnostic, not graded)

Question (card ARU section 8.10): with the SIF loading in place of the EOT20 grid, the WTZZ00DEU fixed solution gets
worse on DOY 143 and 144 (mean up over hours 3 to 6, +0.5 to -8.1 and -1.9 to -7.8 mm) while its float improves. Why?

- **Integers.** The same-arc comparison of the B1 bar between the fixed runs of the two sources (`tools\otl_int_compare.py`;
  `_rap_aru_b8fix_est_<doy>_<site>` against `_rap_aru_b9fix_est_<doy>_<site>`, and `b9fix` against `b10fix`): no pair-arc
  fixed to different integers, on any of the 15 receiver-days (WTZZ00DEU 87, 69, 74, 77 and 53 pair-arcs compared,
  first fixes at the same minute). The move is the tide model's alone.
- **What each source applies.** Copies of the section 7 float (EOT20) and of the b9 float (SIF) with the `ocean_tide`
  logger at trace (`_rap_aru_{otleot,otlsif}_est_<doy>_<site>`, 30 runs, all exit 0; `tools\otl_series.py`). Mean up
  loading over hours 3 to 6 at WTZZ00DEU: EOT20 -1.9, -3.2, -3.4, -2.5 and -1.0 mm, SIF +5.1, +5.2, +4.1, +2.3 and
  +0.2 mm (DOY 143 to 147). The static position does not follow the window mean of the change one for one (the fixed
  height moves -8.6 to +7.5 mm, the float -3.4 to +9.7 mm), but the two sources disagree in sign.
- **The EOT20 phases are read with the wrong sign.** M2, amplitude and Greenwich phase lag, SIF against the EOT20
  synthesis: WTZZ00DEU 5.54 mm at -89.7 deg against 4.65 mm at +92.6 deg, STPM00SPM 19.83 at +166.4 against 19.85 at
  -167.2, BAKE00CAN 5.33 at +125.0 against 5.41 at -139.4. Over the 597 stations of `igs20_SIF.json`
  (`gnss_otl_diag lookup --phases`, `tools\otl_phase_stats.py`; `fixing_control\otl_phase\phases_igs20.csv`,
  `phase_stats_igs20.txt`; constituents under 0.2 mm left out):

  | constituent | stations | median phase difference, as read | with the EOT20 phase negated | within 20 deg, as read / negated | RMS phasor difference, as read / negated (mm) | amplitude ratio EOT20 / SIF |
  | --- | --- | --- | --- | --- | --- | --- |
  | M2 | 595 | 106.9 | 2.7 | 0.06 / 0.84 | 18.79 / 3.48 | 1.05 |
  | S2 | 580 | 128.0 | 3.6 | 0.09 / 0.83 | 13.44 / 10.94 | 1.07 |
  | N2 | 593 | 113.1 | 4.0 | 0.06 / 0.83 | 3.80 / 0.74 | 1.05 |
  | K2 | 540 | 123.7 | 6.0 | 0.07 / 0.82 | 2.36 / 0.63 | 1.07 |
  | K1 | 596 | 96.9 | 2.3 | 0.10 / 0.94 | 13.74 / 1.48 | 1.04 |
  | O1 | 597 | 76.3 | 1.9 | 0.08 / 0.98 | 8.15 / 0.77 | 1.05 |
  | P1 | 593 | 92.0 | 3.8 | 0.08 / 0.89 | 5.87 / 3.76 | 1.10 |
  | Q1 | 583 | 69.1 | 4.2 | 0.11 / 0.94 | 1.45 / 0.25 | 1.04 |

  The SIF reading was checked against HARDISP and against data in card OTL section 9. `OceanTideModel::parseEot20Load`
  takes the phase lag as atan2(-Im, Re) of the grid's complex value; the comparison says the file needs atan2(Im, Re).
  Card OTL compared EOT20 amplitudes only (section 4), and its one EOT20 arm read neutral to harmful (section 8.4).
  Of the user configurations in `config/`, 14 (PPP, PPP-RTK, real-time and baseline, among them `ppp_internal.json` and
  `ppp_rtk_internal.json`, the base of these runs) set `data_download.nc_path` to this grid; the 5 others name no tide
  source, and none sets `otl_from_sif`. Every user run on those 14 applies the reversed phases (radial only). Applied up, EOT20 against the SIF without the diurnal translation, within the 6 h windows: largest difference
  6.9 to 12.9 mm at WTZZ00DEU, 7.4 to 15.2 at STPM00SPM and 7.0 to 14.8 at BAKE00CAN, RMS 4.8 to 10.8 mm; at WTZZ00DEU
  the two series are in anti-phase.
- **Reading of card ARU section 8.10 at WTZZ00DEU.** The base of that comparison applied nearly the opposite of the M2
  loading there, so its fixed heights near zero on DOY 143 to 145 are no evidence for it. The section's attribution of
  the offset at STPM00SPM and BAKE00CAN to the EOT20 loading stands, with this sharpening: the EOT20 loading as applied
  is phase-reversed, a defect, not only a coarser model.
- **The diurnal translation.** Card OTL section 9 found the net translation of the SIF diurnal loading absent from
  data built on CODE orbits and clocks, which these runs use. The b9 runs plus `otl_remove_diurnal_translation`
  (`_rap_aru_b10{fix,flt}_est_<doy>_<site>`, 30 runs, all exit 0; `fixing_control\grade_b10.json`): the WTZZ00DEU fixed
  up over hours 3 to 6 goes from -8.1 to -4.7 and from -7.8 to -5.4 mm on DOY 143 and 144, the float from -7.5 to -6.6
  and from -3.0 to -2.5 mm. Mean absolute up error over hours 3 to 6 (`tools\abs_up_summary.py`), fixed / float:

  | tide loading | all 15 | BAKE00CAN | STPM00SPM | WTZZ00DEU | fixed closer to zero in up |
  | --- | --- | --- | --- | --- | --- |
  | EOT20 grid as read (8.8 fixed, section 7 float) | 6.2 / 7.0 | 6.0 / 3.2 | 9.3 / 8.8 | 3.4 / 8.9 | 8 of 15 |
  | SIF (b9) | 4.2 / 4.0 | 3.2 / 2.3 | 5.0 / 4.6 | 4.5 / 5.3 | 8 of 15 |
  | SIF, diurnal translation removed (b10) | 3.7 / 3.9 | 3.5 / 2.1 | 4.7 / 4.5 | 2.9 / 5.3 | 8 of 15 |
  | SIF, translation removed, nodal corrections (b11, the network's three keys) | 3.7 / 4.0 | 3.5 / 2.2 | 4.8 / 4.5 | 2.8 / 5.3 | 9 of 15 |

  B2 as in card ARU section 8.5 (median 3D over minutes 60 to 360, reported only) with b10: fails on 6 of 15, WTZZ00DEU
  DOY 143, 144, 146 and 147 (7.4 against 7.1, 7.7 against 4.9, 9.2 against 6.9 and 13.7 against 12.9 mm), STPM00SPM
  DOY 144 (12.0 against 7.4) and BAKE00CAN DOY 146 (5.0 against 4.0).
- **The network's three loading keys.** b10 plus `otl_nodal_corrections` (`_rap_aru_b11{fix,late,flt}_est_<doy>_<site>`,
  45 runs, all exit 0; `fixing_control\grade_b11.json`): the nodal factors change the applied loading and the positions
  by at most 0.4 mm. B1 as in card ARU section 8.5 (reported only): 908 pair-arcs, none different. B2 fails on the same
  6 of 15 as b10: WTZZ00DEU DOY 143, 144, 146 and 147 (7.1 against 6.9, 7.5 against 4.8, 9.3 against 7.2 and 13.9 against
  13.3 mm), STPM00SPM DOY 144 (11.9 against 7.4) and BAKE00CAN DOY 146 (4.9 against 4.0). Median 3D over the 15, fixed /
  float: EOT20 as read (8.8) 7.3 / 10.9 mm, SIF 6.8 / 8.3, b10 and b11 6.5 / 8.1. The b10 and b11 fixed runs hold the
  same integers on every pair-arc.
- **Correction to card ARU section 8.10.** The WTZZ00DEU values given there as east (-0.6 to -2.9 and -1.4 to -3.0 mm on
  DOY 143 and 144) are north: `tools\height_table.py` printed east, north and up under a header reading north, east and
  up (`tools\trace_split.py` had the same slip in its dN and dE labels; both fixed 2026-11-13). The east moved from -1.7
  to -3.4 and from -0.1 to -1.0 mm. No other value in card ARU was read from those columns.
- **What is left at WTZZ00DEU.** With the network's three keys the fixed solution still reads 4.3 and 5.1 mm low in up on
  DOY 143 and 144 (float 6.3 and 2.4 mm low), and both solutions read north by +4.5 and +3.4 mm on DOY 146 and +10.5 and
  +10.8 mm on DOY 147 (fixed and float). The north error is there under every tide source (EOT20 as read: +9.7 and
  +10.5 mm on DOY 147), and the 3D failures of B2 at WTZZ00DEU on DOY 146 and 147 come mostly from it. No integer error
  shows in the hours checked (`tools\nl_check.py`, held integers against the b11 float, hour 3 and the last hour of
  DOY 143 and 144): the ionosphere-free misfit is at most 0.17
  narrow-lane cycle in the last hour of DOY 143 and 144 and 0.26 in hour 3 of DOY 144, the wide-lane misfit at most 0.28
  cycle, against at most 0.04 and 0.12 at STPM00SPM DOY 144. Not traced further.
- **Not done.** The EOT20 sign is not corrected: a one-sign change to the default tide source of every user
  configuration that moves every run with the EOT20 grid, the author's decision. No run uses corrected EOT20 phases.
  The 14 other receivers and the streams were not run.

## 3. The EOT20 phase sign fixed: rerun set-up, frozen before the graded runs (2026-11-13)

Entry: the author decided on 2026-11-13 to fix the sign found in section 2 and rerun the 15 receiver-days. Section 1
predates this section: the checks below are frozen here, and B1 to B4 are those of card ARU 8.5.

- **Code** (branch `ar/user-control`, no new key): `OceanTideModel::parseEot20Load` takes the Greenwich phase lag as
  atan2(Im, Re) of the interpolated grid value, so the radial signal is Re cos(chi) + Im sin(chi). The simulator's blend
  between anchor points (`src/sim/OtlField.cpp`, `toComplex` and `fromComplex`) takes the matching inverse; the blend
  of conjugates is the conjugate of the blend, so that edit alone changes no output, while the anchor values it blends
  change with the reader. New test file `tests/test_eot20_phase_convention.cpp`, suite `Eot20PhaseConventionTest`: on
  a synthetic two-by-two grid written by the test the reader returns |Z| and atan2(Im, Re) for every BLQ constituent;
  when the EOT20 file is present (skipped otherwise) the M2, K1 and O1 up phasors at WTZZ00DEU, STPM00SPM and BAKE00CAN
  agree with the SIF values to within 30 % of the SIF amplitude plus 0.3 mm (from the section 2 values: largest
  difference 1.35 mm, BAKE00CAN M2, with the fixed sign; every one of the nine cases fails with the reversed sign).
- **What moves.** Every run that takes its loading from the EOT20 grid: the 14 user configurations of section 2, and
  the simulator with `corrections.ocean_tide` (default off). Not the three network configurations (`otl_from_sif` or
  tide loading off, no grid path set) and not the sim fixture `simnet60_quiet_col_24h` (no tide loading).
- **Executable** `D:\GnssProcessorSupport\gates\exe_arue\gnss_processor_arue.exe`, Release, built from `d6a4696` plus
  this change. The engine sources of `arud` (card ARU 8.7) and `d6a4696` are the same: the one source change between
  them, `src/tools/otl_diag.cpp`, is another target.
- **Runs**, 45, in the order of card ARU section 5: `_rap_aru_b12fix_est_<doy>_<site>` and
  `_rap_aru_b12late_est_<doy>_<site>`, copies of the b8 configurations (card ARU 8.7) with only the run paths changed;
  `_rap_aru_b12flt_est_<doy>_<site>`, copies of the EOT20 float runs with the tide trace of section 2 (`otleot`, the
  card ARU section 7 float plus the `ocean_tide` logger) with only the run paths changed. Control
  `_rap_aru_b12ctl_est_143_wtzz`, a copy of `_rap_aru_b11fix_est_143_wtzz` (SIF loading).
- **Checks, frozen here.** F1, the reader: `gnss_otl_diag lookup --phases` built with the change, over the 597
  stations of section 2, gives a median phase difference to the SIF of at most 10 deg for each of the eight main
  constituents, and at least 80 % of the stations within 20 deg for M2 (as read in section 2: 69 to 128 deg, and
  6 %). F2, the identity: `b12ctl` writes `state_trace.csv`, `ambiguity_trace.csv` and `measurement_residuals.csv`
  byte-identical to `_rap_aru_b11fix_est_143_wtzz`. B1 to B4 exactly as in card ARU 8.5, on b12, B2 against `b12flt`.
- **Reported, no rule.** The size of the move, `b12fix` against `b8fix` and `b12flt` against `otleot`: per
  receiver-day the change of the mean east, north and up over hours 3 to 6 and of the B2 median; the change of the
  applied up loading (largest and RMS over the 6 h); the applied up against the SIF series (`b10flt`); the mean
  absolute up error over hours 3 to 6 beside the rows of the section 2 table; the totals of the release rules.
- **Expected, not a rule.** The corrected grid's applied up follows the SIF series to within a few millimetres, so the
  mean absolute up error should fall from 6.2 / 7.0 mm toward the SIF rows of section 2 (3.7 to 4.2 mm fixed). The
  north error at WTZZ00DEU on DOY 146 and 147 is there under every tide source, and the grid carries no horizontal
  loading, so B2 is expected to fail there.

# ARU: integer fixing at the user, a post-processed control first

**STATUS**

- **id:** ARU
- **topic:** user-ar
- **status:** open
- **summary:** The user engine has never produced a correct integer fix. Stage A measures, with no fixing, whether the float ambiguities of a single receiver on one analysis centre's final products with published phase biases (CODE MGX final orbit, 30 s clock, OSB code and phase biases) are integer within their own formal covariance, with the position estimated and with the position held at the IGS coordinate. Stage B turns fixing on only if stage A passes, against bars frozen below. Stage A result (2026-11-10, section 4): float integer (A1 26 of 30, A2 30 of 30 system-days with the position estimated), covariance optimistic by a factor of about 2 to 3 (A3 15 of 30), stage A not passed as frozen; the MW wide-lane source of the search is wrong by 2 cycles on GPS III (satellite antenna offset per frequency omitted).
- **dates:** 2026-11-10 (pre-registration)
- **knobs / posture:** none new. Stage A runs `estimation.ambiguity_resolution.mode` 1 with `ratio_threshold` 1e9 (the search runs and logs, nothing is accepted) and the resolver log at debug.
- **code:** `src/core/filter/AmbiguityResolver.cpp` (debug line `CLCOV`: the formal covariance of the double differences beside the existing `CLFRAC` values; logged only at debug, no other output changes)
- **run dirs:** `D:\GnssProcessorSupport\runs_nom\_rap_aru_*`; tools and grades `D:\GnssProcessorSupport\presentation\agu26\fixing_control\`
- **source:** the live fixing sessions of 2026-11-10 (`D:\GnssProcessorSupport\presentation\agu26\figures\live_fixing_note.md`: 0 fixes in 27 946 searches, wide lane integer for GPS, ionosphere-free narrow lane near uniform under a formal sigma of 0.005 to 0.04 cycles); card [SSR-BIAS-SIGN](../realtime/SSR-BIAS-SIGN.md); the July 2026 wrong integers on ALGO00CAN ([CONSUMER-AR-BLUNDER](../../record/cards/consumer/CONSUMER-AR-BLUNDER.md))

**Outcome.** Stage A (section 4): on CODE final products the user float IS integer. Narrow lane within 0.10 cycle on 30 of 30 receiver-days (median 0.045 cycle with the position estimated, 0.034 held). The covariance bar A3 fails on most receiver-days: the miss levels off near 5 mm while the formal sigma keeps falling, so stage B was not started. First model term that prevents a correct fix: the MW wide lane fed to the WL-constrained search omits the satellite antenna offset per frequency, 2 cycles wrong on every GPS III pair (5 526 of 5 526 pair-epochs). Open.

> Results are appended TO THIS FILE, below the text.

---

## 1. Why a post-processed control first

On the live streams nothing has fixed, and the float narrow lane holds constant non-integer offsets that
differ between a static and a kinematic engine on the same data. A stream mixes several suspects at once:
the correction source, its signal mapping, the time handling of the engine and the user models. Final
products with phase biases made for integer fixing remove the stream suspects. If the float is not integer
there, the fault is in the user engine's model or covariance; if it is, the streams are the next suspect.

## 2. Set-up

- Receivers: test receivers of the period 23 to 27 May 2026 (`D:\GnssProcessorSupport\presentation\agu26\figures\period2026_note.md`), first WTZZ00DEU (JAVAD, GPS L1C/L2W, Galileo L1X/L5X), BAKE00CAN (Septentrio, GPS L1C/L2W, Galileo L1C/L5Q) and STPM00SPM (Trimble, GPS L1C/L2W, Galileo L1X/L5X). Coordinates: the IGS daily mean of the period (`period2026\coords\test_coords_2026.json`), reduced from the marker to the antenna reference point with the RINEX `ANTENNA: DELTA H/E/N`.
- Products: `C:\GnssProcessor\data\2026-<doy>\products\COD0MGXFIN_*` (orbit 5 min, clock 30 s, OSB, ERP). The OSB file of DOY 145 holds phase biases for 32 GPS satellites on L1C, L1W, L2W (and L1L, L1X, L2L, L2S, L2X) and for 30 Galileo satellites on L1C, L1X, L5Q, L5X, one value per day.
- Engine: `config/ppp_rtk_internal.json` (case D of the period note) with GPS + Galileo, `frequency_mode` dual, `channel_mode` single, between-satellite differences, code and phase biases applied, accumulated wind-up, static position (`position_q` 0). Variant `est`: position estimated from 100 m. Variant `hold`: `receiver.reference_position_ecef` at the antenna reference point with an initial sigma of 0.1 mm. Generator `fixing_control\tools\make_ctl.py`.
- Grader `fixing_control\tools\grade_ctl.py`: per epoch and satellite pair against the resolver's reference satellite (highest elevation, 20 degree fixing mask), the wide lane W = n1 - n2 and the ionosphere-free narrow lane with W rounded, n1_hat = (f1 n1 - f2 n2 - f2 round(W)) / (f1 - f2), each with its distance to the nearest integer and its formal sigma from `CLCOV`.

## 3. Bars, frozen before the graded runs

**Stage A** (the float is integer within its covariance), per receiver-day, graded over minutes 60 to 120
of a 2 h run, per system (GPS, Galileo), the last value of each pair in each 10-minute window:

- **A1 wide lane:** median distance to the nearest integer at most 0.10 cycle.
- **A2 narrow lane:** median distance to the nearest integer at most 0.10 narrow-lane cycle (uniform reads
  0.25), and at least 75 % of the pair-windows within 0.20 cycle.
- **A3 covariance:** the median of (narrow-lane distance / its formal sigma) at most 2.0 (an honest
  covariance gives a half-normal ratio with median 0.67).

A pass needs A1 to A3 on the position-held run (the corrections are applied consistently) AND on the
position-estimated run (fixing happens with the position estimated). A held pass with an estimated fail
places the fault in the position and troposphere path or the covariance; a held fail places it in a model
term (bias sign or signal mapping, wind-up, attitude, antenna offsets per frequency, the clock reference of
the bias set), bisected one change per run.

**Stage B** (fixing on; run only when stage A passes):

- **B1 repeatability:** the same arcs fix to the same integers from two cold starts one hour apart.
- **B2 no harm:** with `hold_variance` 1e-7, the fixed position after convergence (minutes 60 to 360) is no
  worse than the float position at every receiver-day (median 3D error, same run settings otherwise).
- **B3 reported, not gated:** time to 10 cm and the first-hour error, float against fixed, for the 17 test
  receivers and 5 days.
- The two recorded stream sessions (`D:\GnssProcessorSupport\runs\rt_agu_2026-11-10\relay_cnes`,
  `relay_cas`) are graded on B1 and B2 after the post-processed stage passes, through a time-faithful replay.

A fix count is never evidence of correct integers; `ratio = inf` is a sentinel; the search is in cycles.

## 4. Stage A results (2026-11-10)

**Runs.** `D:\GnssProcessorSupport\runs_nom\_rap_aru_a1_{est,hold}_<doy>_<site>` (30 runs: WTZZ00DEU,
BAKE00CAN, STPM00SPM, DOY 143 to 147, 2 h from 00:00, all exit 0) and `_rap_aru_a1gal_est_<doy>_<site>` (15 runs,
the same with the search restricted to Galileo, `estimation.ambiguity_resolution.active_systems` ["Galileo"]).
Executable `D:\GnssProcessorSupport\gates\exe_aru\gnss_processor_aru.exe`, Release, sha256
4b8aae390a5a9733c1a354de78540327188664d48ded7e059104b169730bdf72, built on branch `ar/user-control` from main
`b6bbea7` plus the `CLCOV` trace line. Identity: `_rap_aru_idchk_main_145_wtzz` (the configuration of
`_rap_aru_a1_est_145_wtzz` on the main build `gnss_processor_p26.exe`, sha256 28e4286e...) gives byte-identical
`state_trace.csv`, `ambiguity_trace.csv` and `measurement_residuals.csv`; the resolver logs differ only by the
`CLCOV` lines. Grades: `D:\GnssProcessorSupport\presentation\agu26\fixing_control\grade_a1.{txt,json}` and
`grade_a1gal.{txt,json}` (`tools\agg_a1.py`, `tools\grade_ctl.py`).

**4.1 The bars.** Minutes 60 to 120, per system, pair-windows as frozen in section 3.

| variant | system | A1 wide lane | A2 narrow lane | A3 covariance | wide lane median, range | narrow lane median, range | miss / sigma median, range |
| --- | --- | --- | --- | --- | --- | --- | --- |
| position estimated | GPS | 13 of 15 | 15 of 15 | 9 of 15 | 0.037 to 0.127 | 0.046 (0.021 to 0.095) | 1.94 (0.60 to 3.54) |
| position estimated | Galileo | 13 of 15 | 15 of 15 | 6 of 15 | 0.006 to 0.115 | 0.045 (0.016 to 0.080) | 2.09 (0.58 to 3.80) |
| position held | GPS | 13 of 15 | 15 of 15 | 5 of 15 | 0.037 to 0.127 | 0.034 (0.017 to 0.082) | 2.53 (1.19 to 5.20) |
| position held | Galileo | 13 of 15 | 15 of 15 | 3 of 15 | 0.007 to 0.115 | 0.038 (0.008 to 0.089) | 3.74 (1.00 to 8.86) |

Receiver-days passing every bar on both systems: 5 of 15 with the position estimated (BAKE00CAN 144 to 147,
WTZZ00DEU 144), 2 of 15 held (BAKE00CAN 143, 147). A1 fails on WTZZ00DEU GPS on DOY 145 and 146 (0.109, 0.127:
constant offsets on single pairs, G25-G12 at -0.32 on DOY 143) and on STPM00SPM Galileo on DOY 144 and 147 (0.115,
0.102); not traced. Stage A is therefore not passed as frozen, and stage B was not started.

**4.2 The float is integer.** Over the last hour most pairs hold a constant fraction near zero (spread under 0.1
cycle and mean within 0.15, DOY 143, position estimated: WTZZ00DEU 5 of 6 GPS and 6 of 6 Galileo pairs, BAKE00CAN
11 of 12 and 6 of 6, STPM00SPM 11 of 11 and 5 of 6).
Static 3D position error in hour 2, median 1.17 cm (0.44 to 1.99 cm). On these products the corrections are applied
consistently: bias signs and signal mapping, wind-up, attitude and antenna offsets per frequency leave no
narrow-lane offset of 0.1 cycle or more. Holding the position at the IGS coordinate lowers the narrow-lane miss only
from 0.045 to 0.034 cycle, so the position and troposphere path is not the binding term either.

**4.3 Why the formal sigma is below the miss.** Median over the 30 runs and both systems per 10-minute window:

| window (min) | 0-10 | 20-30 | 40-50 | 60-70 | 80-90 | 110-120 |
| --- | --- | --- | --- | --- | --- | --- |
| estimated: narrow-lane miss | 0.198 | 0.137 | 0.062 | 0.047 | 0.055 | 0.051 |
| estimated: formal sigma | 0.302 | 0.085 | 0.054 | 0.036 | 0.026 | 0.022 |
| held: narrow-lane miss | 0.075 | 0.061 | 0.034 | 0.030 | 0.038 | 0.033 |
| held: formal sigma | 0.038 | 0.016 | 0.012 | 0.011 | 0.010 | 0.010 |

The miss stops falling after about 40 minutes at about 0.045 narrow-lane cycle (5 mm) with the position estimated
and 0.031 (3 mm) held, while the formal sigma keeps shrinking as if every 30 s epoch brought independent
information. The per-epoch weights are not too tight: the post-fit phase residuals are below their stated sigma
(standardized RMS 0.38 to 0.56 in hour 2 at the three receivers on DOY 143, `tools\resid_scale.py`). The optimism is
the time-correlated part of the phase error (multipath, troposphere and receiver antenna mismodelling, orbit and
clock residuals), which the filter carries with no process noise on the ambiguities (`ambiguity_q` 1e-12) and almost
none on the troposphere (1e-9). The wide-lane sigma is honest (miss 0.05 to 0.07, sigma 0.05). An honest narrow-lane
covariance needs a floor near 0.04 cycle, a factor of about 2 to 3 over the formal sigma in hour 2.

**4.4 The first model term that prevents a correct fix: the MW wide lane omits the satellite antenna offset per
frequency.** With .BIA products the resolver takes the WL-constrained route: it imposes the MW detector's
double-differenced wide-lane integer (`WLDUMP dd_wl`) and searches only the narrow lane. That integer was compared
with the float states' wide lane (`CLFRAC` n1 - n2) of the same pair at the same epoch (`tools\agg_a1.py`):

| pairs | position estimated | position held |
| --- | --- | --- |
| GPS, one satellite of Block III | 5 526 of 5 526 disagree | 6 148 of 6 148 |
| GPS, other | 0 of 7 109 | 0 of 7 852 |
| Galileo | 132 of 13 338 | 132 of 14 495 |

- The disagreement is exactly 2 cycles, of the sign of the Block III satellite's side (G13 against G12 at
  WTZZ00DEU on DOY 143: float 4.016, MW integer 2 at every epoch). A direct computation from the RINEX file and the
  OSB file, with no engine involved (`tools\mw_direct.py`), gives G13 - G12 = +1.741 cycles: the raw MW agrees with
  the detector to its rounding and differs from the float by 2.275 cycles.
- Cause: `igs20.atx` gives the Block III satellites a z offset of 1.116 m on L1 and 0.612 m on L2 (G13 and G20,
  SVN G083 and G082; G23 1.184 and 0.707 m); the other GPS blocks have one value for both. The float model applies
  the offset per frequency to code and phase; the MW detector works on raw observables
  (`MwSlipDetector::computeSatMwBias` corrects only the four OSBs). In the MW combination a difference d between the
  L1 and L2 offsets enters as (f1/(f1-f2) - f1/(f1+f2)) d = 3.97 d: 3.97 x 0.504 m = 2.0 m, 2.3 wide-lane cycles of
  0.862 m at a nadir angle near 10 degrees, as measured.
- Galileo: the same term at a smaller size. E21 has an E1 minus E5a offset of 177 mm, E28 and E29 51 and 53 mm; the
  125 mm difference is 0.66 Galileo wide-lane cycle, which flips the rounded integer on E28 - E21 and E29 - E21 at
  WTZZ00DEU on DOY 144 (132 pair-epochs, -1 cycle).
- Effect on the search: a wide lane wrong by 2 cycles moves the narrow-lane target by 2 f2/(f1 - f2) = 7.06 cycles,
  a fraction of only 0.06, so the narrow-lane search cannot see it. A fix through this route sets the L1 integer of
  the Block III pair wrong by 7 cycles and the L2 integer by 5 cycles, while the ionosphere-free ambiguity moves by
  only 0.06 narrow-lane cycle (6 mm): wrong integers the position barely shows, absorbed by the slant ionosphere.
  With every GPS pair in the search, the ratio reached 3.0 in 10 of 30 runs (maximum 16.5); the later gates (success
  rate, per-pair cap) did not run at the 1e9 threshold, so whether such a fix would have been accepted is not known.
- Without Block III pairs (Galileo only) the search ratio exceeds 3.0 in 537 of 1 790 hour-2 searches and at some
  epoch in 12 of 15 runs (maximum 5 206 at WTZZ00DEU on DOY 147). Whether those integers are correct is the
  question of stage B.

**4.5 What stage B needs, in order.** (1) A wide-lane source consistent with the float model: the MW detector
corrected for the satellite (and receiver) antenna offset per frequency, or the wide lane taken from the float
states, default off and identical when off. (2) A narrow-lane covariance with an error floor, or the success-rate
gate evaluated on an inflated covariance. (3) The B1 and B2 bars of section 3, unchanged. Not done here: stage B, the
stream sessions and their replay, the 14 other test receivers, the CAS Galileo signal mapping, a wide-lane source
on stream biases, the Debug unit suite on this branch (the change is one debug log line).

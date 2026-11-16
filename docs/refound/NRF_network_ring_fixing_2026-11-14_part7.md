# NRF part 7: the bed for remedy (b) (sections 52 onwards of card NRF)

**STATUS**

- **id:** NRF-part7
- **topic:** network-vehicle
- **status:** open
- **summary:** Sections 52 onwards of card NRF (2026-11-16), continued from [part 6](NRF_network_ring_fixing_2026-11-14_part6.md). Section 52: the bed for remedy (b) of section 24.3 item 4, the golden simulator fixture with constant GPS code biases per (receiver, satellite, signal), with and without a receiver-and-block offset on GPS III (`scripts/nrf_code_bias_bed.py`), and the adopted set at the cap of 12 on it: no wrong integer, the audits zero, Galileo unchanged; GPS holds 85.5 to 86.7 % of its link-epochs from hour 2 (89.0 and 90.2 % unbiased, 51 to 62 % on observed data), and the block offset gives a block split that follows the reference receiver, several times weaker than observed. Section 53: the reads of the requesting session's E05 finding (a flagged level that moves under constant counters): common chord fractions against a satellite's tree edge exceed chance by 1 to 5 points of satellite-half-hours on Galileo and 7 to 10 on GPS; E05's walk was KOKV00USA's arc (it vanishes without that receiver; the borrowed E5a calibration not shown to be the cause); a decision holds its integer at 0.1 mm and leaves its misfit to the satellite's level; a flag rule that asks the links to agree (rule C) passes the segment bar on Galileo on both days and fails by one GPS run a day. Section 54: an unsettled signal declares itself at every emission (`network.ring_fix.unsettled_steps`, built, default off) and Galileo L1C/L5Q held beside L1X/L5X, pre-registered; results: every bar passes for both (54.1: keys absent identical, only the counters move, the counter changes equal the requesting session's copy; streams for user replays `u12_n144` and `u12_n145`; 54.2: the audit with three held families zero, Galileo C/Q held 71 to 90 % from the third half-hour and flagged from hour 3). Section 55: the slow part of the observed wide-lane error is the same on GPS and Galileo (about 0.05 cycle in 10-min means), so a multipath-like bed would not separate them; not built. Section 56: the step declaration with its release increments adopted in the chain posture (RECOMMEND_SCOPED); rule C not adopted, the flags stay rule B; the unsettled steps take the settling step after a warm resume. Section 57: GPS L1W/L2W held beside L1C/L2W: the audit zero, but L1W/L2W holds almost nothing (its first band's tree on another root than L2W's), takes 2 to 9 % from L1C/L2W, and the flags, kept per satellite signal, cannot carry the shared L2W. Section 58: the root of the flag: the largest set tied by held links gains the first two hours (Galileo C/Q 61 to 75 points, GPS 45 to 58) with the segment bar as rule B's; proposed with a minimum and a hysteresis, not built. Section 59: the per-arc offsets of observed GPS are the same size as Galileo's; a GPS III lean at two receiver types only; the block split reverses with the day. Section 60: a third frequency, the plan: the chord table forms only band 1 with the lowest other band, the shared signal is decided twice, the cascade; simulator arms pre-registered.
- **source:** [part 6](NRF_network_ring_fixing_2026-11-14_part6.md) sections 50 and 51; [part 4](NRF_network_ring_fixing_2026-11-14_part4.md) section 24.3 item 4 (what the simulator needs); the requesting session's order of 2026-11-16 (item 4: the GPS held share, the bed for (b), the third frequency).

**Outcome.** Part 7 carries the stream's honesty and the next signals. The step declaration with its release increments is adopted in the chain posture (section 56); an unsettled signal now declares itself at every emission (built, default off; streams `u12_n144` and `u12_n145`, section 54). Galileo L1C/L5Q can be held beside L1X/L5X with the audit zero (54.2); GPS L1W/L2W cannot yet be held beside L1C/L2W, for the shared L2W's datum and flags (57). A root-free flag, the largest tied set, gains the first two hours (58). The simulator bed for remedy (b) does not yet read like observed GPS (52); a third frequency needs chords for a second family, one datum and a cascade (60).

## 52. 2026-11-16: the bed for remedy (b): GPS code biases per receiver and satellite

**Why** (the requesting session's order, item 4): the simulator's GPS has receiver code biases per station and observable and satellite biases, but no bias per (receiver, satellite), so it cannot show the frame signature of observed GPS, and remedies (a), (b) and (c) of section 24.3 cannot be graded against truth on it (section 24.3 item 4).

**The bed** (`scripts/nrf_code_bias_bed.py`, from the golden simulator fixture `runs/simnet60_quiet_col_24h`, 61 receivers). A constant bias is added to every GPS code observation of C1C and C2W per (receiver, satellite, signal): a draw from N(0, 0.12 m) seeded by (seed 1, receiver, satellite, signal), rounded to the millimetre. Phases, Galileo and every other file are untouched; each receiver's table is in its truth_code_bias.csv; `verify` proves that only the GPS code fields moved, each by its table entry (3 341 448 fields). Two beds: `simb_cb1` with the draws alone, and `simb_cb2` with 0.13 m more on the GPS III satellites of the fixture's day (G04, G11, G14, G18, G23 and G28, from the ATX) at every fourth receiver in sorted order (16: S01000SIM to S57000SIM and the consumer SZZ000SIM), a receiver-and-block offset of 0.15 wide-lane cycle. The draw's size is section 24.3's (an observed per-arc wide-lane offset of about 0.12 cycle p50 corresponds to about 0.10 m on both codes).

**Arms** (exe nrf23, `e5f4baadabbac906`): the adopted set at the cap of 12 (`kq12_sim[_r]` of section 48) with every path pointed at the bed, 3 h from 00:30:15, the default receiver and S45000SIM (a block receiver on `simb_cb2`): `cb1_s12`, `cb1_s12r`, `cb2_s12`, `cb2_s12r`; a 10-epoch smoke first (`cbsmoke`, exit 0). The unbiased bed is `kq12_sim[_r]` (exe nrf21; nrf23 runs it identically, section 50.1). Bars, those of section 44, stated here after the runs: 0 wrong against truth, the two-reference audit zero, every epoch emitted. Reads: held share by family, GPS III against the older blocks at the block receivers and at the others, RAIM rows.

**Results** (grade `_irdu_grades/nrf_cb_grade.txt`, script `_irdu_grades/scripts_s20/grade_cb.sh`; the split by receiver group in `_irdu_grades/nrf_cb_block_split.txt`). All arms exit 0, 360 of 360 epochs emitted.

| bed | arm | decisions wrong | held link-epochs right, wrong | held link-epochs: Galileo L1C/L5Q, GPS L1C/L2W | two-reference audit: checks, failing | RAIM rows | GPS held share by half hour (%) |
|---|---|---|---|---|---|---|---|
| unbiased | `kq12_sim` | 0 | 172 293, 0 | 78 689, 93 604 | 314 434, 0 | 0 | 2.6, 37.9, 82.1, 91.0, 91.0, 90.8 |
| unbiased | `kq12_sim_r` | 0 | 167 618, 0 | 72 173, 95 445 | | 0 | 1.1, 42.1, 87.3, 90.9, 90.8, 90.8 |
| cb1 | `cb1_s12` | 0 | 168 884, 0 | 78 626, 90 258 | 304 166, 0 | 33 | 2.4, 33.4, 77.3, 89.1, 89.4, 89.6 |
| cb1 | `cb1_s12r` | 0 | 163 124, 0 | 73 687, 89 437 | | 58 | 0.8, 33.2, 80.0, 87.6, 87.7, 88.4 |
| cb2 | `cb2_s12` | 0 | 167 253, 0 | 78 525, 88 728 | 302 088, 0 | 24 | 2.4, 31.8, 76.4, 88.0, 88.2, 88.1 |
| cb2 | `cb2_s12r` | 0 | 162 750, 0 | 73 481, 89 269 | | 41 | 0.9, 33.5, 81.3, 86.8, 86.8, 87.7 |

GPS held share from hour 2 (%), GPS III and the older blocks, at the 15 network receivers of the block set (which carry no block offset on the unbiased bed and on `simb_cb1`: a control) and at the others:

| arm | block receivers: GPS III, older | other receivers: GPS III, older |
|---|---|---|
| `kq12_sim` | 87.8, 90.4 | 88.5, 88.9 |
| `kq12_sim_r` | 92.0, 91.9 | 91.8, 89.1 |
| `cb1_s12` | 81.2, 88.2 | 85.5, 87.0 |
| `cb1_s12r` | 87.5, 89.3 | 88.2, 84.6 |
| `cb2_s12` | 75.5, 87.1 | 82.7, 86.5 |
| `cb2_s12r` | 87.1, 88.9 | 86.4, 84.8 |

1. **Every bar passes on both beds:** 0 wrong against truth in the four runs (decisions and held link-epochs), the audits zero, every epoch emitted. Code biases of this size do not make the ring fix take a wrong integer.
2. **Galileo, unbiased, is the control:** 78 626 and 78 525 held link-epochs against 78 689 on the unbiased bed.
3. **GPS holds 3.6 to 6.5 % fewer link-epochs** (90 258 and 89 437 on `simb_cb1`, 88 728 and 89 269 on `simb_cb2`, against 93 604 and 95 445), and its share from hour 2 is 85.5 to 86.7 % (89.0 and 90.2 % unbiased), far above observed GPS (51 to 62 %, section 46). The wide-lane fraction of its links not held rises from 0.13 to 0.14 cycle (median, unbiased) to 0.18 to 0.28, near observed GPS (0.21 at start 0, section 51). The code biases reach RAIM: 24 to 58 rows a run against 0.
4. **The receiver-and-block offset gives a block split that follows the reference receiver.** With the default reference (not a block receiver), GPS III at the block receivers is held 5.7 points less than on `simb_cb1` (75.5 against 81.2 %); with S45000SIM (a block receiver) as reference, the block receivers' GPS III holds as on `simb_cb1` (87.1 against 87.5 %) and the other receivers' GPS III loses 1.8 points (86.4 against 88.2 %). Observed GPS's split also changes with the day and the reference (section 51), but it is several times stronger (DARW00AUS 4.9 against 67.4 %).

**What the bed lacks, for remedy (b).** The bed reproduces the wide-lane fractions of observed GPS's links not held, not its held share: the gate still holds most GPS links. Before (a), (b) and (c) are graded on it, it needs what observed GPS has and these draws do not; candidates, not built: larger biases (0.2 to 0.3 m), the block offset larger or at more receivers, a slowly varying code error (multipath) instead of a constant, each first checked against observed GPS's held share and fraction distribution. The choice is the requesting session's.

## 53. 2026-11-16: a level that moves under constant counters: the reads of the requesting session's E05 finding

**Why** (the requesting session's review of sections 50 and 51, its note ARNG section 4): on `f12_n144` unflagged GPS satellites walk by up to 2.7 narrow-lane cycles inside constant-counter segments, and the flagged Galileo satellite E05 moves +0.42 narrow-lane cycle (4.5 cm) over hours 1 to 6 with no increment; E05's tree edge was KOKV00USA until TOW 13320, its chords elsewhere read one common ionosphere-free fraction of 0.2 to 0.43 cycle for 2.5 h, and GCGO00USA-E05 and GAMB00PYF-E05 were decided at fractions of 0.18 and 0.20. Three reads asked, no build. New runs (exe nrf23): `f12_n145`, the DOY 145 stream with the step declaration, the release increments and the settled flags (its flags equal rule B at every epoch: 88 446 records, no mismatch); `o10_n144_nokokv`, `o10_n144` without KOKV00USA (54 receivers). Scripts in `_irdu_grades/scripts_s20/`: `common_frac.py`, `flag_rule_c.py`, `flag_bar.py`; the requesting session's `stream_seg_drift.py` and `stream_level_series.py`. Fractions here are n_if - round(n_if), the opposite sign of the requesting session's.

### 53.1 Read (i): satellites whose unheld chords share one fraction against their tree edge

Per held family, satellite and half hour: each unheld chord's circular median of its ionosphere-free fraction over the half hour; an event is two (or three) chords agreeing within 0.1 cycle with a median beyond 0.15 cycle; the host is the satellite's tree edge on the family's first band. The null re-assigns the chords' medians at random across the satellites of the same half hour (20 draws).

| run | Galileo L1X/L5X: events / cells (null), 2 chords | 3 chords | GPS L1C/L2W: 2 chords | 3 chords |
|---|---|---|---|---|
| `o10_n144` | 38 / 181, 21.0 % (15.5 %) | 17, 9.4 % (4.9 %) | 107 / 310, 34.5 % (28.5 %) | 71, 22.9 % (12.6 %) |
| `o10_n144r` | 18 / 174, 10.3 % (9.7 %) | 7, 4.0 % (2.4 %) | 143 / 334, 42.8 % (34.6 %) | 82, 24.6 % (15.0 %) |
| `o10_n145` | 29 / 171, 17.0 % (13.0 %) | 14, 8.2 % (5.1 %) | 144 / 347, 41.5 % (37.1 %) | 84, 24.2 % (17.0 %) |
| `o10_n145r` | 15 / 161, 9.3 % (7.0 %) | 4, 2.5 % (1.9 %) | 135 / 349, 38.7 % (35.0 %) | 81, 23.2 % (15.1 %) |

Most two-chord agreements are chance; with three chords the excess over the null is 0.6 to 4.5 points on Galileo (a few satellite-half-hours a run, sizes p50 0.20 to 0.27 cycle) and 7 to 10 points on GPS (25 to 33 a run, p50 0.30 to 0.32). Hosts: Galileo WIND00NAM, BOGT00COL, KOKV00USA and GCGO00USA on DOY 144, STHL00GBR and KRGG00ATF on DOY 145; GPS COCO00AUS, BOR100POL, SEYG00SYC, GUAM00GUM and GAMB00PYF on both days and with both reference receivers. GPS III makes 25 to 42 % of the GPS events (32 % of the satellite-half-hours), so no strong block association.

**KOKV00USA.** Its antenna (ASH701945G_M, no radome) has GPS L1/L2 and GLONASS calibrations only in igs20.atx, as KOKB00USA on the user side; the producer borrows GPS L1 for Galileo E1 (the same frequency) and GPS L2 (1227.6 MHz) for E5a (1176.45 MHz), as at six other receivers (JPLM00USA, STJO00CAN, CHUR00CAN, SYOG00ATA, PARK00AUS, SVTL00RUS). Galileo events at those seven hosts: 6 of 54 hosted satellite-half-hours (11 %) against 36 of 633 at the others (5.7 %); their GPS events (exact calibrations) 11 of 141 against about 25 % elsewhere: a modest Galileo excess. **Without KOKV00USA** (`o10_n144_nokokv`) E05 is hosted at GAMB00PYF then GCGO00USA, its level stays within about 0.1 narrow-lane cycle from hour 1 to hour 6 (0.46 with KOKV00USA), its decisions come at fractions of 0.10 and 0.08 (0.18 and 0.20 with KOKV00USA) and its only common-fraction event is in the first half-hour. So the error was KOKV00USA's arc to E05. The borrowed E5a calibration is consistent with it but not shown to cause it: E05 at KOKV00USA rises from 28° through the zenith (86° near TOW 9500) and back to 49° while the level rises monotonically, and a calibration mismatch of the expected size (millimetres) is far below 4.5 cm; the receiver, the site's multipath and the arc's own carry leave with the station too.

### 53.2 Read (ii): what a decision does with a misfit today

**The decision.** The odds gate decides on the log-odds of the nearest integer against the next (13.8 needed) and the fraction bound (0.20), not on the fraction against its own sigma: GCGO00USA-E05 at TOW 8370 had log-odds 52.3, fraction 0.182 and formal sigma 0.078 (2.3 sigma from the whole number); GAMB00PYF-E05 at TOW 10110 had 215.2, 0.199 and 0.037 (5.4 sigma). Decisions between 0.15 and 0.20 cycle are 6 to 11 % of a run's decisions (Galileo 28 to 34, GPS 23 to 49 a run); 0 to 4 a run lie beyond 3 formal sigma.
**After the hold.** The hold row is a prior at the held integer on each band's ambiguity at 0.1 mm (`kRingFixHoldSigmaM`, `networkRingFixPriors`), so the fraction is not carried: the misfit goes to what the link shares. The geometry-free part goes to the link's slant ionosphere; the ionosphere-free part (about 2 cm here) goes to the satellite's phase bias, which moves the satellite's level for every user, and to the receiver's phase bias, clock and wet delay, which spread it to the receiver's other satellites. The tree edge's pin (1e10 at KOKV00USA) does not move, so that arc holds the other side of the misfit as its residual. The residual monitor (each held link's post-fit ionosphere-free residual above 3 cm at 4 consecutive epochs) does not see a misfit of about 2 cm shared between arcs. At TOW 13320 GCGO00USA-E05 became E05's tree edge: from then on E05's frame is that link's held integers, misfit included. E05's level walked before the first decision too (+0.19 cycle between the quarter-hours starting at TOW 1800 and 7200): the carried floats of its other links pull the satellite's phase bias toward their consensus against the tree pin, slowly and unsignalled; the decisions then hold intermediate states.

### 53.3 Read (iii): a flag that asks the links to agree (rule C), and the bar

**Rule C:** rule B (the stream's flag) and at least two links of the satellite held or pinned (its held or decided links of the family, plus its tree edge) and no unheld chord with a converged float (formal sigma at most 0.10 cycle) more than 0.10 cycle from a whole number. Stamped into copies of the streams (`f12c_n144`, `f12c_n145`); the counters unchanged.

| flagged share by hour (%) | rule B | rule C |
|---|---|---|
| DOY 144 Galileo L1X/L5X | 18, 90, 98, 95, 95, 100 | 13, 80, 88, 88, 86, 95 |
| DOY 144 GPS L1C/L2W | 0, 44, 66, 73, 80, 84 | 0, 42, 60, 71, 74, 80 |
| DOY 145 Galileo L1X/L5X | 0, 0, 97, 100, 99, 97 | 0, 0, 91, 88, 89, 87 |
| DOY 145 GPS L1C/L2W | 0, 39, 56, 61, 66, 70 | 0, 34, 48, 50, 54, 63 |

Rule C withholds a rule-B flag for a disagreeing chord (DOY 144: 1 583 first-band signal-epochs; DOY 145: 1 069) or for fewer than two held or pinned links (765; 1 928).

**The requesting session's segment read** (`stream_seg_drift.py --datum-flagged`, hours 1 to 6, the runs of epochs with both flags up inside constant-counter segments: range p50, p90, max in narrow-lane cycles; runs over 0.15):

| | DOY 144 rule B | DOY 144 rule C | DOY 145 rule B | DOY 145 rule C |
|---|---|---|---|---|
| Galileo L1X/L5X | 0.069, 0.143, 0.306; 8 | 0.043, 0.118, 0.198; 3 | 0.081, 0.139, 0.187; 4 | 0.065, 0.121, 0.184; 1 |
| GPS L1C/L2W | 0.113, 0.178, 0.301; 9 | 0.093, 0.154, 0.294; 8 | 0.089, 0.163, 0.217; 9 | 0.053, 0.132, 0.206; 3 |

**The bar** (`flag_bar.py`: no flagged run over 0.15 narrow-lane cycle, except where the other reference receiver's run, levelled on the same flagged satellites and summed over its own constant-counter pieces, moves the same way to within 0.15): rule B fails 5 Galileo (E08, E13, E05, E26, E07; 0.26 to 0.31) and 3 GPS runs on DOY 144, 0 and 8 on DOY 145. **Rule C passes on Galileo on both days** (every run over 0.15 exempt) and **fails by one GPS run a day**: G09 on DOY 144 (TOW 4770 to 21570, range 0.200; +0.09 here, -0.67 in the GOPE00CZE run) and G27 on DOY 145 (TOW 91020 to 102600, range 0.175; +0.03 here, +1.63 there); in both the other run's satellite walks far more than this one's, so the exemption cannot apply. Variants: a 0.05 cycle agreement keeps both failures (0.160 and 0.185); three links held or pinned removes G27 but not G09 and costs Galileo up to 26 points of flagged share on DOY 145.

### 53.4 The consensus datum or the consensus re-seat

E05 argues for the consensus re-seat. Its fault was local: one satellite reached through one arc whose error the satellite's other chords agreed on for 2.5 h, and the run without that arc shows the consensus level flat. A re-seat would have moved E05 onto its agreeing arcs once, with one declared step, before any decision was taken against the tree; rule C's disagreement test is its detector. Cost: from 53.1, about one to a few re-seats a run on Galileo and 25 to 33 a run of 6 h on GPS, each a declared step (a user reset) on that satellite, and a re-seat that keeps or re-expresses the satellite's held links. The consensus datum would cure E05 too, but it re-defines every level and pin at every epoch (a moving datum, every held integer re-expressed against it), the larger build; nothing in E05 needs the network-wide change. Both stay unbuilt (the author's choice).

## 54. 2026-11-16: an unsettled signal declares itself at every emission; Galileo L1C/L5Q held beside L1X/L5X (pre-registered)

**Why** (the requesting session's order after section 53, its note ARNG sections 5 to 7). On a copy of `f12_n144` in which a satellite whose two family signals are not both flagged steps its phase counters at every epoch, and once more when both flags go up (`_rap_f12s_n144`, its `stream_filter_flagged.py` in mode steps), users started with the network do as well as users started 2 h late: fixing users of both systems 80, 22, 15, 12 and 10 mm in hours 2 to 6, Galileo pairs 99.9 % of verified holds right, GPS pairs 6 669 verified holds and 0 wrong. The rule is ordered built. Its reason, for the ledger: a level that is not tied to the network's integers is not continuous, and the stream then says so; a user that restarts an ambiguity at an increment needs no change.

**The build** (exe nrf24; key `network.ring_fix.unsettled_steps`, default off, ledger row UNVALIDATED; needs `network.ring_fix.settled_flags`). For each held family and satellite at every emission, from the flags on that emission's P records: while the family's two signals are not both flagged, both signals' phase counters step; at the first emission at which both are flagged after one at which they were not, they step once more; while both stay flagged only the other rules (the value test or the class rule, the release increments, the forced marks) step them. A family signal absent from the emission counts as not flagged; a key without a baseline (a first sighting) does not step; signals of no held family are not touched (the requesting session's copy steps every signal of the satellite: not matched). Run-end line: the steps raised per family, while unsettled and at the settling. Unit tests `UnsettledSteps.*` (a file of its own, `tests/test_unsettled_steps.cpp`).

**Arms** (exe nrf24): `u12_n144` and `u12_n145` (`f12_n144` and `f12_n145` with the key: the step declaration, the release increments, the flags and the unsettled steps), the streams for user replays; `kj_sim` (`kd_sim`'s configuration) and `o11_n144` (`o10_n144`'s) for keys absent identical; 10-epoch smokes first. **Galileo L1C/L5Q beside L1X/L5X** (the requesting session's question; a change of `network.ring_fix.pairs` only, to ["E:L1X/L5X", "E:L1C/L5Q", "G:L1C/L2W"]): `g3_n144` and `g3_n144r`, the adopted set at the cap of 12 (`q12_n144[r]`) with the three held families, the step declaration, the flags and the unsettled steps, on DOY 144 with the default receiver and GOPE00CZE.

**Bars.** The rule: keys absent identical (`kj_sim` against `kd_sim`, `o11_n144` against `o10_n144`); with the key on, the C, B and P values and the flags of `u12_n144` and `u12_n145` equal `f12_n144`'s and `f12_n145`'s (only the phase counters move); on DOY 144, the set of (emission, satellite, signal) at which a held-family counter differs from the key's previous emission equals that of `_rap_f12s_n144` on the held families' signals; the run-end steps per family reported. Galileo C/Q: the same-start audit zero per family; every epoch emitted; RAIM rows not above `q12_n144[r]`'s by more than a tenth; reads: the held share and the flagged share per family by hour.

## 55. 2026-11-16: the size of a slowly varying code error on observed data, for the bed of remedy (b)

**Why** (the requesting session's choice among section 52's candidates): a slowly varying, elevation-dependent, time-correlated code error, sized from observed GPS (the per-arc Melbourne-Wubbena scatter and its correlation time), in place of larger constants.

**Read** (`_irdu_grades/scripts_s20/mw_scatter.py` and an inline split by block means; DOY 144, `o10_n144`'s raw-observable trace `logs/network_slip_raw.csv`: the Melbourne-Wubbena combination every 30 s per receiver, satellite and signal pair; arcs with no gap over 60 s and no loss-of-lock flag, each less its own mean, in wide-lane cycles; GPS L1C/L2W against Galileo L1X/L5X):

| | GPS L1C/L2W | Galileo L1X/L5X |
|---|---|---|
| arcs of 1 h or more | 600 | 370 |
| scatter of the 30 s values, p50 (p90) | 0.195 (0.347) | 0.204 (0.347) |
| rms by elevation, 10-30 / 30-50 / 50-90 deg | 1.329 / 0.258 / 0.129 | 0.316 / 0.188 / 0.126 |
| arcs with 20+ epochs under 30 deg; of these with rms over 0.5 cycle | 590; 41 | 362; 17 |
| correlation time of the 30 s values, p50 | 0.5 min (one epoch) | 0.5 min |
| arcs of 2 h or more | 440 | 300 |
| scatter of 10-min means, p50 (white noise would give) | 0.066 (0.041) | 0.070 (0.043) |
| scatter of 30-min means, p50 (white) | 0.041 (0.024) | 0.043 (0.025) |
| lag-1 autocorrelation of the 10-min means, p50 | 0.18 | 0.17 |

Per receiver (1 h arcs): GOPE00CZE 0.131, WTZR00DEU 0.151, COCO00AUS 0.184 and DARW00AUS 0.402 cycle on GPS (GOPE00CZE 0.163 on Galileo).

**What it says.** At 30 s the combination is white to the first lag; beyond the white part a slow component remains, about 0.05 wide-lane cycle (4 cm) in 10-min means and 0.03 in 30-min means, with a correlation time of about 6 min, **the same size on GPS and Galileo**. GPS's 1.33 cycle rms under 30 degrees is one arc's (SGOC00LKA-G22, 38 cycles rms: an unflagged jump inside the arc); arcs with an rms over 0.5 cycle under 30 degrees are 7 % on GPS and 5 % on Galileo, so low elevation does not single out GPS either. A slow error sized this way would act on Galileo as much as on GPS, so it cannot be what separates observed GPS's held share (51 to 62 %) from Galileo's (81 to 90 %); what this read removes, each arc's mean (the constant per-arc offsets of section 52's beds), is where GPS can still differ. **Not built.** Proposed instead, for the requesting session's choice: per-arc constant code offsets read from observed GPS against the network's integers (their distribution by receiver and satellite block), with Galileo left unbiased as the control.

### 54.1 2026-11-16: the unsettled steps: every bar passes

Exe nrf24 (`89caf63ca9ae7de1`, commit 7f32aa3); all arms exit 0, every epoch emitted; 10-epoch smokes first (exit 0). Grade `_irdu_grades/nrf_u_grade.txt` (script `_irdu_grades/scripts_s20/grade_u.sh`; the counter sets by `counter_sets.py`).

- **Keys absent identical:** `kj_sim` (exe nrf24) against `kd_sim` (exe nrf20) and `o11_n144` against `o10_n144`: the products and the 42 and 39 CSV traces identical, wall-clock columns aside.
- **Only the counters move:** the products of `u12_n144` and `u12_n145` equal `f12_n144`'s and `f12_n145`'s with the phase counters masked and the flags kept (389 271 and 391 680 lines, 0 differing); the emitted flags equal rule B at every epoch (87 638 and 88 446 records of held families, no mismatch).
- **The counter changes equal the requesting session's copy:** on DOY 144 the set of (emission, satellite, signal) at which a held-family counter (Galileo L1X and L5X, GPS L1C and L2W) differs from the key's previous emission is the same in `u12_n144` and in `_rap_f12s_n144`: 26 785 in each, 26 785 in both, none in one only. The copy also steps the satellite's other signals (Galileo L1C and L5Q, GPS L1W); the build does not, by design.
- **Run-end steps** (phase-key steps raised by the rule, while unsettled and at the settling): DOY 144 Galileo L1X/L5X 7 314 and 66, GPS L1C/L2W 19 228 and 66; DOY 145 Galileo 14 894 and 68, GPS 23 318 and 72.

**For user replays: `u12_n144` and `u12_n145`** (the step declaration with the release increments, the settled flags under rule B, and the unsettled steps).

### 54.2 2026-11-16: Galileo L1C/L5Q held beside L1X/L5X: every bar passes

`g3_n144` and `g3_n144r` (exe nrf24; the adopted set at the cap of 12 with three held families, the step declaration, the flags and the unsettled steps), against `q12_n144[r]` (two held families, exe nrf22).

| audit (same start, two reference receivers) | Galileo L1C, L5Q | Galileo L1X, L5X | GPS L1C, L2W | checks | failing |
|---|---|---|---|---|---|
| `g3_n144` against `g3_n144r` | 73 910, 73 910 | 84 333, 84 313 | 59 942, 60 211 | 436 619 | 0 |

Every epoch emitted; RAIM rows 0 and 0, as with two families; monitor releases 2 and 0 (1 and 0 with two families); every release named. Held link-epochs: Galileo L1C/L5Q 74 104 and 74 094; Galileo L1X/L5X 87 605 and 88 725 (87 420 and 88 606 with two families); GPS 82 538 and 65 365 (82 324 and 64 508): the third family takes nothing from the other two. Held share of Galileo L1C/L5Q by half hour (default receiver): 3.5, 53.5, 71.1, 70.7, 74.2, 73.3, 73.5, 72.8, 85.6, 86.5, 86.1 and 89.6 %.

**Flagged share** (rule B, by hour from hour 2; the emitted flags equal it at every epoch, 130 079 records): Galileo L1C/L5Q 0, 66, 73, 79 and 76 % in both runs; Galileo L1X/L5X 91, 98, 95, 95 and 100 % (92 to 100 % with GOPE00CZE); GPS 47, 69, 70, 80 and 84 % (40 to 77 %). **Galileo C/Q is unflagged through hour 2:** rule B reaches satellites from the tree's datum receiver, and the C/Q tree's datum receiver is COCO00AUS throughout, whose first held C/Q link is E27 at TOW 7530, while the family's first decision anywhere is at TOW 1050. Users at C/Q receivers get settled signals from hour 3 (66 to 79 % of satellite-epochs).

The change is a configuration change only (`network.ring_fix.pairs`); nothing is adopted here (the pairs are a run setting of the chain posture, not a ledger verdict).

## 56. 2026-11-16: the step declaration adopted in the chain posture; the unsettled steps after a warm resume

**The requesting session's grading** (its note ARNG section 8; 467 user replays on DOY 144, all exit 0): users on the settled part of the stream started with the network, 28 network receivers, median 3D in hours 3 to 6: fixing of both systems 22.4, 14.8, 11.6 and 9.8 mm; float of both 26.0, 18.4, 13.5 and 10.2; fixing of Galileo alone 24.9, 19.2, 10.6 and 10.4 (the user that only waits for the flag on `f11_n144`: 59.2, 35.3, 26.9 and 18.5). The wide lane is never off; GPS L1C/L2W pairs 9 555 held, all equal to the network's whole numbers, 6 669 verified, none wrong. The release increments are neutral at the user (float on `f12_n144` against `f11_n144`, paired: 0.0, 0.0, -0.6 and -0.4 mm). A late start is no remedy with GPS (both systems started 2 h late on `f12_n144`: 62, 27 to 30 and 24 mm in hours 4 to 6), so the unsettled steps are the remedy. Rule C gains nothing at the user (15 % fewer held pair-epochs, fixing users equal within 1.3 mm, the float user of both systems 2.3 and 3.4 mm worse in hours 5 and 6, no wrong hold removed): **rule C is not adopted; the flags stay rule B**; `flag_rule_c.py` stays as a stamping script for comparison.

**Adopted** (the requesting session's order, under the author's rule): `network.disc_step_class_pairs` and `network.disc_step_class_tol_cyc`, the step declaration with its release increments, RECOMMEND_SCOPED in the chain posture with network integer fixing (regime `on("network.ring_fix.enable")`; armed when the list is non-empty and the tolerance 0.15 cycle; posture rows in `appendNetworkPostureItemsScoped_`; the loader defaults stay empty and 0.15; the main posture's goldens unchanged). Note: done 2026-11-16; verified by the user replays of DOY 144 (28 network and 11 independent receivers; float users gain against the stream without the declaration, the release increments are neutral at the user; note ARNG sections 3.2 and 8.6) (basic); to do: DOY 145 and further days, receivers that track Galileo L1C/L5Q, the main posture without the chain. `network.ring_fix.settled_flags` and `network.ring_fix.unsettled_steps` stay UNVALIDATED until the replays on `u12_n144` and `u12_n145` are graded.

**The unsettled steps after a warm resume** (the requesting session's code read of 7f32aa3): the previous emission's state (`us_prev_both_`) is not carried across a warm resume, so a family unsettled before the resume and flagged at the first emission after it took no settling step. An unknown previous state now counts as not settled; a first sighting has no baseline, so a cold start is unchanged. Unit test `UnsettledSteps.AFamilyFlaggedAtTheFirstEmissionAfterARestoreTakesTheSettlingStep` (serialize, restore, flag: the settling step, once). Exe nrf25 (`bbc25062e344be2d`).

## 57. 2026-11-16: GPS L1W/L2W held beside GPS L1C/L2W

**Why** (the requesting session's order 3, a configuration change only): 17 of its 28 user receivers have no GPS L1C/L2W pair, and the stream carries L1W. L2W is shared by two families; if the build does not allow that, what it needs is reported before anything is built.

**Arms** (exe nrf24): `g4_n144` and `g4_n144r`, `g3_n144[r]` with the pairs ["E:L1X/L5X", "E:L1C/L5Q", "G:L1C/L2W", "G:L1W/L2W"]; a 10-epoch smoke first (exit 0). Grade `_irdu_grades/nrf_g4_grade.txt` (script `_irdu_grades/scripts_s20/grade_g4.sh`).

**Results.**
- **The bars of section 54.2 pass:** the same-start audit reads 0 of 432 040 checks (Galileo L1C and L5Q 73 905 each, L1X 84 190, L5X 84 170; GPS L1C 55 582, L1W 2 470, L2W 57 818); every epoch emitted; RAIM rows 0 and 0; monitor releases 2 and 0, as with three families.
- **GPS L1W/L2W holds almost nothing:** 2 483 and 3 756 held link-epochs, a held share of 0.6 to 11.7 % by half hour that falls to 0 by the end, while its first band's tree has another root than the L2W tree (the default run: L1W at LEIJ00DEU, L1C and L2W at BOR100POL). Section 26.2's finding stands.
- **It takes from GPS L1C/L2W:** 81 072 and 59 809 held link-epochs against 82 538 and 65 365 with three families (-1.8 % and -8.5 %, most in hours 4 and 5); Galileo unchanged.
- **The flags cannot carry a shared signal.** The settled flags are kept per (satellite, signal), so on the L2W records the L1W/L2W family's flag (never set: 0 % under rule B, its first band's root ties nothing) replaces the L1C/L2W family's: 11 239 and 9 330 records of GPS L1C/L2W differ from rule B. Such a stream flags GPS L2W unsettled where L1C/L2W is settled: not for user replays.

**What the build needs before GPS L1W/L2W can be held** (nothing built): (1) one datum for the bands two families share, either an election that puts the L1W tree on the L2W tree's root (a family mode over three signals, or a datum row tying the roots), or the cascade of section 60: L1W's integer from the held L1C/L2W through the L1W-L1C phase difference, which on one frequency is free of geometry and ionosphere, decided after the pair; (2) flags kept per family, with a rule for a record that two families share (flagged only while every family it belongs to is settled, or one flag per family on the wire).

## 58. 2026-11-16: the root of the flag: rule B against the largest set tied by held links

**Why** (the requesting session's order 2): section 54.2 left Galileo L1C/L5Q unflagged through hour 2 because its tree's datum receiver held its first C/Q link at TOW 7530 while the family decided elsewhere from TOW 1050. **Rule L** flags the largest set of satellites mutually connected through held links and tree edges that entered as held links, whatever receiver roots it; rule B (as built) flags those reached from the tree's datum receiver. Read on `g3_n144`, `f12_n144` and `f12_n145` (the traces of `u12_*` are `f12_*`'s) by `_irdu_grades/scripts_s20/flag_root.py`, which also stamps rule L into copies for the segment bar (`f12L_n144`, `f12L_n145`).

**Flagged share by half hour, rule B / rule L (%):**

| run, family | 1 | 2 | 3 | 4 | 5 | 6 | 7 to 12 |
|---|---|---|---|---|---|---|---|
| `g3_n144` Galileo L1C/L5Q | 0/6 | 0/61 | 0/73 | 0/75 | 59/73 | 73/73 | equal |
| `g3_n144` Galileo L1X/L5X | 0/3 | 44/53 | 90/90 | 91/91 | 97/97 | 99/99 | equal |
| `g3_n144` GPS L1C/L2W | 0/5 | 0/58 | 24/68 | 70/70 | 71/71 | 67/67 | equal |
| `f12_n144` Galileo L1X/L5X | 0/3 | 36/43 | 89/89 | 91/91 | 97/97 | 99/99 | equal |
| `f12_n144` GPS L1C/L2W | 0/5 | 0/54 | 22/64 | 67/67 | 68/68 | 64/64 | equal |
| `f12_n145` Galileo L1X/L5X | 0/2 | 0/39 | 0/84 | 0/96 | 97/97 | 98/98 | equal |
| `f12_n145` GPS L1C/L2W | 0/5 | 0/45 | 25/59 | 52/52 | 55/55 | 57/57 | equal |

The two rules agree from the third hour; rule L gains in the first two: Galileo C/Q 61 to 75 points in half-hours 2 to 4, Galileo X/X 7 to 9 points in the second half-hour on DOY 144 and 39 to 96 points in half-hours 2 to 4 on DOY 145 (its tree's datum receiver ties nothing there until hour 2.5), GPS 45 to 58 points in the second half-hour and 34 to 44 in the third.

**Changes of identity** (the largest set sharing less than half of the smaller of the two sets with the previous epoch's): `g3_n144` Galileo C/Q 2 (TOW 1350 and 1500), Galileo X/X 3 (1320, 1410, 1530), GPS 0; `f12_n144` Galileo 3 (1320, 1440, 1530), GPS 0; `f12_n145` Galileo 0, GPS 2 (87690 and 87750): all in the first half-hour, while the largest set holds 4 to 8 satellites, with 4 to 6 satellites changing side. For the counters a change means: the satellites that leave the set step at every emission from then on (the unsettled steps), those that join take one settling step; a change with little overlap resets most of a fixing user's flagged satellites.

**The segment bar of section 53.3** (`flag_bar.py`, the same flagged datum in both runs; failing flagged runs over 0.15 narrow-lane cycle, Galileo / GPS): rule B 5 / 3 on DOY 144 and 0 / 8 on DOY 145; rule L 5 / 4 and 2 / 8 (its new failures are E28 and E19 on DOY 145, in hours that rule B leaves unflagged); rule L with section 53's agreement test 0 / 1 and 1 / 1. The requesting session's segment read (flagged runs, p50, p90, max; runs over 0.15): rule L DOY 144 Galileo 0.069, 0.143, 0.306 (8), GPS 0.108, 0.173, 0.301 (10); DOY 145 Galileo 0.092, 0.155, 0.276 (11), GPS 0.087, 0.174, 0.217 (10).

**Proposed (not built): rule L with a minimum and a hysteresis.** Flag the satellites of the largest set mutually tied by held links and certified tree edges once it holds at least 4 satellites, whatever receiver roots it, and keep the incumbent set until another set exceeds it by 2 satellites; the unsettled steps then mark the satellites that change side. A user needs the flagged satellites to be consistent with each other, not with the network's datum receiver, so the root plays no part. Cost: the early gain above; the segment bar as rule B's (it inherits rule B's failures, the local-arc cases of section 53, and adds two early Galileo runs on DOY 145). The agreement test that brings the bar back to rule C's was graded neutral at the user (section 56), so it is not proposed again.

## 59. 2026-11-16: the per-arc offsets of observed GPS by receiver type and block

**Why** (the requesting session's order 4, approved from section 55's proposal; it connects to its user-side card RSCB, a receiver-dependent wide-lane offset of the GPS III satellites against the older blocks of about 0.1 m of code). Read on `o10_n144` and `o10_n145` from hour 2 by `_irdu_grades/scripts_s20/arc_offsets.py`: the refused share of link-epochs by receiver type (the RINEX header of the day) and block (GPS III from the ATX of the day; Galileo as the control); and, per arc, the mean signed wide-lane and ionosphere-free N1 fractions of its refused, converged link-epochs (formal sigma at most 0.25 cycle, window refusals left out, 10 or more), less a two-way fit `x = a_receiver + b_satellite + e` that takes out the frame, so that `e` is the arc's own offset.

**Refusals.** Galileo L1X/L5X: one receiver type stands out, JAVAD TRE_G3TH (KOKV00USA alone), held 63.8 % of its link-epochs against 80.8 to 92.9 % for the other types (DOY 144). GPS L1C/L2W, held share of GPS III against the older blocks by receiver type:

| receiver type | DOY 144 GPS III / older | DOY 145 GPS III / older |
|---|---|---|
| Septentrio AsteRx4 (KIT300UZB) | 27.6 / 78.9 | 0.0 / 0.0 |
| Trimble Alloy | 38.1 / 49.1 | 28.3 / 22.1 |
| Septentrio PolaRx5 | 45.5 / 63.5 | 48.3 / 37.5 |
| Leica GR50 | 46.7 / 73.5 | 48.7 / 46.9 |
| Septentrio PolaRx5TR | 61.7 / 75.4 | 64.6 / 59.4 |
| Trimble NetR9 | 63.9 / 56.9 | 47.8 / 29.1 |
| Leica GR30 | 70.0 / 73.8 | 83.2 / 67.1 |

Over all receivers GPS III is held 45.5 % against 61.9 % on DOY 144 (refused on the odds 16.0 % against 7.8 %, on the fraction 20.4 against 15.6, in a window 15.4 against 12.0), but **43.4 % against 36.1 % on DOY 145**, where GPS III is held more at every receiver type (KIT300UZB's AsteRx4 holds no GPS link at all that day): the block split reverses with the day, as it moved with the reference receiver in section 51.

**Per-arc offsets.** After the two-way fit the arcs' own offsets are the same size on GPS and Galileo: |e| p50 0.043 and 0.045 wide-lane cycle (DOY 144; 0.039 and 0.045 on DOY 145), p90 0.17 to 0.18; ionosphere-free N1 0.042 and 0.048. The satellite terms show no block excess (GPS III |b| p50 0.036 and 0.025 wide-lane cycle on the two days, the older blocks 0.026 and 0.042). A GPS III lean of the arcs' own offsets appears at two receiver types only: Leica GR30, +0.177 (2 arcs, DOY 144) and +0.136 wide-lane cycle (3 arcs, DOY 145), and Septentrio AsteRx4, +0.106 (2 arcs, DOY 144); at the other types the GPS III mean is within 0.07 of 0.

**Reading.** The refused GPS links cluster by block on DOY 144, most at the AsteRx4, Leica GR50 and Trimble Alloy receivers, but not on DOY 145; the converged per-arc offsets carry an RSCB-like GPS III offset (0.1 to 0.18 wide-lane cycle, 0.09 to 0.15 m on both codes) at the Leica GR30 and Septentrio AsteRx4 receivers, on 2 to 3 arcs each, and none at the PolaRx5 and Trimble receivers that hold most GPS III arcs. Elsewhere the GPS III refusal excess of DOY 144 comes with floats that fail the odds, not with a constant offset the floats converge to. The evidence for RSCB from the network's side is thin (a few arcs at two receiver types); the block split itself follows the day and the reference receiver, the frame's.

## 60. 2026-11-16: a third frequency: the plan, the simulator first (pre-registered)

**Why** (the requesting session's order 5): the next rung after more signals, Galileo E5b or E6 beside L1X/L5X and GPS L5; no observed-data run before the simulator passes.

**How a third band enters the ring fix.** The ring fix decides pair families named by two signals, each chord's float measured against the chain's trees of its two bands. A third band enters as a second family that shares a signal with the first: Galileo E1/E5a and E1/E5b (or E1/E6) share E1; GPS L1/L2 and L1/L5 share L1. Three things then need the build:
0. **Chords for the second family.** The chord table pairs every band-1 signal of an arc only with the arc's lowest-digit signal of another band (`chainPairFamilies`), so Galileo L1C/L7Q forms only on arcs without L5Q and GPS L1C/L5Q never forms beside L2W (GPS L1W/L2W does form, beside L1C/L2W). The 10-epoch smoke of the log arm (`t3lsmoke`, exe nrf25) shows it: Galileo L1C/L5Q 1 513 chord rows, L1C/L7Q 8, GPS L1C/L2W 2 067, L1C/L5Q none. The chord table has to form every configured family (the pairs of `network.ring_fix.pairs` that the current rule does not form), default off and identical when off.
1. **One datum for the three bands.** The chain grows one tree per band, and one spanning forest over two bands only for a constellation that tracks exactly two phase signals (the pair-family mode). A family's chords are whole numbers only when its two bands' trees share their datum: in section 26.2 GPS L1W/L2W held 5 links beside L1C/L2W's 124 while the L1W tree's root differed from the L2W tree's. A third band's tree must therefore share the pair's datum. On the simulator the election already does: in both smokes the three bands of a constellation share one datum receiver (Galileo S03000SIM, GPS S13000SIM); observed data, where receivers track different signal sets, may not, and then a three-band family mode (one forest over the three bands, as the pair-family mode grows over two) or a datum row tying the third band's root to the pair's is needed.
2. **One integer for the shared signal.** Two families on one arc each decide the shared signal's integer; the ring fix keeps one hold row per (station, satellite, signal) (`rf.table` is keyed so), and the later family's value replaces the earlier's without a test. The consistent form is a cascade: the pair (E1/E5a) is held first, then the third signal's integer follows from the held pair and the extra-wide lane (E5a-E5b, 9.8 m; GPS L2-L5, 5.9 m), decided after the pair and never beside it, so that the shared signal is decided once. Until the cascade exists, a second family is run in log mode or checked for agreement on the shared signal.

**What the simulator fixture offers.** `runs/simnet60_quiet_col_24h`: one channel per band on every satellite of both constellations (GPS C1C/L1C, C2W/L2W and C5Q/L5Q; Galileo C1C/L1C, C5Q/L5Q and C7Q/L7Q; no E6), 60 stations and the consumer SZZ000SIM, a truth table for every signal's ambiguity, and no slips or gaps (a quiet bed: it certifies the algebra, not the events). The network ran every channel on it stably at 2 h on the golden of 2026-10-23 (card L5B section 11: `processing.frequency_mode` triple, the band-5 and E5b types appended to the signal priorities, `network.sat_gf_extra_band_free`, `network.estimate_rx_extra_band_code_delay`).

**The simulator arms** (exe nrf25 for `t3c`, which needs no build; `t3l` after the chord-table build of item 0; the adopted set at the cap of 12, `kq12_sim[_r]`, 3 h from 00:30:15, the default receiver and S45000SIM, with the four three-band keys of card L5B section 11; 10-epoch smokes first):
- `t3c_sim[_r]`: the three bands with the two held families as now (GPS L1C/L2W, Galileo L1C/L5Q). Does the third band change the pairs' holds or the network?
- `t3l_sim[_r]`: the three bands with the ring fix in log mode on four families (GPS L1C/L2W and L1C/L5Q, Galileo L1C/L5Q and L1C/L7Q). Reads: the share of would-be decisions right against truth per family; whether two families' would-be integers agree on the shared signal of an arc; the datum receiver of each band's tree.

**Bars.** `t3c`: every epoch emitted; 0 wrong against truth; the pairs' held link-epochs within 5 % of `kq12_sim[_r]`'s; RAIM rows not above by more than a tenth. `t3l`: every family's would-be decisions right against truth at 99.9 % or more; on every arc decided by two families the shared signal's integers equal; within a constellation, each band's tree on the same datum receiver. If `t3l` passes, the next step is the cascade, built default off and held on the simulator; observed data after that.

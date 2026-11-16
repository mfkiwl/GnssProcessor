# NRF part 7: the bed for remedy (b) (sections 52 onwards of card NRF)

**STATUS**

- **id:** NRF-part7
- **topic:** network-vehicle
- **status:** open
- **summary:** Sections 52 onwards of card NRF (2026-11-16), continued from [part 6](NRF_network_ring_fixing_2026-11-14_part6.md). Section 52: the bed for remedy (b) of section 24.3 item 4, the golden simulator fixture with constant GPS code biases per (receiver, satellite, signal), with and without a receiver-and-block offset on GPS III (`scripts/nrf_code_bias_bed.py`), and the adopted set at the cap of 12 on it: no wrong integer, the audits zero, Galileo unchanged; GPS holds 85.5 to 86.7 % of its link-epochs from hour 2 (89.0 and 90.2 % unbiased, 51 to 62 % on observed data), and the block offset gives a block split that follows the reference receiver, several times weaker than observed. Section 53: the reads of the requesting session's E05 finding (a flagged level that moves under constant counters): common chord fractions against a satellite's tree edge exceed chance by 1 to 5 points of satellite-half-hours on Galileo and 7 to 10 on GPS; E05's walk was KOKV00USA's arc (it vanishes without that receiver; the borrowed E5a calibration not shown to be the cause); a decision holds its integer at 0.1 mm and leaves its misfit to the satellite's level; a flag rule that asks the links to agree (rule C) passes the segment bar on Galileo on both days and fails by one GPS run a day.
- **source:** [part 6](NRF_network_ring_fixing_2026-11-14_part6.md) sections 50 and 51; [part 4](NRF_network_ring_fixing_2026-11-14_part4.md) section 24.3 item 4 (what the simulator needs); the requesting session's order of 2026-11-16 (item 4: the GPS held share, the bed for (b), the third frequency).

**Outcome.** Question: does a simulator bed with constant GPS code biases per (receiver, satellite) read like observed GPS, so that remedy (b) can be graded against truth on it? Not yet. With biases of 0.12 m, and 0.13 m more on GPS III at a quarter of the receivers, the ring fix decides no wrong integer, the audits stay zero and Galileo (unbiased) is unchanged; the wide-lane fractions of the links not held read like observed GPS, but GPS still holds 85.5 to 86.7 % of its link-epochs from hour 2 against 51 to 62 % observed, and the block split is several times weaker than observed. A satellite's level can also move under a settled flag when its one tree arc carries a local error (E05 on DOY 144); a flag that asks the satellite's links to agree removes that on Galileo (section 53).

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

# NRF part 7: the bed for remedy (b) (sections 52 onwards of card NRF)

**STATUS**

- **id:** NRF-part7
- **topic:** network-vehicle
- **status:** open
- **summary:** Sections 52 onwards of card NRF (2026-11-16), continued from [part 6](NRF_network_ring_fixing_2026-11-14_part6.md). Section 52: the bed for remedy (b) of section 24.3 item 4, the golden simulator fixture with constant GPS code biases per (receiver, satellite, signal), with and without a receiver-and-block offset on GPS III (`scripts/nrf_code_bias_bed.py`), and the adopted set at the cap of 12 on it: no wrong integer, the audits zero, Galileo unchanged; GPS holds 85.5 to 86.7 % of its link-epochs from hour 2 (89.0 and 90.2 % unbiased, 51 to 62 % on observed data), and the block offset gives a block split that follows the reference receiver, several times weaker than observed.
- **source:** [part 6](NRF_network_ring_fixing_2026-11-14_part6.md) sections 50 and 51; [part 4](NRF_network_ring_fixing_2026-11-14_part4.md) section 24.3 item 4 (what the simulator needs); the requesting session's order of 2026-11-16 (item 4: the GPS held share, the bed for (b), the third frequency).

**Outcome.** Question: does a simulator bed with constant GPS code biases per (receiver, satellite) read like observed GPS, so that remedy (b) can be graded against truth on it? Not yet. With biases of 0.12 m, and 0.13 m more on GPS III at a quarter of the receivers, the ring fix decides no wrong integer, the audits stay zero and Galileo (unbiased) is unchanged; the wide-lane fractions of the links not held read like observed GPS, but GPS still holds 85.5 to 86.7 % of its link-epochs from hour 2 against 51 to 62 % observed, and the block split is several times weaker than observed.

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

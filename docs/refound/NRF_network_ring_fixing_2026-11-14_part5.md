# NRF part 5: the formal-sigma pairs with the bad-epoch response on (sections 27 onwards of card NRF)

**STATUS**

- **id:** NRF-part5
- **topic:** network-vehicle
- **status:** open
- **summary:** Sections 27 onwards of card NRF (2026-11-15). Section 27: stage O2's formal-sigma pairs (Galileo L1X/L5X held on DOY 144 with the odds at the formal sigma) re-run with the bad-epoch response of card BER on, pre-registered, with the bars of stage O2 unchanged; a holding run with the response on is added for the user replays. 2026-11-15, results (section 28): with the response on, the formal-sigma pairs agree on every held integer (0 failing of 155 633 checks between two receivers, 0 of 131 369 between two starts, against 13 008 and 13 344 without it), every epoch emitted, RAIM 7 against 7 (15 to 17 without the response), the holding share unchanged (82 to 87 % from hour 2).
- **source:** [NRF part 4](NRF_network_ring_fixing_2026-11-14_part4.md) sections 21 to 23 (stage O2, its bars and the formal-sigma failures); [BER](BER_bad_epoch_response_2026-11-15.md) (the response, `network.amb_float_drop_jump_k`); the requesting session's review of 2026-11-15

**Outcome.** Question: the formal-sigma runs of stage O2 failed the agreement audit (13 008 of 151 698 checks between two reference receivers, 13 344 of 92 547 between two starts), and the requesting session traced 13 of the 18 departing links to wet-delay recoveries after slips at CPVG00CPV (TOW 3990) and MRO100AUS (TOW 7800). Card BER's response removes the spread of the MRO100AUS slip. With it on, do the formal-sigma pairs agree, with every epoch emitted and no RAIM excess? Yes on this bed: 0 failing checks between receivers and between starts, every epoch emitted, RAIM 7 rows in every run, while the formal sigma keeps its holding share (82 to 87 % from hour 2, against 33 to 65 % at twice the formal sigma). Standing: one bed, `sigma_scale` 2 unchanged.

## 27. 2026-11-15: the formal-sigma pairs with the response on (pre-registered)

**Why.** The requesting session's review of stage O2: most formal-sigma failures are not the sigma; they sit inside a wet-delay recovery after a slip, and a wrong hold then keeps the wet delay wrong for hours. Card BER found that the slip's spread comes from the float vehicle's drop and built a response that removes it at MRO100AUS on this bed (BER section 9). The CPVG00CPV case (a slip on G20 at TOW 3990 with a chain re-host and a cut release of 26 arcs) is open: the response acts only where a band's measured step exceeds the birth variance.

**Arms** (exe nrf12, branch `irdu/user-integers`): copies of stage O2's arms with only `network.amb_float_drop_jump_k` 1 added: `o2s1j_n144` (default receiver, start 0), `o2s1j_n144r` (GOPE00CZE, start 0), `o2s1j_n144b` (default receiver, +1 h), each against a key-off run with the response on (`o2offj_n144`, `o2offj_n144r`, `o2offj_n144b`). For the user replays, `o2gj_n144`: the arm `o2g_n144` (Galileo L1X/L5X and GPS L1C/L2W held at twice the formal sigma) with the response on; its product file is kept.

**Bars (as stage O2, frozen).**
1. The same-start audit (`o2s1j_n144` against `o2s1j_n144r`) and the two-start audit (`o2s1j_n144` against `o2s1j_n144b`, the wind-up branches removed with the trace) on held integers and tree pins over every common arc: 0 failing checks, with the sizes of any failing closure; the audit on the arcs both runs start together beside the two-start one.
2. Every epoch emitted.
3. Every release named.
4. RAIM rows not above the key-off run of the same receiver and start by more than a tenth.
5. Every release by the residual monitor listed with its link and time.

**Reads.** Decisions and held shares by ring against `o2s1` and `o2s2`; the 18 departing links of section 23 (CPVG00CPV, MRO100AUS and the rest) with the response; the wet delay of CPVG00CPV and MRO100AUS across their slips.

## 28. 2026-11-15: results of section 27 (the formal-sigma pairs with the response on)

The seven arms of section 27 ran on exe nrf12 (`67ee6e666ada4c9e`), all exit 0; the same-start pair's wind-up traces are byte-identical. Grades: `_irdu_grades/nrf_o2j_*`, script `_irdu_grades/scripts_s20/grade_o2j.sh`.

### 28.1 The bars

| bar | formal sigma without the response (sections 22, 23) | formal sigma with the response |
|---|---|---|
| 1. same-start audit, default receiver against GOPE00CZE, every common arc | 13 008 failing of 151 698: FAIL | **0 of 155 633: PASS** |
| 1. two-start audit, wind-up branches removed with the trace | 13 344 of 92 547: FAIL | **0 of 131 369: PASS** |
| the same on the arcs both runs start together | 1 015 of 26 048 | 0 of 42 584 |
| held links against the tree-tree potentials (same start) | 1 failing link (CPVG00CPV-E04) | 0 |
| 2. every epoch emitted (default, GOPE00CZE, +1 h) | 720, 720, 600 | 720, 720, 600: PASS |
| 3. every release named | 109, 121, 64 | 109 (17 slip, 92 gap), 122 (24 slip, 98 gap), 98 (17 slip, 80 gap, 1 monitor): PASS |
| 4. RAIM rows against the key-off run of the same receiver and start | 15, 17, 8 against 15, 17, 8 | 7, 7, 7 against 7, 7, 7: PASS |
| 5. monitor releases | LMMF00MTQ-E28 at TOW 21150 (+1 h) | the same link at the same epoch (+1 h) |

### 28.2 Reads

- **Held share.** With the response (default receiver, start 0) by hour 20.8, 82.1, 84.4, 82.0, 86.9, 85.7 % against 21.4, 81.5, 84.3, 81.9, 87.0, 85.4 % without it and 0.5, 33.4, 60.0, 59.3, 64.8, 61.1 % at twice the formal sigma; decisions by ring unchanged (59, 62, 131, 58, 36, 10 at rings 2 to 7). The response does not change how much the formal sigma holds; it changes whether the holds agree.
- **The departing link.** CPVG00CPV-E04, decided without the response at TOW 4560 at `sigma_if` 0.166 inside the wet-delay recovery after the slip at TOW 3990 (section 23), is decided with it at TOW 4470 (default) and 5790 (GOPE00CZE), in agreement. CPVG00CPV's wet delay at TOW 3960, 3990, 4200, 4560, 5400, 7200 and 9000 in the key-off runs: 0.215, 0.128, 0.089, 0.099, 0.120, 0.153, 0.169 m without the response; 0.213, 0.212, 0.214, 0.208, 0.196, 0.186, 0.181 m with it.
- **RAIM over 6 h:** 7 rows in every run with the response against 15, 17 and 8 without it.
- **The user-replay run** `o2gj_n144` (Galileo L1X/L5X and GPS L1C/L2W held at twice the formal sigma, the response on): 720 epochs emitted, RAIM 6, 94 releases named; its product file is kept at `runs_nom/_rap_o2gj_n144/products.txt`.

### 28.3 What section 27 says

With the response on, the formal sigma's held integers agree between the two receivers and the two starts on this bed, every epoch is emitted and RAIM falls to 7 rows in every run (15, 17 and 8 without the response), while the formal sigma keeps its holding share (82 to 87 % of the links from hour 2, against 33 to 65 % at twice the formal sigma). The formal-sigma failures of stage O2 came from the slip response's spread (card BER), not from the sigma. One bed and one day; `sigma_scale` 2 stays the setting until the author decides.

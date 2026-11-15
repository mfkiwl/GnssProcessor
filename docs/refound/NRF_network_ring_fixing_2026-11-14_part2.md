# NRF part 2: stage N2, held integers through the chain's events (section 13 of card NRF)

**STATUS**

- **id:** NRF-part2
- **topic:** network-vehicle
- **status:** open
- **summary:** Section 13 of card NRF (2026-11-15): the results of stage N2, pre-registered in section 12 of [NRF](NRF_network_ring_fixing_2026-11-14.md). The ring fix with the order free and the odds gate (N1b-OL), the cut algebra of section 12 and a truth audit in every epoch's frame, on r3c (re-seats, returns, one true slip) and seven event beds: 0 wrong held integers on every cold-start arm (28 000 to 31 000 held link-epochs per bed). The ceiling (every link held at its true integer all run) takes 0 wrong. The steady-state harness (truth for 30 min, then the rule alone) FAILS: 68 wrong decisions after the cut-over. Bar I-b fails on every bed with and without the ring fix, at similar counts.
- **source:** [NRF](NRF_network_ring_fixing_2026-11-14.md) sections 4, 10 to 12; [IRD](IRD_integer_recovering_datum_2026-10-13.md) section 9 (bar I-b); [IRDU part 3](IRDU_user_integers_on_the_chain_2026-11-14_part3.md) section 12.5 (Q4)

**Outcome.** Question: do held integers survive the chain's events, and does a network that is integer stay integer by itself? From a cold start, on r3c and on seven event beds, the ring fix takes 0 wrong integers; every held link that crosses a cut with an unknown step is released at the cut, and re-hosts onto held links keep the frame. A network warmed by truth for 30 min and then left to the rule takes 68 wrong decisions within the next hour, for a reason not yet traced. Standing: default off; the steady-state harness needs a warm start of the network's own.

Sections 1 to 12 are in [NRF](NRF_network_ring_fixing_2026-11-14.md). Results of this section are appended below.

## 13. 2026-11-15: stage N2 results

**What ran.** Commit `65a7d42` with one fix after its first runs (below), exe `gnss_processor_irdu_nrf5.exe` (sha256[:16] `ee72f922a4b65126`). On r3c: `_rap_nrf5_olt_r3c` (N2-r3c: N1b-OL with the truth audit), `_rap_nrf5_olc_r3c` (N2-ceiling: the oracle phase all run), `_rap_nrf5_ols_r3c` (N2-steady: the oracle phase for 30 min from the first decision epoch, cut-over at TOW 263010, then N1b-OL), `_rap_nrf5off_r3c` (the plain chain arm). Event beds, N1b-OL with the truth audit and the bed's plain chain arm (exe nrf5): `_rap_nrf_olt_<bed>` and `_rap_nrf4off_<bed>` for `ird_t2`, `ird_tr`, `ird_t3`, `ird_rv16`, `ird_rg`, `ird_ms`, `ird_msx`. Gates: `_rap_nrf5off_zw_nr3`, `_rap_nrf5_ol_nr3`, `_rap_nrf5_olt_nr3`. Every run exit 0, 240 of 240 epochs. Grades `runs_nom/_irdu_grades/nrf_n2_*`; the steady-state reads `scripts/nrf_steady.py`.

**The fix after the first runs.** On the first build (exe nrf4, `20b7c5c914d9c00c`; runs `_rap_nrf_olc_r3c`, `_rap_nrf_ols_r3c`, `_rap_nrf_olt_r3c`, kept as the record) the truth model did not count the fixture's one true slip (S43000SIM G22 L1C +25 at TOW 261930) at its own epoch: the epoch's clock sits a few microseconds before the stamp. The oracle then held that link 25 cycles off for one epoch, and that arm took 1 wrong held link-epoch. The slip now counts with half a second of slack. The cold-start arm, which held nothing at that epoch, is unchanged by the fix.

**Gates: PASS.** The key off against the previous build (pv1): IDENTICAL whole. N1b-OL on the bed without re-seats against section 11's run: IDENTICAL whole (no cut occurs there). The truth model against the bed's frame file: 87 048 chord-band-epochs compared, 0 differ; on that bed the truth audit reads 12 194 held link-epochs right, 0 wrong.

**N2-B1, 0 wrong holds.**

| arm | links decided | held link-epochs | wrong (truth audit) | held at the end | releases: chain, gap, slip, refloat, monitor | became tree edges |
| --- | --- | --- | --- | --- | --- | --- |
| N2-r3c | 413 | 31 200 | 0 | 200 | 167, 28, 0, 0, 0 | 18 |
| ird_t2 (slip, large subtree) | 423 | 28 266 | 0 | 198 | 182, 27, 0, 0, 0 | 16 |
| ird_tr (slip on the root's edge) | 409 | 30 358 | 0 | 175 | 188, 29, 0, 0, 0 | 17 |
| ird_t3 (slip with LLI) | 415 | 30 735 | 0 | 200 | 168, 28, 0, 0, 0 | 19 |
| ird_rv16 (returning vertex) | 404 | 29 814 | 0 | 199 | 160, 28, 0, 0, 0 | 17 |
| ird_rg (root handover) | 378 | 19 795 | 0 | 175 | 171, 14, 1, 0, 0 | 17 |
| ird_ms (split and merge) | 351 | 27 611 | 0 | 176 | 128, 28, 1, 0, 0 | 16 |
| ird_msx (abrupt cut-off) | 366 | 27 972 | 0 | 187 | 130, 25, 0, 0, 0 | 22 |
| N2-ceiling | 1 068 (oracle) | 92 110 | 0 | 414 | 68, 134, 5, 383, 0 | 64 |
| **N2-steady** | 834 (628 oracle) | 63 467 | **2 728** (68 decisions) | 190 | 207, 82, 3, 184, 125 | 43 |

The independent re-grade with the frame algebra of `scripts/ird_frame_census.py` (`nrf_audit.py --fixture`) agrees with the code's audit to the count on the three r3c arms (N2-r3c 31 200 and 0, N2-ceiling 92 110 and 0, N2-steady 63 467 and 2 728 held link-epochs with 68 wrong decisions). Every cold-start arm and the ceiling take 0 wrong. **N2-steady FAILS the bar** (below).

**The cuts.** On r3c 148 cuts on a band; 36 had a known step, every one 0 (a re-host onto a held link: the chain's target equals the held integer, as card IRDU Q4 found), so no held integer was ever re-expressed by a non-zero step; 112 had an unknown step and released the 167 held links crossing them. No old host was inherited on any bed: the old host's arc had ended or crossed a cut with an unknown step. On the root handover bed the root row pinned the new root at its carried bias and 77 held links kept their integers, 0 wrong. Decided = released + became tree edges + held at the end on every arm (413 = 195 + 18 + 200 on N2-r3c; the run-end line of the first build left the tree transitions out of the sum and printed NOT CLOSED; it counts them now).

**N2-B2: holds on the events exercised.** Every held link crossing a cut with an unknown step is released at the cut's epoch, with an event row naming the cut's row and `step=unknown` (167 on r3c; 128 to 188 per event bed). The IRD slips fall on tree edges (`ird_t2`, `ird_tr`) or on an arc that was a tree edge at the slip (`ird_t3`), so no held link sat on a slipped arc there; their slips release the held links that cross the moved side, at the slip's epoch. A held link on a slipped arc was released at the slip's epoch on r3c's ceiling and steady arms (the fixture's slip, cause slip) and in N1-P (three).

**N2-B3, card IRD's I-b: FAILS on every bed, with and without the ring fix.** The bed's plain chain arm fails I-b too, with thousands of undeclared integer steps per class (r3c: cut releases 5 017 and 5 070 undeclared integer steps without and with the ring fix, kept edges 5 720 and 5 277, non-event epochs 16 035 and 14 672). The ring fix does not change the counts materially; the steps are the chain's own (card IRD's I-b reading of the as-built chain).

**N2-B4: PASSES.** 240 of 240 epochs on every arm.

**The steady state.** After the cut-over (TOW 263010), from `nrf_steady.py`:

| arm | chord link-epochs held after the cut-over | wrong | minutes from birth to hold, p50 (p90), rings 2 / 3 / 4 / 5 |
| --- | --- | --- | --- |
| N2-ceiling | 99.5 % | 0 | (truth at once) |
| N2-steady | 58.1 % | 2 728 | 17.0 (27.0) / 22.5 (43.0) / 31.5 (56.0) / 40.5 (63.0) |
| N2-r3c (cold start, same split) | 44.3 % | 0 | 17.0 (34.5) / 24.0 (43.5) / 41.0 (65.5) / 40.5 (63.0) |

A link born, re-seated or released after the cut-over is held 17 to 41 min later at the median by ring, with or without the warm start: the event window (600 s) and the persistence count (10 epochs) set the floor at 15 min, the floats the rest.

**Why N2-steady fails, as far as traced.** Its first wrong decisions come 16 min after the cut-over (TOW 263970: S19000SIM-G11 and S14000SIM-G19, ring 5), each 1 cycle off truth on both bands (the wide lane right), and the producer's lattice agrees with the wrong integers. Those links were held at truth by the oracle until the cut-over and released by the monitor within 30 to 60 s after it (IF residual above 3 cm at 4 epochs; 125 monitor releases over the run, none on any cold-start arm). After the release the float converged to an integer 1 below truth, and later to 2 and 3 below (S19000SIM-G11 decided 76, 75 and 74 in turn while truth read 77), so its frame drifted by about one cycle per 20 to 40 min on both bands. Holding every link at truth also makes RAIM attribute 408 times on the ceiling and 370 on N2-steady, mostly at the slipped station S43000SIM and two others, where the plain and cold-start arms have none. The candidate: the truth integers conflict with what the producer estimates at some links (around the slipped station first), the oracle phase bends the network to them, and after the cut-over the bent state relaxes while the rule decides. Not traced: the source of the conflict (the slip's response at S43000SIM, a model term the simulator has and the producer lacks, or the oracle's own forcing). The cold-start arm with the same rule on the same bed takes 0 wrong.

**Verdict.** From a cold start the ring fix takes 0 wrong integers through r3c's re-seats and on all seven event beds, releasing what crosses a cut it cannot follow and keeping the frame through re-hosts onto held links and through a pinned root handover. The steady-state harness as built does not answer whether a network that is integer stays integer: its warm start (truth for 30 min) is not a state the network reaches by itself, and after it the rule takes 68 wrong decisions. N2-B1 holds on every cold-start arm and fails on N2-steady; N2-B2 holds where exercised; N2-B3 fails for the chain with and without the ring fix; N2-B4 holds.

**What it points to, for the author's decision.** (a) A steady-state harness warmed by the network's own holds: a cold-start run continued past its first two hours (the 6 h bed of N3 does this), with the reads after hour 2; (b) the conflict between truth and the producer on the ceiling (RAIM's attributions around the slipped station) traced before truth is used as a warm start again; (c) the inheritance of old hosts never fired: re-hosts on these beds follow arcs that end, so the old host is gone; (d) N3 from a cold start, as section 6 plans. N3 waits for the requesting session's word, since N2-steady failed.

**Not verified.** The steady-state failure's cause; a held link on a slipped arc on an IRD slip bed (none occurred); a non-zero known step (none occurred); users on the N2 streams (not replayed: the stage's verdict did not need them, and the steady-state arm failed first).

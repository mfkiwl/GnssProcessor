# NRF part 11: the users of the 24 h days and the stream's continuity guard (sections 90 onwards of card NRF)

**STATUS**

- **id:** NRF-part11
- **topic:** network-vehicle
- **status:** open
- **summary:** Sections 90 onwards of card NRF (2026-11-17), continued from [part 10](NRF_network_ring_fixing_2026-11-14_part10.md). Section 91: the users of DOY 146 graded against the requesting session's card ARNJ (bars 1 to 12): the whole-day users pass bars 1 to 4 (network receivers fixing at most 14.9 mm in every hour from 3 to 24, fixing better than float in every hour, the receivers outside the network at most 15.7 mm, no wrong hold), fail bar 5 (Galileo reference changes at the four receivers of the second Galileo family) and bar 12 (the Leica receivers' Galileo reference changes); the loss-of-lock mask passes bars 10 and 11 at the Leica receivers; the users' resolver logs keep only their last 15 to 17 hours, so bars 4, 5 and 12 are read from hour 7 or 10.
- **source:** [part 10](NRF_network_ring_fixing_2026-11-14_part10.md) sections 83 to 89; the requesting session's card ARNJ (worktree `rx_sat_bias`, `docs/cards/user-ar/ARNJ-USERS-ON-A-24-HOUR-DAY.md`, sections 2 to 4: the runs and bars 1 to 12), handed over on 2026-11-16 at 19:30.

**Outcome.** On the first 24 h day of the adopted configuration, the whole-day users at the network receivers hold their six-hour accuracy through the day (fixing 14.9 mm in hour 3 falling to about 5 mm), fixing stays ahead of float in every hour, and no checked hold is wrong; what fails is the stability of the users' Galileo reference satellite at the receivers of the second Galileo family and at the Leica receivers, the user-side face of that family's unsettled satellites. The joining users and DOY 147's users follow.

## 91. 2026-11-17: the users of DOY 146 against card ARNJ's bars (whole-day users; the Leica receivers)

**Runs** (card ARNJ section 2 and 4; the requesting session's scripts `users_chain_d146.sh`, `derive_d146.py`, engine rscb6, run here from 20:35 on): the network run `_rap_d24_n146` ended with exit 0 and the loss-of-lock mask decision file read 3, so 886 run folders were derived; the 98 whole-day runs (`a24f`, `a24x` at 49 receivers) and the 8 runs with the mask key absent (`a7f`, `a7x` at HKSL, REYK, WTZR, WROC) ended with exit 0 by 00:59; the 780 joining users run after them. Grades: `grades_arnd\d146\` (the chain's) and `grades_arnd\d146_early\` (the same tools on the whole-day runs as soon as they ended).

**A limit of the grades.** The users' ambiguity-resolver logs rotate at 5 MB with three backups (`ambiguity_resolver.log` and `.1` to `.3`), so a 24 h user keeps only the last 15 to 17 hours of the `CLFRAC` lines that `user_fix_vs_float.py` and `ref_changes.py` read: the holds are graded from hour 7 (GPS, Galileo C/Q) or 10 (Galileo X/X) to 24, and the reference changes over 951 to 1 820 of the 2 880 epochs (median 1 269). A full-day grade needs larger logs or a grade from a trace that does not rotate.

**Whole-day users** (bars 1 to 5; hours of the day, hour 1 the first):
1. *Network receivers* (28): the median over the receivers of the hourly 3D median, hours 3 to 24, float 17.5, 12.1, 10.1, 10.3, 8.8, 8.5, 7.6, 8.0, 8.7, 7.5, 7.7, 6.8, 6.2, 6.6, 6.7, 6.2, 6.2, 6.3, 5.9, 5.2, 5.4, 5.3 mm; fixing 14.9, 10.7, 10.5, 8.8, 7.4, 6.7, 6.9, 7.0, 7.8, 6.2, 6.2, 5.8, 5.4, 6.0, 5.9, 5.7, 5.5, 5.8, 5.6, 4.8, 5.2, 5.3 mm. PASS (at most 20 mm).
2. *Fixing against float* (paired per receiver): −1.7 mm in hour 3, −0.1 to −1.3 mm after, negative in every hour. PASS.
3. *Receivers outside the network* (11), fixing: 15.7, 12.8, 9.6, 8.4, 9.9, 10.9, 11.0, 12.2, 10.5, 8.5, 5.9, then 5.2 to 6.9 mm. PASS (at most 25 mm). The receivers of the second Galileo family (7): fixing 17.0 mm in hour 3, 1.5 to 5.9 mm from hour 7.
4. *Holds* (the float sibling decides; hours 7 or 10 to 24): Galileo L1X/L5X 65 687 held pair-epochs (63 020 verified), Galileo L1C/L5Q 10 548 (5 357), GPS L1C/L2W 221 800 (213 638); none wrong; the wide lane off the network's at SEYG on 28 C/Q pair-epochs in hour 24. PASS on the logged hours.
5. *Reference satellite* (fewer than 80 changes per system and run): Galileo FAIL at the four receivers of the second Galileo family, GOP6 307, SEYG 204, HKSL 167 and MRC1 166 changes within their logged spans; the other 42 receivers have at most 24 Galileo changes logged (47 per day at that rate); GPS at most 44 logged (CIBG, about 89 per day at that rate; CUSV 35, about 74).

The per-receiver means of hours 4 to 6 keep their six-hour pattern: LCK400IND 38.5 mm fixing (the elevation mask, section 85; these users run at 15 degrees), UTQI 51.9 mm outside the network, the rest of the network receivers 2.4 to 22.7 mm.

**The Leica receivers** (card ARNJ section 4; HKSL, REYK, WTZR, WROC; fixing with the mask 3 against fixing with the key absent, paired per receiver and hour, median over the four):
10. Hours 3 to 24: −6.3, −7.1, −2.1, −0.7, −0.3, −3.6, −2.9, −2.6, −1.6, −0.8, −1.3, −1.8, −2.1, −1.0, −0.9, −0.4, +0.1, +0.4, +0.5, +0.4, +0.6, +0.5 mm: never worse by more than 2 mm, better in the mean. PASS.
11. Galileo L1C/L5Q holds with the mask at the four: 3 514 held pair-epochs, 1 715 verified, none wrong (logged hours). PASS.
12. Galileo reference changes with the mask: HKSL 167, REYK 172, WROC 309, WTZR 290 within their logged spans. FAIL; with the key absent 1 608, 1 438, 784 and 631 (nearly one per epoch at HKSL and REYK).

**Reading.** The adopted configuration's users hold their six-hour accuracy through a whole day, fixing ahead of float in every hour, with no wrong hold among some 300 000 checked pair-epochs. What does not hold is the users' Galileo reference satellite at the receivers that track the second Galileo family (and the Leica receivers, which track it): its satellites are unsettled for 30 % of the day (section 83.1), and a user's reference moves with them. The loss-of-lock mask is worth up to 7 mm at the Leica receivers in the hours its Galileo fixes land and costs at most 0.6 mm late in the day.

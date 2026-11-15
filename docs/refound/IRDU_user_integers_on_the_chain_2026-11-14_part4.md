# IRDU part 4: the users' position floor on the simulator (section 12 of card IRDU, continued)

**STATUS**

- **id:** IRDU-part4
- **topic:** network-vehicle
- **status:** open
- **summary:** Section 12 of card IRDU continued from [part 3](IRDU_user_integers_on_the_chain_2026-11-14_part3.md) (2026-11-14): the users' position floor of about 0.1 m on the network's streams, float and fixed, which holding every link at its true integer does not remove (12.5), split by user replays only, one change each, pre-registered before the replays (12.6). Results are appended below.
- **source:** [part 3](IRDU_user_integers_on_the_chain_2026-11-14_part3.md) sections 12.3 and 12.5 (the split of the float-user gap, the late-start users); [IRD](IRD_integer_recovering_datum_2026-10-13.md) section 8 (the stream algebra: x, r, E)

Sections 1 to 10 are in [IRDU](IRDU_user_integers_on_the_chain_2026-11-14.md), section 11 in [part 2](IRDU_user_integers_on_the_chain_2026-11-14_part2.md), sections 12 to 12.5 in [part 3](IRDU_user_integers_on_the_chain_2026-11-14_part3.md). Results are appended below.

### 12.6 2026-11-14: the position floor that integers do not explain, user replays only (pre-registered before the replays)

**Assigned** by the requesting session in the author's absence after its re-grade of 12.5, whose own readings (its scripts) are: late-start users from 30 min, second hour, float 23 mm on the truth stream, 119 mm on Q1's and 95 mm without pins; S48000SIM and SZZ000SIM hold 92.2 and 92.4 % on Q1's stream against 92.5 and 91.2 % on the truth stream, at 45 and 69 mm against 8 and 18 mm; each satellite's ionosphere-free phase term against truth, less the epoch's median over satellites and the satellite's own mean, 2.9 mm rms on Q1's stream (p95 5.6 mm; 0 on the truth stream, 13.1 mm without pins), the same term on the code side about 22 mm. The cause is in neither the integers, the start-up nor the phase term that moves.

**Read before the replays** (streams and existing user logs only):

- x per satellite (card IRD section 8; `scripts/irdu_code_datum.py terms`): on Q1's stream and the reference row 0.83 to 4.48 m (median 1.95 m), constant to 0.1 mm over the run; 0 on the truth stream. Observed data give the same values: the broadcast T_GD against CODE's observable-specific code biases of the day (`irdu_code_datum.py observed`) reproduces x for all 32 satellites to the millimetre (G01 4.481 m, G19 0.827 m). The simulator's truth code biases are CODE's, and the network's code biases sit at the broadcast T_GD exactly as on observed data, so whatever x does here it does on observed data. Its common part (1.83 m over the satellites) falls on the receivers; the part specific to a satellite is 0.49 m (p50) and up to 2.65 m.
- r, the range-like code term: each satellite's mean against the epoch's median 3.5 cm (p50) and 9.5 cm (max) on Q1's stream.
- the users' ionosphere: one slant state per satellite (between-satellite single differences, the pivot's state frozen), seeded at 0 with a 50 m prior (the seed from the code needs code-bias coverage, which the replayed user's configuration leaves off, so it falls back to 0 with ten times the 5 m initial sigma), random walk 0.001 m^2/s scaled by the obliquity; the stream carries no ionosphere record and `consume_network_iono` is inert in a replay. By the algebra this user takes a constant x whole into its ionosphere states.
- satellites: each user tracks the same satellites on the truth stream as on Q1's (8.3 to 10.2 per 15 min bin); the accuracy records (U) are the same on the three streams (mean 0.096 m).
- the replay's resets: Q1's phase records carry no discontinuity counter, and a user on it resets ambiguities at 380 satellite-signal epochs from the early start, at 3 to 7 after a 30 min start (all between 31 and 35.5 min) and at none after a 45 min start; none on the truth stream. The 45 min start stalls like the 30 min one, so the resets do not set the floor. The wide-lane flag of the phase records (1 on the truth stream, 0 on Q1's) is parsed and read nowhere in the user.
- the users' wet delay (`scripts/irdu_user_zwd.py`: the absolute estimate in each user's `rt_engine.log` against `truth_tropo.csv`), median over the users per 15 min from 30 min after the start: the truth stream -11 to +10 mm (one bin -25); Q1's -13 to -34 mm at all three starts; the reference row -4 to -27 mm. The network's own wet delay on Q1's run is within 1 to 3 mm of the truth from 15 min (median over the stations). A height error of about 2.5 times a 2 to 3 cm wet-delay error is the floor's size.

**The cases** (one change each against Q1, or against the truth stream for the users' configuration; the five users of section 9, float and fixing):

1. The code datum (candidate 1): `_rap_irdu_cdx_nr3`, Q1's products with x removed (B'_b = B_b + mu_b x, P'_b = P_b - mu_b x: x' = 0, r and every E_b unchanged, so every pair keeps its integers), from the start and from 30 min (20 runs).
2. The users' ionosphere (candidate 2): the user set `fi`, a slant ionosphere free at every epoch with no prior (initial sigma 1000 m, random walk 100 m^2/s, 55 m per 30 s), on Q1's stream and on the truth stream, from the start and from 30 min (40 runs).
3. The users' wet delay and satellites (candidate 3): the readings above, and the wet-delay reading on every case's users.

Additions of this session, the remaining terms one at a time, from 30 min only (30 runs): 4. `_rap_irdu_cdr_nr3`, r removed (B'_b = B_b + r: the code equals the truth's but for x); 5. `_rap_irdu_cdxr_nr3`, x and r removed (code corrections the truth's, phase corrections the truth's plus lambda_b E_b); 6. `_rap_irdu_cdxrf_nr3`, x, r and the fraction of E_b removed (phase corrections the truth's plus whole cycles only: the frame's integer offsets per satellite and band). Each stream is built by `irdu_code_datum.py move` and checked by its `check` (x, r and E_b at what the move promises), and keeps Q1's clock records, phase-record fields and arm.

**Readings.** Float and fixed 3D median over the users per 15 min from each user's own start, against the truth stream under the same user configuration; HELD, WRONG and UNRESOLVED of the fixing users; the users' wet-delay error per 15 min.

**Rule (written before the replays).** A case removes the floor when its float median over the users is within 1.5 times the truth stream's (same user configuration) in each of the bins 45 to 60, 60 to 75 and 75 to 90 min after a 30 min start; it leaves the floor when within 1.25 times Q1's (same user configuration) in those bins; otherwise it removes part. From the start, the second hour's four bins are read the same way.

**Expectation.** The algebra predicts no floor at all: x is taken whole by the users' ionosphere states, the common modes cancel between satellites, every constant on the phase falls into a float ambiguity, and what moves is 3 mm on the phase. The floor is there, so one of these terms reaches the users' wet delay through something the algebra leaves out. Expected: case 1 leaves the floor (x is absorbed); case 2 slows the users on both streams and leaves the ratio; case 4 leaves it (section 12.3's hybrid (b), Q1's code under the truth stream's phase, read at the truth level); case 5 keeps it (by elimination, the phase side); case 6 removes it if the floor is the fraction of E_b, and leaves it if the users do not shed whole-cycle offsets, which would place the cause in the user, not in the stream. In every case the users' wet-delay error tracks the floor.

**Decisions in the author's absence.** (1) Cases 4 to 6 are added, from 30 min only. (2) Cases 1 and 2 run from both starts. (3) The free ionosphere is realized in the users' configuration only (initial sigma and random walk). (4) The facts above were read before the expectation was written; the wet-delay reading is an addition. (5) The observed-data comparison of x takes CODE's biases as the stand-in for the truth.

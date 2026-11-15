# NRF: integer fixing in the network, ring by ring from the chain's root, on the simulator

**STATUS**

- **id:** NRF
- **topic:** network-vehicle
- **status:** open
- **summary:** Pre-registered 2026-11-14 (night), before any graded run, on the author's instruction to build integer fixing in the network by the ring method of card IRDU section 12: a chord's integers are decided ring by ring outward from the chain's root, held in the network's own solve, released at every event that can invalidate them, and every held integer is audited against truth. Simulator only, default off. Stages: N1 the bed without re-seats, N2 r3c with re-seats and event beds, N3 the 6 h reference bed; observed data only after the three pass and are re-graded. Serves card IRD's steps IRD-5 and IRD-8 and card ARL's rungs, with their frozen bars. Results are appended below.
- **source:** the author's two messages of 2026-11-14 (section 1); [IRDU part 3](IRDU_user_integers_on_the_chain_2026-11-14_part3.md) section 12 (the rings, Q1 to Q4, the gated rounding and the log-only search); [IRD](IRD_integer_recovering_datum_2026-10-13.md) sections 9 to 11 (bars, rules, increments); card ARL section 2026-10-24 and card FCFC section 9 (both in the record); [IRDC](IRDC_integer_recovering_datum_events_2026-11-02.md) section 6; [IRDD](IRDD_integer_recovering_datum_rows_2026-11-03.md) sections 2 to 4

**Outcome.** Pre-registered; no graded run yet. Question: do chord integers decided ring by ring from the chain's root, held in the network's solve and released at every event, take only right integers, and how far do they bring the stream towards the level the truth-fed chain reached (card IRDU section 12.1)? The decision rule, the damage gate, the hold, the release causes, the audit and the bars of stage N1 are frozen in sections 4 and 5 before any graded run. Standing: built default off on branch `irdu/user-integers`; N1 runs next.

## 1. The author's words and the assignment

The author's two messages, verbatim, as relayed by the requesting session:

- "Build the safe ring-by-ring fixing on the simulator. Integer fixing in the network is no longer "do not build", in fact, it seems like the current bottleneck we need immediately!"
- "Continue to manage Opus to work on the integer network and our ring method, sim, then observed data, expand to multi-system, multi-frequency if everything works."

The assignment as relayed (a reading of the requesting session, not the author's words): top priority for the night, ahead of the users' rule of card IRDU section 15 (its runs wait) and in place of the queued all-integers run on r3c, which becomes the truth-fed control of N2. Stages N1 to N3 in order; a report at the end of N1. Limits in section 8.

## 2. Why the do-not-build verdict no longer stands for this work

The verdict of 2026-10-07, "producer network AR: do not build", is lifted by the author for this program. Card FCFC section 9 gave the reasons a held producer solve added little: the zero-q float already integrates the whole arc, so conditioning on integers moves the shared parameters only by cross terms; the emitted phase biases were not integer-recovering on the datum then armed (several anchors, float pin targets, no receiver phase-bias states); and the releases cost too much (collateral releases, coverage, a slip no detector saw held for 63 epochs).

Card IRDU section 12 measured the eq34 chain, which differs on each count:

1. **The chain is integer-recovering.** Its tree links are pinned at integer targets, the root receiver's phase bias is pinned and every receiver carries phase-bias states. With every link at its true integer the stream reaches the truth stream's level at every depth: D_NL p50 0.016 to 0.030 cycle at 15 to 30 min against 0.080 to 0.184 cycle without (12.1). On this datum integers move the stream, and here they act through the solve itself, not through a detached second solve that only the emission reads (card FCF's design).
2. **A ring reaches the root's level once its own ring is held**, in 15 to 45 min (12.3).
3. **Re-seats onto links at their integers are free.** The frame is kept and the moved pairs cost nothing after 1 to 5.5 min, against 25 to 45 min of wide-lane cost without (12.5, Q4). The release cost card FCF measured belongs to the release of floats, which held links remove.
4. **Two decision rules made 0 wrong fixes, log-only**, at every stage of the bed without re-seats: the network's search (30 978 kept row-epochs per band, 0 wrong) and a gated rounding (formal sigma at most 0.10 cycle, fraction at most 0.20; 0 wrong at every time and stage) (12.5).

The constraints of card ARL's section of 2026-10-24 stand and are kept here. The fix is the network's, never per station. No tree (pivot) ambiguity is searched or held: the tree links are the frame. An event that changes the frame invalidates the integers it moves: here every frame-changing chain event releases the links it touches (section 4.3). The 14.48 % wrong fixes at a reported success rate of 1.0 came from a covariance blind to the carry; card IRDC section 6 found wrong certifications only on damaged floats. The gate below therefore reads damage and persistence, not sigma alone, and every held integer is audited against truth at every epoch.

## 3. Steps of card IRD served, and the bars reused

- **IRD-5** (certification from the network's own integers): here the chords are certified ring by ring, and IRD-5's "0 wrong lattice-sourced targets" becomes 0 wrong held integers against truth.
- **IRD-8** (the consumer proof): K-a (0 wrong among at least 1 000 settled determined integers per held-out station on each 2 h bed; on the 6 h bed a 95 % Wilson upper bound below 3e-4), K-b, K-c, P-a to P-c, applied at N3. At N1 and N2 the user readings are K-a's zero and the float position by bin.
- **Card ARL's rungs:** 0 wrong on every rung; N2's event beds include the slip rungs for which a fixture exists.
- **The stream bars** W-WL and W-NL (card IRD section 9), per depth class, as read in card IRDU section 12.1.

## 4. The build (default off; byte-identical when off)

**Keys** (three; ledger rows UNVALIDATED; the numbers of the rule are constants of the code, frozen here, not keys):

- `network.ring_fix.enable` (default false): the mechanism.
- `network.ring_fix.rule` (default `gated`): `gated` is the rule of 4.1; `plain` is the negative control only (every candidate rounded: no sigma, fraction, damage or persistence test).
- `network.ring_fix.audit_frame_file` (default empty; simulation only): a frame-target file (`scripts/irdu_frame_targets.py --all`: station, satellite, signal, frame integer, role) against which every held integer is audited each epoch.

The loader refuses `enable` without the eq34 chain and `network.trace_chain_datum` (the chain record the rings are read from), and refuses an audit file that does not exist. Without `enable` no object is built and no branch is reachable.

### 4.1 Decide (frozen)

- **Links.** A link is a (station, satellite) arc of a pair family (band 1 and band 2 of a constellation, as in the chord table of `network_chain_frame.csv`) that is a chord of both bands' trees this epoch. Tree links are never decided or held: they are the frame.
- **Rings.** On the band-1 tree, the root receiver has depth 0. A link's ring is the larger depth of its two vertices; its inner vertex is the one of smaller depth.
- **Candidates, ring by ring.** A ring-2 link is always a candidate (its inner vertex, a satellite at depth 1, reaches the root through one tree link). A link of ring 3 or more is a candidate when every link of its inner vertex to a vertex of smaller depth than the inner vertex is held: tree links count as held, chords count when this mechanism holds them.
- **The gate** (card IRDU 12.4 (b), as measured there): from the link's two-band float f1, f2 (cycles) and its 2x2 conditional covariance (cycles squared, unscaled; the chord table's quantities), the wide lane is rounded first, z = round(f1 - f2); the ionosphere-free row with the wide lane rounded gives n = (F1 f1 - F2 f2 - F2 z) / (F1 - F2), N1 = round(n), N2 = N1 - z. The link passes when the formal sigma of n is at most **0.10 cycle** and |n - N1| is at most **0.20 cycle**.
- **The damage gate.**
  - Event window, **600 s**: both bands' carried entries exist and their last re-level (the carry's own stamp: birth, a slip re-level, a drop, an erase and rebirth) is at least 600 s old; neither band is in this epoch's free-epoch latch; the link has been a chord with a float at every epoch of the last 600 s (a gap above 45 s restarts the count); it has not been a tree link in either band within the last 600 s.
  - Consistency: the producer's lattice of fixed cycles, where it implies the link's integer on a band, agrees with the gate's integer (a disagreement refuses the link); and the link passed the gate with the same (N1, N2) at each of the last **10** epochs at which it was a candidate (any refusal restarts the count).
- **The decision** is taken after the solve of epoch t and held from epoch t + 1.

### 4.2 Hold

One diagonal prior row per band on the link's ambiguity column, at lambda_j N_j in metres, with **sigma 1e-4 m**, folded in PASS B by a station step of its own (the oracle pin's row and path: Λ = 1/sigma², η = Λ (lambda_j N_j - x_lin)). A tight prior, not an exact constraint: at this sigma Q1 put the truth-fed chain at the truth stream's level at every depth (12.1), and the posterior sits within about 1e-4 m of the held value; it stays two decades below the 1e10 datum pins, so the gauge remains the chain's; and a prior row leaves the solve's structure unchanged, so a release is the end of one row plus the vehicle's own drop. A link that the chain pins (a tree link) never takes the row.

### 4.3 Release (frozen)

At the epoch a cause is seen and before PASS B, the link's row ends and its carried entries are re-opened: under the float vehicle by its drop (restored variance the largest of the arc's birth variance, its first variance and the floors; `ambFloatDropFloored`), on the leveling vehicle by an erase. A released link is never held at a stale level, and it re-enters the decision only after the event window (the drop stamps the re-level). Causes:

1. **slip:** either band in this epoch's free-epoch latch (any detector: Melbourne-Wubbena, loss of lock, IF time difference, geometry-free jump, gap re-entry, wind-up restart).
2. **refloat:** either band's carried entry dropped or erased since the previous epoch by another mechanism (RAIM attribution T4, T3 or prior channel, the gap cliff, the gross line-of-sight screen), seen as a new re-level stamp or a missing entry.
3. **gap:** the link absent (no ambiguity column in a band) or no chord of its pair family for longer than `phase_leveling_max_gap_s` (900 s on these beds). Within that horizon the row pauses and the time-linked carry spans the gap, with the slip layer's re-entry test at the return.
4. **chain:** the link becomes a tree link in either band; a cut release (the returning, re-host, slip and merge rows) whose moved side holds either vertex of the link; a root handover, split or merge of its component (stage N1's conservative rule; N2 replaces it by section 4.4).
5. **monitor:** the link's post-fit ionosphere-free phase residual (its two bands' observation phase rows, metres) above **0.03 m** in absolute value at **4** consecutive epochs.

### 4.4 Re-seats (stage N2, not built for N1)

A re-host onto a held link keeps the frame (card IRDU Q4), so nothing is released. Elsewhere a cut moves its side by a step known exactly when the path is held (an integer), and the links crossing the cut are re-expressed by that step; where the path is not held, they are released. Built and pre-registered with N2.

### 4.5 Audit and records

- **Audit** (simulation only): every held link at every epoch against the frame-target file: wrong when either band differs; a held link the file does not list is counted unaudited. N1's bed keeps one tree for the whole run, so the file's integers hold for the whole run. N2 needs the frame integers of links that rise during the run, from truth and the tree of each epoch.
- **Run-end line:** decided, held (links at the end, link-epochs), released by cause, refused by cause (link-epochs), wrong against truth (decisions, held link-epochs), unaudited.
- **Events** (standing invariant 7, both edges with identities): `RINGFIX hold` at each decision and `RINGFIX release` with its cause, in `network_events.csv`.
- **Trace** `network_ring_fix.csv`: per epoch and link, ring, candidate, floats, n, sigma, fraction, the lattice integers, the state (refused and why, decided, held, released and why) and the audit.
- Doxygen, CMake, unit tests of the gate, the candidate rule, the hold bookkeeping and each release cause.

## 5. Stage N1: the bed without re-seats (pre-registered)

**Bed and base.** `irdu_nr` (the third cut of card IRDU section 11.1: one tree for the whole run, root S30000SIM, depth 5), 2 h, the adopted arm A1krhRsmh with the wet delay carried: the configuration of `_rap_irdu_zw_nr3`.

**Arms** (exe: this card's build, copied under its own name, sha256 stated with the results; Release only):

- **N1-0, off identity:** the new build with the key off reproduces `_rap_irdu_zw_nr3` (the plain chain arm) and `_rap_irdu_q1_nr3` (Q1, every link held at its true integer by the oracle pin) whole (`nom_td_gate.py --whole --mask-time`). These two runs are the controls.
- **N1-G:** the plain chain arm with `network.ring_fix.enable` and the audit file `config/sim/irdu/fpin_nr3_all.csv`. Smoke first (10 epochs).
- **N1-P, negative control:** N1-G with `network.ring_fix.rule` `plain`.

**Readings.**

- Links held by ring against time: first hold per ring, the ring complete (every chord of the ring held), held at 30, 60, 90 and 120 min.
- Releases by cause and refusals by cause.
- Feedback: links held on N1-G against the log-only counts on the plain arm (the search's kept rows and the gated rounding's acceptances of card IRDU 12.5 (a) and (b)), and the would-be acceptances on N1-G's own chord table.
- The stream against truth by depth class in 15 min bins (D_WL, D_NL per-pair offsets), N1-G against the plain arm and Q1; card IRD's W-WL and W-NL over hour 2.
- Users (the five of card IRDU, the users' build of this branch): started at 30 min, plus one row started with the network; float 3D by 15 min bins; fixing users HELD and WRONG; on N1-G's stream against the plain arm's and Q1's.

**Bars.**

- **N1-B0:** N1-0 IDENTICAL on both controls.
- **N1-B1:** N1-G holds 0 wrong integers against truth, at every epoch of every held link, with the decided links and held link-epochs stated.
- **N1-B2:** the negative control's audit counts wrong held integers (more than 0). If plain rounding takes none, the control is void and is reported so.
- **N1-B3:** every release names its cause and link; holds and releases are written at both edges; decided minus released equals held at the end.
- **N1-B4:** N1-G emits 240 of 240 epochs.

**Prediction** (written before the runs). On this quiet bed nothing slips and nothing re-seats, so releases come only from the monitor or RAIM, and few or none are expected. The gate accepts few ring-2 links before 60 min (card IRDU 12.5 (b): 3 of 27 at 60 min on the plain arm), so N1-G holds a few links by 60 min and more in hour 2 as held rings tighten the next ring's floats (12.5 (b): 10, 5 and 28 accepted at 60 min once the previous rings were held). The stream moves towards Q1's level only at the depths whose rings are held, so most of the gain, if any, is in hour 2; a 2 h run may hold too few links to move the stream much, which is a reading, not a failure. N1-P takes wrong integers in its first minutes (plain rounding at 30 min took 12 wrong of 186 in 12.3).

**Decision after N1.** N2 is built and pre-registered only if N1-B0 to N1-B4 hold. The report goes to the requesting session at the end of N1.

## 6. Stages N2 and N3 (outline; each is pre-registered in detail before it runs)

- **N2:** r3c with its re-seats (section 4.4 built), and the event beds of card IRDU (a true slip, a returning satellite, a root handover, a split and merge). Control: the truth-fed run on r3c (the former queued all-integers run). Bars: 0 wrong holds; every slipped or cut link released at its epoch.
- **N3:** the 6 h simulator reference bed, with card IRD-8's K-a to K-e and P-a to P-c.
- **Observed data** only after N1 to N3 pass and are re-graded, and only when asked. Multi-system and multi-frequency after that, as the author's second message orders.

## 7. Decisions made in the author's absence, for review

1. A link's ring is the larger depth of its vertices (card IRDU section 12's definition); a link of ring 3 or more waits until its inner vertex's links towards the root are held.
2. The decision rule is the gated rounding of card IRDU 12.4 (b) at its 0.10 cycle gate, not the search's acceptance: it reads one link at a time, which is the ring order, and it was measured on these chord tables. The search's lattice enters only as a veto (a disagreement refuses).
3. The damage gate's numbers: a 600 s event window, a 45 s gap, 10 epochs of the same integers.
4. The hold is the oracle pin's prior row at sigma 1e-4 m, a tight prior rather than an exact constraint (reasons in 4.2).
5. The monitor reads the held link's post-fit ionosphere-free phase residual at 0.03 m for 4 epochs.
6. At N1 every frame-changing chain event releases the links it touches in its component; the exact re-expression waits for N2.
7. The audit at N1 reads a frame-target file (one tree on the bed); N2 audits from truth and each epoch's tree.
8. Three keys; the rule's numbers are frozen constants of the code.
9. The users replay on this branch's build.

## 8. Limits

Simulator only until the author says otherwise. Nothing merged or pushed. No reference configuration and no ledger verdict changed; the new keys are default off with UNVALIDATED rows. Every decision above is listed for the author's review. The runs, commits and numbers are reported so each can be re-graded.

<!-- Results are appended below this line under dated headings. -->

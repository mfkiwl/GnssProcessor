# NRF part 4: stage O2, integers held on observed data (sections 21 onwards of card NRF)

**STATUS**

- **id:** NRF-part4
- **topic:** network-vehicle
- **status:** open
- **summary:** Sections 21 onwards of card NRF (2026-11-15). Section 21: stage O2 pre-registered, the first runs that hold integers on observed data (Galileo L1X/L5X, the bed of DOY 144, two starts, the odds computed with one and with two times the formal sigma), with the build it needs: `network.ring_fix.sigma_scale` and the wind-up arc trace `network.trace_windup_arcs`, which lets the two-start audit cover every common arc.
- **source:** [NRF part 3](NRF_network_ring_fixing_2026-11-14_part3.md) sections 19 and 20; the requesting session's messages of 2026-11-15 (its log-only pilot on the same bed, exe nrf7, four starts)

**Outcome.** Question: on observed data, does the ring fix hold only integers that two runs with different starts agree on, with every epoch emitted and no RAIM excess? Pre-registered: Galileo L1X/L5X held by the rule as built and with the odds computed at twice the formal sigma, each from two starts an hour apart; the bar is a two-start audit with 0 failing checks over every common arc, the wind-up branches removed from a new trace of the stations' accumulators. Standing: default off; pre-registered, runs pending.

Sections 1 to 12 are in [NRF](NRF_network_ring_fixing_2026-11-14.md), 13 to 16.1 in [part 2](NRF_network_ring_fixing_2026-11-14_part2.md), 17 to 20 in [part 3](NRF_network_ring_fixing_2026-11-14_part3.md). Results are appended below, each under its dated heading.

## 21. 2026-11-15: stage O2 pre-registered (integers held on observed data, Galileo L1X/L5X)

Assigned by the requesting session after its log-only pilot (its words condensed; decided in the author's absence and listed for review). The go for holding runs on observed data is its word.

**Why, from the pilot.** The requesting session ran the log rule on the bed of DOY 144 from four starts (0, +0.5, +1 and +2 h; exe nrf7) and audited the would-be integers between the six pairs of runs. Over every common arc the audit failed, mostly by one N1 cycle on both bands; with the arcs restricted to those both runs start together (section 19.5), the rule as built passes on Galileo L1X/L5X: 0 failing of 12 756 checks over all rings (0 of 4 457 with the odds at twice the formal sigma). Galileo L1C/L5Q: 6 failing of 8 770, all wide-lane cycles of one pair of runs (0 of 3 819 at twice the formal sigma). GPS: too few would-be decisions on common young arcs to judge. What stays real from the all-arc audit is the closures of size (3, 4) on L1X/L5X, a wide-lane cycle of E1/E5a that no wind-up branch can make: 41 over the six pairs with the rule as built, all in a young network's first hour on arcs alive at the later start, none with the odds at twice the formal sigma. The requesting session withdrew its interim reading (a ring cap, ring 2 only) once the branches were understood.

**Build (exe nrf9; default off, byte-identical off; ledger rows UNVALIDATED).**
1. `network.ring_fix.sigma_scale` (default 1; in [1, 100]; needs gate `odds`): the log-odds of N1 and of the wide lane are computed with this factor times their formal sigmas. The trace keeps the formal sigmas; the frozen sigma gate is unchanged.
2. `network.trace_windup_arcs` (default false): `network_windup_arcs.csv`, each station's wind-up accumulator per (station, satellite) arc: a row at the arc's start (the seed, or a restart after a gap) and a row at every epoch whose time of week is a multiple of 300 s, with the accumulated angle in cycles (an epoch observer, `network/diag/WindupArcs`; the accumulator itself gains a read-only arc-start stamp, GnssCorrections::windUpArcs). The producer starts an arc from the raw angle, in (-0.5, 0.5] cycle, so it holds no absolute branch to write; what two runs share is the angle itself: at an anchor epoch common to an arc in both runs, round(cycles_A - cycles_B) is the whole number of cycles between their integers of that arc, the same on every band, for the arc's whole common life. `scripts/nrf_two_run_audit.py --windup-trace` removes it link by link, so the audit covers every common arc that reaches an anchor in both runs.
3. Not built: the ring cap (withdrawn); keys for the 600 s event window and the 10-epoch persistence (asked in the first message, not repeated after the correction).

**Gates (simulation).** The new keys at their defaults: `nrf9_ol_nr3` against `nrf8_ol_nr3` and `nrf9_hf_r3c` against `nrf8_hf_r3c`, byte-identical. The trace checked against truth: held first on r3c from two starts with the trace on (`nrf9_hfw_r3c`, and `nrf9_hfw_r3cb` from `start_offset_hours` 0.504167 to the same end); per common link, round(cycles_A - cycles_B) equals the difference of the two runs' truth branches, and the audit with `--windup-trace` reads as it does with `--windup` (truth).

**Runs (Release, observed data: the bed of `_rap_nwa1nh_n144`; every arm with `network.trace_windup_arcs`; a 10-epoch smoke first).**
- `o2off_n144`: the key off. `o2off_n144b`: the key off from the later start (added here: the RAIM reference of the later start).
- `o2s2_n144`, `o2s2_n144b`: holding; rule gated, order certain, gate odds, `sigma_scale` 2, `wl_frac_max` 0.25, `held_first` true, pairs `["E:L1X/L5X"]`; starts 0 and +1 h (`start_offset_hours` 1.004167, the same end).
- `o2s1_n144`, `o2s1_n144b`: the same with `sigma_scale` 1 (the rule as pre-registered).
- `nrf9_log_n144`: the log rule, pairs `["E:L1X/L5X"]`, `wl_frac_max` 0.25, start 0; **gate: products byte-identical to `o2off_n144`**.

**Bars (frozen, the requesting session's).**
1. The two-start audit on held integers and tree pins, with the wind-up branches removed (`--windup-trace`): 0 failing checks for each pair (`o2s2`, `o2s1`), reported with the sizes of any failing closure; the audit on the arcs both runs start together (`--born-after`) beside it.
2. Every epoch emitted.
3. Every release named.
4. RAIM rows not above the key-off run's by more than a tenth (each start against the key-off run of that start).
5. Every release by the residual monitor listed with its link and time.

**Reads.** Held share by hour and by ring (held link-epochs over the pair family's chord link-epochs); decisions and releases by cause; re-attachments through held links; minutes from an arc's birth to its hold (`scripts/nrf_hold_reads.py`, new). A failure is traced, not explained away.

**Known limits.** An error both runs share passes the audit; the wide-lane bound is the guard there, and a slip of equal cycles on both bands does not move the wide lane (section 20.2), the residual monitor is its guard. An arc whose common life in the two runs holds no anchor epoch is not audited (counted). No truth on observed data; no users in O2.

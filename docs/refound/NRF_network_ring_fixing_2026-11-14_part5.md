# NRF part 5: the formal-sigma pairs with the bad-epoch response on (sections 27 onwards of card NRF)

**STATUS**

- **id:** NRF-part5
- **topic:** network-vehicle
- **status:** open
- **summary:** Sections 27 onwards of card NRF (2026-11-15). Section 27: stage O2's formal-sigma pairs (Galileo L1X/L5X held on DOY 144 with the odds at the formal sigma) re-run with the bad-epoch response of card BER on, pre-registered, with the bars of stage O2 unchanged; a holding run with the response on is added for the user replays.
- **source:** [NRF part 4](NRF_network_ring_fixing_2026-11-14_part4.md) sections 21 to 23 (stage O2, its bars and the formal-sigma failures); [BER](BER_bad_epoch_response_2026-11-15.md) (the response, `network.amb_float_drop_jump_k`); the requesting session's review of 2026-11-15

**Outcome.** Question: the formal-sigma runs of stage O2 failed the agreement audit (13 008 of 151 698 checks between two reference receivers, 13 344 of 92 547 between two starts), and the requesting session traced 13 of the 18 departing links to wet-delay recoveries after slips at CPVG00CPV (TOW 3990) and MRO100AUS (TOW 7800). Card BER's response removes the spread of the MRO100AUS slip. With it on, do the formal-sigma pairs agree, with every epoch emitted and no RAIM excess? Pre-registered; results pending.

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

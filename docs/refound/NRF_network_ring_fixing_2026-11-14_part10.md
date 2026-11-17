# NRF part 10: the adopted posture over whole days (sections 83 onwards of card NRF)

**STATUS**

- **id:** NRF-part10
- **topic:** network-vehicle
- **status:** open
- **summary:** Sections 83 onwards of card NRF (2026-11-16), continued from [part 9](NRF_network_ring_fixing_2026-11-14_part9.md). Section 83 pre-registers the first 24 h runs of the adopted chain posture with network integer fixing: DOY 146 from the day's start, a second run from another datum receiver for the two-run audit over the whole day, then DOY 147 (the requesting session's order M).
- **source:** [part 9](NRF_network_ring_fixing_2026-11-14_part9.md) sections 74, 79 to 82; the requesting session's overnight order M (the author's plan: confirm the time-tag repair, check another day, run one 24 h day).

**Outcome.** Pre-registered: the adopted configuration of section 74 run for a whole day on DOY 146 and DOY 147, the first runs of that length in the chain posture with fixing, graded by hour over the 24 h against bars on the emitted epochs, the families' held shares from hour 3, the RAIM rows per hour and a two-run audit over the day.

## 83. 2026-11-16: the adopted posture over 24 h, DOY 146 and 147 (pre-registered)

**Why** (the requesting session's order M, the author's overnight plan): one 24 h network run of a new day, which serves as another day in its first six hours and as the full day, with its stream for the users (started with the network and joining every two hours).

**The arms** (exe nrf32 `cf0816d6d26139ea`, commit 72f594a). `d24_n146`: `f13`'s configuration (section 74, every adopted row armed) on DOY 146 from the day's start for 24 h: the 56 RINEX paths and the observation path moved to DOY 146 (all on disk), `data_download.doy` 146, `processing.max_duration_s` and `network.max_duration_s` 86 400; the products resolved from the day as on DOY 144 and 145; the roster's coordinates the same IGS means. `processing.exact_epoch_time` off: section 81's reads did not all pass the bar of a tenth (Galileo X/X's drift share on DOY 145). `d24r_n146`: `d24_n146` from the datum receiver WTZR00DEU. `d24_n147`: the same on DOY 147, started when the DOY 146 pair ends, no second run. A 10-epoch smoke first (`d24smoke`, exit 0); its posture table reads as `f13`'s: ON tier 22 of 23 and SCOPED tier 68 of 70 armed, the same rows off as on `f13` (`network.emit_pb_hold` and `network.trace_dd_fractional_ref` by design, and the vehicle's held-basis row), every row adopted in section 74 armed. Resources at 2.4 h into the day: 13.7 GB of memory per run, flat over the next hour of data; the traces 318 MB per run (about 3 GB over the day, the largest the postfit rows, about 0.7 GB), so no trace is cut.

**Bars.** Every epoch emitted; from hour 3 on, the held share of GPS L1C/L2W and Galileo L1X/L5X not below 80 % and of Galileo L1C/L5Q not below 65 % in any hour; no hour with more than 5 RAIM rows; the two runs of DOY 146 fail 0 checks of the same-start audit over the day. Reported by hour over the 24 h (`_irdu_grades/scripts_s20/d24_hourly.py`): held and flagged shares per family, releases, slips, gap events, RAIM rows, withheld epochs, decisions per epoch against the cap of 12, the datum receiver of each band's trees and every change of it; with the segment drift of the flagged runs and rule L's changes of identity.

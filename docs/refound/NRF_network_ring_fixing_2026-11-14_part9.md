# NRF part 9: the Galileo C/Q levels after the adoption (sections 75 onwards of card NRF)

**STATUS**

- **id:** NRF-part9
- **topic:** network-vehicle
- **status:** open
- **summary:** Sections 75 onwards of card NRF (2026-11-16), continued from [part 8](NRF_network_ring_fixing_2026-11-14_part8.md). Section 75: the trace of Galileo C/Q's moving flagged levels on DOY 144 continued (section 73's next read): each satellite's C/Q-only drift correlates with the mapping function of the C/Q receivers that tie it but with signs that change from satellite to satellite, and the C/Q receivers' traced wet delays behave as the X/X receivers' do (a C/Q and an X/X receiver 4 m apart agree within 0.009 m), so a wet-delay error of the C/Q sub-network is not the cause; the cause is still not traced.
- **source:** [part 8](NRF_network_ring_fixing_2026-11-14_part8.md) sections 68.1, 73 and 74; the requesting session's order after its adoption verdict (the trace of the C/Q levels, then the cascade on the simulator).

**Outcome.** The trace of Galileo C/Q's moving flagged levels on DOY 144 rules out the wet delay of the C/Q receivers: their estimated wet delays spread as the X/X receivers' do, and a C/Q and an X/X receiver 4 m apart agree within a centimetre over the day. The per-satellite drift is real (C/Q against the same satellites' X/X, 0.24 narrow-lane cycle at the median) and its correlation with the tying receivers' mapping function is not specific. Open candidates: the C/Q receivers' antenna models for Galileo and the family's lower held share.

## 75. 2026-11-16: Galileo C/Q's moving levels on DOY 144: not the wet delay (a read)

**Why** (section 73's next read; the requesting session's order after its adoption verdict, the trace before the cascade): what the C/Q sub-network's receivers put into the C/Q satellite phase biases that the X/X receivers do not, first their wet delay against each satellite's elevation.

**How.** (1) `_irdu_grades/scripts_s20/cq_trace2.py` on `g13_n144` and `g13_n145`, hours 1 to 6: per satellite, D = its C/Q level less its X/X level (each against its family's median step, narrow-lane cycles) over its longest run of constant counters in both families, regressed on m, the mean of 1 / sin(elevation) over the C/Q receivers that tie it at each epoch (elevations from `network_slip_raw.csv`). (2) `g13z_n144`, `g13_n144` with `network.trace_zwd` (a trace key: its products equal `g13_n144`'s byte for byte), and `_irdu_grades/scripts_s20/cq_trace3.py`: receivers of one site, the wet delay by family, and the receivers that tie the most-moving satellites. Grades `_irdu_grades/nrf_cq_trace2.txt`, `nrf_cq_trace3.txt`.

**Results.**
- **The mapping function** (DOY 144): per satellite the slope of D on m is large, 16 to 53 mm at the zenith in either direction, with |correlation| median 0.63; but its sign changes from satellite to satellite (median slope -0.6 mm, p10 -34, p90 +40). On DOY 145 the slopes are small (p10 -9 mm, p90 +15) and |correlation| median 0.30. One zenith error common to the C/Q receivers would give one sign.
- **The wet delay as estimated** (DOY 144): GOP600CZE (C/Q) and GOPE00CZE (X/X), 4 m apart, differ by at most 0.009 m over hours 1 to 6 (first to last +0.002 m); WTZR00DEU and WTZS00DEU (both C/Q), 69 m apart, by at most 0.016 m. The 27 C/Q receivers' wet delays range p50 0.020 m and p90 0.034 m over the window, the 28 X/X receivers' 0.023 and 0.042 m; first to last p50 0.007 m in both. The receivers that tie the most-moving satellites (E04, E06, E09, E13, E21, E23, E36) move their wet delay by 0.3 to 2.4 cm.

**Reading.** The C/Q receivers' wet delays behave as their neighbours' do, so a wet-delay error of the C/Q sub-network is not what moves the C/Q satellite biases on DOY 144. The per-satellite correlation with the mapping function is not specific: a smooth drift correlates with any smooth function of time. The cause is not traced. Two candidates remain to be read: the antenna models of the C/Q receivers on Galileo (mostly Septentrio; an antenna without Galileo calibrations takes the GPS band of its frequency), and the family's lower held share on DOY 144 (71 to 74 % against 84 to 89 % for X/X, section 68.1), which leaves more of its satellites' biases float.

### 75.1 2026-11-16: the antenna models: seven receivers take Galileo E5a from GPS L2

From `g13_n144`'s setup lines (the receiver ATX source): seven roster receivers have no Galileo calibration in `igs20.atx` and take the cross-system fallback, Galileo band 1 from G01 and band 5 from G02 (GPS L2, 1227.60 MHz, standing for E5a at 1176.45 MHz, since these antennas carry no L5 calibration either): CHUR00CAN, JPLM00USA, PARK00AUS and STJO00CAN in the C/Q family, KOKV00USA, SVTL00RUS and SYOG00ATA in the X/X family. Both families have them (4 of 27 against 3 of 28), so they do not separate C/Q from X/X by count; but STJO00CAN, CHUR00CAN and JPLM00USA are among the receivers that tie the most-moving C/Q satellites (E06, E09, E23), and an L2 pattern standing for E5a puts an elevation-dependent error into the ionosphere-free phase of those links. A candidate, not a cause: the test is the C/Q drift with those four receivers left out of the C/Q family (or with an E5a calibration where one exists).

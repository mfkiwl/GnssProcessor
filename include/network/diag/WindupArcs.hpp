/**
 * @file WindupArcs.hpp
 * @brief The stations' wind-up accumulators, traced per arc
 *        (@c network.trace_windup_arcs -> @c network_windup_arcs.csv).
 *
 * In accumulated mode each station's corrections start a (station, satellite) arc from the raw
 * wind-up angle, in (-0.5, 0.5] cycle, and unwrap it epoch to epoch
 * (GnssCorrections::computePhaseWindUp).  Two runs that start the same arc at different epochs
 * (two start times, a station that joins later) therefore apply the same angle up to a whole
 * number of cycles, the same on every signal, and their integer ambiguities of that arc differ
 * by that number.  A comparison of two runs' integers must remove it; this trace gives it.
 *
 * One row at each arc's start (kind @c start: the seed or a restart after a gap) and one row
 * per arc at every epoch whose time of week is a multiple of @ref kWindupArcAnchorS (kind
 * @c anchor), with the accumulated angle after that epoch.  At an anchor epoch common to an
 * arc in two runs, round(cycles_A - cycles_B) is the whole number of cycles between them, and
 * it holds for the whole common life of the arc (the two runs unwrap the same angles).
 *
 * Measure-only: it reads the accumulators (GnssCorrections::windUpArcs) after the epoch and
 * writes nothing back.  Off by default: no stream, no file, and the solve is byte-identical.
 * Empty in fractional wind-up mode (no accumulator).
 */
#pragma once

#include "network/driver/RunTypes.hpp"

namespace GnssProcessor {

/// The anchor period of @c network_windup_arcs.csv (s of the time of week).
inline constexpr double kWindupArcAnchorS = 300.0;

/**
 * @brief Writes the epoch's rows of @c network_windup_arcs.csv: each (station, satellite)
 *        accumulator that started an arc at this epoch, and at an anchor epoch every
 *        accumulator updated at this epoch.
 *
 * Columns: week, tow, station, sat, kind (@c start or @c anchor), cycles (the accumulated
 * wind-up after the epoch), start_tow (the arc's start, in seconds of this epoch's week).  A
 * start at an anchor epoch writes both rows.
 *
 * @param run The run: the stations' models (read) and the trace stream (written).
 * @param ep  The epoch, read only (its time).
 */
void networkWindupArcsTrace(NetworkRun& run, const NetworkEpoch& ep);

}  // namespace GnssProcessor

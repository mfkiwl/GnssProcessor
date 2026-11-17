#pragma once
/**
 * @file PhaseVisibleStepTest.hpp
 * @brief The phase-bias step declaration on what a user sees (@c network.disc_phase_visible).
 *
 * ## What it tests
 *
 * The emitter's legacy value test declares a phase-bias step of a (satellite, signal) when
 * the emitted phase bias P alone moves by more than the threshold between two emissions.
 * A user's phase reads the satellite through its clock and its phase bias together, the
 * phase-visible correction C - P, and in a between-satellite difference it reads that
 * correction less the reference satellite's.  The network moves two quantities that the
 * user's phase does not see: the split between a satellite's clock
 * and its phase biases (C and P move together, C - P stays) and the network's phase level
 * (every satellite's C - P of a signal moves alike, and the move cancels between
 * satellites).  This test declares a step when what a user of between-satellite
 * differences sees moves:
 *
 *     d_k   = change of (C - P) of key k since its last emission
 *     m_g   = median of d_k over the voting keys of group g (one constellation, one signal)
 *     step  = |d_k - m_g| > bar_k        (bar_k: discfrac x wavelength, or the flat gate)
 *
 * ## The median
 *
 * A key votes when its change is defined (a fresh baseline: an earlier emission with a
 * clock, within the staleness horizon, and no forced mark this epoch) and its baseline is
 * the previous emission of the stream (consecutive epochs).  The median of an odd count is
 * the middle value; of an even count, the mean of the two middle values.  With at least
 * @c min_sats voters the group is tested against its median.  Below that count the median
 * is not formed and each key is tested on its own change d_k: the shared part is then
 * declared with the rest, the safe side.
 *
 * ## Whom the declaration protects
 *
 * A user that differences between satellites the stream corrects: the shared part cancels
 * in its differences, so the test does not declare it.  A user that pairs a corrected
 * satellite with one the stream does not correct reads the shared
 * part as a between-satellite move and carries it undeclared; the consumer's rule
 * @c network.closed_loop.drop_unrecorded keeps such satellites out of its differences.  The
 * stream header states the assumption (the @c discpv= token).
 *
 * A pair's difference can move by up to twice the bar with neither satellite declared (two
 * satellites moving apart by just under the bar each), as under the legacy test.
 *
 * Pure: the function holds no state and reads only its arguments.
 */

#include <string>
#include <vector>

namespace GnssProcessor {

/// Minimum number of voting satellites of a (constellation, signal) for the median to be
/// formed.  Travels in the stream header as the value of the @c discpv= token.
constexpr int kPhaseVisibleMinSats = 4;

/**
 * @brief One (satellite, signal) key of an epoch, as the phase-visible step test reads it.
 */
struct PhaseVisibleKey {
    std::string sat;               ///< Satellite id, e.g. "G05".
    std::string signal;            ///< Phase signal, e.g. "L1C".
    char        constellation{0};  ///< RINEX constellation letter: the group is (constellation, signal).
    bool        tested{false};     ///< The change is defined (fresh baseline with a clock, no forced mark).
    bool        votes{false};      ///< Tested and its baseline is the previous emission: its change enters the median.
    double      change_m{0.0};     ///< Change of the phase-visible correction C - P since the baseline (m).
    double      bar_m{0.0};        ///< Declaration threshold of the key (m).
};

/**
 * @brief The test's verdict for one key (same order as the input).
 */
struct PhaseVisibleVerdict {
    bool   step{false};          ///< Declare a step: the key's discontinuity counter bumps.
    bool   tested{false};        ///< The key was tested (copied from the input).
    bool   median_basis{false};  ///< Tested against its group's median (false: below the minimum count).
    double median_m{0.0};        ///< The group's median change (0 below the minimum count).
    double deviation_m{0.0};     ///< The tested quantity: change less the median, or the change itself.
};

/**
 * @brief Run-end counters of the phase-visible step test.
 */
struct PhaseVisibleCounters {
    long long groups{0};              ///< Group-epochs with at least one tested key.
    long long groups_median{0};       ///< Of those, tested against a median (at least the minimum count of voters).
    long long groups_below_min{0};    ///< Of those, below the minimum count: keys tested on their own change.
    long long keys_tested{0};         ///< Keys tested.
    long long keys_stepped{0};        ///< Keys declared.
    long long keys_stepped_below_min{0};  ///< Of those, declared in a group below the minimum count.
    long long shared_over_bar{0};     ///< Group-epochs whose median moved by more than the group's smallest bar
                                      ///< (a step a user that does not difference would have needed).
    double    max_abs_median_m{0.0};  ///< Largest |median| seen (m).
};

/**
 * @brief The median of a list of values: the middle value, or the mean of the two middle
 *        values for an even count.
 * @param v The values (copied; empty gives 0).
 * @return The median.
 */
double phaseVisibleMedian(std::vector<double> v);

/**
 * @brief Decide which keys of one epoch declare a phase step on what a user sees.
 *
 * Groups the keys by (constellation, signal).  In a group with at least @p min_sats voting
 * keys, every tested key is declared when its change less the group's median exceeds its
 * bar; in a smaller group, when its change itself exceeds its bar.  An untested key is never
 * declared here (a first record, a return past the staleness horizon, a forced mark, a key
 * without a clock: the caller decides those).
 *
 * @param keys      The epoch's keys.
 * @param min_sats  Minimum number of voters for the median (>= 1).
 * @param counters  Optional run-end counters to add this epoch to.
 * @return One verdict per key, in the order of @p keys.
 */
std::vector<PhaseVisibleVerdict> decidePhaseVisibleSteps(const std::vector<PhaseVisibleKey>& keys,
                                                         int min_sats,
                                                         PhaseVisibleCounters* counters = nullptr);

} // namespace GnssProcessor

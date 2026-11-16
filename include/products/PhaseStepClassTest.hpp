#pragma once
/**
 * @file PhaseStepClassTest.hpp
 * @brief The phase-bias step declaration by the class of the step a user sees
 *        (@c network.disc_step_class_pairs).
 *
 * ## What it declares
 *
 * The stream re-defines a satellite signal's phase level whenever the network's chain moves
 * it: a cut release, a re-pin, a re-host onto another arc.  A user that holds the satellite's
 * ambiguities sees the move as a step of the level its phase reads.  This test classifies
 * each satellite's step on one pair of signals (a family: two phase signals on two bands and
 * their two code signals) and declares the signals that stepped, so that each of them carries
 * a discontinuity-counter increment at that epoch, and no increment is raised for a move the
 * user's own states absorb.
 *
 * ## The level and its step
 *
 * Per satellite and emission, with C the satellite clock, P_b the phase bias and B_b the code
 * bias of band b (metres), lambda_b the wavelength and gamma = (f1 / f2)^2:
 *
 *     x   = ((C - B_1) - (C - B_2)) / (1 - gamma)             the code-defined ionosphere term
 *     E_1 = (C - P_1 + x) / lambda_1,   E_2 = (C - P_2 + gamma x) / lambda_2     (cycles)
 *
 * The change of E_b since the previous emission, less its median over the satellites of the
 * family (the clock datum, which cancels between satellites), is the satellite's own step
 * (x_1, x_2); its ionosphere-free part in narrow-lane cycles is
 * dn = (f1 x_1 - f2 x_2) / (f1 - f2).  Classes, with tol in cycles:
 *
 *     quiet      |x_1| and |x_2| under tol                          nothing declared
 *     whole      both within tol of whole numbers, not both zero    the bands with a non-zero
 *                                                                   whole number declared
 *     iono-like  not whole, |dn| under tol                          nothing declared: the user's
 *                                                                   slant ionosphere absorbs it
 *     fraction   everything else                                    the bands whose |x_b| reaches
 *                                                                   tol declared
 *
 * These are the classes of the stream-step read the requesting session uses
 * (`stream_jumps.py`), so a stream under the test can be checked against it step by step.
 *
 * ## The median
 *
 * A satellite is tested when both emissions are defined (clock, both phase biases and both
 * code biases) and the earlier one is the previous emission of the stream.  The median of an
 * odd count is the middle value, of an even count the mean of the two middle values
 * (@ref phaseVisibleMedian).  With fewer than @c min_sats tested satellites in the family the
 * epoch is not classified there: no satellite of that family is tested, and the caller keeps
 * its other test for those keys.
 *
 * Pure: the function holds no state and reads only its arguments.
 */

#include <string>
#include <vector>

namespace GnssProcessor {

/// Minimum number of tested satellites of a family for the median to be formed (the stream
/// read's own minimum).
constexpr int kStepClassMinSats = 4;

/**
 * @brief The class of one satellite's step on one family.
 */
enum class StepClass {
    Untested,  ///< Not classified (no defined change, or the family below the minimum count).
    Quiet,     ///< Both bands under the tolerance.
    Whole,     ///< Both bands within the tolerance of whole numbers, not both zero: a re-pin.
    IonoLike,  ///< Not whole, ionosphere-free part under the tolerance: absorbed by the user's ionosphere.
    Fraction   ///< Everything else: the ionosphere-free level moves by a part of a cycle.
};

/**
 * @brief One satellite of one family at one emission, as the test reads it.
 */
struct StepClassSat {
    std::string sat;          ///< Satellite id, e.g. "E18".
    bool        tested{false};///< Both emissions defined and the earlier one is the previous emission.
    double      d1_cyc{0.0};  ///< Change of E_1 since the previous emission (cycles of band 1).
    double      d2_cyc{0.0};  ///< Change of E_2 since the previous emission (cycles of band 2).
};

/**
 * @brief The test's verdict for one satellite (same order as the input).
 */
struct StepClassVerdict {
    StepClass cls{StepClass::Untested};  ///< The class of the step.
    bool      step1{false};              ///< Declare band 1's signal.
    bool      step2{false};              ///< Declare band 2's signal.
    double    x1_cyc{0.0};               ///< Band 1's step less the family's median (cycles).
    double    x2_cyc{0.0};               ///< Band 2's step less the family's median (cycles).
    double    dn_cyc{0.0};               ///< Ionosphere-free part of the step (narrow-lane cycles).
};

/**
 * @brief Run-end counters of the step-class test.
 */
struct StepClassCounters {
    long long families{0};          ///< Family-epochs with at least one tested satellite.
    long long families_below_min{0};///< Of those, below the minimum count (not classified).
    long long sats_tested{0};       ///< Satellite-family-epochs classified.
    long long quiet{0};             ///< Of those, quiet.
    long long whole{0};             ///< Of those, whole.
    long long iono_like{0};         ///< Of those, ionosphere-like.
    long long fraction{0};          ///< Of those, fraction.
    long long signals_declared{0};  ///< Signals declared (a whole or fraction step's declared bands).
};

/**
 * @brief The levels E_1 and E_2 of one satellite on one family (cycles).
 * @param clock_m The satellite clock C (m).
 * @param p1_m    Band 1's phase bias (m).
 * @param p2_m    Band 2's phase bias (m).
 * @param b1_m    Band 1's code bias (m).
 * @param b2_m    Band 2's code bias (m).
 * @param f1_hz   Band 1's frequency (Hz).
 * @param f2_hz   Band 2's frequency (Hz).
 * @param e1_cyc  Written: E_1 (cycles of band 1).
 * @param e2_cyc  Written: E_2 (cycles of band 2).
 */
void stepClassLevels(double clock_m, double p1_m, double p2_m, double b1_m, double b2_m,
                     double f1_hz, double f2_hz, double& e1_cyc, double& e2_cyc);

/**
 * @brief Classify the steps of one family's satellites at one emission.
 *
 * With at least @p min_sats tested satellites, each tested satellite's change less the
 * family's median on each band is classified (quiet, whole, ionosphere-like, fraction) and
 * the bands to declare are set.  Below the minimum count, or for an untested satellite, the
 * verdict is @ref StepClass::Untested and nothing is declared.
 *
 * @param sats     The family's satellites at this emission.
 * @param f1_hz    Band 1's frequency (Hz).
 * @param f2_hz    Band 2's frequency (Hz).
 * @param tol_cyc  The tolerance (cycles, > 0).
 * @param min_sats Minimum number of tested satellites for the median (>= 1).
 * @param counters Optional run-end counters to add this family-epoch to.
 * @return One verdict per satellite, in the order of @p sats.
 */
std::vector<StepClassVerdict> classifyStepClasses(const std::vector<StepClassSat>& sats, double f1_hz,
                                                  double f2_hz, double tol_cyc, int min_sats,
                                                  StepClassCounters* counters = nullptr);

/**
 * @brief The name of a class, as the run-end report prints it.
 * @param c The class.
 * @return "untested", "quiet", "whole", "iono_like" or "fraction".
 */
const char* stepClassName(StepClass c);

} // namespace GnssProcessor

#pragma once
/**
 * @file UnrecordedSatGate.hpp
 * @brief The consumer's rule for satellites the network stream does not correct: such a satellite
 *        is left out of the solution while it lacks its stream records.
 *
 * A consumer of a network product stream corrects most of its satellites with the stream's clock
 * and biases.  A satellite the stream carries no clock record for keeps the a priori clock and no
 * bias, so a term the stream's corrections share (the network's phase level moving against its code
 * level) is, for the consumer, a difference between a corrected and an uncorrected satellite in
 * every single difference that pairs the two.  A satellite with the stream's clock and no phase-bias
 * record for a phase signal the receiver uses is not phase-corrected either: under the emission hold
 * in its phase-clock mode the clock less the phase bias is the constant of a generation and the clock
 * record alone wanders with the network's code-level clock.
 *
 * Two rules, each armed by its own key:
 *  - the clock rule (@c processing.ssr_drop_unrecorded, derived from
 *    @c network.closed_loop.drop_unrecorded): a satellite without a clock record is left out;
 *  - the phase-bias rule (@c processing.ssr_drop_unrecorded_phase_bias, derived from
 *    @c network.closed_loop.drop_unrecorded_phase_bias): a satellite without a clock record, or with
 *    one and without a phase-bias record for one of the phase signals the receiver uses for it, is
 *    left out (the whole satellite, also when only one of its signals lacks the record).
 *
 * This gate holds the decisions and their counters and nothing else: it is pure, so the edges are
 * unit-tested on hand-built epochs (tests/test_unrecorded_sat_gate.cpp).  The engine side
 * (@c RealTimeEngine::dropUnrecorded, RealTimeEnginePrepare.cpp) asks the store for each modelled
 * satellite's records with the freshness tests of the apply sites, erases the satellites the gate
 * leaves out and logs the events.
 *
 * Edges (standing invariant 7: an exclusion is an event at both edges).  A satellite seen without its
 * records, at its first sighting or when a record is lost, is a Drop, which names the missing record
 * (the clock, or the phase bias of a named signal); a dropped satellite whose records are all back is
 * a Readmit.  A dropped satellite that is out of view keeps its dropped mark, so its next sighting
 * without its records makes no second Drop, and with them it is a Readmit; a dropped satellite whose
 * missing record changes kind stays out without a second Drop.  At the Drop the model prunes the
 * satellite's ambiguity and ionosphere states, as for a satellite out of view; at the Readmit they are
 * seeded afresh, a new float, so nothing estimated without the stream's corrections enters the
 * stream's frame.
 */

#include <cstddef>
#include <set>
#include <string>
#include <utility>
#include <vector>

namespace GnssProcessor {

/**
 * @brief Decisions and counters of the rule for satellites without their stream records.
 */
class UnrecordedSatGate {
public:
    /// @brief The kind of an edge.
    enum class EventKind {
        Drop,     ///< A satellite seen without its records is left out (first sighting or record lost).
        Readmit   ///< A dropped satellite's records are all back: it is in the solution, its states afresh.
    };

    /// @brief Which of a satellite's stream records is missing at an epoch.
    enum class Missing {
        None,       ///< Every record the rule asks for is present: the satellite is kept.
        Clock,      ///< No clock record.
        PhaseBias   ///< A clock record, and no phase-bias record for a phase signal the receiver uses.
    };

    /**
     * @brief One satellite of an epoch as the engine sees it.
     */
    struct SatState {
        std::string sat;                      ///< The satellite ("E02").
        Missing     missing{ Missing::None }; ///< The missing record, or None.
        std::string signal;                   ///< PhaseBias only: the first phase signal without a record ("L5Q").
    };

    /**
     * @brief One edge of the rule, for the log and the tests.
     */
    struct Event {
        EventKind   kind{ EventKind::Drop };  ///< Drop or Readmit.
        std::string sat;                      ///< The satellite ("G12").
        bool        first_sighting{ false };  ///< Drop only: the satellite had never been seen with its records.
        Missing     missing{ Missing::None }; ///< Drop only: the record whose absence dropped it.
        std::string signal;                   ///< Drop for a missing phase bias only: the signal without a record.
    };

    /**
     * @brief Run counters (the run-end line).
     */
    struct Counters {
        std::size_t epochs{ 0 };               ///< Epochs the gate decided.
        std::size_t drops{ 0 };                ///< Drop events.
        std::size_t drops_first_sighting{ 0 }; ///< Of them, satellites never seen with their records.
        std::size_t drops_no_phase_bias{ 0 };  ///< Of them, dropped for a missing phase-bias record.
        std::size_t readmits{ 0 };             ///< Readmit events.
        std::size_t sat_epochs_out{ 0 };       ///< Satellite-epochs left out.
        std::size_t sat_epochs_out_no_phase_bias{ 0 };  ///< Of them, left out for a missing phase-bias record.
        std::size_t sat_epochs_seen{ 0 };      ///< Satellite-epochs decided (left out or kept).
    };

    /**
     * @brief Decide one epoch.
     *
     * @param sats      Each modelled satellite of the epoch with its missing record, if any (a
     *                  satellite listed twice is decided once, by its first entry).
     * @param[out] out  The satellites to leave out of this epoch's solution (cleared first).
     * @return The edges of this epoch, in the order of @p sats.
     */
    std::vector<Event> step(const std::vector<SatState>& sats, std::set<std::string>& out);

    /**
     * @brief Decide one epoch of the clock rule: each satellite with whether the stream holds a
     *        clock record for it (false is a missing clock).  Equivalent to the @ref SatState form.
     *
     * @param sats      Each modelled satellite of the epoch with whether it has a clock record.
     * @param[out] out  The satellites to leave out of this epoch's solution (cleared first).
     * @return The edges of this epoch, in the order of @p sats.
     */
    std::vector<Event> step(const std::vector<std::pair<std::string, bool>>& sats,
                            std::set<std::string>& out);

    /// @brief The run counters.
    /// @return The counters so far.
    const Counters& counters() const { return counters_; }

    /// @brief The satellites currently left out (dropped and not readmitted).
    /// @return The dropped set.
    const std::set<std::string>& dropped() const { return dropped_; }

private:
    std::set<std::string> dropped_;      ///< Left out, awaiting their records.
    std::set<std::string> ever_recorded_;///< Seen with their records at least once (a later loss is no first sighting).
    Counters              counters_;     ///< Run counters.
};

} // namespace GnssProcessor

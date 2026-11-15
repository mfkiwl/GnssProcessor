#pragma once
/**
 * @file UnrecordedSatGate.hpp
 * @brief The consumer's rule for satellites the network stream does not correct: such a satellite
 *        is left out of the solution while it has no stream record (card IRDU section 12.10).
 *
 * A consumer of a network product stream corrects most of its satellites with the stream's clock
 * and biases.  A satellite the stream carries no record for keeps the a priori clock and no bias,
 * so a term the stream's corrections share (the network's phase level moving against its code
 * level) is, for the consumer, a difference between a corrected and an uncorrected satellite in
 * every single difference that pairs the two.  Armed (@c processing.ssr_drop_unrecorded, derived
 * from @c network.closed_loop.drop_unrecorded), the engine leaves out every satellite without a
 * record, so no single difference mixes the two.
 *
 * This gate holds the decisions and their counters and nothing else: it is pure, so the edges are
 * unit-tested on hand-built epochs (tests/test_unrecorded_sat_gate.cpp).  The engine side
 * (@c RealTimeEngine::dropUnrecorded, RealTimeEnginePrepare.cpp) asks the store for each modelled
 * satellite's record, erases the satellites the gate leaves out and logs the events.
 *
 * Edges (standing invariant 7: an exclusion is an event at both edges).  A satellite seen without a
 * record, at its first sighting or when its record is lost, is a Drop; a dropped satellite whose
 * record returns is a Readmit.  A dropped satellite that is out of view keeps its dropped mark, so
 * its next sighting without a record makes no second Drop, and with a record it is a Readmit.  At
 * the Drop the model prunes the satellite's ambiguity and ionosphere states, as for a satellite out
 * of view; at the Readmit they are seeded afresh, a new float, so nothing estimated against the a
 * priori clock enters the stream's frame.
 */

#include <cstddef>
#include <set>
#include <string>
#include <utility>
#include <vector>

namespace GnssProcessor {

/**
 * @brief Decisions and counters of the rule for satellites without a stream record.
 */
class UnrecordedSatGate {
public:
    /// @brief The kind of an edge.
    enum class EventKind {
        Drop,     ///< A satellite seen without a record is left out (first sighting or record lost).
        Readmit   ///< A dropped satellite's record returned: it is back in the solution, its states afresh.
    };

    /**
     * @brief One edge of the rule, for the log and the tests.
     */
    struct Event {
        EventKind   kind{ EventKind::Drop };  ///< Drop or Readmit.
        std::string sat;                      ///< The satellite ("G12").
        bool        first_sighting{ false };  ///< Drop only: the satellite had never been seen with a record.
    };

    /**
     * @brief Run counters (the run-end line).
     */
    struct Counters {
        std::size_t epochs{ 0 };               ///< Epochs the gate decided.
        std::size_t drops{ 0 };                ///< Drop events.
        std::size_t drops_first_sighting{ 0 }; ///< Of them, satellites never seen with a record.
        std::size_t readmits{ 0 };             ///< Readmit events.
        std::size_t sat_epochs_out{ 0 };       ///< Satellite-epochs left out.
        std::size_t sat_epochs_seen{ 0 };      ///< Satellite-epochs decided (left out or kept).
    };

    /**
     * @brief Decide one epoch.
     *
     * @param sats      Each modelled satellite of the epoch with whether the stream holds a record
     *                  for it at the epoch (a satellite listed twice is decided once, by its first entry).
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
    std::set<std::string> dropped_;      ///< Left out, awaiting a record.
    std::set<std::string> ever_recorded_;///< Seen with a record at least once (a later loss is no first sighting).
    Counters              counters_;     ///< Run counters.
};

} // namespace GnssProcessor

/**
 * @file UnrecordedSatGate.cpp
 * @brief Decisions of the rule for satellites without their stream records (see the header).
 */

#include "realtime/UnrecordedSatGate.hpp"

namespace GnssProcessor {

std::vector<UnrecordedSatGate::Event> UnrecordedSatGate::step(const std::vector<SatState>& sats,
                                                              std::set<std::string>& out) {
    out.clear();
    std::vector<Event> events;
    std::set<std::string> decided;
    ++counters_.epochs;
    for (const SatState& s : sats) {
        if (!decided.insert(s.sat).second) continue;   // listed twice: the first entry decides
        ++counters_.sat_epochs_seen;
        if (s.missing == Missing::None) {
            ever_recorded_.insert(s.sat);
            if (dropped_.erase(s.sat) > 0) {
                ++counters_.readmits;
                events.push_back({ EventKind::Readmit, s.sat, false, Missing::None, std::string{} });
            }
            continue;
        }
        out.insert(s.sat);
        ++counters_.sat_epochs_out;
        if (s.missing == Missing::PhaseBias) ++counters_.sat_epochs_out_no_phase_bias;
        if (dropped_.insert(s.sat).second) {
            const bool first = (ever_recorded_.count(s.sat) == 0);
            ++counters_.drops;
            if (first) ++counters_.drops_first_sighting;
            if (s.missing == Missing::PhaseBias) ++counters_.drops_no_phase_bias;
            events.push_back({ EventKind::Drop, s.sat, first, s.missing,
                               s.missing == Missing::PhaseBias ? s.signal : std::string{} });
        }
    }
    return events;
}

std::vector<UnrecordedSatGate::Event> UnrecordedSatGate::step(
    const std::vector<std::pair<std::string, bool>>& sats, std::set<std::string>& out) {
    std::vector<SatState> states;
    states.reserve(sats.size());
    for (const auto& [sat, has_clock] : sats)
        states.push_back({ sat, has_clock ? Missing::None : Missing::Clock, std::string{} });
    return step(states, out);
}

} // namespace GnssProcessor

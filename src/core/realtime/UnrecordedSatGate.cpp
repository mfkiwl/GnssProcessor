/**
 * @file UnrecordedSatGate.cpp
 * @brief Decisions of the rule for satellites without a stream record (see the header).
 */

#include "realtime/UnrecordedSatGate.hpp"

namespace GnssProcessor {

std::vector<UnrecordedSatGate::Event> UnrecordedSatGate::step(
    const std::vector<std::pair<std::string, bool>>& sats, std::set<std::string>& out) {
    out.clear();
    std::vector<Event> events;
    std::set<std::string> decided;
    ++counters_.epochs;
    for (const auto& [sat, has_record] : sats) {
        if (!decided.insert(sat).second) continue;   // listed twice: the first entry decides
        ++counters_.sat_epochs_seen;
        if (has_record) {
            ever_recorded_.insert(sat);
            if (dropped_.erase(sat) > 0) {
                ++counters_.readmits;
                events.push_back({ EventKind::Readmit, sat, false });
            }
            continue;
        }
        out.insert(sat);
        ++counters_.sat_epochs_out;
        if (dropped_.insert(sat).second) {
            const bool first = (ever_recorded_.count(sat) == 0);
            ++counters_.drops;
            if (first) ++counters_.drops_first_sighting;
            events.push_back({ EventKind::Drop, sat, first });
        }
    }
    return events;
}

} // namespace GnssProcessor

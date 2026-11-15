/**
 * @file WindupArcs.cpp
 * @brief The stations' wind-up accumulators, traced per arc (network/diag/WindupArcs.hpp).
 */
#include "network/diag/WindupArcs.hpp"

#include "network/diag/RunTraces.hpp"
#include "network/driver/Epoch.hpp"   // NetworkEpoch
#include "network/driver/Run.hpp"     // NetworkRun
#include "network/state/RunContext.hpp"
#include "model/PppModel.hpp"

#include <cmath>
#include <fmt/format.h>
#include <string>
#include <vector>

namespace GnssProcessor {

void networkWindupArcsTrace(NetworkRun& run, const NetworkEpoch& ep) {
    // ---- From the run and the epoch (writes are marked `// written`) ----
    const NetworkKnobs& knobs = run.ctx.knobs;
    const std::vector<NetStation>& stations = run.setup.stations;
    std::ofstream& out = run.traces.windup_arcs_trace;   // written: this trace's rows
    const GnssTime& t = ep.se.time;
    // ---- End of the bindings ----
    if (!knobs.trace_windup_arcs || !out.is_open()) return;
    const double week_s = static_cast<double>(t.week) * 604800.0;
    const double now_s = week_s + t.tow;
    const bool anchor = std::llround(t.tow) % std::llround(kWindupArcAnchorS) == 0;
    for (const NetStation& st : stations) {
        if (!st.model) continue;
        for (const auto& [sat, arc] : st.model->windUpArcs()) {
            // Only the accumulators this epoch updated (the epoch clock may sit microseconds off).
            if (std::abs(arc.epoch_s - now_s) > 0.5) continue;
            const double start_tow = arc.start_epoch_s - week_s;
            if (arc.start_epoch_s == arc.epoch_s)
                out << fmt::format("{},{:.3f},{},{},start,{:.6f},{:.3f}\n", t.week, t.tow, st.name, sat, arc.cycles,
                                   start_tow);
            if (anchor)
                out << fmt::format("{},{:.3f},{},{},anchor,{:.6f},{:.3f}\n", t.week, t.tow, st.name, sat, arc.cycles,
                                   start_tow);
        }
    }
}

}  // namespace GnssProcessor

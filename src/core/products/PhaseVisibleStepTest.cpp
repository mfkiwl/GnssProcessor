/**
 * @file PhaseVisibleStepTest.cpp
 * @brief The phase-bias step declaration on what a user sees (@c network.disc_phase_visible).
 */

#include "products/PhaseVisibleStepTest.hpp"

#include <algorithm>
#include <cmath>
#include <map>
#include <utility>

namespace GnssProcessor {

double phaseVisibleMedian(std::vector<double> v) {
    if (v.empty()) return 0.0;
    std::sort(v.begin(), v.end());
    const std::size_t n = v.size();
    return (n % 2 == 1) ? v[n / 2] : 0.5 * (v[n / 2 - 1] + v[n / 2]);
}

std::vector<PhaseVisibleVerdict> decidePhaseVisibleSteps(const std::vector<PhaseVisibleKey>& keys,
                                                         int min_sats,
                                                         PhaseVisibleCounters* counters) {
    std::vector<PhaseVisibleVerdict> out(keys.size());
    // Group the keys by (constellation, signal), in input order within a group.
    std::map<std::pair<char, std::string>, std::vector<std::size_t>> groups;
    for (std::size_t i = 0; i < keys.size(); ++i)
        groups[{ keys[i].constellation, keys[i].signal }].push_back(i);

    for (const auto& [group, idx] : groups) {
        std::vector<double> votes;
        bool any_tested = false;
        double min_bar = 0.0;
        for (std::size_t i : idx) {
            const PhaseVisibleKey& k = keys[i];
            if (!k.tested) continue;
            if (!any_tested || k.bar_m < min_bar) min_bar = k.bar_m;
            any_tested = true;
            if (k.votes) votes.push_back(k.change_m);
        }
        if (!any_tested) continue;
        const bool median_basis = static_cast<int>(votes.size()) >= std::max(1, min_sats);
        const double median = median_basis ? phaseVisibleMedian(votes) : 0.0;
        if (counters) {
            ++counters->groups;
            if (median_basis) {
                ++counters->groups_median;
                counters->max_abs_median_m = std::max(counters->max_abs_median_m, std::abs(median));
                if (std::abs(median) > min_bar) ++counters->shared_over_bar;
            } else {
                ++counters->groups_below_min;
            }
        }
        for (std::size_t i : idx) {
            const PhaseVisibleKey& k = keys[i];
            PhaseVisibleVerdict& v = out[i];
            v.tested = k.tested;
            if (!k.tested) continue;
            v.median_basis = median_basis;
            v.median_m     = median;
            v.deviation_m  = k.change_m - median;
            v.step         = std::abs(v.deviation_m) > k.bar_m;
            if (counters) {
                ++counters->keys_tested;
                if (v.step) {
                    ++counters->keys_stepped;
                    if (!median_basis) ++counters->keys_stepped_below_min;
                }
            }
        }
    }
    return out;
}

} // namespace GnssProcessor

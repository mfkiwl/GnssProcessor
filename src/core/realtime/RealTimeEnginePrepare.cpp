/**
 * @file RealTimeEnginePrepare.cpp
 * @brief Measurement-set conditioning seams for RealTimeEngine::processEpoch.
 *
 * Steps that reshape the epoch's observation set or the filter's starting
 * point after computeModels and before the KF predict.
 *
 * seedClockFromWls and regaugeBssd are mutually exclusive by construction:
 * the seed requires hasClock(), the re-gauge requires !hasClock() (and BSSD
 * enabled).  Under BSSD the filter carries no receiver clock state to seed,
 * and the re-gauge exists for that case.  Each self-gates, so the driver
 * calls both unconditionally.
 */

#include "realtime/RealTimeEngine.hpp"
#include "common/GnssIdentity.hpp"
#include "math/TimeUtils.hpp"
#include "math/WlsEstimator.hpp"
#include "products/SsrCorrectionStore.hpp"   // getOrbitClock, getPhaseBias (the unrecorded-satellite rule)
#include <algorithm>
#include <cmath>
#include <set>
#include <string>
#include <utility>
#include <vector>

namespace GnssProcessor {

/**
 * @brief Drop broadcast-grade satellites (@c broadcast_only set) from the precise SSR
 *        PPP-RTK solution when the corrections-ready gate's drop_broadcast_grade is set.
 *
 * Relocated verbatim from the pre-cut RealTimeEngine::processEpoch
 * (frozen lines 1235-1244); see scripts/rt_seam_verify.py.
 */
void RealTimeEngine::dropBroadcastGrade(RtEpochContext& ctx) {
    auto log = log_manager_.getLogger("rt_engine");
    const std::string& epoch_prefix = ctx.epoch_prefix;
    std::vector<PppObservation>& modeled_obs = ctx.modeled_obs;

    if (config_.getCorrectionsReadyGate().drop_broadcast_grade) {
        size_t dropped = 0;
        for (auto it = modeled_obs.begin(); it != modeled_obs.end(); ) {
            if (it->broadcast_only) { it = modeled_obs.erase(it); ++dropped; }
            else ++it;
        }
        if (dropped > 0)
            log->debug("{}Dropped {} broadcast-grade sat(s) (no SSR clock) from the precise solution",
                       epoch_prefix, dropped);
    }
}

/**
 * @brief Leave out of the solution every satellite that lacks its stream records (the clock rule,
 *        processing.ssr_drop_unrecorded, derived from network.closed_loop.drop_unrecorded; the
 *        phase-bias rule, processing.ssr_drop_unrecorded_phase_bias, derived from
 *        network.closed_loop.drop_unrecorded_phase_bias).
 *
 * A satellite has its clock record when the store returns a clock for it at the model's own
 * freshness limit (getSsrMaxAge), the test by which the model applies the stream's correction.  A
 * satellite without one keeps the a priori clock and no bias, so a term the stream's corrections
 * share would be a between-satellite term in every single difference that pairs it with a corrected
 * satellite.  Under the phase-bias rule a satellite with its clock also needs a phase-bias record for
 * every raw phase signal the receiver uses for it, asked with the phase-bias apply site's own test
 * (ObservationEquation addSsrBias: the bias age limit times the stale-hold factor at the observation
 * time when the bias staleness gate is on, the latest record otherwise); a missing code bias is no
 * reason to leave a satellite out.  The decisions and counters are UnrecordedSatGate's; this seam
 * asks the store, erases the satellites the gate leaves out (before the model chooses its pivot and
 * builds its rows) and logs each edge with its satellite and missing record.  At a drop the model
 * prunes the satellite's ambiguity and ionosphere states as for a satellite out of view; at a
 * readmit they are seeded afresh.  The seam runs before the phase-bias reaction of the epoch
 * (resetOnPhaseBiasDisc), so a satellite left out is not seen by its freshness-flip test: its last
 * applied state stays as it was while the satellite was in the solution, and the readmit's fresh
 * start takes the place of the flip's reset.
 */
void RealTimeEngine::dropUnrecorded(RtEpochContext& ctx) {
    const bool phase_rule = config_.ssrDropUnrecordedPhaseBias();
    if (!config_.ssrDropUnrecorded() && !phase_rule) return;
    auto log = log_manager_.getLogger("rt_engine");
    const std::string& epoch_prefix = ctx.epoch_prefix;
    const GnssTime& current_time = ctx.current_time;
    std::vector<PppObservation>& modeled_obs = ctx.modeled_obs;

    const SsrCorrectionStore& store = ssrStore();
    const double max_age = config_.getSsrMaxAge();
    // The phase-bias apply site's own freshness test (ObservationEquation addSsrBias).
    const bool   bias_age_gate = config_.enableSsrBiasMaxAge();
    const double bias_max_age  = config_.getSsrBiasMaxAge() * config_.getSsrBiasStaleHoldFactor();
    std::vector<UnrecordedSatGate::SatState> sats;
    sats.reserve(modeled_obs.size());
    for (const auto& obs : modeled_obs) {
        UnrecordedSatGate::SatState st;
        st.sat = obs.satellite;
        const auto oc = store.getOrbitClock(obs.satellite, current_time, max_age);
        if (!(oc.has_value() && oc->has_clock)) {
            st.missing = UnrecordedSatGate::Missing::Clock;
        } else if (phase_rule) {
            for (const auto& kv : obs.modeled) {
                const std::string& code = kv.first;
                if (obsTypeOf(code) != ObsType::Phase || isIonoFreePairLabel(code)) continue;
                const bool has = bias_age_gate
                    ? store.getPhaseBias(obs.satellite, code, obs.time, bias_max_age).has_value()
                    : store.getPhaseBias(obs.satellite, code).has_value();
                if (!has) {
                    st.missing = UnrecordedSatGate::Missing::PhaseBias;
                    st.signal  = code;
                    break;
                }
            }
        }
        sats.push_back(st);
    }
    std::set<std::string> out;
    for (const auto& ev : unrecorded_gate_.step(sats, out)) {
        if (ev.kind == UnrecordedSatGate::EventKind::Drop
            && ev.missing == UnrecordedSatGate::Missing::PhaseBias)
            log->info("{}Unrecorded-satellite rule: DROP {} ({}): no phase-bias record for {}; left "
                      "out of the solution, its ambiguity and ionosphere pruned",
                      epoch_prefix, ev.sat, ev.first_sighting ? "first sighting" : "record lost",
                      ev.signal);
        else if (ev.kind == UnrecordedSatGate::EventKind::Drop)
            log->info("{}Unrecorded-satellite rule: DROP {} ({}): no stream record; left out of "
                      "the solution, its ambiguity and ionosphere pruned",
                      epoch_prefix, ev.sat, ev.first_sighting ? "first sighting" : "record lost");
        else
            log->info("{}Unrecorded-satellite rule: READMIT {}: its stream record returned; back "
                      "in the solution, its ambiguity and ionosphere seeded afresh",
                      epoch_prefix, ev.sat);
    }
    if (out.empty()) return;
    modeled_obs.erase(std::remove_if(modeled_obs.begin(), modeled_obs.end(),
                                     [&](const PppObservation& o) { return out.count(o.satellite) > 0; }),
                      modeled_obs.end());
}

void RealTimeEngine::logUnrecordedGateSummary(const char* tag) const {
    const bool phase_rule = config_.ssrDropUnrecordedPhaseBias();
    if (!config_.ssrDropUnrecorded() && !phase_rule) return;   // both off: never printed (byte-identical)
    const auto& c = unrecorded_gate_.counters();
    std::string still;
    for (const auto& s : unrecorded_gate_.dropped()) still += (still.empty() ? "" : ",") + s;
    if (!phase_rule) {
        log_manager_.getLogger("rt_engine")->info(
            "[RT] Unrecorded-satellite rule ({}): epochs {}; drops {} (first sightings {}), "
            "readmits {}; satellite-epochs left out {} of {}; still out at the end: {}",
            tag, c.epochs, c.drops, c.drops_first_sighting, c.readmits, c.sat_epochs_out,
            c.sat_epochs_seen, still.empty() ? "none" : still);
        return;
    }
    log_manager_.getLogger("rt_engine")->info(
        "[RT] Unrecorded-satellite rule with phase biases ({}): epochs {}; drops {} (first "
        "sightings {}; {} for a missing phase-bias record), readmits {}; satellite-epochs left out "
        "{} of {} ({} for a missing phase-bias record); still out at the end: {}",
        tag, c.epochs, c.drops, c.drops_first_sighting, c.drops_no_phase_bias, c.readmits,
        c.sat_epochs_out, c.sat_epochs_seen, c.sat_epochs_out_no_phase_bias,
        still.empty() ? "none" : still);
}

/**
 * @brief WLS receiver-clock seed.  Self-gated on hasClock(), so it never runs together with
 *        regaugeBssd().  Overwrites the KF clock with the WLS clock when they differ by at
 *        least 0.05 ms (about 15 km), after a data gap, or on the first epoch.
 *
 * Relocated verbatim from the pre-cut RealTimeEngine::processEpoch
 * (frozen lines 1249-1271); see scripts/rt_seam_verify.py.
 */
void RealTimeEngine::seedClockFromWls(RtEpochContext& ctx) {
    auto log = log_manager_.getLogger("rt_engine");
    const std::string& epoch_prefix = ctx.epoch_prefix;
    const GnssTime& current_time = ctx.current_time;
    const std::vector<PppObservation>& modeled_obs = ctx.modeled_obs;
    const bool gap_detected = ctx.gap_detected;

    if (state_manager_->hasClock()) {
        const auto wls_result = wls_estimator_->estimate(current_time, modeled_obs);
        if (wls_result.success() && wls_result.state.size() >= 4) {
            const double wls_clock = wls_result.state(3);
            const Eigen::VectorXd sv = state_manager_->getStateVector();
            const size_t clk_idx = state_manager_->getClockIndex();
            const double kf_clock = (sv.size() > static_cast<Eigen::Index>(clk_idx))
                                    ? sv(clk_idx) : 0.0;

            constexpr double kJumpThresh = 0.00005 * 299792458.0; // 0.05 ms (5e-5 s), about 14.99 km
            const double delta = wls_clock - kf_clock;
            const bool should_seed = (std::abs(delta) >= kJumpThresh)
                                     || gap_detected || first_epoch_;
            if (should_seed && sv.size() > static_cast<Eigen::Index>(clk_idx)) {
                Eigen::VectorXd sv2 = sv;
                sv2(clk_idx) = wls_clock;
                state_manager_->setStateVector(sv2);
                ppp_state_.clock_bias = wls_clock;
                log->info("{}Seeded clock: wls={:.1f} kf={:.1f} d={:.1f}",
                          epoch_prefix, wls_clock, kf_clock, delta);
            }
        }
    }
}

/**
 * @brief BSSD code/phase re-gauge: remove the bulk receiver clock.  Self-gated on
 *        enableBetweenSatelliteSd() and !hasClock(), so it never runs together with
 *        seedClockFromWls().  Subtracts the median code innovation (metres) from every
 *        code and phase observable; a common-mode shift leaves the SD observations unchanged.
 *
 * Relocated verbatim from the pre-cut RealTimeEngine::processEpoch
 * (frozen lines 1300-1333); see scripts/rt_seam_verify.py.
 */
void RealTimeEngine::regaugeBssd(RtEpochContext& ctx) {
    auto log = log_manager_.getLogger("rt_engine");
    const std::string& epoch_prefix = ctx.epoch_prefix;
    std::vector<PppObservation>& modeled_obs = ctx.modeled_obs;

    if (config_.enableBetweenSatelliteSd() && !state_manager_->hasClock()) {
        std::vector<double> code_innov;
        code_innov.reserve(modeled_obs.size());
        for (const auto& o : modeled_obs) {
            for (const auto& [code, val] : o.observed) {
                if (obsTypeOf(code) != ObsType::Code) continue;            // code only
                const auto mit = o.modeled.find(code);
                if (mit == o.modeled.end()) continue;
                const double innov = val - mit->second;
                if (std::isfinite(innov)) code_innov.push_back(innov);
            }
        }
        if (!code_innov.empty()) {
            const size_t mid = code_innov.size() / 2;
            std::nth_element(code_innov.begin(), code_innov.begin() + mid, code_innov.end());
            const double common_clock_m = code_innov[mid];
            if (std::isfinite(common_clock_m)) {
                size_t n_reduced = 0;
                for (auto& o : modeled_obs) {
                    for (auto& kv : o.observed) {
                        const std::string& code = kv.first;
                        if (code.empty()) continue;
                        const ObsType type = obsTypeOf(code);
                        if (type != ObsType::Code && type != ObsType::Phase) continue;  // code + phase
                        kv.second -= common_clock_m;               // common-mode: SD-invariant
                        ++n_reduced;
                    }
                }
                log->debug("{}BSSD re-gauge: removed common rx clock {:.3f} m "
                           "(median of {} code innovations) from {} observables",
                           epoch_prefix, common_clock_m, code_innov.size(), n_reduced);
            }
        }
    }
}

} // namespace GnssProcessor

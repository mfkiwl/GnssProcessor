/**
 * @file RingFixSeams.cpp
 * @brief The network seams of the ring fix: setup, the release and hold table before PASS B, the
 *        PASS B hold rows, the decision after the solve, and the run-end report (see
 *        network/ar/RingFix.hpp).
 */

#include "network/ar/RingFix.hpp"

#include "config/GnssConfig.hpp"
#include "filter/StateKeySchema.hpp"            // StateKeys::makeAmbiguityKey
#include "network/ar/AmbFloat.hpp"              // ambFloatDropFloored, ambFloatBirthFloor, ambFloatDropFloorNow
#include "network/assembly/Contributions.hpp"   // makeRowTag
#include "network/assembly/StationBuild.hpp"    // StationBuild, StationCarryFrame
#include "network/diag/AmbStateTrace.hpp"       // ambStateNoteDrop
#include "network/diag/RunTraces.hpp"
#include "network/driver/Epoch.hpp"
#include "network/driver/Run.hpp"
#include "network/driver/RunTypes.hpp"
#include "network/driver/SetupResult.hpp"
#include "network/runend/RunEnd.hpp"
#include "network/solve/ChainChordTable.hpp"
#include "network/solve/ChainFrame.hpp"
#include "network/solve/Estimator.hpp"
#include "network/state/RunContext.hpp"
#include "network/state/StationParams.hpp"
#include "rinex/MultiRinexSync.hpp"             // SyncedEpoch

#include <fmt/format.h>

#include <algorithm>
#include <cmath>
#include <optional>

namespace GnssProcessor {

namespace {



std::string rxKey(int station) { return "R:" + std::to_string(station); }
std::string svKey(const std::string& sat) { return "S:" + sat; }
std::string groupOf(const std::string& sat, const std::string& sig) { return sat.substr(0, 1) + "|" + sig; }

/// The arcs in this epoch's free-epoch latch, as (station, satellite, signal).
std::set<net::ArcTuple> latchedArcs(const RelevelEpochState& relevel) {
    std::set<net::ArcTuple> out;
    for (const auto& [sta, amb_key] : relevel.free_ambs) {
        const std::optional<ArcId> arc = net::arcKey(sta, amb_key);
        if (!arc) continue;
        out.insert({sta, net::satKey(arc->sat), net::signalKey(arc->signal)});
    }
    return out;
}

/// What the release reads from the chain record: tree arcs, chords, roots and cut vertices.
struct ChainFacts {
    std::set<net::ArcTuple> tree;    ///< Tree edges (station, satellite, signal).
    std::set<net::ArcTuple> chords;  ///< Chords (station, satellite, signal).
    /// group -> vertex key -> its component's root receiver.
    std::map<std::string, std::map<std::string, std::string>> root_of;
    std::set<std::string> cut_vertices;   ///< Vertices on a cut release's moved side ("R:<i>", "S:<sat>").
    /// @brief The root of a vertex's component in a group ("" when unknown).
    /// @param g The group. @param v The vertex key. @return The root receiver's name.
    std::string root(const std::string& g, const std::string& v) const {
        const auto gi = root_of.find(g);
        if (gi == root_of.end()) return {};
        const auto vi = gi->second.find(v);
        return vi == gi->second.end() ? std::string{} : vi->second;
    }
};

ChainFacts chainFacts(const ChainEpochObs* obs) {
    ChainFacts f;
    if (obs == nullptr || !obs->armed) return f;
    for (const ChainEdgeObs& e : obs->edges) {
        f.tree.insert({e.station, e.sat, e.signal});
        f.root_of[e.group][e.child] = e.r1;
        f.root_of[e.group][e.parent] = e.r1;
    }
    for (const ChainChordCycle& c : obs->chords) f.chords.insert({c.station, c.sat, c.signal});
    for (const ChainReleaseObs& r : obs->releases) {
        for (const std::string& s : r.sats) f.cut_vertices.insert(svKey(s));
        for (int i : r.stations) f.cut_vertices.insert(rxKey(i));
    }
    return f;
}

/// The post-fit residual (m) of the observation phase row on an ambiguity column, if one exists.
std::optional<double> phaseResidual(const StationAssembly& R, const Eigen::VectorXd& resid, Eigen::Index col) {
    if (col < 0 || col >= R.A_r.cols()) return std::nullopt;
    const Eigen::Index n = std::min<Eigen::Index>(R.A_r.rows(), static_cast<Eigen::Index>(R.row_tags.size()));
    for (Eigen::Index k = 0; k < n && k < resid.size(); ++k) {
        const ContributionKind kind = R.row_tags[static_cast<std::size_t>(k)].kind;
        if (kind != ContributionKind::DataPhase && kind != ContributionKind::DataPhaseSecond) continue;
        if (std::abs(R.A_r(k, col)) > 0.5) return resid(k);
    }
    return std::nullopt;
}

const char* auditName(RingFixAudit a) {
    switch (a) {
        case RingFixAudit::Right:    return "right";
        case RingFixAudit::Wrong:    return "wrong";
        case RingFixAudit::Unlisted: return "unlisted";
    }
    return "?";
}

std::string cellOf(double v, int digits) {
    if (!std::isfinite(v)) return std::string();
    return fmt::format("{:.{}f}", v, digits);
}

}  // namespace

// ---- Setup ----

void networkRingFixArm(NetworkRun& run) {
    NetworkRunContext& ctx = run.ctx;
    const NetworkConfig& nc = run.nc;
    const std::shared_ptr<spdlog::logger>& log = run.log;
    // ---- End of the bindings ----
    if (!nc.ring_fix.enable) return;
    auto rf = std::make_unique<NetworkRingFix>();
    rf->rule = nc.ring_fix.rule == "plain" ? RingFixRule::Plain : RingFixRule::Gated;
    rf->max_gap_s = ctx.knobs.pl_max_gap_s;
    rf->audit_file = nc.ring_fix.audit_frame_file;
    if (!rf->audit_file.empty()) rf->audit = ringFixReadAuditFile(rf->audit_file);
    log->warn("Network (ring fix): ARMED, rule {} ({}). Chords of pair families are decided ring by ring "
              "from the chain's root (gate: sigma at most {:.2f} cycle and fraction at most {:.2f} of the "
              "ionosphere-free N1 with the wide lane rounded; event window {:.0f} s; {} epochs of the same "
              "integers; the lattice vetoes), held by a prior row of sigma {:g} m from the next epoch, and "
              "released at a slip latch, a refloat, a gap beyond {:.0f} s, a chain event or the residual "
              "monitor ({:.3f} m at {} epochs). Audit: {}.",
              rf->rule == RingFixRule::Plain ? "plain" : "gated",
              rf->rule == RingFixRule::Plain ? "NEGATIVE CONTROL: every candidate rounded" : "the frozen rule",
              kRingFixMaxSigmaCyc, kRingFixMaxFracCyc, kRingFixWindowS, kRingFixPersistEpochs,
              kRingFixHoldSigmaM, rf->max_gap_s, kRingFixMonitorBoundM, kRingFixMonitorEpochs,
              rf->audit_file.empty() ? std::string("none")
                                     : fmt::format("'{}' ({} arcs)", rf->audit_file, rf->audit.size()));
    ctx.carry.ring_fix = std::move(rf);
}

// ---- Before PASS B: the releases and the hold table ----

void networkRingFixHoldEpoch(NetworkRun& run, const NetworkEpoch& ep) {
    NetworkRunContext& ctx = run.ctx;
    NetworkRunTraces& traces = run.traces;
    const GnssConfig& config_ = run.config;
    const std::vector<NetStation>& stations = run.setup.stations;
    const GnssTime& t = ep.se.time;
    const double now_s = ep.clock.pl_now_s;
    const ChainEpochObs* obs_rec = ep.events.phase_datum.chain.get();
    const RelevelEpochState& relevel = ep.events.slip.relevel;
    net::ArcTable& arc_rows = ctx.entities.arcs;   // written: the released links' carried entries
    // ---- End of the bindings ----
    if (!ctx.carry.ring_fix) return;
    NetworkRingFix& rf = *ctx.carry.ring_fix;
    rf.table.clear();
    const bool any_held = std::any_of(rf.links.begin(), rf.links.end(),
                                      [](const auto& kv) { return kv.second.held; });
    if (any_held) {
        const std::set<net::ArcTuple> latched = latchedArcs(relevel);
        const ChainFacts facts = chainFacts(obs_rec);
        std::map<RingFixLinkId, RingFixHoldObs> obs;
        for (const auto& [id, L] : rf.links) {
            if (!L.held) continue;
            RingFixHoldObs o;
            o.tree_now = facts.tree.count({id.station, id.sat, id.sig1}) > 0
                      || facts.tree.count({id.station, id.sat, id.sig2}) > 0;
            o.present = facts.chords.count({id.station, id.sat, id.sig1}) > 0
                     && facts.chords.count({id.station, id.sat, id.sig2}) > 0;
            o.in_cut = facts.cut_vertices.count(rxKey(id.station)) > 0
                    || facts.cut_vertices.count(svKey(id.sat)) > 0;
            o.root = facts.root(groupOf(id.sat, id.sig1), rxKey(id.station));
            o.latched = latched.count({id.station, id.sat, id.sig1}) > 0
                     || latched.count({id.station, id.sat, id.sig2}) > 0;
            const LocalCarry* c1 = net::getArc(arc_rows, net::ArcTuple{id.station, id.sat, id.sig1}, &net::ArcState::amb);
            const LocalCarry* c2 = net::getArc(arc_rows, net::ArcTuple{id.station, id.sat, id.sig2}, &net::ArcState::amb);
            o.carry_ok = c1 != nullptr && c2 != nullptr;
            o.stamp1 = c1 != nullptr ? c1->relevel_s : 0.0;
            o.stamp2 = c2 != nullptr ? c2->relevel_s : 0.0;
            obs[id] = o;
        }
        const std::vector<RingFixEvent> events = ringFixReleaseStep(rf, obs, now_s);
        // A slip is answered by the vehicle's drop pass of this epoch and a refloat already was:
        // the other causes re-open the carried entries here, unless something re-levelled them
        // since the decision.
        const long long now_ep = static_cast<long long>(ctx.counters.n_loop_epochs);
        const double elev_power = config_.getCodeElevationPower();
        const auto reopen = [&](const RingFixLinkId& id, const std::string& sig, double stamp) {
            const net::ArcTuple key{id.station, id.sat, sig};
            LocalCarry* lc = net::getArc(arc_rows, key, &net::ArcState::amb);
            if (lc == nullptr || lc->relevel_s > stamp) return;
            const std::string name = (id.station >= 0 && static_cast<std::size_t>(id.station) < stations.size())
                                         ? stations[static_cast<std::size_t>(id.station)].name : std::string{};
            if (ctx.knobs.amb_float_kf) {
                const double drop_base = ambFloatDropFloorNow(ctx.knobs.amb_drop_var_floor, now_ep,
                                                              ctx.knobs.amb_drop_floor_after_ep);
                ambFloatDropFloored(*lc, ambFloatBirthFloor(ctx.knobs.amb_birth_var_floor, -1.0, elev_power),
                                    ambFloatBirthFloor(drop_base, -1.0, elev_power), now_s, now_ep,
                                    ctx.knobs.amb_drop_decouple_always);
                if (ctx.knobs.trace_amb_state)
                    ambStateNoteDrop(ctx, t.week, t.tow, name, id.sat, sig, *lc, "ring_fix_release");
            } else {
                net::dropArc(arc_rows, key, &net::ArcState::amb);
            }
            ++rf.counters.carry_reopened;
        };
        for (const RingFixEvent& ev : events) {
            const RingFixLink& L = rf.links.at(ev.id);
            if (ev.release == RingFixRelease::Chain || ev.release == RingFixRelease::Monitor
                || ev.release == RingFixRelease::Gap) {
                reopen(ev.id, ev.id.sig1, L.stamp1);
                reopen(ev.id, ev.id.sig2, L.stamp2);
            }
            const std::string name = (ev.id.station >= 0 && static_cast<std::size_t>(ev.id.station) < stations.size())
                                         ? stations[static_cast<std::size_t>(ev.id.station)].name : std::string{};
            traces.emitEvent(t, "RINGFIX", "release", ev.id.sat, name, std::nullopt, std::nullopt,
                             ringFixReleaseName(ev.release),
                             fmt::format("sig1={} sig2={} n1={} n2={} ring={} held_s={:.0f}", ev.id.sig1,
                                         ev.id.sig2, L.n1, L.n2, L.ring, now_s - L.decided_s));
        }
    }
    for (const auto& [id, L] : rf.links) {
        if (!L.held) continue;
        rf.table[{id.station, id.sat, id.sig1}] = L.lambda1 * static_cast<double>(L.n1);
        rf.table[{id.station, id.sat, id.sig2}] = L.lambda2 * static_cast<double>(L.n2);
    }
}

// ---- PASS B: the hold rows ----

void networkRingFixPriors(StationCarryFrame& carry) {
    StationBuild& build = carry.build;
    const NetworkRunContext& ctx = build.ctx;
    const NetworkSetupResult& setup = build.setup;
    const int i = build.i;
    NetStation& st = build.st;
    StationAssembly& R = build.R;
    std::map<int, int>& h2local = R.h2local;
    const bool legacy_local_inject = carry.legacy_local_inject;
    const Eigen::VectorXd& x_lin = carry.x_lin;
    std::vector<std::tuple<Eigen::Index, double, double, RowTag>>& inj = carry.inj;
    const auto& stations = setup.stations;
    // This epoch's hold table, built serially before PASS B and only read here; null on every
    // run without the ring fix, so this step is unreachable when off.
    const std::map<std::tuple<int, std::string, std::string>, double>* table =
        ctx.carry.ring_fix ? &ctx.carry.ring_fix->table : nullptr;
    const bool rfix_on = table != nullptr && !table->empty();
    // ---- End of the bindings ----
    if (!(legacy_local_inject && rfix_on)) return;
    const double lam = 1.0 / (kRingFixHoldSigmaM * kRingFixHoldSigmaM);
    for (const auto& [arc, amb_idx] : st.params.amb) {
        const std::string arc_sat = net::satKey(arc.sat);
        const std::string arc_signal = net::signalKey(arc.signal);
        const auto it = table->find(std::make_tuple(i, arc_sat, arc_signal));
        if (it == table->end()) continue;
        ++R.rfix_offered;
        // A tree edge's 1e10 pin is the frame: a second row there would fight it.  The release
        // step releases a link that became a tree edge before PASS B; this is the backstop.
        if (stations[static_cast<std::size_t>(i)].pinned_amb_targets.count(
                StateKeys::makeAmbiguityKey(arc_sat, arc_signal)) != 0) {
            ++R.rfix_gauge_skipped;
            continue;
        }
        if (amb_idx >= x_lin.size()) { ++R.rfix_no_column; continue; }
        const auto hit = h2local.find(amb_idx);
        if (hit == h2local.end() || !std::isfinite(x_lin(amb_idx))) { ++R.rfix_no_column; continue; }
        const double eta = lam * (it->second - x_lin(amb_idx));
        if (!std::isfinite(eta)) { ++R.rfix_no_column; continue; }
        inj.emplace_back(static_cast<Eigen::Index>(hit->second), lam, eta,
                         makeRowTag(ContributionKind::PriorAmbiguityRingHold, arc_sat, arc_signal));
        ++R.rfix_rows;
    }
}

void networkRingFixStationTally(NetworkRunContext& ctx, const std::vector<StationAssembly>& asm_res) {
    if (!ctx.carry.ring_fix) return;
    RingFixCounters& C = ctx.carry.ring_fix->counters;
    for (const StationAssembly& Rc : asm_res) {
        C.rows_injected      += Rc.rfix_rows;
        C.rows_gauge_skipped += Rc.rfix_gauge_skipped;
        C.rows_no_column     += Rc.rfix_no_column;
    }
}

// ---- After the solve: the monitor, the audit and the decisions ----

void networkRingFixDecide(NetworkRun& run, const NetworkEpoch& ep) {
    NetworkRunContext& ctx = run.ctx;
    NetworkRunTraces& traces = run.traces;
    const std::vector<NetStation>& stations = run.setup.stations;
    const NetworkEstimator& est = run.engines.est;
    const GnssTime& t = ep.se.time;
    const double now_s = ep.clock.pl_now_s;
    const Eigen::VectorXd& x_s = ep.solve.x_s;
    const NetworkSbasis::Plan& plan = ep.solve.plan;
    const std::vector<StationAssembly>& asm_res = ep.assembly.asm_res;
    const std::vector<int>& est_index_of = ep.assembly.est_index_of;
    const ChainEpochObs* obs_rec = ep.events.phase_datum.chain.get();
    const RelevelEpochState& relevel = ep.events.slip.relevel;
    const net::ArcTable& arc_rows = ctx.entities.arcs;
    const arcgraph::CycleLattice& lattice = ctx.carry.ar_lattice.lattice;
    // ---- End of the bindings ----
    if (!ctx.carry.ring_fix || obs_rec == nullptr || !obs_rec->armed) return;
    NetworkRingFix& rf = *ctx.carry.ring_fix;
    const ChainEpochObs& obs = *obs_rec;

    // The chain this epoch: tree arcs, groups, each group's tree and chords, the roots.
    std::set<net::ArcTuple> tree_arcs;
    std::set<std::string> chain_signals;
    std::map<std::string, RingFixTree> trees;
    std::map<std::string, std::map<std::string, std::string>> root_of;
    for (const ChainEdgeObs& e : obs.edges) {
        tree_arcs.insert({e.station, e.sat, e.signal});
        chain_signals.insert(e.sys + "|" + e.signal);
        trees[e.group].edges.emplace_back(e.child, e.parent, e.depth);
        root_of[e.group][e.child] = e.r1;
        root_of[e.group][e.parent] = e.r1;
        rf.last_tree_s[{e.station, e.sat}] = now_s;
    }
    std::map<net::ArcTuple, const ChainChordCycle*> cyc_of;
    for (const ChainChordCycle& c : obs.chords) {
        cyc_of[{c.station, c.sat, c.signal}] = &c;
        trees[groupOf(c.sat, c.signal)].chords.emplace_back(rxKey(c.station), svKey(c.sat));
    }
    std::map<std::string, std::set<std::pair<std::string, std::string>>> held_by_group;
    for (const auto& [id, L] : rf.links)
        if (L.held) held_by_group[groupOf(id.sat, id.sig1)].insert({rxKey(id.station), svKey(id.sat)});
    std::map<std::string, std::map<std::pair<std::string, std::string>, RingFixRingInfo>> rings;
    for (const auto& [g, tree] : trees) rings[g] = ringFixRings(tree, held_by_group[g]);
    const std::set<net::ArcTuple> latched = latchedArcs(relevel);

    // Every pair-family chord with its readings.
    std::vector<RingFixDecideObs> links;
    std::map<RingFixLinkId, RingFixGate> gate_of;   // the trace's gate reading of every link with a float
    for (std::size_t i = 0; i < stations.size() && i < asm_res.size() && i < est_index_of.size(); ++i) {
        if (est_index_of[i] < 0) continue;
        const int ii = static_cast<int>(i);
        const StationAssembly& R = asm_res[i];
        const ChainAmbColumns cols = chainAmbColumns(R);
        std::vector<ChainChordRow> rows = chainStationChordRows(ii, stations[i].name, cols, tree_arcs, chain_signals);
        if (rows.empty()) continue;
        std::vector<char> filled;
        Eigen::VectorXd xr;
        const bool station_ok = chainChordFloats(est, static_cast<std::size_t>(est_index_of[i]), x_s,
                                                 plan.shared_datum, cols, rows, filled, &xr);
        Eigen::VectorXd resid;
        bool resid_formed = false;
        for (std::size_t r_i = 0; r_i < rows.size(); ++r_i) {
            const ChainChordRow& r = rows[r_i];
            RingFixDecideObs o;
            o.id = {ii, r.sat, r.sig1, r.sig2};
            o.lambda1 = chainWavelengthM(r.sat, r.sig1);
            o.lambda2 = chainWavelengthM(r.sat, r.sig2);
            o.have_float = station_ok && filled[r_i] != 0;
            if (o.have_float) {
                o.f1 = r.float_cyc_1; o.f2 = r.float_cyc_2;
                o.q11 = r.q11; o.q12 = r.q12; o.q22 = r.q22;
                gate_of[o.id] = ringFixGate(o.f1, o.f2, o.q11, o.q12, o.q22, o.lambda1, o.lambda2);
            }
            const std::string g = groupOf(r.sat, r.sig1);
            const auto rg = rings.find(g);
            if (rg != rings.end()) {
                const auto ri = rg->second.find({rxKey(ii), svKey(r.sat)});
                if (ri != rg->second.end()) { o.ring = ri->second.ring; o.candidate = ri->second.candidate; }
            }
            const auto rt = root_of.find(g);
            if (rt != root_of.end()) {
                const auto v = rt->second.find(rxKey(ii));
                if (v != rt->second.end()) o.root = v->second;
            }
            const auto cy1 = cyc_of.find({ii, r.sat, r.sig1});
            if (cy1 != cyc_of.end()) o.have_lat1 = chainLatticeChordInteger(lattice, *cy1->second, o.lat1);
            const auto cy2 = cyc_of.find({ii, r.sat, r.sig2});
            if (cy2 != cyc_of.end()) o.have_lat2 = chainLatticeChordInteger(lattice, *cy2->second, o.lat2);
            const LocalCarry* lc1 = net::getArc(arc_rows, net::ArcTuple{ii, r.sat, r.sig1}, &net::ArcState::amb);
            const LocalCarry* lc2 = net::getArc(arc_rows, net::ArcTuple{ii, r.sat, r.sig2}, &net::ArcState::amb);
            o.carry_ok = lc1 != nullptr && lc2 != nullptr;
            o.relevel1_s = lc1 != nullptr ? lc1->relevel_s : 0.0;
            o.relevel2_s = lc2 != nullptr ? lc2->relevel_s : 0.0;
            o.latched = latched.count({ii, r.sat, r.sig1}) > 0 || latched.count({ii, r.sat, r.sig2}) > 0;
            const auto held_it = rf.links.find(o.id);
            if (held_it != rf.links.end() && held_it->second.held && station_ok
                && R.A_s.cols() == x_s.size() && xr.size() == R.A_r.cols()) {
                if (!resid_formed) {
                    resid = R.y - R.A_s * x_s - R.A_r * xr;   // post-fit O - C
                    resid_formed = true;
                }
                const std::optional<double> r1 = phaseResidual(R, resid, cols.at({r.sat, r.sig1}).first);
                const std::optional<double> r2 = phaseResidual(R, resid, cols.at({r.sat, r.sig2}).first);
                if (r1 && r2 && o.lambda2 > o.lambda1 && o.lambda1 > 0.0) {
                    const double l1s = o.lambda1 * o.lambda1, l2s = o.lambda2 * o.lambda2;
                    o.have_resid = true;
                    o.resid_if_m = (l2s * *r1 - l1s * *r2) / (l2s - l1s);
                }
            }
            links.push_back(o);
        }
    }

    // The audit of every link held in this epoch's solve.
    std::map<RingFixLinkId, RingFixAudit> audit_of;
    for (auto& [id, L] : rf.links) {
        if (!L.held) continue;
        const std::string name = (id.station >= 0 && static_cast<std::size_t>(id.station) < stations.size())
                                     ? stations[static_cast<std::size_t>(id.station)].name : std::string{};
        const RingFixAudit a = rf.audit.empty() ? RingFixAudit::Unlisted
                                                : ringFixAuditLink(rf.audit, name, id, L.n1, L.n2);
        audit_of[id] = a;
        L.wrong_now = a == RingFixAudit::Wrong;
        if (a == RingFixAudit::Right) ++rf.counters.audit_right;
        else if (a == RingFixAudit::Wrong) ++rf.counters.audit_wrong;
        else ++rf.counters.audit_unlisted;
    }
    std::map<RingFixLinkId, bool> held_before;
    for (const RingFixDecideObs& o : links) {
        const auto it = rf.links.find(o.id);
        held_before[o.id] = it != rf.links.end() && it->second.held;
    }

    const std::vector<RingFixEvent> events = ringFixDecideStep(rf, links, now_s);
    std::map<RingFixLinkId, const RingFixEvent*> event_of;
    for (const RingFixEvent& ev : events) event_of[ev.id] = &ev;
    for (const RingFixEvent& ev : events) {
        if (ev.kind != RingFixEvent::Kind::Hold) continue;
        const std::string name = (ev.id.station >= 0 && static_cast<std::size_t>(ev.id.station) < stations.size())
                                     ? stations[static_cast<std::size_t>(ev.id.station)].name : std::string{};
        const RingFixAudit a = rf.audit.empty() ? RingFixAudit::Unlisted
                                                : ringFixAuditLink(rf.audit, name, ev.id, ev.gate.n1, ev.gate.n2);
        if (a == RingFixAudit::Wrong) ++rf.counters.decided_wrong;
        else if (a == RingFixAudit::Right) ++rf.counters.decided_right;
        traces.emitEvent(t, "RINGFIX", "hold", ev.id.sat, name, ev.gate.sigma_if, kRingFixMaxSigmaCyc, "decide",
                         fmt::format("sig1={} sig2={} ring={} n1={} n2={} wl={} frac_if={:.3f} sigma_if={:.3f} "
                                     "frac_wl={:.3f} rule={} audit={}",
                                     ev.id.sig1, ev.id.sig2, rf.links.at(ev.id).ring, ev.gate.n1, ev.gate.n2,
                                     ev.gate.wl, ev.gate.frac_if, ev.gate.sigma_if, ev.gate.frac_wl,
                                     rf.rule == RingFixRule::Plain ? "plain" : "gated", auditName(a)));
    }

    // network_ring_fix.csv: one row per pair-family chord.
    if (traces.ring_fix_trace.is_open()) {
        for (const RingFixDecideObs& o : links) {
            const RingFixLink& L = rf.links.at(o.id);
            const auto ev = event_of.find(o.id);
            const char* state = "refused";
            std::string cause;
            if (held_before[o.id]) { state = "held"; }
            else if (ev != event_of.end() && ev->second->kind == RingFixEvent::Kind::Hold) { state = "decided"; }
            else if (ev != event_of.end()) { cause = ringFixRefuseName(ev->second->refuse); }
            const auto g = gate_of.find(o.id);
            const RingFixGate gr = g != gate_of.end() ? g->second : RingFixGate{};
            const auto au = audit_of.find(o.id);
            std::string audit;
            if (au != audit_of.end()) audit = auditName(au->second);
            else if (state[0] == 'd' && !rf.audit.empty())
                audit = auditName(ringFixAuditLink(rf.audit, stations[static_cast<std::size_t>(o.id.station)].name,
                                                   o.id, L.n1, L.n2));
            traces.ring_fix_trace
                << t.week << ',' << fmt::format("{:.3f}", t.tow) << ','
                << stations[static_cast<std::size_t>(o.id.station)].name << ',' << o.id.sat << ',' << o.id.sig1
                << ',' << o.id.sig2 << ',' << o.ring << ',' << (o.candidate ? 1 : 0) << ',' << state << ','
                << cause << ',' << (o.have_float ? cellOf(o.f1, 4) : std::string()) << ','
                << (o.have_float ? cellOf(o.f2, 4) : std::string()) << ','
                << (gr.valid ? cellOf(gr.n_if, 4) : std::string()) << ','
                << (gr.valid ? cellOf(gr.sigma_if, 4) : std::string()) << ','
                << (gr.valid ? cellOf(gr.frac_if, 4) : std::string()) << ','
                << (gr.valid ? std::to_string(gr.wl) : std::string()) << ','
                << (gr.valid ? cellOf(gr.frac_wl, 4) : std::string()) << ','
                << ((L.held || gr.valid) ? std::to_string(L.held ? L.n1 : gr.n1) : std::string()) << ','
                << ((L.held || gr.valid) ? std::to_string(L.held ? L.n2 : gr.n2) : std::string()) << ','
                << (o.have_lat1 ? std::to_string(o.lat1) : std::string()) << ','
                << (o.have_lat2 ? std::to_string(o.lat2) : std::string()) << ','
                << (o.have_resid ? cellOf(o.resid_if_m, 5) : std::string()) << ',' << L.streak << ','
                << audit << '\n';
        }
    }
}

// ---- Run-end report ----

int networkRingFixRunEnd(const NetworkRunEndView& v) {
    const NetworkRunContext& ctx = v.ctx;
    const std::shared_ptr<spdlog::logger>& log = v.log;
    // ---- End of the bindings ----
    if (!ctx.carry.ring_fix) return 0;
    const NetworkRingFix& rf = *ctx.carry.ring_fix;
    const RingFixCounters& C = rf.counters;
    long long held_end = 0;
    std::map<int, long long> held_by_ring;
    for (const auto& [id, L] : rf.links)
        if (L.held) { ++held_end; ++held_by_ring[L.ring]; }
    std::string by_ring, first, held_rings;
    for (int r = 0; r < 8; ++r) {
        if (C.decided_by_ring[r] > 0)
            by_ring += fmt::format("{}ring {}: {}", by_ring.empty() ? "" : ", ", r, C.decided_by_ring[r]);
        if (C.first_hold_s[r] >= 0.0)
            first += fmt::format("{}ring {} at TOW {:.0f}", first.empty() ? "" : ", ", r,
                                 std::fmod(C.first_hold_s[r], 604800.0));
    }
    for (const auto& [r, n] : held_by_ring)
        held_rings += fmt::format("{}ring {}: {}", held_rings.empty() ? "" : ", ", r, n);
    std::string released, refused;
    for (std::size_t k = 0; k < kRingFixReleaseCount; ++k)
        released += fmt::format("{}{} {}", k ? ", " : "", ringFixReleaseName(static_cast<RingFixRelease>(k)),
                                C.released[k]);
    for (std::size_t k = 0; k < kRingFixRefuseCount; ++k)
        refused += fmt::format("{}{} {}", k ? ", " : "", ringFixRefuseName(static_cast<RingFixRefuse>(k)),
                               C.refused[k]);
    long long rel_total = 0;
    for (std::size_t k = 0; k < kRingFixReleaseCount; ++k) rel_total += C.released[k];
    log->warn("Network (ring fix, rule {}): {} link(s) decided over {} decision epoch(s) ({}); first hold by "
              "ring: {}; held at the end {} ({}); {} held link-epoch(s); {} hold row(s) folded, {} skipped on a "
              "tree edge, {} without a column.",
              rf.rule == RingFixRule::Plain ? "plain" : "gated", C.decided, C.epochs_decided,
              by_ring.empty() ? "none" : by_ring, first.empty() ? "none" : first, held_end,
              held_rings.empty() ? "none" : held_rings, C.held_link_epochs, C.rows_injected,
              C.rows_gauge_skipped, C.rows_no_column);
    log->warn("Network (ring fix): released {} ({}); {} carried entr(ies) re-opened by the release; "
              "decided {} = released {} + held {}: {}.  Refused link-epochs: {}.",
              rel_total, released, C.carry_reopened, C.decided, rel_total, held_end,
              C.decided == rel_total + held_end ? "closed" : "NOT CLOSED", refused);
    if (rf.audit.empty())
        log->warn("Network (ring fix audit): no audit file; nothing was compared against truth.");
    else
        log->warn("Network (ring fix audit, '{}'): decisions right {}, WRONG {}; held link-epochs right {}, "
                  "WRONG {}, not listed {}.",
                  rf.audit_file, C.decided_right, C.decided_wrong, C.audit_right, C.audit_wrong,
                  C.audit_unlisted);
    return 0;
}

} // namespace GnssProcessor

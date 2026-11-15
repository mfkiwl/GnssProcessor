/**
 * @file RingFix.cpp
 * @brief The pure steps of the ring fix: the gate, the rings, the decision, the release and the
 *        audit (see the header).  The network seams are in RingFixSeams.cpp.
 */

#include "network/ar/RingFix.hpp"

#include <algorithm>
#include <cmath>
#include <fstream>
#include <limits>
#include <sstream>
#include <stdexcept>

namespace GnssProcessor {

const char* ringFixReleaseName(RingFixRelease c) {
    switch (c) {
        case RingFixRelease::Slip:    return "slip";
        case RingFixRelease::Refloat: return "refloat";
        case RingFixRelease::Gap:     return "gap";
        case RingFixRelease::Chain:   return "chain";
        case RingFixRelease::Monitor: return "monitor";
    }
    return "?";
}

const char* ringFixRefuseName(RingFixRefuse c) {
    switch (c) {
        case RingFixRefuse::NotCandidate: return "not_candidate";
        case RingFixRefuse::NoFloat:      return "no_float";
        case RingFixRefuse::Window:       return "window";
        case RingFixRefuse::Sigma:        return "sigma";
        case RingFixRefuse::Fraction:     return "fraction";
        case RingFixRefuse::Lattice:      return "lattice";
        case RingFixRefuse::Persist:      return "persist";
    }
    return "?";
}

RingFixGate ringFixGate(double f1, double f2, double q11, double q12, double q22,
                        double lambda1, double lambda2) {
    RingFixGate g;
    if (!(std::isfinite(f1) && std::isfinite(f2) && std::isfinite(q11) && std::isfinite(q12)
          && std::isfinite(q22) && std::isfinite(lambda1) && std::isfinite(lambda2)))
        return g;
    if (!(lambda1 > 0.0 && lambda2 > lambda1)) return g;
    const double r = lambda2 / lambda1;          // F1 / F2
    const double a = r / (r - 1.0);
    const double b = -1.0 / (r - 1.0);
    const double var_if = a * a * q11 + 2.0 * a * b * q12 + b * b * q22;
    const double var_wl = q11 + q22 - 2.0 * q12;
    if (!(var_if >= 0.0) || !(var_wl >= 0.0)) return g;
    const double w = f1 - f2;
    g.wl = std::llround(w);
    g.frac_wl = std::abs(w - static_cast<double>(g.wl));
    g.sigma_wl = std::sqrt(var_wl);
    g.n_if = (r * f1 - f2 - static_cast<double>(g.wl)) / (r - 1.0);
    g.n1 = std::llround(g.n_if);
    g.n2 = g.n1 - g.wl;
    g.frac_if = std::abs(g.n_if - static_cast<double>(g.n1));
    g.sigma_if = std::sqrt(var_if);
    g.valid = true;
    g.pass = g.sigma_if <= kRingFixMaxSigmaCyc && g.frac_if <= kRingFixMaxFracCyc;
    return g;
}

std::map<std::pair<std::string, std::string>, RingFixRingInfo>
ringFixRings(const RingFixTree& tree, const std::set<std::pair<std::string, std::string>>& held) {
    std::map<std::string, int> depth;
    // Every link at a vertex: the other end and whether the link is a tree edge.
    std::map<std::string, std::vector<std::pair<std::string, bool>>> nbr;
    for (const auto& [child, parent, d] : tree.edges) {
        depth[child] = d;
        depth.emplace(parent, d - 1);
        nbr[child].emplace_back(parent, true);
        nbr[parent].emplace_back(child, true);
    }
    for (const auto& [rx, sv] : tree.chords) {
        nbr[rx].emplace_back(sv, false);
        nbr[sv].emplace_back(rx, false);
    }
    const auto isHeld = [&](const std::string& u, const std::string& v) {
        // A chord is keyed (receiver key, satellite key).
        if (!u.empty() && u[0] == 'R') return held.count({u, v}) > 0;
        return held.count({v, u}) > 0;
    };
    std::map<std::pair<std::string, std::string>, RingFixRingInfo> out;
    for (const auto& [rx, sv] : tree.chords) {
        RingFixRingInfo info;
        const auto dr = depth.find(rx), ds = depth.find(sv);
        if (dr == depth.end() || ds == depth.end()) { out[{rx, sv}] = info; continue; }
        info.ring = std::max(dr->second, ds->second);
        info.inner = dr->second < ds->second ? rx : sv;
        const int d_in = std::min(dr->second, ds->second);
        bool complete = true;
        for (const auto& [u, is_tree] : nbr[info.inner]) {
            const auto du = depth.find(u);
            if (du == depth.end() || du->second >= d_in) continue;
            if (!is_tree && !isHeld(info.inner, u)) { complete = false; break; }
        }
        info.candidate = complete;
        out[{rx, sv}] = info;
    }
    return out;
}

namespace {

/// The window test of the damage gate (the header of ringFixDecideStep).
bool windowOk(const RingFixLink& L, const RingFixDecideObs& o, double last_tree_s, double now_s) {
    if (!o.carry_ok || o.latched) return false;
    if (o.relevel1_s > 0.0 && now_s - o.relevel1_s < kRingFixWindowS) return false;
    if (o.relevel2_s > 0.0 && now_s - o.relevel2_s < kRingFixWindowS) return false;
    if (L.chord_since_s < 0.0 || now_s - L.chord_since_s < kRingFixWindowS) return false;
    if (now_s - last_tree_s < kRingFixWindowS) return false;
    if (L.released_s >= 0.0 && now_s - L.released_s < kRingFixWindowS) return false;
    return true;
}

}  // namespace

std::vector<RingFixEvent> ringFixDecideStep(NetworkRingFix& rf,
                                            const std::vector<RingFixDecideObs>& links,
                                            double now_s) {
    std::vector<RingFixEvent> events;
    RingFixCounters& C = rf.counters;
    ++C.epochs_decided;
    for (const RingFixDecideObs& o : links) {
        RingFixLink& L = rf.links[o.id];
        L.lambda1 = o.lambda1;
        L.lambda2 = o.lambda2;
        if (o.have_float) {
            if (L.last_chord_s < 0.0 || now_s - L.last_chord_s > kRingFixGapS) L.chord_since_s = now_s;
            L.last_chord_s = now_s;
        }
        if (L.held) {
            ++C.held_link_epochs;
            if (o.have_resid && std::isfinite(o.resid_if_m)
                && std::abs(o.resid_if_m) > kRingFixMonitorBoundM) {
                if (++L.monitor_bad >= kRingFixMonitorEpochs) L.monitor_trip = true;
            } else {
                L.monitor_bad = 0;
            }
            continue;
        }
        RingFixEvent ev;
        ev.id = o.id;
        const auto refuse = [&](RingFixRefuse c) {
            ev.kind = RingFixEvent::Kind::Refuse;
            ev.refuse = c;
            ++C.refused[static_cast<std::size_t>(c)];
            if (c != RingFixRefuse::Persist) L.streak = 0;
            events.push_back(ev);
        };
        if (!o.candidate) { refuse(RingFixRefuse::NotCandidate); continue; }
        if (!o.have_float) { refuse(RingFixRefuse::NoFloat); continue; }
        ev.gate = ringFixGate(o.f1, o.f2, o.q11, o.q12, o.q22, o.lambda1, o.lambda2);
        if (!ev.gate.valid) { refuse(RingFixRefuse::NoFloat); continue; }
        bool decide = false;
        if (rf.rule == RingFixRule::Plain) {
            decide = true;
        } else {
            const auto lt = rf.last_tree_s.find({o.id.station, o.id.sat});
            const double last_tree =
                lt == rf.last_tree_s.end() ? -std::numeric_limits<double>::infinity() : lt->second;
            if (!windowOk(L, o, last_tree, now_s)) { refuse(RingFixRefuse::Window); continue; }
            if (ev.gate.sigma_if > kRingFixMaxSigmaCyc) { refuse(RingFixRefuse::Sigma); continue; }
            if (ev.gate.frac_if > kRingFixMaxFracCyc) { refuse(RingFixRefuse::Fraction); continue; }
            if ((o.have_lat1 && o.lat1 != ev.gate.n1) || (o.have_lat2 && o.lat2 != ev.gate.n2)) {
                refuse(RingFixRefuse::Lattice);
                continue;
            }
            if (L.streak > 0 && L.streak_n1 == ev.gate.n1 && L.streak_n2 == ev.gate.n2) {
                ++L.streak;
            } else {
                L.streak = 1;
                L.streak_n1 = ev.gate.n1;
                L.streak_n2 = ev.gate.n2;
            }
            if (L.streak < kRingFixPersistEpochs) { refuse(RingFixRefuse::Persist); continue; }
            decide = true;
        }
        if (!decide) continue;
        L.held = true;
        L.n1 = ev.gate.n1;
        L.n2 = ev.gate.n2;
        L.ring = o.ring;
        L.decided_s = now_s;
        L.stamp1 = o.relevel1_s;
        L.stamp2 = o.relevel2_s;
        L.root = o.root;
        L.absent_since_s = -1.0;
        L.monitor_bad = 0;
        L.monitor_trip = false;
        L.streak = 0;
        L.wrong_now = false;
        ++C.decided;
        const int ri = std::clamp(o.ring, 0, 7);
        ++C.decided_by_ring[ri];
        if (C.first_hold_s[ri] < 0.0) C.first_hold_s[ri] = now_s;
        ev.kind = RingFixEvent::Kind::Hold;
        events.push_back(ev);
    }
    return events;
}

std::vector<RingFixEvent> ringFixReleaseStep(NetworkRingFix& rf,
                                             const std::map<RingFixLinkId, RingFixHoldObs>& obs,
                                             double now_s) {
    std::vector<RingFixEvent> events;
    for (auto& [id, L] : rf.links) {
        if (!L.held) continue;
        const auto it = obs.find(id);
        bool release = false;
        RingFixRelease cause = RingFixRelease::Gap;
        if (it != obs.end()) {
            const RingFixHoldObs& o = it->second;
            const bool root_changed = !o.root.empty() && !L.root.empty() && o.root != L.root;
            const bool relevelled = !o.carry_ok || o.stamp1 > L.stamp1 || o.stamp2 > L.stamp2;
            if (o.tree_now || o.in_cut || root_changed) { release = true; cause = RingFixRelease::Chain; }
            else if (o.latched)                          { release = true; cause = RingFixRelease::Slip; }
            else if (o.present && relevelled)            { release = true; cause = RingFixRelease::Refloat; }
            else if (L.monitor_trip)                     { release = true; cause = RingFixRelease::Monitor; }
            else if (o.present)                          { L.absent_since_s = -1.0; }
        } else if (L.monitor_trip) {
            release = true;
            cause = RingFixRelease::Monitor;
        }
        if (!release && (it == obs.end() || !it->second.present)) {
            if (L.absent_since_s < 0.0) L.absent_since_s = now_s;
            if (now_s - L.absent_since_s > rf.max_gap_s) { release = true; cause = RingFixRelease::Gap; }
        }
        if (!release) continue;
        L.held = false;
        L.released_s = now_s;
        L.streak = 0;
        L.monitor_bad = 0;
        L.monitor_trip = false;
        L.absent_since_s = -1.0;
        L.wrong_now = false;
        ++rf.counters.released[static_cast<std::size_t>(cause)];
        RingFixEvent ev;
        ev.kind = RingFixEvent::Kind::Release;
        ev.id = id;
        ev.release = cause;
        events.push_back(ev);
    }
    return events;
}

std::map<std::tuple<std::string, std::string, std::string>, long long>
ringFixReadAuditFile(const std::string& path) {
    std::ifstream in(path);
    if (!in) throw std::runtime_error("network.ring_fix.audit_frame_file: cannot open '" + path + "'");
    std::string line;
    if (!std::getline(in, line)) throw std::runtime_error("ring fix audit file '" + path + "' is empty");
    if (!line.empty() && line.back() == '\r') line.pop_back();
    if (line.rfind("station,sat,signal,frame_int", 0) != 0)
        throw std::runtime_error("ring fix audit file '" + path
                                 + "': the header must begin station,sat,signal,frame_int");
    std::map<std::tuple<std::string, std::string, std::string>, long long> out;
    long long row = 1;
    while (std::getline(in, line)) {
        ++row;
        if (!line.empty() && line.back() == '\r') line.pop_back();
        if (line.empty()) continue;
        std::stringstream ss(line);
        std::string sta, sat, sig, val;
        if (!std::getline(ss, sta, ',') || !std::getline(ss, sat, ',') || !std::getline(ss, sig, ',')
            || !std::getline(ss, val, ','))
            throw std::runtime_error("ring fix audit file '" + path + "': malformed row "
                                     + std::to_string(row));
        long long v = 0;
        try {
            std::size_t used = 0;
            v = std::stoll(val, &used);
            if (used != val.size()) throw std::invalid_argument(val);
        } catch (...) {
            throw std::runtime_error("ring fix audit file '" + path + "': bad frame_int in row "
                                     + std::to_string(row));
        }
        if (!out.emplace(std::make_tuple(sta, sat, sig), v).second)
            throw std::runtime_error("ring fix audit file '" + path + "': duplicate arc in row "
                                     + std::to_string(row));
    }
    return out;
}

RingFixAudit ringFixAuditLink(
    const std::map<std::tuple<std::string, std::string, std::string>, long long>& audit,
    const std::string& station_name, const RingFixLinkId& id, long long n1, long long n2) {
    const auto a1 = audit.find({station_name, id.sat, id.sig1});
    const auto a2 = audit.find({station_name, id.sat, id.sig2});
    if (a1 == audit.end() && a2 == audit.end()) return RingFixAudit::Unlisted;
    if ((a1 != audit.end() && a1->second != n1) || (a2 != audit.end() && a2->second != n2))
        return RingFixAudit::Wrong;
    return RingFixAudit::Right;
}

} // namespace GnssProcessor

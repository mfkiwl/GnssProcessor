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
        case RingFixRefuse::Odds:         return "odds";
        case RingFixRefuse::Cap:          return "cap";
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
    // The likelihood ratio of the nearest and the next integer of a Gaussian float at distance d from
    // the nearest: exp(((1 - d)^2 - d^2) / (2 sigma^2)) = exp((1 - 2 d) / (2 sigma^2)).
    const auto logOdds = [](double d, double sigma) {
        return sigma > 0.0 ? (1.0 - 2.0 * d) / (2.0 * sigma * sigma)
                           : (d < 0.5 ? std::numeric_limits<double>::infinity() : 0.0);
    };
    g.log_odds_if = logOdds(g.frac_if, g.sigma_if);
    g.log_odds_wl = logOdds(g.frac_wl, g.sigma_wl);
    g.pass_odds = g.frac_if <= kRingFixMaxFracCyc && g.log_odds_if >= kRingFixMinLogOdds
               && g.log_odds_wl >= kRingFixMinLogOdds;
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
    if (rf.t0_s < 0.0) rf.t0_s = now_s;
    // The oracle phase (simulation only): every link with true integers is held at them; the rule waits.
    if (rf.oracle_until_s > 0.0 && now_s - rf.t0_s < rf.oracle_until_s) {
        for (const RingFixDecideObs& o : links) {
            RingFixLink& L = rf.links[o.id];
            L.lambda1 = o.lambda1;
            L.lambda2 = o.lambda2;
            if (o.have_float) {
                if (L.last_chord_s < 0.0 || now_s - L.last_chord_s > kRingFixGapS) L.chord_since_s = now_s;
                L.last_chord_s = now_s;
            }
            if (L.held) ++C.held_link_epochs;
            if (!o.have_truth) continue;
            if (L.held) {
                if (L.n1 != o.truth1 || L.n2 != o.truth2) {
                    L.n1 = o.truth1;
                    L.n2 = o.truth2;
                    ++C.oracle_corrected;
                }
                continue;
            }
            RingFixEvent ev;
            ev.id = o.id;
            ev.oracle = true;
            ev.gate.n1 = o.truth1;
            ev.gate.n2 = o.truth2;
            ev.gate.wl = o.truth1 - o.truth2;
            L.held = true;
            L.n1 = o.truth1;
            L.n2 = o.truth2;
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
            L.rebase_stamps = !o.carry_ok;
            L.inherited = false;
            L.oracle = true;
            ++C.decided;
            ++C.oracle_decided;
            const int ri = std::clamp(o.ring, 0, 7);
            ++C.decided_by_ring[ri];
            if (C.first_hold_s[ri] < 0.0) C.first_hold_s[ri] = now_s;
            ev.kind = RingFixEvent::Kind::Hold;
            events.push_back(ev);
        }
        return events;
    }
    // Change O: the links that passed every test this epoch, decided after the loop.
    std::vector<std::pair<const RingFixDecideObs*, RingFixEvent>> eligible;
    const auto hold = [&](RingFixLink& L, const RingFixDecideObs& o, RingFixEvent& ev) {
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
        L.rebase_stamps = false;
        L.inherited = false;
        L.oracle = false;
        ++C.decided;
        const int ri = std::clamp(o.ring, 0, 7);
        ++C.decided_by_ring[ri];
        if (C.first_hold_s[ri] < 0.0) C.first_hold_s[ri] = now_s;
        ev.kind = RingFixEvent::Kind::Hold;
        events.push_back(ev);
    };
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
        const bool candidate = rf.order == RingFixOrder::Certain ? o.have_float : o.candidate;
        if (!candidate) { refuse(RingFixRefuse::NotCandidate); continue; }
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
            if (rf.gate_rule == RingFixGateRule::Odds) {
                if (ev.gate.frac_if > kRingFixMaxFracCyc) { refuse(RingFixRefuse::Fraction); continue; }
                if (!ev.gate.pass_odds) { refuse(RingFixRefuse::Odds); continue; }
            } else {
                if (ev.gate.sigma_if > kRingFixMaxSigmaCyc) { refuse(RingFixRefuse::Sigma); continue; }
                if (ev.gate.frac_if > kRingFixMaxFracCyc) { refuse(RingFixRefuse::Fraction); continue; }
            }
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
        if (rf.order == RingFixOrder::Certain && rf.rule != RingFixRule::Plain) {
            eligible.emplace_back(&o, ev);
            continue;
        }
        hold(L, o, ev);
    }
    if (!eligible.empty()) {
        std::stable_sort(eligible.begin(), eligible.end(), [](const auto& a, const auto& b) {
            if (a.second.gate.log_odds_if != b.second.gate.log_odds_if)
                return a.second.gate.log_odds_if > b.second.gate.log_odds_if;
            return a.first->id < b.first->id;
        });
        int decided_now = 0;
        for (auto& [o, ev] : eligible) {
            RingFixLink& L = rf.links[o->id];
            if (decided_now < kRingFixMaxDecisionsPerEpoch) {
                hold(L, *o, ev);
                ++decided_now;
            } else {
                ev.kind = RingFixEvent::Kind::Refuse;
                ev.refuse = RingFixRefuse::Cap;
                ++C.refused[static_cast<std::size_t>(RingFixRefuse::Cap)];
                events.push_back(ev);   // the persistence count is kept
            }
        }
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
            if (L.rebase_stamps && o.carry_ok) {   // a cut release erased its carried entries
                L.stamp1 = o.stamp1;
                L.stamp2 = o.stamp2;
                L.rebase_stamps = false;
                ++rf.counters.stamps_rebased;
            }
            const bool root_changed = !o.root.empty() && !L.root.empty() && o.root != L.root;
            const bool relevelled = !o.carry_ok || o.stamp1 > L.stamp1 || o.stamp2 > L.stamp2;
            if (o.tree_now || o.in_cut || root_changed) { release = true; cause = RingFixRelease::Chain; }
            else if (o.latched)                          { release = true; cause = RingFixRelease::Slip; }
            else if (o.present && relevelled && !L.rebase_stamps) { release = true; cause = RingFixRelease::Refloat; }
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

// ---- Stage N2: held integers through the chain's events ------------------------------------------

bool ringFixCutStep(bool held_before, long long n_held, double target_cyc, bool sat_is_child,
                    long long& delta) {
    if (!held_before || !std::isfinite(target_cyc)) return false;
    const double r = std::round(target_cyc);
    if (std::abs(target_cyc - r) > 1e-6) return false;
    const long long k = std::llround(r);
    delta = sat_is_child ? n_held - k : k - n_held;
    return true;
}

RingFixCutOutcome ringFixApplyCuts(NetworkRingFix& rf, const std::vector<RingFixCut>& cuts, double now_s) {
    RingFixCutOutcome out;
    if (cuts.empty()) return out;
    for (const RingFixCut& c : cuts) {
        ++rf.counters.cuts;
        if (c.known) {
            ++rf.counters.cuts_known;
            if (c.delta == 0) ++rf.counters.cuts_known_zero;
        }
    }
    for (auto& [id, L] : rf.links) {
        if (!L.held) continue;
        long long d1 = 0, d2 = 0;
        bool unknown = false, touched = false;
        std::string rows, unknown_row;
        for (const RingFixCut& c : cuts) {
            const int band = c.signal == id.sig1 ? 1 : (c.signal == id.sig2 ? 2 : 0);
            if (band == 0) continue;
            const bool in_s = c.sats.count(id.sat) > 0;
            const bool in_r = c.stations.count(id.station) > 0;
            if (in_s || in_r) touched = true;
            if (in_s == in_r) continue;   // both ends in M, or none: the integer is kept
            if (!c.known) { unknown = true; unknown_row = c.row; continue; }
            const long long step = in_s ? -c.delta : c.delta;
            (band == 1 ? d1 : d2) += step;
            if (rows.find(c.row) == std::string::npos) rows += (rows.empty() ? "" : "+") + c.row;
        }
        if (unknown) {
            L.held = false;
            L.released_s = now_s;
            L.streak = 0;
            L.monitor_bad = 0;
            L.monitor_trip = false;
            L.absent_since_s = -1.0;
            L.rebase_stamps = false;
            ++rf.counters.released[static_cast<std::size_t>(RingFixRelease::Chain)];
            ++rf.counters.cut_released;
            out.released.emplace_back(id, unknown_row);
            continue;
        }
        if (d1 != 0 || d2 != 0) {
            L.n1 += d1;
            L.n2 += d2;
            ++rf.counters.reexpressed;
            out.reexpressed.emplace_back(id, d1, d2, rows);
        }
        if (touched) {
            L.rebase_stamps = true;
            ++out.touched;
        }
    }
    return out;
}

std::vector<RingFixEvent> ringFixInherit(NetworkRingFix& rf, const std::vector<RingFixInheritCand>& cands,
                                         const std::vector<RingFixCut>& cuts, double now_s) {
    std::vector<RingFixEvent> events;
    for (const RingFixInheritCand& c : cands) {
        if (c.latched) continue;
        RingFixLink& L = rf.links[c.id];
        if (L.held) continue;
        long long n1 = c.k1, n2 = c.k2;
        bool ok = true;
        for (const RingFixCut& cut : cuts) {
            const int band = cut.signal == c.id.sig1 ? 1 : (cut.signal == c.id.sig2 ? 2 : 0);
            if (band == 0) continue;
            const bool in_s = cut.sats.count(c.id.sat) > 0;
            const bool in_r = cut.stations.count(c.id.station) > 0;
            if (in_s == in_r) continue;
            if (!cut.known) { ok = false; break; }
            (band == 1 ? n1 : n2) += in_s ? -cut.delta : cut.delta;
        }
        if (!ok) continue;
        L.lambda1 = c.lambda1;
        L.lambda2 = c.lambda2;
        L.held = true;
        L.n1 = n1;
        L.n2 = n2;
        L.ring = c.ring;
        L.decided_s = now_s;
        L.root = c.root;
        L.absent_since_s = -1.0;
        L.monitor_bad = 0;
        L.monitor_trip = false;
        L.streak = 0;
        L.wrong_now = false;
        L.rebase_stamps = true;   // its carried entries were erased by the cut or are being re-created
        L.inherited = true;
        L.oracle = false;
        ++rf.counters.decided;
        ++rf.counters.inherited;
        const int ri = std::clamp(c.ring, 0, 7);
        ++rf.counters.decided_by_ring[ri];
        if (rf.counters.first_hold_s[ri] < 0.0) rf.counters.first_hold_s[ri] = now_s;
        RingFixEvent ev;
        ev.kind = RingFixEvent::Kind::Hold;
        ev.id = c.id;
        ev.inherited = true;
        ev.gate.n1 = n1;
        ev.gate.n2 = n2;
        ev.gate.wl = n1 - n2;
        events.push_back(ev);
    }
    return events;
}

// ---- Truth (simulation only) ----------------------------------------------------------------------

long long ringFixWindupBranch(double w) { return static_cast<long long>(std::floor(w + 0.5)); }

void ringFixTruthObserve(RingFixTruth& T, int station, const std::string& sat, double tow) {
    auto& list = T.branches[{station, sat}];
    if (!list.empty() && tow - list.back().last_tow <= kRingFixArcGapS && tow >= list.back().last_tow) {
        list.back().last_tow = tow;
        return;
    }
    RingFixTruth::Branch b;
    b.start_tow = tow;
    b.last_tow = tow;
    const auto w = T.windup.find({station, sat});
    bool found = false;
    if (w != T.windup.end()) {
        const auto it = w->second.lower_bound(tow - 1e-3);
        if (it != w->second.end() && std::abs(it->first - tow) <= 1e-3) {
            b.k = ringFixWindupBranch(it->second);
            found = true;
        }
    }
    if (!found) ++T.arcs_without_windup;
    list.push_back(b);
}

bool ringFixTruthN(const RingFixTruth& T, int station, const std::string& sat, const std::string& signal,
                   double now_s, double tow, long long& n) {
    // A slip stamped at an epoch is in that epoch's observation; the epoch's clock can sit a few
    // microseconds before the stamp, so the bound takes half a second of slack.
    constexpr double kSlipStampSlackS = 0.5;
    const auto a = T.arcs.find({station, sat, signal});
    if (a == T.arcs.end()) return false;
    long long v = a->second.n_int;
    for (const auto& [s, d] : a->second.slips) {
        if (s > now_s + kSlipStampSlackS) break;
        v += d;
    }
    const auto b = T.branches.find({station, sat});
    if (b != T.branches.end()) {
        long long k = 0;
        for (const RingFixTruth::Branch& br : b->second) {
            if (br.start_tow <= tow + 1e-6) k = br.k;
            else break;
        }
        v += k;
    }
    n = v;
    return true;
}

bool ringFixTruthFrameInteger(const RingFixTruth& T,
                              const std::vector<std::tuple<int, std::string, std::string, int>>& terms,
                              double pin_sum_cyc, bool pins_integer, double now_s, double tow, long long& n) {
    if (!pins_integer || !std::isfinite(pin_sum_cyc)) return false;
    double total = -pin_sum_cyc;
    for (const auto& [sta, sat, sig, coeff] : terms) {
        long long m = 0;
        if (!ringFixTruthN(T, sta, sat, sig, now_s, tow, m)) return false;
        total += static_cast<double>(coeff) * static_cast<double>(m);
    }
    const double r = std::round(total);
    if (std::abs(total - r) > 1e-6) return false;
    n = std::llround(r);
    return true;
}

std::map<std::string, std::map<double, double>> ringFixParseWindupCsv(const std::string& path) {
    std::ifstream in(path);
    if (!in) throw std::runtime_error("ring fix truth: cannot open '" + path + "'");
    std::string line;
    if (!std::getline(in, line)) throw std::runtime_error("ring fix truth: '" + path + "' is empty");
    if (!line.empty() && line.back() == '\r') line.pop_back();
    if (line.rfind("week,tow_s,satellite,windup_cycles", 0) != 0)
        throw std::runtime_error("ring fix truth: '" + path
                                 + "': the header must begin week,tow_s,satellite,windup_cycles");
    std::map<std::string, std::map<double, double>> out;
    long long row = 1;
    while (std::getline(in, line)) {
        ++row;
        if (!line.empty() && line.back() == '\r') line.pop_back();
        if (line.empty()) continue;
        std::stringstream ss(line);
        std::string week, tow, sat, wu;
        if (!std::getline(ss, week, ',') || !std::getline(ss, tow, ',') || !std::getline(ss, sat, ',')
            || !std::getline(ss, wu, ','))
            throw std::runtime_error("ring fix truth: '" + path + "': malformed row " + std::to_string(row));
        try {
            out[sat][std::stod(tow)] = std::stod(wu);
        } catch (...) {
            throw std::runtime_error("ring fix truth: '" + path + "': bad number in row " + std::to_string(row));
        }
    }
    return out;
}

} // namespace GnssProcessor

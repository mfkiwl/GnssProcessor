/**
 * @file ChainChordTable.cpp
 * @brief The chord table's quantities of the eq34 chain (see the header).
 */

#include "network/solve/ChainChordTable.hpp"

#include "common/GnssIdentity.hpp"      // SatId, SignalId, nominalWavelengthOfDigitM
#include "network/driver/RunTypes.hpp"  // StationAssembly, PlAmb

#include <algorithm>
#include <cmath>
#include <optional>

namespace GnssProcessor {

ChainAmbColumns chainAmbColumns(const StationAssembly& R) {
    ChainAmbColumns out;
    const std::vector<PlAmb>& src = R.pl_amb.empty() ? R.qc_amb : R.pl_amb;
    for (const PlAmb& a : src) out[{a.sat, a.signal}] = {a.col, a.x_lin};
    return out;
}

double chainWavelengthM(const std::string& sat, const std::string& signal) {
    const std::optional<SatId> id = SatId::parse(sat);
    if (!id) return 0.0;
    const std::optional<SignalId> sig = SignalId::fromObsCode(id->sys, signal);
    if (!sig) return 0.0;
    const double lam = nominalWavelengthOfDigitM(id->sys, sig->digit);
    return (std::isfinite(lam) && lam > 0.0) ? lam : 0.0;
}

std::vector<std::pair<std::string, std::string>> chainArcFamilies(const std::string& sat,
                                                                  const std::set<std::string>& sigs,
                                                                  const ChainConfiguredPairs* extra) {
    std::vector<std::pair<std::string, std::string>> out = chainPairFamilies(sigs);
    if (extra == nullptr || sat.empty()) return out;
    const auto it = extra->find(sat[0]);
    if (it == extra->end()) return out;
    for (const auto& p : it->second)
        if (sigs.count(p.first) != 0 && sigs.count(p.second) != 0
            && std::find(out.begin(), out.end(), p) == out.end())
            out.push_back(p);
    return out;
}

std::vector<std::pair<std::string, std::string>> chainPairFamilies(const std::set<std::string>& sigs) {
    std::vector<std::pair<std::string, std::string>> out;
    std::string other;
    for (const std::string& s : sigs)
        if (s.size() >= 2 && s[1] != '1' && (other.empty() || s[1] < other[1])) other = s;
    if (other.empty()) return out;
    for (const std::string& s : sigs)
        if (s.size() >= 2 && s[1] == '1') out.emplace_back(s, other);
    return out;
}

std::vector<ChainChordRow> chainStationChordRows(
    int station, const std::string& station_name, const ChainAmbColumns& cols,
    const std::set<std::tuple<int, std::string, std::string>>& tree_arcs,
    const std::set<std::string>& chain_signals, const ChainConfiguredPairs* extra) {
    std::map<std::string, std::set<std::string>> sigs_of;   // sat -> its phase signals
    for (const auto& [k, v] : cols) {
        (void)v;
        if (k.second.find('_') != std::string::npos) continue;
        sigs_of[k.first].insert(k.second);
    }
    std::vector<ChainChordRow> rows;
    for (const auto& [sat, sigs] : sigs_of) {
        const std::string c = sat.substr(0, 1);
        for (const auto& [s1, s2] : chainArcFamilies(sat, sigs, extra)) {
            if (!chain_signals.count(c + "|" + s1) || !chain_signals.count(c + "|" + s2)) continue;
            if (tree_arcs.count({station, sat, s1}) || tree_arcs.count({station, sat, s2})) continue;
            ChainChordRow r;
            r.family = c + "|" + s1 + "+" + s2;
            r.sig1 = s1; r.sig2 = s2;
            r.station = station; r.station_name = station_name; r.sat = sat;
            rows.push_back(r);
        }
    }
    return rows;
}

bool chainLatticeChordInteger(const arcgraph::CycleLattice& lattice, const ChainChordCycle& c,
                              long long& out) {
    if (!c.pins_integer || lattice.rows.empty()) return false;
    const std::optional<long long> v = arcgraph::latticeImplied(lattice, c.cycle);
    if (!v) return false;
    out = *v - std::llround(c.pin_sum_cyc);
    return true;
}

bool chainChordFloats(const NetworkEstimator& est, std::size_t est_idx, const Eigen::VectorXd& x_s,
                      const NetworkEstimator::Datum& shared_datum, const ChainAmbColumns& cols,
                      std::vector<ChainChordRow>& rows, std::vector<char>& ok,
                      Eigen::VectorXd* xr_out) {
    ok.assign(rows.size(), 0);
    Eigen::VectorXd xr;
    std::vector<std::pair<std::size_t, Eigen::Index>> reqs;
    std::vector<std::vector<int>> blocks;
    for (const ChainChordRow& r : rows) {
        const int k = static_cast<int>(reqs.size());
        reqs.emplace_back(est_idx, cols.at({r.sat, r.sig1}).first);
        reqs.emplace_back(est_idx, cols.at({r.sat, r.sig2}).first);
        blocks.push_back({k, k + 1});
    }
    std::vector<Eigen::MatrixXd> covs;
    try {
        xr = est.reconstructStation(est_idx, x_s);
        covs = est.blockConditionalCovariances(reqs, shared_datum, blocks);
    } catch (...) { return false; }
    if (covs.size() != rows.size()) return false;
    for (std::size_t r_i = 0; r_i < rows.size(); ++r_i) {
        ChainChordRow& r = rows[r_i];
        const auto& c1 = cols.at({r.sat, r.sig1});
        const auto& c2 = cols.at({r.sat, r.sig2});
        const double l1 = chainWavelengthM(r.sat, r.sig1), l2 = chainWavelengthM(r.sat, r.sig2);
        if (!(l1 > 0.0 && l2 > 0.0) || c1.first >= xr.size() || c2.first >= xr.size()) continue;
        const Eigen::MatrixXd& C = covs[r_i];
        if (C.rows() != 2 || C.cols() != 2) continue;
        r.float_cyc_1 = (c1.second + xr(c1.first)) / l1;
        r.float_cyc_2 = (c2.second + xr(c2.first)) / l2;
        r.q11 = C(0, 0) / (l1 * l1);
        r.q12 = C(0, 1) / (l1 * l2);
        r.q22 = C(1, 1) / (l2 * l2);
        ok[r_i] = 1;
    }
    if (xr_out != nullptr) *xr_out = std::move(xr);
    return true;
}

} // namespace GnssProcessor

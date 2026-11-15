#pragma once
/**
 * @file ChainChordTable.hpp
 * @brief The chord table's quantities of the eq34 chain: a station's ambiguity columns, the pair
 *        families of its signals, a chord's two-band float with its conditional covariance, and
 *        the integer the producer's lattice implies for a chord.
 *
 * One owner for what the frame observatory (network/solve/ChainFrame.hpp, the chord table of
 * network_chain_frame.csv) and the ring fix (network/ar/RingFix.hpp) both read: the observatory
 * traces them, the ring fix decides on them.  Pure reads of the solved epoch.
 */

#include "network/solve/ChainFrame.hpp"   // ChainChordRow, ChainChordCycle
#include "network/solve/Estimator.hpp"    // NetworkEstimator (Datum)

#include <tuple>

#include <Eigen/Dense>

#include <cstddef>
#include <map>
#include <set>
#include <string>
#include <utility>
#include <vector>

namespace GnssProcessor {

struct StationAssembly;   // network/driver/RunTypes.hpp

/// A station's ambiguity columns this epoch: (satellite, signal) -> (A_r column, linearization point).
using ChainAmbColumns = std::map<std::pair<std::string, std::string>, std::pair<Eigen::Index, double>>;

/**
 * @brief A station's ambiguity columns: its post-solve ambiguity pool (@c pl_amb, else @c qc_amb).
 * @param R The station's assembled block.
 * @return (satellite, signal) -> (A_r column, linearization point).
 */
ChainAmbColumns chainAmbColumns(const StationAssembly& R);

/**
 * @brief The carrier wavelength of a phase signal of a satellite's constellation.
 * @param sat    Satellite ("G05").
 * @param signal Phase signal ("L1C").
 * @return The nominal wavelength (m); 0 when the satellite or signal does not parse or has none.
 */
double chainWavelengthM(const std::string& sat, const std::string& signal);

/**
 * @brief The band-1 and band-2 signals of a pair family for one arc: every band-1 (digit '1')
 *        signal pairs with the arc's lowest-digit signal of another band.
 * @param sigs The arc's phase signals.
 * @return (band-1 signal, band-2 signal) pairs; empty when no other band is present.
 */
std::vector<std::pair<std::string, std::string>> chainPairFamilies(const std::set<std::string>& sigs);

/**
 * @brief One station's chords of the chord table: every arc of a pair family whose two bands are
 *        chain groups and neither of which is a tree edge.
 *
 * Ionosphere-free labels (a signal with '_') are not phase signals of a band and are skipped.
 *
 * @param station       The station (roster index).
 * @param station_name  Its name.
 * @param cols          Its ambiguity columns (@ref chainAmbColumns).
 * @param tree_arcs     This epoch's tree edges, (station, satellite, signal).
 * @param chain_signals This epoch's chain groups, "<constellation key>|<signal>".
 * @return The rows with family, sig1, sig2, station, station_name and sat set, in satellite order.
 */
std::vector<ChainChordRow> chainStationChordRows(
    int station, const std::string& station_name, const ChainAmbColumns& cols,
    const std::set<std::tuple<int, std::string, std::string>>& tree_arcs,
    const std::set<std::string>& chain_signals);

/**
 * @brief The integer the producer's lattice of fixed cycles implies for a chord (cycles).
 * @param lattice The lattice.
 * @param c       The chord's fundamental cycle in this epoch's tree.
 * @param[out] out The chord's integer, written only on success.
 * @return True when every target on the path is an integer, the lattice is not empty and it
 *         determines the cycle.
 */
bool chainLatticeChordInteger(const arcgraph::CycleLattice& lattice, const ChainChordCycle& c,
                              long long& out);

/**
 * @brief The two-band floats and 2x2 conditional covariances of one station's chords.
 *
 * The station is reconstructed once (@c reconstructStation) and the covariances of all rows are
 * taken in one call (@c blockConditionalCovariances, one 2x2 block per row, band 1 then band 2).
 * A row is filled when both wavelengths are known, both columns lie inside the reconstruction
 * and its block is 2x2: float_cyc_j = (x_lin_j + x_r(col_j)) / lambda_j and the covariance in
 * cycles squared, unscaled.
 *
 * @param est          The solved estimator.
 * @param est_idx      The station's index in the estimator.
 * @param x_s          The shared solution.
 * @param shared_datum The epoch's shared datum pins.
 * @param cols         The station's ambiguity columns; every row's (sat, sig1) and (sat, sig2) must be in it.
 * @param rows         [in/out] Rows with sat, sig1 and sig2 set; the floats and covariances are written.
 * @param[out] ok      One flag per row: the row was filled.
 * @param[out] xr_out  Optional: the station's reconstruction.
 * @return False when the reconstruction or the covariances threw or returned a block count
 *         different from the rows (nothing filled); true otherwise.
 */
bool chainChordFloats(const NetworkEstimator& est, std::size_t est_idx, const Eigen::VectorXd& x_s,
                      const NetworkEstimator::Datum& shared_datum, const ChainAmbColumns& cols,
                      std::vector<ChainChordRow>& rows, std::vector<char>& ok,
                      Eigen::VectorXd* xr_out = nullptr);

} // namespace GnssProcessor

#pragma once
/**
 * @file RingFix.hpp
 * @brief Integer fixing in the network, ring by ring outward from the eq34 chain's root
 *        (@c network.ring_fix.*, default off).
 *
 * ## What it does
 *
 * The eq34 chain pins the ambiguities of a spanning tree per band at integer targets and the
 * root receiver's phase bias, so every other link (a chord) has, in the chain's frame, an
 * absolute ambiguity equal to its wavelength times an integer.  This mechanism decides those
 * integers for chords of a pair family (band 1 and band 2 of a constellation), holds them in
 * the network's own solve, and releases them at every event that can invalidate them:
 *
 *  1. **Decide** (after the solve of epoch t, @ref networkRingFixDecide): a chord is a candidate
 *     ring by ring outward from the root (@ref ringFixRings); its two-band float passes the
 *     gate (@ref ringFixGate: the wide lane rounded first, the ionosphere-free row with the wide
 *     lane rounded, formal sigma and fraction bounds), the damage gate (an event window, the
 *     lattice veto) and a persistence count (@ref ringFixDecideStep).
 *  2. **Hold** (from epoch t + 1, in PASS B, @ref networkRingFixPriors): one diagonal prior row
 *     per band at lambda times the integer, the row shape of the simulation-only oracle pin.
 *  3. **Release** (before PASS B, @ref networkRingFixHoldEpoch and @ref ringFixReleaseStep): at a
 *     slip latch, a refloat by another mechanism, a gap beyond the leveling horizon, a chain event
 *     that touches the link, or the residual monitor; the carried entries are re-opened by the
 *     vehicle's drop (or erased on the leveling vehicle), so a released link is never held at a
 *     stale level.
 *  4. **Audit** (simulation only, @c network.ring_fix.audit_frame_file): every held integer at
 *     every epoch against a frame-target file.
 *
 * Both edges of a hold are events with identities (standing invariant 7): a @c RINGFIX @c hold
 * row at the decision and a @c RINGFIX @c release row with its cause, in network_events.csv; the
 * per-epoch trace is network_ring_fix.csv and the run-end line counts every decision, release,
 * refusal and audit verdict.
 *
 * ## Off path
 *
 * Without @c network.ring_fix.enable the run state (@c NetworkCarryState::ring_fix) is null and
 * every call site tests it first, so no branch below is reachable and the output is
 * byte-identical.
 *
 * The rule's numbers are constants of this file, frozen by the card that pre-registered the
 * mechanism before any graded run; they are not keys.
 */

#include "network/state/Entities.hpp"   // net::ArcTable

#include <spdlog/spdlog.h>

#include <cstddef>
#include <cstdint>
#include <fstream>
#include <map>
#include <memory>
#include <set>
#include <string>
#include <tuple>
#include <utility>
#include <vector>

namespace GnssProcessor {

// ---- The frozen rule --------------------------------------------------------------------------

/// The gate's bound on the formal sigma of the ionosphere-free N1 (cycles).
inline constexpr double kRingFixMaxSigmaCyc = 0.10;
/// The gate's bound on the fraction of the ionosphere-free N1 (cycles).
inline constexpr double kRingFixMaxFracCyc = 0.20;
/// The damage gate's event window (s): no decision on a link with an event inside it.
inline constexpr double kRingFixWindowS = 600.0;
/// A pause longer than this between two epochs at which a link is a chord with a float restarts
/// its continuity count (s).
inline constexpr double kRingFixGapS = 45.0;
/// Epochs at which a candidate must pass the gate with the same integers before it is decided.
inline constexpr int kRingFixPersistEpochs = 10;
/// The hold row's sigma on each band's ambiguity column (m): the oracle pin's row.
inline constexpr double kRingFixHoldSigmaM = 1.0e-4;
/// The monitor's bound on the held link's post-fit ionosphere-free phase residual (m).
inline constexpr double kRingFixMonitorBoundM = 0.03;
/// Consecutive epochs above the monitor's bound that release a held link.
inline constexpr int kRingFixMonitorEpochs = 4;
/// A released link's carried variance is re-opened to at least this (m^2): a link held from its first
/// stash has the hold's own variance as its birth variance, which a drop would restore.
inline constexpr double kRingFixReleaseFloorM2 = 1.0;
/// Change O: at most this many links are decided per epoch, the most certain first.
inline constexpr int kRingFixMaxDecisionsPerEpoch = 3;
/// Change L: the bound on the log of the likelihood ratio between the nearest and the next integer,
/// ln(1e6), for N1 and for the wide lane.
inline constexpr double kRingFixMinLogOdds = 13.815510557964274;

/// The order of the decisions (@c network.ring_fix.order).
enum class RingFixOrder : std::uint8_t {
    Ring,     ///< Ring by ring: a link waits until its inner vertex's links towards the root are held.
    Certain,  ///< Change O: every chord with a float is a candidate; the most certain decided first, a few per epoch.
};

/// The gate of the decisions (@c network.ring_fix.gate).
enum class RingFixGateRule : std::uint8_t {
    Sigma,  ///< The frozen gate: the formal sigma and the fraction of the ionosphere-free N1.
    Odds,   ///< Change L: the log-odds of N1 and of the wide lane's own float, and the fraction of N1.
};

/// The decision rule of a run (@c network.ring_fix.rule).
enum class RingFixRule : std::uint8_t {
    Gated,  ///< The frozen rule: the gate, the damage gate and the persistence count.
    Plain,  ///< The negative control: every candidate with a float is rounded and held at once.
    Log,    ///< Log only: the frozen rule is evaluated and traced, nothing is held (the products are unchanged).
};

/// Why a held link was released.
enum class RingFixRelease : std::uint8_t {
    Slip,     ///< Either band in the epoch's free-epoch latch (any slip detector or re-entry response).
    Refloat,  ///< Either band's carried entry dropped or erased by another mechanism (RAIM, gap cliff, screen).
    Gap,      ///< The link absent, or no chord of its pair family, for longer than the leveling horizon.
    Chain,    ///< The link became a tree link, lies on a cut release's moved side, or its component's root changed.
    Monitor,  ///< The post-fit ionosphere-free phase residual above its bound at consecutive epochs.
};
/// Number of release causes.
inline constexpr std::size_t kRingFixReleaseCount = 5;

/// Why a link that is not held was not decided at an epoch (the first test it failed).
enum class RingFixRefuse : std::uint8_t {
    NotCandidate,  ///< Its ring's turn has not come: a link of its inner vertex towards the root is not held.
    NoFloat,       ///< No usable two-band float or covariance this epoch.
    Window,        ///< An event inside the window (re-level, latch, gap, tree link, release) or a missing carry.
    Sigma,         ///< The formal sigma of the ionosphere-free N1 above its bound.
    Fraction,      ///< The fraction of the ionosphere-free N1 above its bound.
    Lattice,       ///< The producer's lattice of fixed cycles implies another integer on a band.
    Persist,       ///< Passed this epoch, the persistence count not yet reached.
    Odds,          ///< Change L: the log-odds of N1 or of the wide lane below the bound.
    Cap,           ///< Change O: passed every test, passed over by the per-epoch cap (the count is kept).
    WlFraction,    ///< Passed every other test (persistence included); the wide lane's fraction above network.ring_fix.wl_frac_max.
};
/// Number of refusal causes.
inline constexpr std::size_t kRingFixRefuseCount = 10;

/**
 * @brief The name of a decision rule ("gated", "plain", "log").
 * @param r The rule.
 * @return Its name as a static string; "?" for a value outside the enum.
 */
const char* ringFixRuleName(RingFixRule r);

/**
 * @brief The name of a release cause ("slip", "refloat", "gap", "chain", "monitor").
 * @param c The cause.
 * @return Its name as a static string; "?" for a value outside the enum.
 */
const char* ringFixReleaseName(RingFixRelease c);

/**
 * @brief The name of a refusal cause ("not_candidate", "no_float", "window", "sigma",
 *        "fraction", "lattice", "persist", "odds", "cap", "wl_fraction").
 * @param c The cause.
 * @return Its name as a static string; "?" for a value outside the enum.
 */
const char* ringFixRefuseName(RingFixRefuse c);

// ---- The gate ---------------------------------------------------------------------------------

/// The gate's reading of one two-band float.
struct RingFixGate {
    bool      valid{false};    ///< The inputs were finite and the covariance usable.
    long long wl{0};           ///< The rounded wide lane, round(f1 - f2) (cycles).
    long long n1{0};           ///< Band 1's integer, round of the ionosphere-free row with the wide lane rounded.
    long long n2{0};           ///< Band 2's integer, n1 - wl.
    double    n_if{0.0};       ///< The ionosphere-free row with the wide lane rounded (cycles of band 1).
    double    sigma_if{0.0};   ///< Its formal sigma (cycles).
    double    frac_if{0.0};    ///< |n_if - n1| (cycles).
    double    sigma_wl{0.0};   ///< The wide lane's formal sigma (cycles).
    double    frac_wl{0.0};    ///< |(f1 - f2) - wl| (cycles).
    bool      pass{false};     ///< sigma_if and frac_if within the frozen bounds.
    double    log_odds_if{0.0};  ///< ln of the likelihood ratio of N1's nearest and next integer, (1 - 2 frac_if) / (2 sigma_if^2).
    double    log_odds_wl{0.0};  ///< The same for the wide lane's own float, (1 - 2 frac_wl) / (2 sigma_wl^2).
    bool      pass_odds{false};  ///< Change L: frac_if within its bound and both log-odds at least kRingFixMinLogOdds.
};

/**
 * @brief The gate on one link's two-band float: the wide lane rounded first, then band 1's
 *        integer from the ionosphere-free row with the wide lane rounded.
 *
 * With r = lambda2 / lambda1 (= F1 / F2), the row is n = (r f1 - f2 - z) / (r - 1) with
 * z = round(f1 - f2); n1 = round(n), n2 = n1 - z.  Its formal variance is
 * a^2 q11 + 2 a b q12 + b^2 q22 with a = r / (r - 1), b = -1 / (r - 1).  The link passes when the
 * sigma is at most @ref kRingFixMaxSigmaCyc and |n - n1| at most @ref kRingFixMaxFracCyc.
 *
 * @param f1      Band-1 float (cycles).
 * @param f2      Band-2 float (cycles).
 * @param q11     Band-1 variance (cycles^2).
 * @param q12     Band-1, band-2 covariance (cycles^2).
 * @param q22     Band-2 variance (cycles^2).
 * @param lambda1 Band-1 wavelength (m).
 * @param lambda2 Band-2 wavelength (m), longer than band 1's.
 * @param sigma_scale A factor on both formal sigmas in the two log-odds (network.ring_fix.sigma_scale;
 *        1, the default, uses the formal sigmas).  @c sigma_if, @c sigma_wl and @c pass keep the
 *        formal sigmas.
 * @return The reading; @c valid false for non-finite inputs, a negative variance of the row or
 *         wavelengths that do not order.
 */
RingFixGate ringFixGate(double f1, double f2, double q11, double q12, double q22,
                        double lambda1, double lambda2, double sigma_scale = 1.0);

// ---- Rings and candidates ---------------------------------------------------------------------

/// A link's identity: the station (roster index), the satellite and its pair family's signals.
struct RingFixLinkId {
    int         station{-1};  ///< Roster index.
    std::string sat;          ///< Satellite ("G05").
    std::string sig1;         ///< Band-1 phase signal ("L1C").
    std::string sig2;         ///< Band-2 phase signal ("L2W").
    /// @brief Strict weak order (station, satellite, band 1, band 2).
    /// @param o The other identity.
    /// @return True when this identity sorts first.
    bool operator<(const RingFixLinkId& o) const {
        return std::tie(station, sat, sig1, sig2) < std::tie(o.station, o.sat, o.sig1, o.sig2);
    }
};

/// One band's tree and chords, as the rings read them.  Vertices are keys: "R:<station index>"
/// for a receiver, "S:<satellite>" for a satellite (the chain record's keys).
struct RingFixTree {
    /// Tree edges: (child, parent, the child's depth below its component's root).
    std::vector<std::tuple<std::string, std::string, int>> edges;
    /// Chords: (receiver key, satellite key).
    std::vector<std::pair<std::string, std::string>> chords;
};

/// A chord's place in the rings.
struct RingFixRingInfo {
    int         ring{-1};          ///< The larger depth of its two vertices (-1: a vertex not in the tree).
    std::string inner;             ///< The vertex of smaller depth.
    bool        candidate{false};  ///< Every link of the inner vertex towards the root is held.
};

/**
 * @brief The rings of one band's chords and which of them are candidates.
 *
 * A vertex's depth is read from the tree edges (a child's depth is given, its parent's is one
 * less).  A chord's ring is the larger depth of its two vertices and its inner vertex the one of
 * smaller depth.  The chord is a candidate when every link of its inner vertex to a vertex of
 * smaller depth than the inner vertex is held: a tree link always is, a chord when it is in
 * @p held.  A ring-2 chord's inner vertex (a satellite at depth 1) reaches the root through its
 * tree link alone, so ring 2 is always a candidate.
 *
 * @param tree One band's tree edges and chords.
 * @param held The chords held now, as (receiver key, satellite key).
 * @return Every chord of @p tree with its ring, inner vertex and candidacy.
 */
std::map<std::pair<std::string, std::string>, RingFixRingInfo>
ringFixRings(const RingFixTree& tree, const std::set<std::pair<std::string, std::string>>& held);

// ---- The run state ------------------------------------------------------------------------------

/// One link's state across epochs.
struct RingFixLink {
    double    lambda1{0.0};          ///< Band-1 wavelength (m).
    double    lambda2{0.0};          ///< Band-2 wavelength (m).
    double    chord_since_s{-1.0};   ///< Start of the current run of epochs at which it is a chord with a float (-1: none).
    double    last_chord_s{-1.0};    ///< Last epoch at which it was a chord with a float (-1: never).
    int       streak{0};             ///< Consecutive candidate epochs that passed with the same integers.
    long long streak_n1{0};          ///< The streak's band-1 integer.
    long long streak_n2{0};          ///< The streak's band-2 integer.
    bool      held{false};           ///< Held now.
    long long n1{0};                 ///< The held band-1 integer (cycles).
    long long n2{0};                 ///< The held band-2 integer (cycles).
    int       ring{-1};              ///< The ring at the decision.
    double    decided_s{-1.0};       ///< When it was decided (continuous GPS seconds; -1: never).
    double    stamp1{0.0};           ///< Band 1's carried re-level stamp when it was decided.
    double    stamp2{0.0};           ///< Band 2's carried re-level stamp when it was decided.
    std::string root;                ///< Its component's root receiver when it was decided.
    double    absent_since_s{-1.0};  ///< Held and absent since (-1: present).
    int       monitor_bad{0};        ///< Consecutive epochs above the monitor's bound.
    bool      monitor_trip{false};   ///< The monitor asks for a release at the next epoch.
    double    released_s{-1.0};      ///< Its last release (-1: never).
    bool      wrong_now{false};      ///< The audit found its held integers wrong at the last epoch.
    bool      rebase_stamps{false};  ///< A cut release erased its carried entries: take the next stamps as the baseline.
    bool      inherited{false};      ///< Held as an old host of a cut (not decided by the rule).
    bool      oracle{false};         ///< Held by the oracle phase.
    bool      log_decided{false};    ///< Log rule: the rule would have decided it (at least once).
    long long log_n1{0};             ///< Log rule: the first would-be band-1 integer.
    long long log_n2{0};             ///< Log rule: the first would-be band-2 integer.
};

/// One link as the decision reads it after the solve.
struct RingFixDecideObs {
    RingFixLinkId id;                  ///< The link.
    double    lambda1{0.0};            ///< Band-1 wavelength (m).
    double    lambda2{0.0};            ///< Band-2 wavelength (m).
    bool      have_float{false};       ///< A usable two-band float and covariance this epoch.
    double    f1{0.0};                 ///< Band-1 float (cycles).
    double    f2{0.0};                 ///< Band-2 float (cycles).
    double    q11{0.0};                ///< Band-1 variance (cycles^2).
    double    q12{0.0};                ///< Covariance (cycles^2).
    double    q22{0.0};                ///< Band-2 variance (cycles^2).
    int       ring{-1};                ///< Its ring this epoch.
    bool      candidate{false};        ///< Its ring's turn has come.
    std::string root;                  ///< Its component's root receiver this epoch.
    bool      have_lat1{false};        ///< The lattice implies band 1's integer.
    bool      have_lat2{false};        ///< The lattice implies band 2's integer.
    long long lat1{0};                 ///< That integer (band 1).
    long long lat2{0};                 ///< That integer (band 2).
    bool      carry_ok{false};         ///< Both bands' carried entries exist.
    double    relevel1_s{0.0};         ///< Band 1's carried re-level stamp (0: unstamped).
    double    relevel2_s{0.0};         ///< Band 2's carried re-level stamp (0: unstamped).
    bool      latched{false};          ///< Either band in this epoch's free-epoch latch.
    bool      have_resid{false};       ///< Held links: the post-fit ionosphere-free phase residual was formed.
    double    resid_if_m{0.0};         ///< That residual (m).
    bool      have_truth{false};       ///< Simulation only: the link's true integers in this epoch's frame are known.
    long long truth1{0};               ///< Its true band-1 integer.
    long long truth2{0};               ///< Its true band-2 integer.
};

/// One link as the release reads it before PASS B.
struct RingFixHoldObs {
    bool        present{false};   ///< A chord of both bands' trees this epoch.
    bool        tree_now{false};  ///< A tree link in either band this epoch.
    bool        in_cut{false};    ///< A vertex on the moved side of one of this epoch's cut releases.
    std::string root;             ///< Its component's root receiver this epoch ("" when not found).
    bool        latched{false};   ///< Either band in this epoch's free-epoch latch.
    bool        carry_ok{false};  ///< Both bands' carried entries exist.
    double      stamp1{0.0};      ///< Band 1's carried re-level stamp now.
    double      stamp2{0.0};      ///< Band 2's carried re-level stamp now.
};

/// What a step did to one link.
struct RingFixEvent {
    enum class Kind : std::uint8_t {
        Hold,     ///< Decided: held from the next epoch.
        Release,  ///< Released, with @ref release.
        Refuse,   ///< Not decided this epoch, with @ref refuse.
    };
    Kind           kind{Kind::Refuse};              ///< What happened.
    RingFixLinkId  id;                              ///< The link.
    RingFixRelease release{RingFixRelease::Slip};   ///< Release: the cause.
    RingFixRefuse  refuse{RingFixRefuse::NotCandidate};  ///< Refuse: the cause.
    RingFixGate    gate;                            ///< The gate's reading (Hold, and Refuse when formed).
    bool           inherited{false};                ///< Hold: an old host of a cut, held at its moved target.
    bool           oracle{false};                   ///< Hold: decided by the oracle phase.
    bool           log_only{false};                 ///< Hold under the log rule: a would-be decision, nothing held.
};

/// The run counters (the run-end line).
struct RingFixCounters {
    long long epochs_decided{0};          ///< Epochs the decision ran.
    long long decided{0};                 ///< Links decided.
    long long decided_by_ring[8]{};       ///< Of them, by ring (index 7: ring 7 or more).
    long long held_link_epochs{0};        ///< Held links present at an epoch's decision.
    long long released[kRingFixReleaseCount]{};  ///< Releases by cause.
    long long refused[kRingFixRefuseCount]{};    ///< Link-epochs refused, by cause.
    long long rows_injected{0};           ///< Hold rows folded in PASS B.
    long long rows_gauge_skipped{0};      ///< Table hits on a gauge-pinned (tree) arc, never folded.
    long long rows_no_column{0};          ///< Table hits without a column this epoch.
    long long carry_reopened{0};          ///< Carried entries the release re-opened (drop or erase).
    long long audit_right{0};             ///< Held link-epochs whose integers the audit found right.
    long long audit_wrong{0};             ///< Held link-epochs whose integers the audit found wrong.
    long long audit_unlisted{0};          ///< Held link-epochs the audit file does not list.
    long long decided_wrong{0};           ///< Decisions the audit found wrong at the decision.
    long long decided_right{0};           ///< Decisions the audit found right at the decision.
    double    first_hold_s[8]{-1, -1, -1, -1, -1, -1, -1, -1};  ///< First decision by ring (continuous GPS seconds; -1: none).
    // Stage N2.
    long long cuts{0};                    ///< Cut releases seen (per band).
    long long cuts_known{0};              ///< Of them, with a known step.
    long long cuts_known_zero{0};         ///< Of them, with a step of 0 (the frame kept).
    long long reexpressed{0};             ///< Held links re-expressed by a known step.
    long long cut_released{0};            ///< Held links released for crossing a cut with an unknown step (in released[Chain] too).
    long long to_tree{0};                 ///< Held links that became tree edges (left the held set, the chain pins them).
    long long inherited{0};               ///< Old hosts held at their moved target.
    long long root_kept{0};               ///< Held links kept through a pinned root handover.
    long long stamps_rebased{0};          ///< Stamp rebases after a cut release's erase.
    long long oracle_decided{0};          ///< Links held by the oracle phase.
    long long oracle_corrected{0};        ///< Held integers the oracle phase set again (they differed from truth).
    long long truth_right{0};             ///< Held link-epochs the truth audit found right.
    long long truth_wrong{0};             ///< Held link-epochs the truth audit found wrong.
    long long truth_none{0};              ///< Held link-epochs without a true integer (no cycle, no truth row).
    long long decided_truth_wrong{0};     ///< Decisions the truth audit found wrong at the decision.
    long long truth_file_checked{0};      ///< Chord-band-epochs where the truth and the audit file both give an integer.
    long long truth_file_mismatch{0};     ///< Of them, where they differ.
    // Stage N2b.
    long long cuts_held_first{0};         ///< Cuts whose moved side re-attached through a held link the walk took first.
    long long cuts_held_first_zero{0};    ///< Of them, with a known step of 0.
    long long reattached{0};              ///< Re-attachments through a held link (one per released edge the walk took first).
    long long held_first_kept{0};         ///< Held links crossing those cuts, kept at their integers (the entry links not counted).
    long long cut_released_usable{0};     ///< Held links released across an unknown step while usable (not latched, monitor not tripped).
    long long cuts_nested{0};             ///< Cuts whose whole moved side holds a release of its own.
    long long release_floored{0};         ///< Carried entries the release floor re-opened (the vehicle's drop alone stayed tighter).
    long long log_truth_right{0};         ///< Log rule: would-be decisions at the true integers (simulation only).
    long long log_truth_wrong{0};         ///< Log rule: would-be decisions off the true integers (simulation only).
    long long oracle_waited{0};           ///< Oracle holds put off to the next epoch (the link released or latched this epoch).
    long long log_links{0};               ///< Log rule: links the rule would have decided.
    long long log_link_epochs{0};         ///< Log rule: link-epochs at which it would have decided.
    long long log_changed{0};             ///< Log rule: would-be decisions with integers other than the link's first.
    // Stages N2c and O1.
    long long excluded_link_epochs{0};    ///< Chord link-epochs of pair families outside network.ring_fix.pairs (never decided).
    long long mask_epochs{0};             ///< Simulation only: epochs at which the slip mask removed the masked arc's flags.
    long long mask_keys_removed{0};       ///< Of them, the latch, funnel and bridge-pend entries removed.
    long long mask_carries_restored{0};   ///< Of them, carried entries the epoch's drains had changed, restored.
};

struct RingFixTruth;   // below: the fixture's truth (simulation only)

/**
 * @brief Run-scope state of the ring fix.  Null on every run without @c network.ring_fix.enable.
 *
 * Non-copyable (a copy would duplicate the held set and misreport the edges); movable.
 */
struct NetworkRingFix {
    /** @brief Default constructor: no links, nothing held. */
    NetworkRingFix() = default;
    /** @brief Deleted: a copy would duplicate the held set and misreport the edges. */
    NetworkRingFix(const NetworkRingFix&) = delete;
    /** @brief Deleted (see the copy constructor).
     *  @return Not applicable: the operator is deleted. */
    NetworkRingFix& operator=(const NetworkRingFix&) = delete;
    /** @brief Move constructor: the state moves whole (one owner at a time). */
    NetworkRingFix(NetworkRingFix&&) = default;
    /** @brief Move assignment: the state moves whole (one owner at a time).
     *  @return This state. */
    NetworkRingFix& operator=(NetworkRingFix&&) = default;

    RingFixRule rule{RingFixRule::Gated};   ///< The decision rule.
    RingFixOrder order{RingFixOrder::Ring};          ///< The order of the decisions.
    RingFixGateRule gate_rule{RingFixGateRule::Sigma};  ///< The gate of the decisions.
    double      max_gap_s{900.0};           ///< The gap horizon of a held link (the leveling carry's, phase_leveling_max_gap_s).
    std::string audit_file;                 ///< The audit's frame-target file ("" = no audit).
    /// (station name, satellite, signal) -> the frame integer of the audit file.
    std::map<std::tuple<std::string, std::string, std::string>, long long> audit;
    /// Every link seen as a chord of a pair family, with its state.
    std::map<RingFixLinkId, RingFixLink> links;
    /// (station index, satellite) -> the last epoch it was a tree link in either band.
    std::map<std::pair<int, std::string>, double> last_tree_s;
    /// This epoch's hold rows, built before PASS B: (station index, satellite, signal) -> the held
    /// value lambda times the integer (m).  Read only inside the parallel PASS B produce.
    std::map<std::tuple<int, std::string, std::string>, double> table;
    RingFixCounters counters;               ///< Run counters.
    // Stage N2.
    std::unique_ptr<RingFixTruth> truth;    ///< The fixture's truth (network.ring_fix.truth_root); null without it.
    double      oracle_until_s{0.0};        ///< The oracle phase's length from the first epoch (s; 0 = none).
    bool        held_first{false};          ///< The chain's walk re-attaches through held links first (network.ring_fix.held_first).
    /// The pair families considered (network.ring_fix.pairs), as (constellation key, signal 1, signal 2); empty: all.
    std::set<std::tuple<std::string, std::string, std::string>> pairs;
    double      wl_frac_max{0.0};           ///< The decision's bound on the wide lane's fraction (cycles; 0: none).
    double      sigma_scale{1.0};           ///< The odds gate's factor on the formal sigmas (network.ring_fix.sigma_scale).
    // Simulation only: the slip mask (network.ring_fix.mask_slip_*).
    int         mask_station{-1};           ///< The masked arc's station (roster index; -1: no mask).
    std::string mask_sat;                   ///< The masked arc's satellite.
    double      mask_tow{-1.0};             ///< The first masked epoch (GPS time of week, s).
    int         mask_n_epochs{1};           ///< The number of masked epochs.
    /// @brief Whether a link's pair family is considered (network.ring_fix.pairs; all when the list is empty).
    /// @param sys The constellation key ("G", "E"). @param sig1 Band-1 signal. @param sig2 Band-2 signal.
    /// @return True when the family is in the list or the list is empty.
    bool pairConsidered(const std::string& sys, const std::string& sig1, const std::string& sig2) const {
        return pairs.empty() || pairs.count({sys, sig1, sig2}) != 0;
    }
    double      t0_s{-1.0};                 ///< The first epoch the ring fix saw (continuous GPS seconds).
    /// The previous epoch's tree edges with their targets: (station, satellite, signal) -> target (cycles).
    std::map<std::tuple<int, std::string, std::string>, double> prev_targets;
};

// ---- The steps (pure: unit-tested on hand-built epochs) ---------------------------------------

/**
 * @brief The decision of one epoch, after the solve.
 *
 * For each observed link: its continuity is updated; a held link updates its monitor (the
 * residual above @ref kRingFixMonitorBoundM at @ref kRingFixMonitorEpochs consecutive epochs sets
 * @c monitor_trip, read by the next release step); a link that is not held is refused (the first
 * test it fails, in the order not candidate, no float, window, sigma, fraction, lattice, persist)
 * or decided.  Under @ref RingFixRule::Plain a candidate with a float is decided at once.  The
 * window holds when both carried entries exist, their re-level stamps (when stamped) are at least
 * @ref kRingFixWindowS old, neither band is latched, the link has been a chord with a float for
 * at least the window, was no tree link within it and was not released within it.  A link
 * passes the persistence test at the @ref kRingFixPersistEpochs th consecutive epoch that passed
 * with the same integers; any refusal restarts the count.
 *
 * Under @ref RingFixGateRule::Odds the sigma test is replaced by the odds test (after the fraction
 * test): both log-odds at least @ref kRingFixMinLogOdds.  Under @ref RingFixOrder::Certain every link
 * with a float is a candidate, and the links that pass every test are decided after the loop, the
 * highest log-odds of N1 first (ties by link), at most @ref kRingFixMaxDecisionsPerEpoch; the others
 * are refused with the cause cap and keep their persistence count.
 *
 * During the oracle phase (simulation only: @c rf.oracle_until_s after @c rf.t0_s) every link with
 * true integers is held at them at once, and a held link whose integers differ is set to them; the
 * rule does not run.
 *
 * @param rf     The run state (links and counters written).
 * @param links  This epoch's chords of pair families with their readings.
 * @param now_s  The epoch (continuous GPS seconds).
 * @return One event per decision and per refusal, in the order of @p links.
 */
std::vector<RingFixEvent> ringFixDecideStep(NetworkRingFix& rf,
                                            const std::vector<RingFixDecideObs>& links,
                                            double now_s);

/**
 * @brief The release of one epoch, before PASS B.
 *
 * For each held link the first cause that applies, in the order chain (a tree link now, on a cut
 * release's moved side, or its component's root changed), slip (latched), refloat (a carried
 * entry missing or re-levelled since the decision), monitor (tripped), gap (absent for longer than
 * @c rf.max_gap_s).  A held link absent within the horizon keeps its hold and takes no row.  A
 * released link is no longer held, its streak and monitor restart and its release time is
 * recorded; the caller re-opens its carried entries.
 *
 * @param rf    The run state (links and counters written).
 * @param obs   The held links' readings this epoch; a held link missing from the map is absent.
 * @param now_s The epoch (continuous GPS seconds).
 * @return One event per release.
 */
std::vector<RingFixEvent> ringFixReleaseStep(NetworkRingFix& rf,
                                             const std::map<RingFixLinkId, RingFixHoldObs>& obs,
                                             double now_s);

/**
 * @brief Read an audit frame-target file into the run state.
 *
 * Header contract: the line begins `station,sat,signal,frame_int` (the frame-target files of
 * scripts/irdu_frame_targets.py; further columns are ignored).
 *
 * @param path File to read.
 * @return (station name, satellite, signal) -> frame integer.
 * @throws std::runtime_error on a missing file, a malformed header or row, or a duplicate arc.
 */
std::map<std::tuple<std::string, std::string, std::string>, long long>
ringFixReadAuditFile(const std::string& path);

/// The audit's verdict on one held link at one epoch.
enum class RingFixAudit : std::uint8_t {
    Right,     ///< Both bands' integers equal the file's.
    Wrong,     ///< A band's integer differs from the file's.
    Unlisted,  ///< The file lists neither band.
};

/**
 * @brief The audit of one held link.
 * @param audit        The audit file's integers.
 * @param station_name The link's station name.
 * @param id           The link.
 * @param n1           Its held band-1 integer.
 * @param n2           Its held band-2 integer.
 * @return Right when every listed band matches and at least one is listed, Wrong when a listed
 *         band differs, Unlisted when neither band is listed.
 */
RingFixAudit ringFixAuditLink(
    const std::map<std::tuple<std::string, std::string, std::string>, long long>& audit,
    const std::string& station_name, const RingFixLinkId& id, long long n1, long long n2);

// ---- Stage N2: held integers through the chain's events ------------------------------------------

/**
 * @brief One cut release of the epoch on one band, as the held integers read it.
 *
 * The chain re-attached the moved side M (the released vertex and its subtree) through a released
 * edge; every vertex of M moved by one integer frame step on the band.  The step is known only when
 * the released edge was a held link before the event (@ref ringFixCutStep).
 */
struct RingFixCut {
    std::string           sys;             ///< The band's constellation key ("G", "E"; empty: any), the release's group being "<key>|<signal>".
    std::string           signal;          ///< The band's phase signal.
    std::set<int>         stations;        ///< Receivers of M (roster index).
    std::set<std::string> sats;            ///< Satellites of M.
    bool                  known{false};    ///< The step is known.
    long long             delta{0};        ///< M's frame step on the band (cycles), when known.
    std::string           row;             ///< The releasing row's name ("rehost", "returning", "slip", "merge").
    int                   entry_station{-1};  ///< The released edge's station (the edge that carries M now).
    std::string           entry_sat;          ///< The released edge's satellite.
    bool                  held_first{false};  ///< The walk took the released edge first because its integer was held.
};

/**
 * @brief The frame step of a cut's moved side from its released edge.
 *
 * With the released edge e' held at N_h before the event and pinned at k' now: delta = N_h - k' when
 * the moved vertex is e''s satellite, k' - N_h when it is e''s receiver.
 *
 * @param held_before   The released edge was held before the event (and not latched, not tripped).
 * @param n_held        Its held integer on the band.
 * @param target_cyc    Its target this epoch (cycles), which must be an integer.
 * @param sat_is_child  The moved vertex is the released edge's satellite.
 * @param[out] delta    The step, written when known.
 * @return True when the step is known.
 */
bool ringFixCutStep(bool held_before, long long n_held, double target_cyc, bool sat_is_child,
                    long long& delta);

/// What the cuts of an epoch did to the held links.
struct RingFixCutOutcome {
    std::vector<std::pair<RingFixLinkId, std::string>> released;  ///< Links released (crossing a cut with an unknown step), with the cut's row.
    /// Links re-expressed: (link, step on band 1, step on band 2, the rows).
    std::vector<std::tuple<RingFixLinkId, long long, long long, std::string>> reexpressed;
    long long touched{0};   ///< Held links with an end in a moved side (their carries were erased: stamps rebased).
    /// Per cut, in the order given: the held links that cross it and keep their integers.
    std::vector<std::vector<RingFixLinkId>> kept_by_cut;
};

/**
 * @brief Apply an epoch's cuts to the held links.
 *
 * A held link with exactly one end in a cut's moved side on one of its bands is re-expressed by the
 * cut's step (minus when its satellite is in M, plus when its receiver is) when the step is known,
 * and released (cause chain) when it is not; one with both ends in M, or none, keeps its integer.
 * Every held link with an end in a moved side has its carried stamps rebased at the next release step.
 * A cut's moved side is the released vertex's whole subtree, so a link that leaves a nested cut and its
 * outer one crosses both and takes both steps.
 *
 * @param rf    The run state (links and counters written).
 * @param cuts  This epoch's cuts.
 * @param now_s The epoch (continuous GPS seconds).
 * @return What the cuts did.
 */
RingFixCutOutcome ringFixApplyCuts(NetworkRingFix& rf, const std::vector<RingFixCut>& cuts, double now_s);

/**
 * @brief The band of a held link that a cut is on.
 *
 * A band is a constellation and a phase signal: GPS L1 and Galileo E1 share the code L1C, and a cut
 * on one says nothing about the other's frame.
 *
 * @param c  The cut (an empty @c sys matches any constellation).
 * @param id The link.
 * @return 1 or 2 for the link's band 1 or band 2, 0 when the cut is on neither.
 */
int ringFixCutBand(const RingFixCut& c, const RingFixLinkId& id);

/// A tree edge of the previous epoch that is a chord of its pair family now.
struct RingFixInheritCand {
    RingFixLinkId id;               ///< The link.
    long long     k1{0};            ///< Its target on band 1 at the previous epoch (cycles).
    long long     k2{0};            ///< Its target on band 2 at the previous epoch (cycles).
    double        lambda1{0.0};     ///< Band-1 wavelength (m).
    double        lambda2{0.0};     ///< Band-2 wavelength (m).
    bool          latched{false};   ///< Either band in this epoch's free-epoch latch.
    int           ring{-1};         ///< Its ring now.
    std::string   root;             ///< Its component's root now.
};

/**
 * @brief Hold the old hosts: each candidate not held and not latched is held at its previous targets
 *        moved by the steps of the cuts it crosses, when every such step is known.
 * @param rf    The run state.
 * @param cands The candidates.
 * @param cuts  This epoch's cuts.
 * @param now_s The epoch.
 * @return One Hold event (flag @c inherited) per link held.
 */
std::vector<RingFixEvent> ringFixInherit(NetworkRingFix& rf, const std::vector<RingFixInheritCand>& cands,
                                         const std::vector<RingFixCut>& cuts, double now_s);

// ---- Truth (simulation only) ----------------------------------------------------------------------

/**
 * @brief The fixture's truth as the ring fix reads it: each arc's integer and slips, each receiver's
 *        wind-up per satellite, and the producer's wind-up branch of each arc.
 *
 * The producer's integer of an arc is the fixture's slip-accumulated integer plus the branch
 * round_half_up(wu(t0)), wu the fixture's accumulated wind-up at the arc's first epoch t0, a new arc
 * after a gap above @ref kRingFixArcGapS (the rule of scripts/simnet_producer_ar_grade.py).
 */
struct RingFixTruth {
    /// One arc's integer and its jumps (continuous GPS seconds, cycles), ascending.
    struct Arc {
        long long n_int{0};                              ///< The pre-slip integer.
        std::vector<std::pair<double, long long>> slips;  ///< (time, jump).
    };
    /// One wind-up branch of a (receiver, satellite): its first epoch, its last epoch, its integer.
    struct Branch {
        double    start_tow{0.0};  ///< First epoch (time of week, s).
        double    last_tow{0.0};   ///< Last epoch seen (time of week, s).
        long long k{0};            ///< The branch integer.
    };
    std::map<std::tuple<int, std::string, std::string>, Arc> arcs;          ///< (station, sat, signal) -> the arc.
    std::map<std::pair<int, std::string>, std::map<double, double>> windup; ///< (station, sat) -> tow -> cycles.
    std::map<std::pair<int, std::string>, std::vector<Branch>> branches;   ///< (station, sat) -> its branches.
    long long arcs_without_windup{0};   ///< Branches started without a wind-up row (k = 0).
};

/// A gap above this ends a (receiver, satellite) arc for the wind-up branch (s).
inline constexpr double kRingFixArcGapS = 300.0;

/**
 * @brief round_half_up of a wind-up in cycles: floor(w + 0.5).
 * @param w The accumulated wind-up (cycles).
 * @return The branch integer.
 */
long long ringFixWindupBranch(double w);

/**
 * @brief Record that a (receiver, satellite) is seen at an epoch: a new branch at its first epoch or
 *        after a gap above @ref kRingFixArcGapS, with the wind-up at that epoch.
 * @param T       The truth.
 * @param station Roster index.
 * @param sat     Satellite.
 * @param tow     Time of week (s).
 */
void ringFixTruthObserve(RingFixTruth& T, int station, const std::string& sat, double tow);

/**
 * @brief The producer's true integer of an arc at an epoch.
 * @param T       The truth.
 * @param station Roster index.
 * @param sat     Satellite.
 * @param signal  Phase signal.
 * @param now_s   Continuous GPS seconds (the slips' clock; a slip at now_s counts).
 * @param tow     Time of week (s), for the branch.
 * @param[out] n  The integer.
 * @return False when the arc has no truth row.
 */
bool ringFixTruthN(const RingFixTruth& T, int station, const std::string& sat, const std::string& signal,
                   double now_s, double tow, long long& n);

/**
 * @brief The true integer of a chord in the frame of an epoch: the sum over its fundamental cycle of
 *        coefficient times the true integer, less the sum over the tree terms of coefficient times target.
 * @param T            The truth.
 * @param terms        The cycle's terms: (station, satellite, signal, coefficient), the chord included (+1).
 * @param pin_sum_cyc  Sum over the tree terms of coefficient times target (cycles).
 * @param pins_integer Every target on the path is an integer.
 * @param now_s        Continuous GPS seconds.
 * @param tow          Time of week (s).
 * @param[out] n       The integer.
 * @return False when a target is not an integer, a term has no truth, or the sum is not an integer.
 */
bool ringFixTruthFrameInteger(const RingFixTruth& T,
                              const std::vector<std::tuple<int, std::string, std::string, int>>& terms,
                              double pin_sum_cyc, bool pins_integer, double now_s, double tow, long long& n);

/**
 * @brief Read one receiver's truth_windup.csv.
 *
 * Header contract: the line begins `week,tow_s,satellite,windup_cycles`.
 *
 * @param path File to read.
 * @return satellite -> tow -> accumulated wind-up (cycles).
 * @throws std::runtime_error on a missing file or a malformed header or row.
 */
std::map<std::string, std::map<double, double>> ringFixParseWindupCsv(const std::string& path);

// ---- The network seams ----------------------------------------------------------------------

struct NetworkRun;          // network/driver/Run.hpp
struct NetworkEpoch;        // network/driver/Epoch.hpp
struct NetworkRunEndView;   // network/runend/RunEnd.hpp
struct NetworkRunContext;   // network/state/RunContext.hpp
struct StationAssembly;     // network/driver/RunTypes.hpp
struct StationCarryFrame;   // network/assembly/StationBuild.hpp

/**
 * @brief Setup builder: builds the run state when @c network.ring_fix.enable is set and reads
 *        the audit file.  Called once from runNetwork.
 * @param run The run: writes run.ctx.carry.ring_fix; reads run.nc, run.config and run.log.
 * @throws std::runtime_error when the audit file cannot be read.
 */
void networkRingFixArm(NetworkRun& run);

/**
 * @brief Before PASS B: the releases of this epoch and the hold rows PASS B folds.
 *
 * Serial, after the phase-datum election (the chain record) and PASS A's slip latch, and before
 * the float vehicle's drop pass and PASS B.  Reads each held link's state from the chain record,
 * the latch and the carried entries, runs @ref ringFixReleaseStep, re-opens the released links'
 * carried entries (the vehicle's drop under float_kf, an erase on the leveling vehicle; skipped
 * for a slip, which the drop pass answers, and for a refloat, already answered), writes the
 * release events and rebuilds the hold table.  Gate: the run state exists.
 *
 * @param run The run. Written: run.ctx (the ring fix's state, the carried entries of released
 *            links), run.traces (events). Read: run.config, run.setup.stations, run.log.
 * @param ep  The epoch: ep.se.time, ep.clock.pl_now_s, ep.events.phase_datum.chain,
 *            ep.events.slip.relevel.
 */
void networkRingFixHoldEpoch(NetworkRun& run, const NetworkEpoch& ep);

/**
 * @brief The hold rows of one station: one diagonal prior row per held band column.
 *
 * Step `ring_hold` of kStationCarrySteps (network/assembly/StationBuild.hpp); its kinds:
 * PriorAmbiguityRingHold.  It returns at once unless `legacy_local_inject` holds and the hold
 * table is non-empty.  Records: the rfix_* counters of StationAssembly.
 *
 * @param carry The station's carry frame (the build, the priors, the block columns).
 */
void networkRingFixPriors(StationCarryFrame& carry);

/**
 * @brief Folds the stations' hold-row accounting into the run counters.  Serial, after the
 *        parallel produce.  Does nothing without the run state.
 * @param ctx     The run context: the counters are written.
 * @param asm_res The stations' assembled blocks, read.
 */
void networkRingFixStationTally(NetworkRunContext& ctx,
                                const std::vector<StationAssembly>& asm_res);

/**
 * @brief After the solve: the monitor, the audit and the decisions of this epoch.
 *
 * Serial, after the producer's search and the lattice step, before the solution's preparation.
 * Forms each pair-family chord's two-band float and conditional covariance (the chord table's
 * quantities, @c chainChordFloats), its ring (@ref ringFixRings), its lattice integers and its
 * carried entries' stamps; each held link's post-fit ionosphere-free phase residual; runs
 * @ref ringFixDecideStep; audits every held link; writes the hold events and the trace.
 * Gate: the run state exists and the chain record is armed.
 *
 * @param run The run. Written: run.ctx (the ring fix's state), run.traces (events, the trace).
 *            Read: run.engines.est, run.setup.stations, run.config.
 * @param ep  The epoch after the solve: ep.solve (x_s, plan), ep.assembly (asm_res,
 *            est_index_of), ep.events (the chain record, the latch), ep.se.time, ep.clock.
 */
void networkRingFixDecide(NetworkRun& run, const NetworkEpoch& ep);

/**
 * @brief Run-end report: the ring fix's decisions, holds, releases, refusals and audit.
 *
 * Gate: the run state exists (nothing is printed otherwise).
 *
 * @param v The run at its end.
 * @return 0 (the report does not set the exit code).
 */
int networkRingFixRunEnd(const NetworkRunEndView& v);

} // namespace GnssProcessor

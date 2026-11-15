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

/// The decision rule of a run (@c network.ring_fix.rule).
enum class RingFixRule : std::uint8_t {
    Gated,  ///< The frozen rule: the gate, the damage gate and the persistence count.
    Plain,  ///< The negative control: every candidate with a float is rounded and held at once.
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
};
/// Number of refusal causes.
inline constexpr std::size_t kRingFixRefuseCount = 7;

/**
 * @brief The name of a release cause ("slip", "refloat", "gap", "chain", "monitor").
 * @param c The cause.
 * @return Its name as a static string; "?" for a value outside the enum.
 */
const char* ringFixReleaseName(RingFixRelease c);

/**
 * @brief The name of a refusal cause ("not_candidate", "no_float", "window", "sigma",
 *        "fraction", "lattice", "persist").
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
 * @return The reading; @c valid false for non-finite inputs, a negative variance of the row or
 *         wavelengths that do not order.
 */
RingFixGate ringFixGate(double f1, double f2, double q11, double q12, double q22,
                        double lambda1, double lambda2);

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
};

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

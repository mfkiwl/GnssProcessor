// Unit tests of the ring fix's pure steps (include/network/ar/RingFix.hpp): the gate, the rings
// and candidates, the decision with its damage gate and persistence, the hold bookkeeping, every
// release cause and the audit.

#include "network/ar/RingFix.hpp"

#include <gtest/gtest.h>

#include <cmath>
#include <cstdio>
#include <fstream>
#include <string>

using namespace GnssProcessor;

namespace {

constexpr double kL1 = 0.19029367279836487;   // GPS L1 (m)
constexpr double kL2 = 0.24421021342456825;   // GPS L2 (m)

/// A float near (n1, n2) with an ionosphere-like error e1 on band 1 (band 2 takes e1 * F1/F2).
RingFixDecideObs obsNear(const RingFixLinkId& id, long long n1, long long n2, double e1, double var) {
    RingFixDecideObs o;
    o.id = id;
    o.lambda1 = kL1;
    o.lambda2 = kL2;
    o.have_float = true;
    o.f1 = static_cast<double>(n1) + e1;
    o.f2 = static_cast<double>(n2) + e1 * (kL2 / kL1);
    o.q11 = var;
    o.q12 = var * 0.9;
    o.q22 = var;
    o.ring = 2;
    o.candidate = true;
    o.root = "S30000SIM";
    o.carry_ok = true;
    o.relevel1_s = 1000.0;
    o.relevel2_s = 1000.0;
    return o;
}

/// A run state with the link's continuity and tree history already old enough for the window.
NetworkRingFix stateWithHistory(const RingFixLinkId& id, double now_s) {
    NetworkRingFix rf;
    RingFixLink& L = rf.links[id];
    L.chord_since_s = now_s - 2.0 * kRingFixWindowS;
    L.last_chord_s = now_s - 30.0;
    return rf;
}

const RingFixLinkId kId{3, "G05", "L1C", "L2W"};

}  // namespace

// ---- The gate ----

TEST(RingFixGate, AnIonosphereLikeErrorPassesTheIonosphereFreeRow) {
    // An error that is pure ionosphere cancels in the ionosphere-free row: the band integers come
    // back although each band's float is 0.4 cycle off.
    const RingFixGate g = ringFixGate(10.4, 7.0 + 0.4 * (kL2 / kL1), 1e-4, 0.9e-4, 1e-4, kL1, kL2);
    ASSERT_TRUE(g.valid);
    EXPECT_EQ(g.wl, 3);
    EXPECT_EQ(g.n1, 10);
    EXPECT_EQ(g.n2, 7);
    EXPECT_NEAR(g.frac_if, 0.0, 1e-9);
    EXPECT_TRUE(g.pass);
}

TEST(RingFixGate, TheSigmaAndTheFractionBoundsAreTheFrozenOnes) {
    // The ionosphere-free sigma for band variances v and correlation 0.9: a^2 v + 2ab 0.9 v + b^2 v.
    const double r = kL2 / kL1, a = r / (r - 1.0), b = -1.0 / (r - 1.0);
    const double unit = std::sqrt(a * a + 2.0 * a * b * 0.9 + b * b);
    const double v_at = std::pow(kRingFixMaxSigmaCyc / unit, 2.0);
    const RingFixGate in = ringFixGate(10.0, 7.0, v_at * 0.99, 0.9 * v_at * 0.99, v_at * 0.99, kL1, kL2);
    const RingFixGate out = ringFixGate(10.0, 7.0, v_at * 1.01, 0.9 * v_at * 1.01, v_at * 1.01, kL1, kL2);
    EXPECT_TRUE(in.pass);
    EXPECT_FALSE(out.pass);
    EXPECT_NEAR(in.sigma_if, kRingFixMaxSigmaCyc * std::sqrt(0.99), 1e-9);
    // A non-ionosphere error of 0.25 cycle on band 1 alone moves the row by a = 4.53 x 0.25: the
    // fraction bound refuses it.
    const RingFixGate frac = ringFixGate(10.05, 7.0, 1e-6, 0.0, 1e-6, kL1, kL2);
    EXPECT_GT(frac.frac_if, kRingFixMaxFracCyc);
    EXPECT_FALSE(frac.pass);
}

TEST(RingFixGate, AWrongWideLaneMovesTheRowByMoreThanTheFractionBound) {
    // A two-cycle ionosphere-like error on (10, 7) moves the wide lane by -0.567 cycle, so it rounds
    // to 2 instead of 3; the row with that wide lane is 10 + 1/(r - 1) = 13.53, a fraction of 0.47.
    const double r = kL2 / kL1;
    const RingFixGate g = ringFixGate(12.0, 7.0 + 2.0 * r, 1e-6, 0.0, 1e-6, kL1, kL2);
    ASSERT_TRUE(g.valid);
    EXPECT_EQ(g.wl, 2);
    EXPECT_NEAR(g.n_if, 10.0 + 1.0 / (r - 1.0), 1e-9);
    EXPECT_GT(g.frac_if, kRingFixMaxFracCyc);
    EXPECT_FALSE(g.pass);
}

TEST(RingFixGate, NonFiniteOrUnorderedInputsAreNotValid) {
    EXPECT_FALSE(ringFixGate(NAN, 7.0, 1e-4, 0.0, 1e-4, kL1, kL2).valid);
    EXPECT_FALSE(ringFixGate(10.0, 7.0, 1e-4, 0.0, 1e-4, kL2, kL1).valid);
    EXPECT_FALSE(ringFixGate(10.0, 7.0, -1.0, 0.0, -1.0, kL1, kL2).valid);
}

// ---- Rings and candidates ----

TEST(RingFixRings, RingTwoIsACandidateAndRingThreeWaitsForItsInnerVertex) {
    // Root R:0; satellites S:A, S:B at depth 1; receivers R:1 (under A) and R:2 (under B) at depth
    // 2; satellite S:C at depth 3 under R:1.  Chords: R:1-S:B (ring 2), R:2-S:C (ring 3, inner R:2,
    // whose shallower links are its tree edge to S:B and nothing else) and R:1-S:A... is a tree edge.
    RingFixTree tree;
    tree.edges = {{"S:A", "R:0", 1}, {"S:B", "R:0", 1}, {"R:1", "S:A", 2}, {"R:2", "S:B", 2},
                  {"S:C", "R:1", 3}};
    tree.chords = {{"R:1", "S:B"}, {"R:2", "S:C"}, {"R:2", "S:A"}};
    auto rings = ringFixRings(tree, {});
    EXPECT_EQ(rings.at({"R:1", "S:B"}).ring, 2);
    EXPECT_TRUE(rings.at({"R:1", "S:B"}).candidate);
    EXPECT_EQ(rings.at({"R:2", "S:A"}).ring, 2);
    EXPECT_TRUE(rings.at({"R:2", "S:A"}).candidate);
    // R:2-S:C: ring 3, inner vertex R:2 (depth 2), whose links to depth-1 satellites are its tree
    // edge to S:B and the chord to S:A: a candidate only once R:2-S:A is held.
    EXPECT_EQ(rings.at({"R:2", "S:C"}).ring, 3);
    EXPECT_EQ(rings.at({"R:2", "S:C"}).inner, "R:2");
    EXPECT_FALSE(rings.at({"R:2", "S:C"}).candidate);
    rings = ringFixRings(tree, {{"R:2", "S:A"}});
    EXPECT_TRUE(rings.at({"R:2", "S:C"}).candidate);
}

TEST(RingFixRings, AChordWithAVertexOutsideTheTreeHasNoRing) {
    RingFixTree tree;
    tree.edges = {{"S:A", "R:0", 1}};
    tree.chords = {{"R:9", "S:A"}};
    const auto rings = ringFixRings(tree, {});
    EXPECT_EQ(rings.at({"R:9", "S:A"}).ring, -1);
    EXPECT_FALSE(rings.at({"R:9", "S:A"}).candidate);
}

// ---- The decision ----

TEST(RingFixDecide, ALinkIsDecidedAtTheTenthConsecutiveEpochWithTheSameIntegers) {
    double now = 100000.0;
    NetworkRingFix rf = stateWithHistory(kId, now);
    for (int k = 1; k < kRingFixPersistEpochs; ++k, now += 30.0) {
        const auto ev = ringFixDecideStep(rf, {obsNear(kId, 10, 7, 0.02, 1e-5)}, now);
        ASSERT_EQ(ev.size(), 1u);
        EXPECT_EQ(ev[0].kind, RingFixEvent::Kind::Refuse);
        EXPECT_EQ(ev[0].refuse, RingFixRefuse::Persist);
        EXPECT_FALSE(rf.links.at(kId).held);
    }
    const auto ev = ringFixDecideStep(rf, {obsNear(kId, 10, 7, 0.02, 1e-5)}, now);
    ASSERT_EQ(ev.size(), 1u);
    EXPECT_EQ(ev[0].kind, RingFixEvent::Kind::Hold);
    const RingFixLink& L = rf.links.at(kId);
    EXPECT_TRUE(L.held);
    EXPECT_EQ(L.n1, 10);
    EXPECT_EQ(L.n2, 7);
    EXPECT_EQ(L.root, "S30000SIM");
    EXPECT_EQ(rf.counters.decided, 1);
    EXPECT_EQ(rf.counters.decided_by_ring[2], 1);
}

TEST(RingFixDecide, AChangeOfIntegersOrAnyRefusalRestartsThePersistenceCount) {
    double now = 100000.0;
    NetworkRingFix rf = stateWithHistory(kId, now);
    for (int k = 0; k < kRingFixPersistEpochs - 1; ++k, now += 30.0)
        ringFixDecideStep(rf, {obsNear(kId, 10, 7, 0.0, 1e-5)}, now);
    EXPECT_EQ(rf.links.at(kId).streak, kRingFixPersistEpochs - 1);
    // A sigma refusal restarts the count.
    ringFixDecideStep(rf, {obsNear(kId, 10, 7, 0.0, 1e-2)}, now);
    EXPECT_EQ(rf.links.at(kId).streak, 0);
    now += 30.0;
    ringFixDecideStep(rf, {obsNear(kId, 10, 7, 0.0, 1e-5)}, now);
    EXPECT_EQ(rf.links.at(kId).streak, 1);
    // Other integers restart it at one.
    now += 30.0;
    ringFixDecideStep(rf, {obsNear(kId, 11, 8, 0.0, 1e-5)}, now);
    EXPECT_EQ(rf.links.at(kId).streak, 1);
    EXPECT_EQ(rf.links.at(kId).streak_n1, 11);
}

TEST(RingFixDecide, TheDamageWindowRefusesARecentEventOfEveryKind) {
    const double now = 100000.0;
    const auto refusedBy = [&](NetworkRingFix& rf, const RingFixDecideObs& o) {
        const auto ev = ringFixDecideStep(rf, {o}, now);
        return ev.size() == 1 && ev[0].kind == RingFixEvent::Kind::Refuse ? ev[0].refuse : RingFixRefuse::Persist;
    };
    {   // a recent re-level of band 2 (a slip re-level, a drop, a birth)
        NetworkRingFix rf = stateWithHistory(kId, now);
        RingFixDecideObs o = obsNear(kId, 10, 7, 0.0, 1e-5);
        o.relevel2_s = now - 0.5 * kRingFixWindowS;
        EXPECT_EQ(refusedBy(rf, o), RingFixRefuse::Window);
    }
    {   // latched this epoch
        NetworkRingFix rf = stateWithHistory(kId, now);
        RingFixDecideObs o = obsNear(kId, 10, 7, 0.0, 1e-5);
        o.latched = true;
        EXPECT_EQ(refusedBy(rf, o), RingFixRefuse::Window);
    }
    {   // a carried entry missing
        NetworkRingFix rf = stateWithHistory(kId, now);
        RingFixDecideObs o = obsNear(kId, 10, 7, 0.0, 1e-5);
        o.carry_ok = false;
        EXPECT_EQ(refusedBy(rf, o), RingFixRefuse::Window);
    }
    {   // a chord for less than the window (a gap above kRingFixGapS restarted the count)
        NetworkRingFix rf = stateWithHistory(kId, now);
        rf.links.at(kId).last_chord_s = now - 2.0 * kRingFixGapS;
        EXPECT_EQ(refusedBy(rf, obsNear(kId, 10, 7, 0.0, 1e-5)), RingFixRefuse::Window);
    }
    {   // a tree link within the window
        NetworkRingFix rf = stateWithHistory(kId, now);
        rf.last_tree_s[{kId.station, kId.sat}] = now - 60.0;
        EXPECT_EQ(refusedBy(rf, obsNear(kId, 10, 7, 0.0, 1e-5)), RingFixRefuse::Window);
    }
    {   // released within the window
        NetworkRingFix rf = stateWithHistory(kId, now);
        rf.links.at(kId).released_s = now - 60.0;
        EXPECT_EQ(refusedBy(rf, obsNear(kId, 10, 7, 0.0, 1e-5)), RingFixRefuse::Window);
    }
}

TEST(RingFixDecide, TheLatticeVetoesADisagreeingIntegerAndTheRingRefusesFirst) {
    const double now = 100000.0;
    NetworkRingFix rf = stateWithHistory(kId, now);
    RingFixDecideObs o = obsNear(kId, 10, 7, 0.0, 1e-5);
    o.have_lat2 = true;
    o.lat2 = 8;
    auto ev = ringFixDecideStep(rf, {o}, now);
    ASSERT_EQ(ev.size(), 1u);
    EXPECT_EQ(ev[0].refuse, RingFixRefuse::Lattice);
    o.have_lat2 = false;
    o.candidate = false;
    ev = ringFixDecideStep(rf, {o}, now + 30.0);
    EXPECT_EQ(ev[0].refuse, RingFixRefuse::NotCandidate);
    o.candidate = true;
    o.have_float = false;
    ev = ringFixDecideStep(rf, {o}, now + 60.0);
    EXPECT_EQ(ev[0].refuse, RingFixRefuse::NoFloat);
}

TEST(RingFixDecide, ThePlainRuleRoundsAtOnceWithoutAnyGate) {
    NetworkRingFix rf;
    rf.rule = RingFixRule::Plain;
    RingFixDecideObs o = obsNear(kId, 10, 7, 0.45, 1.0);   // far from its integers, sigma huge
    o.carry_ok = false;
    const auto ev = ringFixDecideStep(rf, {o}, 1000.0);
    ASSERT_EQ(ev.size(), 1u);
    EXPECT_EQ(ev[0].kind, RingFixEvent::Kind::Hold);
    EXPECT_TRUE(rf.links.at(kId).held);
}

// ---- The monitor and the releases ----

NetworkRingFix heldState(double now_s) {
    NetworkRingFix rf;
    RingFixLink& L = rf.links[kId];
    L.held = true;
    L.n1 = 10;
    L.n2 = 7;
    L.lambda1 = kL1;
    L.lambda2 = kL2;
    L.decided_s = now_s - 600.0;
    L.stamp1 = 1000.0;
    L.stamp2 = 1000.0;
    L.root = "S30000SIM";
    return rf;
}

RingFixHoldObs presentObs() {
    RingFixHoldObs o;
    o.present = true;
    o.carry_ok = true;
    o.stamp1 = 1000.0;
    o.stamp2 = 1000.0;
    o.root = "S30000SIM";
    return o;
}

TEST(RingFixRelease, AQuietHeldLinkStaysHeld) {
    NetworkRingFix rf = heldState(5000.0);
    const auto ev = ringFixReleaseStep(rf, {{kId, presentObs()}}, 5000.0);
    EXPECT_TRUE(ev.empty());
    EXPECT_TRUE(rf.links.at(kId).held);
}

TEST(RingFixRelease, EachCauseReleasesWithItsName) {
    struct Case { const char* what; RingFixRelease cause; void (*set)(RingFixHoldObs&, RingFixLink&); };
    const Case cases[] = {
        {"tree link", RingFixRelease::Chain, [](RingFixHoldObs& o, RingFixLink&) { o.tree_now = true; }},
        {"cut", RingFixRelease::Chain, [](RingFixHoldObs& o, RingFixLink&) { o.in_cut = true; }},
        {"root", RingFixRelease::Chain, [](RingFixHoldObs& o, RingFixLink&) { o.root = "S01000SIM"; }},
        {"slip", RingFixRelease::Slip, [](RingFixHoldObs& o, RingFixLink&) { o.latched = true; }},
        {"refloat stamp", RingFixRelease::Refloat, [](RingFixHoldObs& o, RingFixLink&) { o.stamp2 = 4000.0; }},
        {"refloat erase", RingFixRelease::Refloat, [](RingFixHoldObs& o, RingFixLink&) { o.carry_ok = false; }},
        {"monitor", RingFixRelease::Monitor, [](RingFixHoldObs&, RingFixLink& L) { L.monitor_trip = true; }},
    };
    for (const Case& c : cases) {
        NetworkRingFix rf = heldState(5000.0);
        RingFixHoldObs o = presentObs();
        c.set(o, rf.links.at(kId));
        const auto ev = ringFixReleaseStep(rf, {{kId, o}}, 5000.0);
        ASSERT_EQ(ev.size(), 1u) << c.what;
        EXPECT_EQ(ev[0].release, c.cause) << c.what;
        const RingFixLink& L = rf.links.at(kId);
        EXPECT_FALSE(L.held) << c.what;
        EXPECT_EQ(L.released_s, 5000.0) << c.what;
        EXPECT_FALSE(L.monitor_trip) << c.what;
        EXPECT_EQ(rf.counters.released[static_cast<std::size_t>(c.cause)], 1) << c.what;
    }
}

TEST(RingFixRelease, AnAbsenceWithinTheHorizonPausesAndBeyondItReleases) {
    NetworkRingFix rf = heldState(5000.0);
    rf.max_gap_s = 900.0;
    RingFixHoldObs absent = presentObs();
    absent.present = false;
    EXPECT_TRUE(ringFixReleaseStep(rf, {{kId, absent}}, 5000.0).empty());
    EXPECT_TRUE(ringFixReleaseStep(rf, {}, 5600.0).empty());          // missing from the map: absent
    EXPECT_TRUE(rf.links.at(kId).held);
    EXPECT_EQ(rf.links.at(kId).absent_since_s, 5000.0);
    // Back within the horizon: the pause ends, the hold goes on.
    EXPECT_TRUE(ringFixReleaseStep(rf, {{kId, presentObs()}}, 5630.0).empty());
    EXPECT_EQ(rf.links.at(kId).absent_since_s, -1.0);
    // Absent again, now beyond the horizon.
    EXPECT_TRUE(ringFixReleaseStep(rf, {{kId, absent}}, 6000.0).empty());
    const auto ev = ringFixReleaseStep(rf, {{kId, absent}}, 6000.0 + 901.0);
    ASSERT_EQ(ev.size(), 1u);
    EXPECT_EQ(ev[0].release, RingFixRelease::Gap);
    EXPECT_FALSE(rf.links.at(kId).held);
}

TEST(RingFixMonitor, FourConsecutiveEpochsAboveTheBoundTripTheMonitor) {
    NetworkRingFix rf = heldState(5000.0);
    RingFixDecideObs o = obsNear(kId, 10, 7, 0.0, 1e-6);
    o.have_resid = true;
    o.resid_if_m = 0.05;
    for (int k = 1; k < kRingFixMonitorEpochs; ++k) {
        ringFixDecideStep(rf, {o}, 5000.0 + 30.0 * k);
        EXPECT_FALSE(rf.links.at(kId).monitor_trip);
    }
    // One epoch under the bound restarts the count.
    o.resid_if_m = 0.01;
    ringFixDecideStep(rf, {o}, 5200.0);
    EXPECT_EQ(rf.links.at(kId).monitor_bad, 0);
    o.resid_if_m = -0.05;
    for (int k = 0; k < kRingFixMonitorEpochs; ++k) ringFixDecideStep(rf, {o}, 5300.0 + 30.0 * k);
    EXPECT_TRUE(rf.links.at(kId).monitor_trip);
    EXPECT_EQ(rf.counters.held_link_epochs, 2 * kRingFixMonitorEpochs);
    const auto ev = ringFixReleaseStep(rf, {{kId, presentObs()}}, 5500.0);
    ASSERT_EQ(ev.size(), 1u);
    EXPECT_EQ(ev[0].release, RingFixRelease::Monitor);
}

TEST(RingFixHold, DecidedEqualsReleasedPlusHeld) {
    double now = 100000.0;
    NetworkRingFix rf = stateWithHistory(kId, now);
    for (int k = 0; k < kRingFixPersistEpochs; ++k, now += 30.0)
        ringFixDecideStep(rf, {obsNear(kId, 10, 7, 0.0, 1e-5)}, now);
    ASSERT_TRUE(rf.links.at(kId).held);
    RingFixHoldObs o = presentObs();
    o.latched = true;
    ringFixReleaseStep(rf, {{kId, o}}, now);
    long long released = 0, held = 0;
    for (long long r : rf.counters.released) released += r;
    for (const auto& kv : rf.links) held += kv.second.held ? 1 : 0;
    EXPECT_EQ(rf.counters.decided, released + held);
}

// ---- The audit ----

TEST(RingFixAudit, TheAuditComparesBothBandsAndReadsTheFile) {
    const std::string path = ::testing::TempDir() + "ring_fix_audit.csv";
    {
        std::ofstream f(path);
        f << "station,sat,signal,frame_int,role,ring\n"
          << "S01000SIM,G05,L1C,10,chord,2\nS01000SIM,G05,L2W,7,chord,2\n";
    }
    const auto audit = ringFixReadAuditFile(path);
    ASSERT_EQ(audit.size(), 2u);
    EXPECT_EQ(ringFixAuditLink(audit, "S01000SIM", kId, 10, 7), RingFixAudit::Right);
    EXPECT_EQ(ringFixAuditLink(audit, "S01000SIM", kId, 10, 8), RingFixAudit::Wrong);
    EXPECT_EQ(ringFixAuditLink(audit, "S02000SIM", kId, 10, 7), RingFixAudit::Unlisted);
    std::remove(path.c_str());
}

TEST(RingFixAudit, AMalformedFileIsRefused) {
    const std::string path = ::testing::TempDir() + "ring_fix_audit_bad.csv";
    {
        std::ofstream f(path);
        f << "sat,station,signal,frame_int\nG05,S01000SIM,L1C,10\n";
    }
    EXPECT_THROW(ringFixReadAuditFile(path), std::runtime_error);
    std::remove(path.c_str());
    EXPECT_THROW(ringFixReadAuditFile(path + ".missing"), std::runtime_error);
}

TEST(RingFixNames, EveryCauseHasAName) {
    for (std::size_t k = 0; k < kRingFixReleaseCount; ++k)
        EXPECT_STRNE(ringFixReleaseName(static_cast<RingFixRelease>(k)), "?");
    for (std::size_t k = 0; k < kRingFixRefuseCount; ++k)
        EXPECT_STRNE(ringFixRefuseName(static_cast<RingFixRefuse>(k)), "?");
}

// ---- Stage N1b: the odds gate (change L) and the order (change O) ----

TEST(RingFixGateOdds, TheLogOddsAreTheLikelihoodRatioOfTheNearestAndTheNextInteger) {
    // A float on its integers with small variances: both log-odds far above the bound.
    const RingFixGate g = ringFixGate(10.0, 7.0, 1e-6, 0.0, 1e-6, kL1, kL2);
    ASSERT_TRUE(g.valid);
    EXPECT_NEAR(g.log_odds_if, (1.0 - 2.0 * g.frac_if) / (2.0 * g.sigma_if * g.sigma_if), 1e-6);
    EXPECT_NEAR(g.log_odds_wl, (1.0 - 2.0 * g.frac_wl) / (2.0 * g.sigma_wl * g.sigma_wl), 1e-6);
    EXPECT_TRUE(g.pass_odds);
    // sigma 0.20 cycle on N1 at fraction 0.05: (0.9) / (0.08) = 11.25 < ln 1e6: the odds refuse what a
    // fraction alone would take.
    const double r = kL2 / kL1, a = r / (r - 1.0), b = -1.0 / (r - 1.0);
    const double v = 0.04 / (a * a + b * b);   // uncorrelated bands: sigma_if^2 = 0.04
    const RingFixGate h = ringFixGate(10.0 + 0.05 / a, 7.0, v, 0.0, v, kL1, kL2);
    ASSERT_TRUE(h.valid);
    EXPECT_NEAR(h.sigma_if, 0.20, 1e-9);
    EXPECT_LT(h.log_odds_if, kRingFixMinLogOdds);
    EXPECT_FALSE(h.pass_odds);
}

TEST(RingFixGateOdds, TheWideLaneOddsAreTestedOnTheirOwn) {
    // A covariance stretched along the ionosphere direction (band 2 moves r times band 1, 1 cycle of
    // band 1): the ionosphere-free row cancels it, so N1 is sharp, while the wide lane keeps (1 - r) of it,
    // 0.28 cycle.  The frozen gate passes this float; the odds gate refuses it on the wide lane.
    const double r = kL2 / kL1, e2 = 1e-6;
    const RingFixGate g = ringFixGate(10.0, 7.0, 1.0 + e2, r, r * r + e2, kL1, kL2);
    ASSERT_TRUE(g.valid);
    EXPECT_GE(g.log_odds_if, kRingFixMinLogOdds);
    EXPECT_LT(g.log_odds_wl, kRingFixMinLogOdds);
    EXPECT_TRUE(g.pass);
    EXPECT_FALSE(g.pass_odds);
}

TEST(RingFixDecideOdds, TheOddsGateReplacesTheSigmaBoundAndKeepsTheFraction) {
    double now = 100000.0;
    {   // sigma_if above 0.10 but odds above ln 1e6: refused by the frozen gate, taken by the odds gate
        NetworkRingFix sg = stateWithHistory(kId, now), od = stateWithHistory(kId, now);
        od.gate_rule = RingFixGateRule::Odds;
        RingFixDecideObs o = obsNear(kId, 10, 7, 0.0, 1e-6);
        const double r = kL2 / kL1, a = r / (r - 1.0), b = -1.0 / (r - 1.0);
        const double v = 0.0144 / (a * a + b * b);   // sigma_if 0.12 cycle, frac 0: log-odds 34.7
        o.q11 = v; o.q12 = 0.0; o.q22 = v;
        const auto e1 = ringFixDecideStep(sg, {o}, now);
        ASSERT_EQ(e1.size(), 1u);
        EXPECT_EQ(e1[0].refuse, RingFixRefuse::Sigma);
        const auto e2 = ringFixDecideStep(od, {o}, now);
        ASSERT_EQ(e2.size(), 1u);
        EXPECT_EQ(e2[0].refuse, RingFixRefuse::Persist) << "passed the odds gate, the count begins";
    }
    {   // a fraction above 0.20 is refused by its own bound under the odds gate
        NetworkRingFix od = stateWithHistory(kId, now);
        od.gate_rule = RingFixGateRule::Odds;
        const auto ev = ringFixDecideStep(od, {obsNear(kId, 10, 7, 0.0, 1e-6)}, now);
        ASSERT_EQ(ev.size(), 1u);
        RingFixDecideObs o = obsNear(kId, 10, 7, 0.0, 1e-8);
        o.f1 = 10.06;   // a non-ionosphere error on band 1: frac_if = 0.27
        const auto ev2 = ringFixDecideStep(od, {o}, now + 30.0);
        ASSERT_EQ(ev2.size(), 1u);
        EXPECT_EQ(ev2[0].refuse, RingFixRefuse::Fraction);
    }
}

TEST(RingFixDecideOrder, UnderTheCertainOrderARingWaitIsNoRefusal) {
    double now = 100000.0;
    NetworkRingFix rf = stateWithHistory(kId, now);
    rf.order = RingFixOrder::Certain;
    for (int k = 0; k < kRingFixPersistEpochs; ++k, now += 30.0) {
        RingFixDecideObs o = obsNear(kId, 10, 7, 0.0, 1e-5);
        o.candidate = false;   // the ring order would refuse it
        o.ring = 4;
        ringFixDecideStep(rf, {o}, now);
    }
    EXPECT_TRUE(rf.links.at(kId).held);
    EXPECT_EQ(rf.counters.refused[static_cast<std::size_t>(RingFixRefuse::NotCandidate)], 0);
    EXPECT_EQ(rf.counters.decided_by_ring[4], 1);
}

TEST(RingFixDecideOrder, TheCapDecidesTheMostCertainFirstAndKeepsTheOthersCount) {
    double now = 100000.0;
    NetworkRingFix rf;
    rf.order = RingFixOrder::Certain;
    std::vector<RingFixLinkId> ids;
    for (int i = 0; i < 5; ++i) {
        RingFixLinkId id{i, "G0" + std::to_string(i + 1), "L1C", "L2W"};
        ids.push_back(id);
        RingFixLink& L = rf.links[id];
        L.chord_since_s = now - 2.0 * kRingFixWindowS;
        L.last_chord_s = now - 30.0;
    }
    // Five links passing every test, with variances 1e-5 x (i + 1): the smaller the variance, the higher
    // the log-odds.
    const auto epochObs = [&]() {
        std::vector<RingFixDecideObs> v;
        for (int i = 0; i < 5; ++i) v.push_back(obsNear(ids[static_cast<std::size_t>(i)], 10, 7, 0.0, 1e-5 * (i + 1)));
        return v;
    };
    for (int k = 1; k < kRingFixPersistEpochs; ++k, now += 30.0) ringFixDecideStep(rf, epochObs(), now);
    const auto ev = ringFixDecideStep(rf, epochObs(), now);
    int holds = 0, caps = 0;
    for (const RingFixEvent& e : ev) {
        if (e.kind == RingFixEvent::Kind::Hold) ++holds;
        if (e.kind == RingFixEvent::Kind::Refuse && e.refuse == RingFixRefuse::Cap) ++caps;
    }
    EXPECT_EQ(holds, kRingFixMaxDecisionsPerEpoch);
    EXPECT_EQ(caps, 5 - kRingFixMaxDecisionsPerEpoch);
    for (int i = 0; i < 5; ++i)
        EXPECT_EQ(rf.links.at(ids[static_cast<std::size_t>(i)]).held, i < kRingFixMaxDecisionsPerEpoch) << i;
    EXPECT_GE(rf.links.at(ids[3]).streak, kRingFixPersistEpochs);   // the count is kept
    now += 30.0;
    ringFixDecideStep(rf, epochObs(), now);
    EXPECT_TRUE(rf.links.at(ids[3]).held);
    EXPECT_TRUE(rf.links.at(ids[4]).held);
    EXPECT_EQ(rf.counters.decided, 5);
}

// ---- Stage N2: held integers through the chain's events ----

TEST(RingFixCuts, TheStepOfAMovedSideComesFromItsHeldReleasedEdge) {
    long long d = 0;
    EXPECT_TRUE(ringFixCutStep(true, 12, 12.0, true, d));
    EXPECT_EQ(d, 0);                                   // re-host onto a link at its integer: the frame is kept
    EXPECT_TRUE(ringFixCutStep(true, 12, 10.0, true, d));
    EXPECT_EQ(d, 2);                                   // satellite moved: N_h - k'
    EXPECT_TRUE(ringFixCutStep(true, 12, 10.0, false, d));
    EXPECT_EQ(d, -2);                                  // receiver moved: k' - N_h
    EXPECT_FALSE(ringFixCutStep(false, 12, 10.0, true, d));   // not held: unknown
    EXPECT_FALSE(ringFixCutStep(true, 12, 10.4, true, d));    // a target off the integers: unknown
}

TEST(RingFixCuts, CrossingLinksAreReexpressedInsideLinksKeptUnknownStepsRelease) {
    NetworkRingFix rf = heldState(5000.0);             // kId: station 3, G05, held (10, 7)
    const RingFixLinkId inside{4, "G06", "L1C", "L2W"}, crossing_r{5, "G05", "L1C", "L2W"};
    for (const RingFixLinkId& id : {inside, crossing_r}) {
        RingFixLink& L = rf.links[id];
        L.held = true; L.n1 = 20; L.n2 = 15; L.lambda1 = kL1; L.lambda2 = kL2;
    }
    // M: receivers {3, 4}, satellites {G06} on L1C with a known step 2; band 2 kept (0).
    RingFixCut c1;
    c1.signal = "L1C"; c1.stations = {3, 4}; c1.sats = {"G06"}; c1.known = true; c1.delta = 2; c1.row = "rehost";
    RingFixCut c2 = c1;
    c2.signal = "L2W"; c2.delta = 0;
    const RingFixCutOutcome out = ringFixApplyCuts(rf, {c1, c2}, 5000.0);
    // kId: receiver 3 in M, G05 outside: crossing, +2 on band 1.
    EXPECT_EQ(rf.links.at(kId).n1, 12);
    EXPECT_EQ(rf.links.at(kId).n2, 7);
    // inside: receiver 4 and G06 both in M: kept.
    EXPECT_EQ(rf.links.at(inside).n1, 20);
    // crossing_r: receiver 5 outside, G05 outside: untouched.
    EXPECT_EQ(rf.links.at(crossing_r).n1, 20);
    EXPECT_FALSE(rf.links.at(crossing_r).rebase_stamps);
    EXPECT_TRUE(rf.links.at(kId).rebase_stamps);
    EXPECT_TRUE(rf.links.at(inside).rebase_stamps);
    EXPECT_EQ(out.reexpressed.size(), 1u);
    EXPECT_EQ(rf.counters.cuts_known_zero, 1);
    // A satellite in M, its receiver outside: minus the step.
    NetworkRingFix rs = heldState(5000.0);
    RingFixCut c3;
    c3.signal = "L2W"; c3.sats = {"G05"}; c3.known = true; c3.delta = 3; c3.row = "returning";
    ringFixApplyCuts(rs, {c3}, 5000.0);
    EXPECT_EQ(rs.links.at(kId).n2, 4);
    // An unknown step across the link releases it.
    NetworkRingFix ru = heldState(5000.0);
    RingFixCut c4;
    c4.signal = "L1C"; c4.stations = {3}; c4.known = false; c4.row = "rehost";
    const RingFixCutOutcome o4 = ringFixApplyCuts(ru, {c4}, 5000.0);
    EXPECT_FALSE(ru.links.at(kId).held);
    ASSERT_EQ(o4.released.size(), 1u);
    EXPECT_EQ(ru.counters.released[static_cast<std::size_t>(RingFixRelease::Chain)], 1);
    EXPECT_EQ(ru.counters.cut_released, 1);
}

TEST(RingFixCuts, AStampRebaseAfterACutIsNoRefloat) {
    NetworkRingFix rf = heldState(5000.0);
    rf.links.at(kId).rebase_stamps = true;
    RingFixHoldObs o = presentObs();
    o.stamp1 = 5001.0;   // the harvest re-created the entries the cut erased
    o.stamp2 = 5001.0;
    EXPECT_TRUE(ringFixReleaseStep(rf, {{kId, o}}, 5030.0).empty());
    EXPECT_TRUE(rf.links.at(kId).held);
    EXPECT_FALSE(rf.links.at(kId).rebase_stamps);
    EXPECT_EQ(rf.links.at(kId).stamp1, 5001.0);
    EXPECT_EQ(rf.counters.stamps_rebased, 1);
    // A later re-level is a refloat again.
    o.stamp2 = 5100.0;
    const auto ev = ringFixReleaseStep(rf, {{kId, o}}, 5120.0);
    ASSERT_EQ(ev.size(), 1u);
    EXPECT_EQ(ev[0].release, RingFixRelease::Refloat);
}

TEST(RingFixCuts, TheOldHostIsInheritedAtItsMovedTargetWhenEveryStepIsKnown) {
    NetworkRingFix rf;
    RingFixInheritCand c;
    c.id = {7, "G09", "L1C", "L2W"};
    c.k1 = 5; c.k2 = 4; c.lambda1 = kL1; c.lambda2 = kL2; c.ring = 3; c.root = "S30000SIM";
    RingFixCut cut;
    cut.signal = "L1C"; cut.sats = {"G09"}; cut.known = true; cut.delta = 1; cut.row = "rehost";
    const auto ev = ringFixInherit(rf, {c}, {cut}, 6000.0);
    ASSERT_EQ(ev.size(), 1u);
    EXPECT_TRUE(ev[0].inherited);
    const RingFixLink& L = rf.links.at(c.id);
    EXPECT_TRUE(L.held);
    EXPECT_EQ(L.n1, 4);    // satellite in M: minus the step
    EXPECT_EQ(L.n2, 4);
    EXPECT_TRUE(L.rebase_stamps);
    EXPECT_EQ(rf.counters.inherited, 1);
    // Unknown step or a latch: not inherited.
    NetworkRingFix r2;
    cut.known = false;
    EXPECT_TRUE(ringFixInherit(r2, {c}, {cut}, 6000.0).empty());
    NetworkRingFix r3;
    c.latched = true;
    cut.known = true;
    EXPECT_TRUE(ringFixInherit(r3, {c}, {cut}, 6000.0).empty());
}

TEST(RingFixOracle, TheOraclePhaseHoldsEveryLinkAtTruthThenTheRuleDecides) {
    NetworkRingFix rf;
    rf.oracle_until_s = 600.0;
    RingFixDecideObs o = obsNear(kId, 10, 7, 0.4, 1.0);   // a float far from anything the gate would take
    o.have_truth = true;
    o.truth1 = 11;
    o.truth2 = 8;
    o.relevel1_s = 500.0;   // not re-levelled in the epoch of the hold
    o.relevel2_s = 500.0;
    const auto ev = ringFixDecideStep(rf, {o}, 1000.0);   // t0 = 1000
    ASSERT_EQ(ev.size(), 1u);
    EXPECT_TRUE(ev[0].oracle);
    EXPECT_EQ(rf.links.at(kId).n1, 11);
    // Inside the phase a held integer that differs is set again.
    rf.links.at(kId).n1 = 13;
    ringFixDecideStep(rf, {o}, 1300.0);
    EXPECT_EQ(rf.links.at(kId).n1, 11);
    EXPECT_EQ(rf.counters.oracle_corrected, 1);
    // After the phase the rule runs: a released link with this float is not decided again.
    rf.links.at(kId).held = false;
    const auto ev2 = ringFixDecideStep(rf, {o}, 1700.0);
    ASSERT_EQ(ev2.size(), 1u);
    EXPECT_EQ(ev2[0].kind, RingFixEvent::Kind::Refuse);
}

TEST(RingFixTruthModel, TheBranchTheSlipsAndTheCycle) {
    RingFixTruth T;
    T.arcs[{0, "G01", "L1C"}] = {100, {{1000.0, 2}}};
    T.arcs[{1, "G01", "L1C"}] = {50, {}};
    T.arcs[{1, "G02", "L1C"}] = {70, {}};
    T.arcs[{0, "G02", "L1C"}] = {30, {}};
    T.windup[{0, "G01"}] = {{200.0, 0.6}, {800.0, -1.4}};
    EXPECT_EQ(ringFixWindupBranch(0.5), 1);
    EXPECT_EQ(ringFixWindupBranch(-0.5), 0);
    EXPECT_EQ(ringFixWindupBranch(-1.4), -1);
    ringFixTruthObserve(T, 0, "G01", 200.0);   // first arc: branch round(0.6) = 1
    ringFixTruthObserve(T, 0, "G01", 230.0);
    long long n = 0;
    ASSERT_TRUE(ringFixTruthN(T, 0, "G01", "L1C", 500.0, 230.0, n));
    EXPECT_EQ(n, 101);
    ringFixTruthObserve(T, 0, "G01", 800.0);   // a gap above 300 s: a new arc, branch round(-1.4) = -1
    ASSERT_TRUE(ringFixTruthN(T, 0, "G01", "L1C", 1000.0, 800.0, n));
    EXPECT_EQ(n, 100 + 2 - 1);                 // the slip at 1000 counts at 1000
    ASSERT_TRUE(ringFixTruthN(T, 0, "G01", "L1C", 999.99999, 800.0, n));
    EXPECT_EQ(n, 100 + 2 - 1);                 // and at an epoch clock a few microseconds before its stamp
    ASSERT_TRUE(ringFixTruthN(T, 0, "G01", "L1C", 970.0, 800.0, n));
    EXPECT_EQ(n, 100 - 1);                     // not at the epoch before
    EXPECT_FALSE(ringFixTruthN(T, 9, "G01", "L1C", 0.0, 0.0, n));
    // A 4-cycle: chord (1, G01) +1, path (1, G02) -1, (0, G02) +1, (0, G01) -1 with targets 3 and 4 on the path.
    const std::vector<std::tuple<int, std::string, std::string, int>> terms = {
        {1, "G01", "L1C", 1}, {1, "G02", "L1C", -1}, {0, "G02", "L1C", 1}, {0, "G01", "L1C", -1}};
    // pin_sum = (-1)(3) + (+1)(4) + (-1)(5) = -4 for targets 3, 4, 5 on the three path terms.
    ASSERT_TRUE(ringFixTruthFrameInteger(T, terms, -4.0, true, 500.0, 230.0, n));
    EXPECT_EQ(n, 50 - 70 + 30 - 101 + 4);
    EXPECT_FALSE(ringFixTruthFrameInteger(T, terms, -4.0, false, 500.0, 230.0, n));
}

// ---- Stage N2b ----

TEST(RingFixCutsN2b, ALinkLeavingANestedCutAndItsOuterOneTakesBothSteps) {
    // The outer side (unknown step) is its released vertex's whole subtree: receivers {3, 4} and
    // satellites {G05, G06}, the nested side included.  The nested side (G06) re-attached through a
    // held link the walk took first, with a step of 0.
    NetworkRingFix rf = heldState(5000.0);                     // kId: receiver 3, G05: both in the outer side
    const RingFixLinkId leaves{7, "G06", "L1C", "L2W"};       // receiver 7 outside, G06 in both sides
    const RingFixLinkId across{4, "G06", "L1C", "L2W"};       // receiver 4 in the outer side, G06 nested
    for (const RingFixLinkId& id : {leaves, across}) {
        RingFixLink& L = rf.links[id];
        L.held = true; L.n1 = 20; L.n2 = 15; L.lambda1 = kL1; L.lambda2 = kL2;
    }
    RingFixCut outer;
    outer.signal = "L1C"; outer.stations = {3, 4}; outer.sats = {"G05", "G06"}; outer.known = false;
    outer.row = "rehost";
    RingFixCut nested;
    nested.signal = "L1C"; nested.sats = {"G06"}; nested.known = true; nested.delta = 0; nested.row = "rehost";
    nested.held_first = true;
    const RingFixCutOutcome out = ringFixApplyCuts(rf, {outer, nested}, 5000.0);
    EXPECT_FALSE(rf.links.at(leaves).held);   // across the unknown outer step
    EXPECT_TRUE(rf.links.at(across).held);    // inside the outer side, across the nested one at 0
    EXPECT_EQ(rf.links.at(across).n1, 20);
    EXPECT_TRUE(rf.links.at(kId).held);
    ASSERT_EQ(out.kept_by_cut.size(), 2u);
    EXPECT_TRUE(out.kept_by_cut[0].empty());
    ASSERT_EQ(out.kept_by_cut[1].size(), 1u);
    EXPECT_EQ(out.kept_by_cut[1][0].station, 4);
    EXPECT_EQ(rf.counters.cuts_held_first, 1);
    EXPECT_EQ(rf.counters.cuts_held_first_zero, 1);
    EXPECT_EQ(rf.counters.cut_released, 1);
}

TEST(RingFixLogRule, TheLogRuleTracesWouldBeDecisionsAndHoldsNothing) {
    double now = 100000.0;
    NetworkRingFix rf = stateWithHistory(kId, now);
    rf.rule = RingFixRule::Log;
    for (int k = 1; k < kRingFixPersistEpochs; ++k, now += 30.0)
        ringFixDecideStep(rf, {obsNear(kId, 10, 7, 0.02, 1e-5)}, now);
    auto ev = ringFixDecideStep(rf, {obsNear(kId, 10, 7, 0.02, 1e-5)}, now);
    ASSERT_EQ(ev.size(), 1u);
    EXPECT_EQ(ev[0].kind, RingFixEvent::Kind::Hold);
    EXPECT_TRUE(ev[0].log_only);
    EXPECT_FALSE(rf.links.at(kId).held);
    EXPECT_EQ(rf.counters.decided, 0);
    EXPECT_EQ(rf.counters.log_links, 1);
    EXPECT_EQ(rf.counters.log_link_epochs, 1);
    now += 30.0;
    ev = ringFixDecideStep(rf, {obsNear(kId, 10, 7, 0.02, 1e-5)}, now);   // the same integers again
    ASSERT_EQ(ev.size(), 1u);
    EXPECT_TRUE(ev[0].log_only);
    EXPECT_EQ(rf.counters.log_link_epochs, 2);
    EXPECT_EQ(rf.counters.log_changed, 0);
    for (int k = 0; k < kRingFixPersistEpochs; ++k) {   // other integers, decided again after the count
        now += 30.0;
        ev = ringFixDecideStep(rf, {obsNear(kId, 11, 8, 0.02, 1e-5)}, now);
    }
    ASSERT_EQ(ev.size(), 1u);
    EXPECT_TRUE(ev[0].log_only);
    EXPECT_EQ(rf.counters.log_links, 1);
    EXPECT_EQ(rf.counters.log_changed, 1);
    EXPECT_EQ(rf.counters.decided, 0);
    EXPECT_FALSE(rf.links.at(kId).held);
}

TEST(RingFixOracle, TheOracleWaitsOutTheEpochOfAReleaseALatchARelevelOrACut) {
    NetworkRingFix rf;
    rf.oracle_until_s = 6000.0;
    RingFixDecideObs o = obsNear(kId, 10, 7, 0.4, 1.0);
    o.have_truth = true;
    o.truth1 = 11;
    o.truth2 = 8;
    o.relevel1_s = 500.0;
    o.relevel2_s = 500.0;
    rf.links[kId].released_s = 1000.0;   // released in this epoch
    EXPECT_TRUE(ringFixDecideStep(rf, {o}, 1000.0).empty());
    EXPECT_FALSE(rf.links.at(kId).held);
    RingFixDecideObs latched = o;
    latched.latched = true;
    EXPECT_TRUE(ringFixDecideStep(rf, {latched}, 1030.0).empty());
    RingFixDecideObs relevelled = o;
    relevelled.relevel2_s = 1060.0;
    EXPECT_TRUE(ringFixDecideStep(rf, {relevelled}, 1060.0).empty());
    RingFixDecideObs erased = o;
    erased.carry_ok = false;
    EXPECT_TRUE(ringFixDecideStep(rf, {erased}, 1090.0).empty());
    EXPECT_EQ(rf.counters.oracle_waited, 4);
    const auto ev = ringFixDecideStep(rf, {o}, 1120.0);   // the next quiet epoch: held at truth
    ASSERT_EQ(ev.size(), 1u);
    EXPECT_TRUE(rf.links.at(kId).held);
    EXPECT_EQ(rf.links.at(kId).n1, 11);
    EXPECT_EQ(rf.links.at(kId).n2, 8);
}

TEST(RingFixNames, TheRulesHaveNames) {
    EXPECT_STREQ(ringFixRuleName(RingFixRule::Gated), "gated");
    EXPECT_STREQ(ringFixRuleName(RingFixRule::Plain), "plain");
    EXPECT_STREQ(ringFixRuleName(RingFixRule::Log), "log");
}

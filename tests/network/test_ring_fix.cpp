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

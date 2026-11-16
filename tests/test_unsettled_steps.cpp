// Unit tests of the unsettled steps of the network product emitter (network.ring_fix.unsettled_steps): while a held
// family's two signals are not both flagged settled their phase counters step at every emission, and once more when
// both become flagged.

#include "products/NetworkProductEmitter.hpp"
#include "products/SsrCorrectionStore.hpp"

#include <gtest/gtest.h>

#include <map>
#include <sstream>
#include <string>

using namespace GnssProcessor;

namespace {

/// One satellite of an emission: its L1X and L5X flags (signal_integer); the biases do not move.
struct Flags { bool x1{true}, x5{true}; };

NetworkSolutionEpoch emission(double tow, const std::map<std::string, Flags>& sats) {
    NetworkSolutionEpoch sol;
    sol.epoch_time = GnssTime{ 2313, tow };
    sol.iod_ssr = 1; sol.provider_id = 1; sol.solution_id = 1;
    for (const auto& [id, f] : sats) {
        NetworkSatSolution ns;
        ns.sat = id; ns.has_clock = true; ns.clock_c0_m = 0.0;
        ns.phase_bias["L1X"] = NetworkPhaseBias{ 1.0, f.x1, 1 };
        ns.phase_bias["L5X"] = NetworkPhaseBias{ 2.0, f.x5, 1 };
        ns.phase_bias["L1C"] = NetworkPhaseBias{ 3.0, false, 0 };   // a signal of no held family
        sol.sats.push_back(ns);
    }
    return sol;
}

int ctr(const NetworkProductEmitter& em, const std::string& sat, const std::string& sig) {
    return em.discontinuityCounter(sat, sig);
}

}  // namespace

TEST(UnsettledSteps, AnUnsettledFamilyStepsAtEveryEmissionAndOnceMoreWhenItSettles) {
    NetworkProductEmitter em(0.05);
    em.setUnsettledSteps({ "E:L1X/L5X" });
    ASSERT_TRUE(em.unsettledStepsArmed());
    SsrCorrectionStore store;
    em.emitToStore(emission(0.0, { { "E01", { true, true } }, { "E02", { true, false } } }), store);   // baselines
    em.emitToStore(emission(30.0, { { "E01", { true, true } }, { "E02", { true, false } } }), store);
    EXPECT_EQ(ctr(em, "E01", "L1X"), 0);
    EXPECT_EQ(ctr(em, "E02", "L1X"), 1);   // not both flagged: both signals step
    EXPECT_EQ(ctr(em, "E02", "L5X"), 1);
    em.emitToStore(emission(60.0, { { "E01", { true, true } }, { "E02", { true, true } } }), store);
    EXPECT_EQ(ctr(em, "E02", "L1X"), 2);   // settles: once more
    EXPECT_EQ(ctr(em, "E02", "L5X"), 2);
    em.emitToStore(emission(90.0, { { "E01", { true, true } }, { "E02", { true, true } } }), store);
    EXPECT_EQ(ctr(em, "E02", "L1X"), 2);   // stays flagged: no step
    EXPECT_EQ(ctr(em, "E01", "L5X"), 0);
    EXPECT_EQ(ctr(em, "E02", "L1C"), 0);   // a signal of no held family is untouched
    const auto& n = em.unsettledStepCounts();
    ASSERT_EQ(n.count("E:L1X/L5X"), 1u);
    EXPECT_EQ(n.at("E:L1X/L5X").first, 2);    // E02's two signals at TOW 30
    EXPECT_EQ(n.at("E:L1X/L5X").second, 2);   // and at TOW 60
}

TEST(UnsettledSteps, AFamilyFlaggedAtTheFirstEmissionAfterARestoreTakesTheSettlingStep) {
    NetworkProductEmitter a(0.05);
    a.setUnsettledSteps({ "E:L1X/L5X" });
    SsrCorrectionStore store;
    a.emitToStore(emission(0.0, { { "E02", { true, false } } }), store);
    a.emitToStore(emission(30.0, { { "E02", { true, false } } }), store);   // unsettled: steps
    ASSERT_EQ(ctr(a, "E02", "L1X"), 1);
    std::stringstream snap;
    a.serializeState(snap);
    NetworkProductEmitter b(0.05);
    b.setUnsettledSteps({ "E:L1X/L5X" });
    ASSERT_TRUE(b.restoreState(snap));
    b.emitToStore(emission(60.0, { { "E02", { true, true } } }), store);    // flagged after the restore
    EXPECT_EQ(ctr(b, "E02", "L1X"), 2);   // the settling step: the previous state is unknown
    EXPECT_EQ(ctr(b, "E02", "L5X"), 2);
    b.emitToStore(emission(90.0, { { "E02", { true, true } } }), store);
    EXPECT_EQ(ctr(b, "E02", "L1X"), 2);   // and only once
}

TEST(UnsettledSteps, AFamilySignalMissingCountsAsUnflaggedAndUnarmedNothingSteps) {
    NetworkProductEmitter em(0.05);
    em.setUnsettledSteps({ "E:L1X/L5X" });
    SsrCorrectionStore store;
    em.emitToStore(emission(0.0, { { "E01", { true, true } } }), store);
    NetworkSolutionEpoch e = emission(30.0, { { "E01", { true, true } } });
    e.sats[0].phase_bias.erase("L5X");
    em.emitToStore(e, store);
    EXPECT_EQ(ctr(em, "E01", "L1X"), 1);   // the family is not both flagged with L5X absent
    NetworkProductEmitter off(0.05);
    off.emitToStore(emission(0.0, { { "E01", { true, false } } }), store);
    off.emitToStore(emission(30.0, { { "E01", { true, false } } }), store);
    EXPECT_FALSE(off.unsettledStepsArmed());
    EXPECT_EQ(ctr(off, "E01", "L1X"), 0);
    EXPECT_THROW(off.setUnsettledSteps({ "E-L1X/L5X" }), std::invalid_argument);
}

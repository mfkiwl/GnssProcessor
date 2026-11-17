/**
 * @file test_continuity_guard.cpp
 * @brief Unit tests of the network product emitter's continuity guard (network.ring_fix.continuity_guard_cyc):
 *        suite ContinuityGuard.
 *
 * Per held family and satellite the emitter forms the satellite's level in narrow-lane cycles from its own records
 * (clock, the two phase biases, the two code biases of the same bands) less the family's running median step; while
 * both flags stay up and neither counter steps, a level that moves from its value at the run's start by more than the
 * threshold lowers both flags for the hold and steps both counters; the unsettled steps then step them while lowered
 * and once more when the flags rise.
 *
 * The epochs here hold five Galileo satellites with L1X / L5X phases and C1X / C5X codes; one of them (E05) has its
 * L1X phase bias moved by 1 mm per epoch, which moves its level by f1^2 / (c (f1 - f2)) x 1 mm = 0.0208 narrow-lane
 * cycle per epoch (E1 / E5a), below the emitter's 5 cm value-jump bar; the other four hold the family's median step at
 * zero.
 */
#include "products/NetworkProductEmitter.hpp"
#include "products/SsrCorrectionStore.hpp"

#include <gtest/gtest.h>

#include <algorithm>
#include <map>
#include <stdexcept>
#include <string>

using namespace GnssProcessor;

namespace {

/// An emission at @p tow: five Galileo satellites, every flag up, E05's L1X phase bias moved by @p e05_l1x_m.
NetworkSolutionEpoch emission(double tow, double e05_l1x_m, bool e05_flags = true) {
    NetworkSolutionEpoch sol;
    sol.epoch_time = GnssTime{ 2313, tow };
    sol.iod_ssr = 1; sol.provider_id = 1; sol.solution_id = 1;
    for (const char* id : { "E01", "E02", "E03", "E04", "E05" }) {
        NetworkSatSolution ns;
        ns.sat = id; ns.has_clock = true; ns.clock_c0_m = 10.0;
        const bool moving = std::string(id) == "E05";
        const bool f = moving ? e05_flags : true;
        ns.phase_bias["L1X"] = NetworkPhaseBias{ 1.0 + (moving ? e05_l1x_m : 0.0), f, 1 };
        ns.phase_bias["L5X"] = NetworkPhaseBias{ 2.0, f, 1 };
        ns.code_bias_m["C1X"] = 0.3;
        ns.code_bias_m["C5X"] = 0.5;
        sol.sats.push_back(ns);
    }
    return sol;
}

/// Arms @p em with the unsettled steps of E:L1X/L5X and the guard (0.15 cycle, @p hold emissions, runs of 4).
void arm(NetworkProductEmitter& em, int hold) {
    em.setUnsettledSteps({ "E:L1X/L5X" });
    em.setContinuityGuard(0.15, hold, 4);
}

}  // namespace

TEST(ContinuityGuard, ArmingNeedsTheUnsettledStepsAndLegalValues) {
    NetworkProductEmitter em(0.05);
    EXPECT_THROW(em.setContinuityGuard(0.15, 20, 4), std::invalid_argument);
    em.setUnsettledSteps({ "E:L1X/L5X" });
    EXPECT_THROW(em.setContinuityGuard(0.0, 20, 4), std::invalid_argument);
    EXPECT_THROW(em.setContinuityGuard(0.15, 0, 4), std::invalid_argument);
    EXPECT_THROW(em.setContinuityGuard(0.15, 20, 0), std::invalid_argument);
    EXPECT_FALSE(em.continuityGuardArmed());
    em.setContinuityGuard(0.15, 20, 4);
    EXPECT_TRUE(em.continuityGuardArmed());
}

TEST(ContinuityGuard, AStaticFamilyNeverTrips) {
    NetworkProductEmitter em(0.05);
    arm(em, 5);
    SsrCorrectionStore store;
    for (int k = 0; k < 30; ++k) em.emitToStore(emission(30.0 * k, 0.0), store);
    EXPECT_TRUE(em.continuityGuardTrips().empty());
    EXPECT_EQ(em.discontinuityCounter("E05", "L1X"), 0);
    EXPECT_EQ(em.continuityGuardLoweredKeys(), 0);
}

TEST(ContinuityGuard, AMovingFlaggedLevelTripsLowersTheFlagsAndStepsTheCounters) {
    NetworkProductEmitter em(0.05);
    arm(em, 5);
    SsrCorrectionStore store;
    // E05 moves 1 mm per epoch from epoch 5 to epoch 12 (0.0208 cycle each), then stays: its level has moved 0.166
    // cycle at epoch 12, past the 0.15 bar after a run of 13 emissions.
    const auto offset = [](int k) { return k < 5 ? 0.0 : 0.001 * (std::min(k, 12) - 4); };
    for (int k = 0; k <= 11; ++k) em.emitToStore(emission(30.0 * k, offset(k)), store);
    EXPECT_TRUE(em.continuityGuardTrips().empty());   // 0.145 cycle at epoch 11: not yet
    EXPECT_EQ(em.discontinuityCounter("E05", "L1X"), 0);
    NetworkSolutionEpoch trip = emission(30.0 * 12, offset(12));
    em.emitToStore(trip, store);   // the trip
    em.applyContinuityGuardFlags(trip);   // the file is written from the solution: it says what the store says
    for (const NetworkSatSolution& s : trip.sats) {
        EXPECT_EQ(s.phase_bias.at("L1X").signal_integer, s.sat != "E05") << s.sat;
        EXPECT_EQ(s.phase_bias.at("L5X").signal_integer, s.sat != "E05") << s.sat;
    }
    ASSERT_EQ(em.continuityGuardTrips().count("E:L1X/L5X"), 1u);
    EXPECT_EQ(em.continuityGuardTrips().at("E:L1X/L5X"), 1);
    EXPECT_EQ(em.discontinuityCounter("E05", "L1X"), 1);
    EXPECT_EQ(em.discontinuityCounter("E05", "L5X"), 1);
    EXPECT_FALSE(store.getPhaseBias("E05", "L1X")->signal_integer);
    EXPECT_FALSE(store.getPhaseBias("E05", "L5X")->signal_integer);
    EXPECT_TRUE(store.getPhaseBias("E04", "L1X")->signal_integer);   // the others untouched
    EXPECT_EQ(em.discontinuityCounter("E04", "L1X"), 0);
    // The hold: lowered at the trip and the next 4 emissions, the unsettled steps stepping both counters.
    for (int k = 13; k <= 16; ++k) {
        em.emitToStore(emission(30.0 * k, offset(k)), store);
        EXPECT_FALSE(store.getPhaseBias("E05", "L1X")->signal_integer) << "epoch " << k;
        EXPECT_EQ(em.discontinuityCounter("E05", "L5X"), k - 11) << "epoch " << k;
    }
    // The flags rise again with the settling step; the level no longer moves, so the new run does not trip.
    em.emitToStore(emission(30.0 * 17, offset(17)), store);
    EXPECT_TRUE(store.getPhaseBias("E05", "L1X")->signal_integer);
    EXPECT_EQ(em.discontinuityCounter("E05", "L1X"), 6);
    for (int k = 18; k < 40; ++k) em.emitToStore(emission(30.0 * k, offset(k)), store);
    EXPECT_EQ(em.continuityGuardTrips().at("E:L1X/L5X"), 1);
    EXPECT_EQ(em.discontinuityCounter("E05", "L1X"), 6);
    EXPECT_EQ(em.continuityGuardLoweredKeys(), 10);   // two keys at five emissions
}

TEST(ContinuityGuard, AnUnflaggedSatelliteIsNotGuarded) {
    NetworkProductEmitter em(0.05);
    arm(em, 5);
    SsrCorrectionStore store;
    for (int k = 0; k < 20; ++k) em.emitToStore(emission(30.0 * k, 0.001 * k, /*e05_flags=*/false), store);
    EXPECT_TRUE(em.continuityGuardTrips().empty());   // its counters step by the unsettled steps alone
    EXPECT_EQ(em.discontinuityCounter("E05", "L1X"), 19);
}

TEST(ContinuityGuard, AStepOfAnotherRuleRestartsTheRun) {
    NetworkProductEmitter em(0.05);
    arm(em, 5);
    SsrCorrectionStore store;
    // A 6 cm jump of E05's L1X at epoch 6 is past the 5 cm value bar: the counter steps by that rule and the run
    // restarts there, so the 1.2-cycle level jump itself is no trip.
    for (int k = 0; k < 20; ++k) em.emitToStore(emission(30.0 * k, k < 6 ? 0.0 : 0.06), store);
    EXPECT_TRUE(em.continuityGuardTrips().empty());
    EXPECT_EQ(em.discontinuityCounter("E05", "L1X"), 1);
}

TEST(ContinuityGuard, OffIsUntouched) {
    NetworkProductEmitter em(0.05);
    em.setUnsettledSteps({ "E:L1X/L5X" });
    SsrCorrectionStore store;
    for (int k = 0; k < 20; ++k) em.emitToStore(emission(30.0 * k, k < 5 ? 0.0 : 0.001 * (k - 4)), store);
    EXPECT_FALSE(em.continuityGuardArmed());
    EXPECT_EQ(em.discontinuityCounter("E05", "L1X"), 0);
    EXPECT_TRUE(store.getPhaseBias("E05", "L1X")->signal_integer);
}

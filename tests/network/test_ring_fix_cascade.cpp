// Unit tests of the ring fix's cascade (include/network/ar/RingFix.hpp, network.ring_fix.cascade): the reference a
// third signal is decided against, and the gate on their float difference.

#include "network/ar/RingFix.hpp"

#include <gtest/gtest.h>

#include <cmath>
#include <string>

using namespace GnssProcessor;

TEST(RingFixCascade, TheReferenceIsTheSiblingOnTheThirdsBandElseTheNearestFrequency) {
    EXPECT_EQ(ringFixCascadeReference("G01", "L1C", "L2W", "L1W"), "L1C");   // a same-frequency sibling
    EXPECT_EQ(ringFixCascadeReference("G01", "L1C", "L2W", "L5Q"), "L2W");   // GPS L5 from L2
    EXPECT_EQ(ringFixCascadeReference("E01", "L1C", "L5Q", "L7Q"), "L5Q");   // Galileo E5b from E5a
    EXPECT_EQ(ringFixCascadeReference("E01", "L1X", "L5X", "L6C"), "L5X");   // Galileo E6 nearer E5a than E1
}

TEST(RingFixCascadeGate, TheDifferenceDecidesWithinTheFractionAndTheOdds) {
    // A float difference 0.03 cycle off 7 with a sigma of 0.02: decided.
    RingFixCascadeGate g = ringFixCascadeGate(105.0, 98.03, 1e-8, 0.0, 4e-4, 1.0);
    ASSERT_TRUE(g.valid);
    EXPECT_EQ(g.d, 7);
    EXPECT_NEAR(g.frac, 0.03, 1e-9);
    EXPECT_NEAR(g.sigma, std::sqrt(4e-4 + 1e-8), 1e-12);
    EXPECT_TRUE(g.pass);
    // The same with 0.15 cycle off: refused for the fraction.
    g = ringFixCascadeGate(105.0, 97.85, 1e-8, 0.0, 4e-4, 1.0);
    EXPECT_FALSE(g.pass);
    EXPECT_GT(g.frac, kRingFixCascadeMaxFracCyc);
    // 0.05 off with a sigma of 0.2: the odds refuse it.
    g = ringFixCascadeGate(105.0, 98.05, 1e-8, 0.0, 0.04, 1.0);
    EXPECT_FALSE(g.pass);
    EXPECT_LT(g.log_odds, kRingFixMinLogOdds);
    // A covariance that cancels the variance: the difference is exact.
    g = ringFixCascadeGate(10.0, 7.0, 0.01, 0.01, 0.01, 1.0);
    EXPECT_TRUE(g.pass);
    EXPECT_EQ(g.d, 3);
    EXPECT_FALSE(ringFixCascadeGate(NAN, 1.0, 0.0, 0.0, 0.0, 1.0).valid);
}

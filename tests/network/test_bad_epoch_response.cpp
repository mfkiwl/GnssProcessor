/**
 * @file test_bad_epoch_response.cpp
 * @brief The response to a bad epoch: the size of each band's step at a slip, and a float-vehicle drop that
 *        covers it (network.amb_float_drop_jump_k).
 *
 * A flagged slip of 288 cycles on L1 alone (about 55 m) used to be dropped to the arc's birth variance at its
 * pre-slip level, a prior about 90 sigma wrong that the epoch's solve spread into the line of sight's
 * ionosphere, the arc's other band and the receiver's wet delay and clock.  The response measures each band's
 * phase-minus-code step and lets the drop's variance cover it.
 */
#include <gtest/gtest.h>

#include "network/ar/AmbFloat.hpp"
#include "network/driver/RunTypes.hpp"
#include "network/slip/RawObservables.hpp"

#include <cmath>

namespace GnssProcessor {

TEST(BadEpochResponse, AnL1OnlySlipStepsTheL1PhaseMinusCodeAndLeavesL2AtCodeNoise) {
    RawSlipObs r;
    r.satellite = "G20";
    r.sig1 = "L1C";
    r.sig2 = "L2W";
    r.dual = true;
    RawSlipVerdict v;
    v.measured = true;
    v.d_l1c1 = 54.80 + 0.30;      // 288 cycles of L1 and 0.30 m of code noise on C1
    v.d_gf = 54.83;               // the phase GF moves with L1 alone
    v.d_gf_code = 0.20;           // code noise on C1 - C2
    const auto [j1, j2] = rawSlipBandJumps(r, v);
    EXPECT_NEAR(j1, 55.10, 1e-9);
    EXPECT_NEAR(j2, std::abs(55.10 - 54.83 + 0.20), 1e-9);   // L2 - C2: code noise only
    // A step formed across a pair change, or not measured, gives nothing.
    v.pair_changed = true;
    EXPECT_EQ(rawSlipBandJumps(r, v).first, 0.0);
    v.pair_changed = false;
    v.measured = false;
    EXPECT_EQ(rawSlipBandJumps(r, v).second, 0.0);
}

TEST(BadEpochResponse, TheBandStepsAreKeyedLikeTheFreeEpochLatch) {
    RawSlipEpoch ep;
    ep.rows.resize(2);
    ep.verdict.resize(2);
    RawSlipObs r;
    r.satellite = "G20";
    r.sig1 = "L1C";
    r.sig2 = "L2W";
    r.dual = true;
    ep.rows[1].push_back(r);
    RawSlipVerdict v;
    v.measured = true;
    v.d_l1c1 = -3.0;
    v.d_gf = -3.0;
    ep.verdict[1]["G20"] = v;
    std::map<std::pair<int, std::string>, double> out;
    networkRawSlipBandJumps(ep, out);
    ASSERT_EQ(out.size(), 2u);
    EXPECT_NEAR(out.at({1, "G20_L1C"}), 3.0, 1e-12);
    EXPECT_NEAR(out.at({1, "G20_L2W"}), 0.0, 1e-12);
}

TEST(BadEpochResponse, ACoveringDropTakesTheStepAsItsVarianceAndKeepsTheValue) {
    LocalCarry lc{-10.42, 0.004, 0.0};
    lc.var_birth = 0.37;
    // The drop as before: the birth variance, the pre-slip value.
    LocalCarry plain = lc;
    ambFloatDropFloored(plain, 0.37, 0.0, 1000.0, 10);
    EXPECT_NEAR(plain.var, 0.37, 1e-12);
    EXPECT_EQ(plain.value_abs, -10.42);
    // Covering a 55 m step: the band is effectively free this epoch.
    LocalCarry covered = lc;
    const double cover_m2 = 55.10 * 55.10;
    const AmbDropOutcome o = ambFloatDropFloored(covered, std::max(0.37, cover_m2), 0.0, 1000.0, 10);
    EXPECT_TRUE(o.acted);
    EXPECT_NEAR(covered.var, cover_m2, 1e-9);
    EXPECT_EQ(covered.value_abs, -10.42);
    // A one-cycle slip's step sits at code noise, below the birth variance: the drop is unchanged.
    LocalCarry small = lc;
    ambFloatDropFloored(small, std::max(0.37, 0.4 * 0.4), 0.0, 1000.0, 10);
    EXPECT_NEAR(small.var, 0.37, 1e-12);
}

}  // namespace GnssProcessor

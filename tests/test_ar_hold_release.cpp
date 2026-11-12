/**
 * @file test_ar_hold_release.cpp
 * @brief Unit tests for the held-pair release of the WL-constrained resolver
 *        (@c estimation.ambiguity_resolution.hold_release_cyc).
 *
 * The misfit is exact algebra on synthetic DDs built from known integers: a float
 * equal to the held integers gives zero, a widelane slip moves both measures, and
 * a pure ionosphere change moves the widelane but leaves the ionosphere-free
 * combination where it was.  The satellite choice is checked on small held sets.
 *
 * Suite name @c ArHoldReleaseTest is owned solely by this file.
 */

#include <gtest/gtest.h>

#include "filter/AmbiguityResolver.hpp"
#include "common/Constants.hpp"

#include <string>
#include <utility>
#include <vector>

namespace GnssProcessor {

/// Test seam for the private static helpers (friend in AmbiguityResolver.hpp).
struct ArHoldReleaseTestAccess {
    using Held   = AmbiguityResolution::HeldPairFix;
    using Misfit = AmbiguityResolver::HoldMisfit;
    using Pairs  = std::vector<std::pair<std::string, std::string>>;
    static Misfit misfit(const Held& h, double dd1, double dd2) {
        return AmbiguityResolver::holdMisfit_(h, dd1, dd2);
    }
    static std::vector<std::string> choose(const Pairs& held, const Pairs& bad) {
        return AmbiguityResolver::chooseReleaseSatellites_(held, bad);
    }
};

} // namespace GnssProcessor

using namespace GnssProcessor;

namespace {

constexpr double kF1 = 1575.42e6;
constexpr double kF2 = 1227.60e6;
const double kL1 = Constants::SPEED_OF_LIGHT / kF1;
const double kL2 = Constants::SPEED_OF_LIGHT / kF2;

ArHoldReleaseTestAccess::Held heldPair(int n1, int wl) {
    return { "G06", "G31", "L1W", "L2W", kF1, kF2, kL1, kL2, n1, wl };
}

} // namespace

TEST(ArHoldReleaseTest, FloatAtTheHeldIntegersHasNoMisfit) {
    const auto h = heldPair(0, 4);
    const auto m = ArHoldReleaseTestAccess::misfit(h, 0.0 * kL1, -4.0 * kL2);
    EXPECT_NEAR(m.d_wl, 0.0, 1e-12);
    EXPECT_NEAR(m.d_if, 0.0, 1e-12);
}

TEST(ArHoldReleaseTest, WidelaneOneCycleOffMovesBothMeasures) {
    // Held N_1 = 0, WL = 3 (N_2 = -3); the data say N_2 = -4 (WL = 4).
    const auto h = heldPair(0, 3);
    const auto m = ArHoldReleaseTestAccess::misfit(h, 0.0 * kL1, -4.0 * kL2);
    EXPECT_NEAR(m.d_wl, 1.0, 1e-12);
    // One L2 cycle in the ionosphere-free combination: f2^2 lambda_2 / (f1^2 - f2^2),
    // in narrow-lane cycles lambda_NL = c / (f1 + f2): f2 / (f1 - f2) = 3.53 cycles.
    EXPECT_NEAR(m.d_if, kF2 / (kF1 - kF2), 1e-9);
}

TEST(ArHoldReleaseTest, IonosphereChangeMovesOnlyTheWidelane) {
    // Phase ambiguities in metres absorb -I on L1 and -gamma I on L2 when the
    // slant ionosphere is mis-split: the ionosphere-free combination is unchanged.
    const auto h = heldPair(2, 1);
    const double gamma = (kF1 / kF2) * (kF1 / kF2);
    const double I = 0.05;
    const double dd1 = 2.0 * kL1 - I;
    const double dd2 = 1.0 * kL2 - gamma * I;
    const auto m = ArHoldReleaseTestAccess::misfit(h, dd1, dd2);
    EXPECT_NEAR(m.d_if, 0.0, 1e-12);
    EXPECT_NEAR(m.d_wl, -I / kL1 + gamma * I / kL2, 1e-12);
}

TEST(ArHoldReleaseTest, OneContradictedPairRefloatsItsNonReferenceSatellite) {
    const ArHoldReleaseTestAccess::Pairs held = {
        { "G06", "G31" }, { "G03", "G31" }, { "G04", "G31" } };
    const auto out = ArHoldReleaseTestAccess::choose(held, { { "G06", "G31" } });
    EXPECT_EQ(out, (std::vector<std::string>{ "G06" }));
}

TEST(ArHoldReleaseTest, MostPairsOfOneReferenceRefloatTheReference) {
    const ArHoldReleaseTestAccess::Pairs held = {
        { "G06", "G31" }, { "G03", "G31" }, { "G04", "G31" } };
    const auto out = ArHoldReleaseTestAccess::choose(held, { { "G06", "G31" }, { "G03", "G31" } });
    EXPECT_EQ(out, (std::vector<std::string>{ "G31" }));
}

TEST(ArHoldReleaseTest, AMinorityOfAReferencesPairsRefloatsEachSatellite) {
    const ArHoldReleaseTestAccess::Pairs held = {
        { "G06", "G31" }, { "G03", "G31" }, { "G04", "G31" }, { "G09", "G31" }, { "G26", "G31" } };
    const auto out = ArHoldReleaseTestAccess::choose(held, { { "G06", "G31" }, { "G03", "G31" } });
    EXPECT_EQ(out, (std::vector<std::string>{ "G03", "G06" }));
}

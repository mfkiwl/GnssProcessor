// Unit tests of the re-attachment of untied satellites (include/network/ar/RingFix.hpp, network.ring_fix.reattach):
// whether an untied satellite's candidate links agree, and which of them carries the satellite.

#include "network/ar/RingFix.hpp"

#include <gtest/gtest.h>

#include <cstddef>
#include <vector>

using namespace GnssProcessor;

TEST(RingFixReattach, TooFewCandidatesMoveNothing) {
    const std::vector<RingFixReattachCand> c{{1, 0.20, -0.30}, {2, 0.21, -0.31}};
    const RingFixReattachPick p = ringFixReattachChoice(c);
    EXPECT_FALSE(p.ok);
    EXPECT_EQ(p.n, 2);
    EXPECT_EQ(p.index, -1);
    EXPECT_FALSE(ringFixReattachChoice({}).ok);
}

TEST(RingFixReattach, AgreeingCandidatesChooseTheOneAtTheirMedians) {
    // A common offset of about +0.2 cycle (ionosphere-free) and -0.3 cycle (wide lane); station 7 holds the median of
    // both fractions, so it carries the satellite.
    const std::vector<RingFixReattachCand> c{
        {3, 0.16, -0.34}, {5, 0.24, -0.28}, {7, 0.20, -0.30}, {9, 0.22, -0.26}, {11, 0.19, -0.31}};
    const RingFixReattachPick p = ringFixReattachChoice(c);
    ASSERT_TRUE(p.ok);
    EXPECT_EQ(p.n, 5);
    EXPECT_EQ(c[static_cast<std::size_t>(p.index)].station, 7);
    EXPECT_NEAR(p.med_if, 0.20, 1e-9);
    EXPECT_NEAR(p.med_wl, -0.30, 1e-9);
    EXPECT_LT(p.sd_if, kRingFixReattachMaxSdIfCyc);
    EXPECT_LT(p.sd_wl, kRingFixReattachMaxSdWlCyc);
}

TEST(RingFixReattach, CandidatesThatDisagreeMoveNothing) {
    const std::vector<RingFixReattachCand> c{{1, 0.20, -0.30}, {2, -0.20, 0.10}, {3, 0.45, 0.40}};
    const RingFixReattachPick p = ringFixReattachChoice(c);
    EXPECT_FALSE(p.ok);
    EXPECT_EQ(p.index, -1);
    EXPECT_GT(p.sd_if, kRingFixReattachMaxSdIfCyc);
}

TEST(RingFixReattach, FractionsAcrossHalfACycleAreOneCluster) {
    // +0.48, -0.49 and +0.49 lie within 0.03 cycle of one another on the circle of one cycle.
    const std::vector<RingFixReattachCand> c{{1, 0.48, 0.02}, {2, -0.49, 0.01}, {3, 0.49, 0.03}};
    const RingFixReattachPick p = ringFixReattachChoice(c);
    ASSERT_TRUE(p.ok);
    EXPECT_LT(p.sd_if, 0.02);
    EXPECT_NEAR(p.med_if, 0.49, 1e-9);
    EXPECT_NEAR(p.med_wl, 0.02, 1e-9);
    EXPECT_EQ(c[static_cast<std::size_t>(p.index)].station, 3);
}

TEST(RingFixReattach, AgreementOnASmallOffsetIsAConvergenceNotAMove) {
    const std::vector<RingFixReattachCand> small{{1, 0.03, -0.05}, {2, 0.05, -0.08}, {3, 0.04, -0.06}};
    const RingFixReattachPick p = ringFixReattachChoice(small);
    EXPECT_FALSE(p.ok);
    EXPECT_TRUE(p.converging);
    EXPECT_EQ(p.index, -1);
    // A wide-lane offset alone is an offset: the satellite moves.
    const std::vector<RingFixReattachCand> wl{{1, 0.03, -0.20}, {2, 0.05, -0.22}, {3, 0.04, -0.18}};
    const RingFixReattachPick q = ringFixReattachChoice(wl);
    EXPECT_TRUE(q.ok);
    EXPECT_FALSE(q.converging);
    EXPECT_EQ(wl[static_cast<std::size_t>(q.index)].station, 1);
}

TEST(RingFixReattach, TheWideLaneAloneCanRefuse) {
    const std::vector<RingFixReattachCand> c{{1, 0.10, -0.30}, {2, 0.11, 0.05}, {3, 0.09, 0.35}};
    const RingFixReattachPick p = ringFixReattachChoice(c);
    EXPECT_FALSE(p.ok);
    EXPECT_LT(p.sd_if, kRingFixReattachMaxSdIfCyc);
    EXPECT_GT(p.sd_wl, kRingFixReattachMaxSdWlCyc);
}

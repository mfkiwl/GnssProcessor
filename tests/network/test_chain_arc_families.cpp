// Unit tests of the pair families of one arc (include/network/solve/ChainChordTable.hpp, chainArcFamilies): the
// rule that pairs every band-1 signal with the arc's lowest other band, and the configured families that
// network.ring_fix.form_configured_pairs adds beside it.

#include "network/solve/ChainChordTable.hpp"

#include <gtest/gtest.h>

#include <set>
#include <string>
#include <utility>

using namespace GnssProcessor;

TEST(ChainArcFamilies, AConfiguredFamilyOfAThirdBandIsFormedBesideTheRule) {
    const std::set<std::string> sigs = {"L1C", "L5Q", "L7Q"};
    EXPECT_EQ(chainPairFamilies(sigs).size(), 1u);   // the rule: band 1 with the lowest other band only
    const ChainConfiguredPairs extra = {{'E', {{"L1C", "L5Q"}, {"L1C", "L7Q"}}}};
    const auto fams = chainArcFamilies("E11", sigs, &extra);
    ASSERT_EQ(fams.size(), 2u);
    EXPECT_EQ(fams[0], std::make_pair(std::string("L1C"), std::string("L5Q")));
    EXPECT_EQ(fams[1], std::make_pair(std::string("L1C"), std::string("L7Q")));
    EXPECT_EQ(chainArcFamilies("G11", sigs, &extra).size(), 1u);   // another constellation's families do not apply
    EXPECT_EQ(chainArcFamilies("E11", {"L1C", "L5Q"}, &extra).size(), 1u);   // L7Q not tracked
    EXPECT_EQ(chainArcFamilies("E11", sigs, nullptr).size(), 1u);
}

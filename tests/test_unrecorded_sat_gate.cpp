// Card IRDU section 12.10: the consumer's rule for satellites without a stream record.
// The gate is pure: these cases drive its edges and counters on hand-built epochs.

#include "realtime/UnrecordedSatGate.hpp"

#include <gtest/gtest.h>

#include <set>
#include <string>
#include <utility>
#include <vector>

using GnssProcessor::UnrecordedSatGate;

namespace {

using Epoch = std::vector<std::pair<std::string, bool>>;

}  // namespace

TEST(UnrecordedSatGate, RecordedSatellitesPassWithoutEvents) {
    UnrecordedSatGate g;
    std::set<std::string> out;
    const auto ev = g.step(Epoch{ { "G01", true }, { "G02", true } }, out);
    EXPECT_TRUE(ev.empty());
    EXPECT_TRUE(out.empty());
    EXPECT_EQ(g.counters().sat_epochs_seen, 2u);
    EXPECT_EQ(g.counters().sat_epochs_out, 0u);
}

TEST(UnrecordedSatGate, FirstSightingWithoutRecordIsADrop) {
    UnrecordedSatGate g;
    std::set<std::string> out;
    const auto ev = g.step(Epoch{ { "G01", true }, { "G12", false } }, out);
    ASSERT_EQ(ev.size(), 1u);
    EXPECT_EQ(ev[0].kind, UnrecordedSatGate::EventKind::Drop);
    EXPECT_EQ(ev[0].sat, "G12");
    EXPECT_TRUE(ev[0].first_sighting);
    EXPECT_EQ(out, (std::set<std::string>{ "G12" }));
    EXPECT_EQ(g.counters().drops_first_sighting, 1u);
}

TEST(UnrecordedSatGate, StaysOutWithoutASecondDrop) {
    UnrecordedSatGate g;
    std::set<std::string> out;
    g.step(Epoch{ { "G12", false } }, out);
    const auto ev = g.step(Epoch{ { "G12", false } }, out);
    EXPECT_TRUE(ev.empty());
    EXPECT_EQ(out, (std::set<std::string>{ "G12" }));
    EXPECT_EQ(g.counters().drops, 1u);
    EXPECT_EQ(g.counters().sat_epochs_out, 2u);
}

TEST(UnrecordedSatGate, LostRecordIsADropThatIsNoFirstSighting) {
    UnrecordedSatGate g;
    std::set<std::string> out;
    g.step(Epoch{ { "G05", true } }, out);
    const auto ev = g.step(Epoch{ { "G05", false } }, out);
    ASSERT_EQ(ev.size(), 1u);
    EXPECT_EQ(ev[0].kind, UnrecordedSatGate::EventKind::Drop);
    EXPECT_FALSE(ev[0].first_sighting);
    EXPECT_EQ(g.counters().drops_first_sighting, 0u);
}

TEST(UnrecordedSatGate, ReturningRecordIsAReadmit) {
    UnrecordedSatGate g;
    std::set<std::string> out;
    g.step(Epoch{ { "G05", true } }, out);
    g.step(Epoch{ { "G05", false } }, out);
    const auto ev = g.step(Epoch{ { "G05", true } }, out);
    ASSERT_EQ(ev.size(), 1u);
    EXPECT_EQ(ev[0].kind, UnrecordedSatGate::EventKind::Readmit);
    EXPECT_TRUE(out.empty());
    EXPECT_TRUE(g.dropped().empty());
    EXPECT_EQ(g.counters().readmits, 1u);
}

TEST(UnrecordedSatGate, OutOfViewKeepsTheDroppedMark) {
    UnrecordedSatGate g;
    std::set<std::string> out;
    g.step(Epoch{ { "G12", false } }, out);
    g.step(Epoch{ { "G01", true } }, out);           // G12 out of view: no event, still dropped
    EXPECT_EQ(g.dropped(), (std::set<std::string>{ "G12" }));
    const auto again = g.step(Epoch{ { "G12", false } }, out);
    EXPECT_TRUE(again.empty());                      // seen again without a record: no second drop
    const auto back = g.step(Epoch{ { "G12", true } }, out);
    ASSERT_EQ(back.size(), 1u);
    EXPECT_EQ(back[0].kind, UnrecordedSatGate::EventKind::Readmit);
    EXPECT_EQ(g.counters().drops, 1u);
    EXPECT_EQ(g.counters().readmits, 1u);
}

TEST(UnrecordedSatGate, ASatelliteListedTwiceIsDecidedOnce) {
    UnrecordedSatGate g;
    std::set<std::string> out;
    const auto ev = g.step(Epoch{ { "G12", false }, { "G12", true } }, out);
    ASSERT_EQ(ev.size(), 1u);
    EXPECT_EQ(out, (std::set<std::string>{ "G12" }));
    EXPECT_EQ(g.counters().sat_epochs_seen, 1u);
}

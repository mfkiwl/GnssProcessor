// The consumer's rule for satellites without their stream records: the clock rule
// (processing.ssr_drop_unrecorded) and its phase-bias extension
// (processing.ssr_drop_unrecorded_phase_bias).  The gate is pure: these cases drive its edges and
// counters on hand-built epochs.

#include "realtime/UnrecordedSatGate.hpp"

#include <gtest/gtest.h>

#include <set>
#include <string>
#include <utility>
#include <vector>

using GnssProcessor::UnrecordedSatGate;

namespace {

using Epoch = std::vector<std::pair<std::string, bool>>;
using Missing = UnrecordedSatGate::Missing;
using States = std::vector<UnrecordedSatGate::SatState>;

UnrecordedSatGate::SatState ok(const std::string& sat) { return { sat, Missing::None, "" }; }
UnrecordedSatGate::SatState noClock(const std::string& sat) { return { sat, Missing::Clock, "" }; }
UnrecordedSatGate::SatState noPb(const std::string& sat, const std::string& sig) {
    return { sat, Missing::PhaseBias, sig };
}

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

// ---------------------------------------------------------------------------
// The phase-bias extension: a satellite with its clock and without a phase-bias record.
// ---------------------------------------------------------------------------
TEST(UnrecordedSatGate, MissingPhaseBiasIsADropThatNamesTheSignal) {
    UnrecordedSatGate g;
    std::set<std::string> out;
    const auto ev = g.step(States{ ok("E11"), noPb("E02", "L1C") }, out);
    ASSERT_EQ(ev.size(), 1u);
    EXPECT_EQ(ev[0].kind, UnrecordedSatGate::EventKind::Drop);
    EXPECT_EQ(ev[0].sat, "E02");
    EXPECT_EQ(ev[0].missing, Missing::PhaseBias);
    EXPECT_EQ(ev[0].signal, "L1C");
    EXPECT_TRUE(ev[0].first_sighting);
    EXPECT_EQ(out, (std::set<std::string>{ "E02" }));
    EXPECT_EQ(g.counters().drops_no_phase_bias, 1u);
    EXPECT_EQ(g.counters().sat_epochs_out_no_phase_bias, 1u);
}

TEST(UnrecordedSatGate, LostPhaseBiasThenItsReturnIsADropAndAReadmit) {
    UnrecordedSatGate g;
    std::set<std::string> out;
    g.step(States{ ok("E34") }, out);
    const auto lost = g.step(States{ noPb("E34", "L5Q") }, out);
    ASSERT_EQ(lost.size(), 1u);
    EXPECT_FALSE(lost[0].first_sighting);
    EXPECT_EQ(lost[0].signal, "L5Q");
    const auto back = g.step(States{ ok("E34") }, out);
    ASSERT_EQ(back.size(), 1u);
    EXPECT_EQ(back[0].kind, UnrecordedSatGate::EventKind::Readmit);
    EXPECT_EQ(back[0].missing, Missing::None);
    EXPECT_TRUE(out.empty());
    EXPECT_EQ(g.counters().readmits, 1u);
}

TEST(UnrecordedSatGate, AChangeOfTheMissingRecordKeepsTheSatelliteOutWithoutASecondDrop) {
    UnrecordedSatGate g;
    std::set<std::string> out;
    g.step(States{ noClock("E15") }, out);
    const auto ev = g.step(States{ noPb("E15", "L1C") }, out);   // the clock is back, no phase bias yet
    EXPECT_TRUE(ev.empty());
    EXPECT_EQ(out, (std::set<std::string>{ "E15" }));
    EXPECT_EQ(g.counters().drops, 1u);
    EXPECT_EQ(g.counters().drops_no_phase_bias, 0u) << "it was dropped for its clock";
    EXPECT_EQ(g.counters().sat_epochs_out, 2u);
    EXPECT_EQ(g.counters().sat_epochs_out_no_phase_bias, 1u);
}

TEST(UnrecordedSatGate, TheClockFormIsTheStateFormWithAMissingClock) {
    UnrecordedSatGate a, b;
    std::set<std::string> oa, ob;
    const std::vector<Epoch> eps = { { { "G01", true }, { "G12", false } }, { { "G01", false }, { "G12", true } },
                                     { { "G01", true } } };
    for (const auto& e : eps) {
        States st;
        for (const auto& [sat, has] : e) st.push_back(has ? ok(sat) : noClock(sat));
        const auto ea = a.step(e, oa);
        const auto eb = b.step(st, ob);
        ASSERT_EQ(ea.size(), eb.size());
        for (std::size_t i = 0; i < ea.size(); ++i) {
            EXPECT_EQ(ea[i].kind, eb[i].kind);
            EXPECT_EQ(ea[i].sat, eb[i].sat);
            EXPECT_EQ(ea[i].first_sighting, eb[i].first_sighting);
            EXPECT_EQ(ea[i].missing, eb[i].missing);
        }
        EXPECT_EQ(oa, ob);
    }
    EXPECT_EQ(a.counters().drops_no_phase_bias, 0u);
    EXPECT_EQ(a.counters().sat_epochs_out_no_phase_bias, 0u);
}

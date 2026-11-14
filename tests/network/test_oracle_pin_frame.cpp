/**
 * @file test_oracle_pin_frame.cpp
 * @brief The oracle pin's chain-frame mode (network.cycle_slip.oracle_pin_frame_file, card IRDU section 12):
 *        the frame-target file parser and the frame table's decisions (links the chain does not pin held at
 *        lambda times their frame integer, links it pins checked at that integer, the latch when the chain pins a
 *        link elsewhere, the release at a true slip).
 */
#include <gtest/gtest.h>

#include "common/GnssTypes.hpp"
#include "common/PppUtils.hpp"
#include "config/GnssConfig.hpp"
#include "filter/StateKeySchema.hpp"
#include "logging/LogManager.hpp"
#include "network/slip/OraclePin.hpp"

#include <filesystem>
#include <fstream>
#include <map>
#include <string>
#include <tuple>
#include <vector>
#include "../support/TestTempDir.hpp"   // per-process, per-test scratch directory

namespace GnssProcessor {
namespace {

namespace fs = std::filesystem;

/// GPS week 2313, the sim fixtures' frame.
constexpr double kW = 2313.0 * 604800.0;
constexpr double kTow = 261030.0;

fs::path writeFile(const std::string& tag, const std::string& body) {
    const fs::path p = gnss_test::tempDir() / ("opin_frame_" + tag + ".csv");
    std::ofstream f(p);
    f << body;
    return p;
}

/// A three-station bed on one band: S0 the root with tree link (S0, G01); S1 hangs from G01 by the tree link
/// (S1, G01) and holds the chord (S1, G02); S2 holds the tree link (S2, G02) and the chord (S2, G01).
struct FrameBed {
    LogManager log_manager;
    NetworkOraclePin pin;
    std::vector<NetStation> stations;
    net::ArcTable carry;
    double lam{0.0};

    FrameBed() {
        PppUtils utils(log_manager);
        lam = utils.getWavelength(System::GPS, "L1C", "G01");
        stations.resize(3);
        for (int r = 0; r < 3; ++r) stations[static_cast<std::size_t>(r)].name = "S" + std::to_string(r) + "000SIM";
        pin.utils = std::make_unique<PppUtils>(log_manager);
        pin.frame_mode = true;
        // truth for every arc (the pin reads lambda and the slips from it)
        for (int r = 0; r < 3; ++r)
            for (const char* s : {"G01", "G02"}) {
                NetworkOraclePin::Truth t;
                t.n_int    = 10 * r + (s[2] - '0');
                t.lambda_m = lam;
                pin.truth[{r, s, "L1C"}] = t;
            }
        // the reference tree and its pins (targets 0 and 3), and the chords' frame integers
        setTree(0, "G01", 0);
        setTree(1, "G01", 0);
        setTree(2, "G02", 3);
        pin.frame[{1, "G02", "L1C"}] = {-7, false};
        pin.frame[{2, "G01", "L1C"}] = {12, false};
        // a carried float on one chord, 0.2 cycle off its frame integer
        LocalCarry lc{};
        lc.value_abs = lam * (-7.0 + 0.2);
        lc.var = 1e-4;
        net::putArcIn(carry, {1, "G02", "L1C"}, &net::ArcState::amb) = lc;
        // one armed scope, all arcs, from kTow
        NetworkOraclePin::Armed a;
        a.ev_index = 0;
        a.sigma_m  = 1.0e-4;
        a.tow      = kTow;
        std::string why;
        a.scope = oraclePinParseScope("all", why);
        pin.scopes.push_back(std::move(a));
    }

    void setTree(int r, const std::string& sat, long long target) {
        stations[static_cast<std::size_t>(r)].pinned_amb_targets[StateKeys::makeAmbiguityKey(sat, "L1C")] =
            lam * static_cast<double>(target);
        pin.frame[{r, sat, "L1C"}] = {target, true};
    }

    int table(double tow) { return networkOraclePinFrameTable(pin, stations, carry, kW + tow, tow, {0}); }
};

} // namespace

TEST(OraclePinFrame, ParsesTheHeaderRolesAndAnAppendedColumn) {
    const fs::path p = writeFile("ok", "station,sat,signal,frame_int,role,ring\n"
                                       "S01000SIM,G04,L1C,0,tree,3\n"
                                       "S01000SIM,G05,L2W,-118,chord,2\n");
    const auto m = networkOraclePinParseFrameCsv(p.string());
    ASSERT_EQ(m.size(), 2u);
    const auto t = m.at({"S01000SIM", "G04", "L1C"});
    const auto c = m.at({"S01000SIM", "G05", "L2W"});
    EXPECT_TRUE(t.tree);
    EXPECT_EQ(t.frame_int, 0);
    EXPECT_FALSE(c.tree);
    EXPECT_EQ(c.frame_int, -118);
}

TEST(OraclePinFrame, RefusesAWrongHeaderAnUnknownRoleADuplicateAndANonInteger) {
    for (const char* body : {"sat,station,signal,frame_int,role\nS0,G01,L1C,1,chord\n",
                             "station,sat,signal,frame_int,role\nS0,G01,L1C,1,anchor\n",
                             "station,sat,signal,frame_int,role\nS0,G01,L1C,1,chord\nS0,G01,L1C,2,chord\n",
                             "station,sat,signal,frame_int,role\nS0,G01,L1C,1.5,chord\n",
                             "station,sat,signal,frame_int,role\nS0,G01,L1C,1\n"}) {
        const fs::path p = writeFile("bad", body);
        EXPECT_THROW(networkOraclePinParseFrameCsv(p.string()), std::runtime_error) << body;
    }
}

TEST(OraclePinFrame, PinsChordsAtLambdaTimesTheirFrameIntegerAndNeverTreeLinks) {
    FrameBed bed;
    EXPECT_EQ(bed.table(kTow), 2);
    ASSERT_EQ(bed.pin.table.size(), 2u);
    EXPECT_DOUBLE_EQ(bed.pin.table.at({1, "G02", "L1C"}).value_m, bed.lam * -7.0);
    EXPECT_DOUBLE_EQ(bed.pin.table.at({2, "G01", "L1C"}).value_m, bed.lam * 12.0);
    for (const auto& [key, p] : bed.pin.table) EXPECT_FALSE(bed.pin.frame.at(key).tree);
    EXPECT_EQ(bed.pin.frame_tree_checked, 3);
    // the residual: the one carried chord sits 0.2 cycle off; the other has no carry and is pinned all the same
    EXPECT_EQ(bed.pin.fit_resid_n, 1);
    EXPECT_NEAR(bed.pin.fit_resid_max_cyc, 0.2, 1e-9);
    EXPECT_EQ(bed.pin.frame_not_carried, 1);
    EXPECT_LT(bed.pin.frame_changed_tow, 0.0);
}

TEST(OraclePinFrame, ATreeLinkPinnedAtAnotherTargetLatchesTheReleaseOfEveryPin) {
    FrameBed bed;
    EXPECT_EQ(bed.table(kTow), 2);
    bed.stations[2].pinned_amb_targets[StateKeys::makeAmbiguityKey("G02", "L1C")] = bed.lam * 4.0;
    EXPECT_EQ(bed.table(kTow + 30.0), 0);
    EXPECT_TRUE(bed.pin.table.empty());
    EXPECT_DOUBLE_EQ(bed.pin.frame_changed_tow, kTow + 30.0);
    // the latch holds even when the chain's pin returns to the file's target
    bed.stations[2].pinned_amb_targets[StateKeys::makeAmbiguityKey("G02", "L1C")] = bed.lam * 3.0;
    EXPECT_EQ(bed.table(kTow + 60.0), 0);
    EXPECT_DOUBLE_EQ(bed.pin.frame_changed_tow, kTow + 30.0);
}

TEST(OraclePinFrame, AReHostOntoALinkAtItsIntegerKeepsTheFrameAndEveryPin) {
    // S1 leaves G01 for G02: the chain now pins the file's chord (S1, G02) at its integer and no longer pins the
    // file's tree link (S1, G01), which the oracle then holds at its own integer.  The frame is kept.
    FrameBed bed;
    bed.stations[1].pinned_amb_targets.erase(StateKeys::makeAmbiguityKey("G01", "L1C"));
    bed.stations[1].pinned_amb_targets[StateKeys::makeAmbiguityKey("G02", "L1C")] = bed.lam * -7.0;
    EXPECT_EQ(bed.table(kTow), 2);
    EXPECT_LT(bed.pin.frame_changed_tow, 0.0);
    EXPECT_EQ(bed.pin.table.count({1, "G02", "L1C"}), 0u);               // the chain's pin, checked
    EXPECT_DOUBLE_EQ(bed.pin.table.at({1, "G01", "L1C"}).value_m, 0.0);   // the old tree link, held at its integer 0
    EXPECT_EQ(bed.pin.frame_tree_unpinned, 1);
    EXPECT_EQ(bed.pin.frame_tree_checked, 3);
}

TEST(OraclePinFrame, AChordThatTheChainPinsElsewhereIsAStep) {
    FrameBed bed;
    bed.stations[1].pinned_amb_targets[StateKeys::makeAmbiguityKey("G02", "L1C")] = bed.lam * -6.0;
    EXPECT_EQ(bed.table(kTow), 0);
    EXPECT_DOUBLE_EQ(bed.pin.frame_changed_tow, kTow);
}

TEST(OraclePinFrame, AChordIsReleasedForGoodAtItsFirstTrueSlip) {
    FrameBed bed;
    NetworkSlipOracle::TruthSlip sl{};
    sl.s = kW + kTow + 45.0;
    sl.delta_cyc = 2;
    bed.pin.truth[{2, "G01", "L1C"}].slips.push_back(sl);
    EXPECT_EQ(bed.table(kTow), 2);
    EXPECT_EQ(bed.table(kTow + 30.0), 2);          // before the slip
    EXPECT_EQ(bed.table(kTow + 60.0), 1);          // after it: released
    EXPECT_EQ(bed.pin.table.count({2, "G01", "L1C"}), 0u);
    EXPECT_EQ(bed.pin.frame_released_slip, 1);
    EXPECT_EQ(bed.table(kTow + 90.0), 1);          // for good
    EXPECT_EQ(bed.pin.frame_released_slip, 1);
    EXPECT_LT(bed.pin.frame_changed_tow, 0.0);
}

TEST(OraclePinFrame, NoScopeHasStartedSoNothingIsPinned) {
    FrameBed bed;
    EXPECT_EQ(networkOraclePinFrameTable(bed.pin, bed.stations, bed.carry, kW + kTow, kTow, {}), 0);
    EXPECT_TRUE(bed.pin.table.empty());
    EXPECT_EQ(bed.pin.frame_tree_checked, 0);
}

} // namespace GnssProcessor

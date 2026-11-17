/**
 * @file test_phase_visible_step_test.cpp
 * @brief The phase step declaration on what a user sees (`network.disc_phase_visible`).
 *
 * The emitter's legacy value test declares a phase step when the emitted phase bias alone
 * moves by more than the threshold.  Armed, the test declares a step when a key's change of
 * its clock less phase bias, less the median of that change over the satellites of its
 * constellation and signal, exceeds the threshold (products/PhaseVisibleStepTest.hpp).  The
 * tests lock:
 *   - the pure rule on hand-built epochs: a shared move alone declares nothing; one
 *     satellite's own move declares that satellite only; fewer voters than the minimum test
 *     each key on its own change; untested keys are never declared and do not vote; the
 *     groups are per constellation and signal; the median of an even count;
 *   - the emitter: off is the legacy test; a phase-bias move matched by its clock declares
 *     nothing; a satellite appearing, leaving and returning, a key without a clock, a forced
 *     mark and a return past the staleness horizon each take their stated path and counter;
 *   - the state round-trips a snapshot (v4) and refuses an unarmed emitter's;
 *   - the S contract token `discpv=` (absent when off), its parse, the replay emitter and the
 *     contract check; a file replay reproduces the producer's counters epoch by epoch;
 *   - the config key, and its disarming under `network.emit_pb_hold`.
 */

#include <gtest/gtest.h>

#include "config/GnssConfig.hpp"
#include "logging/LogManager.hpp"
#include "products/NetworkProductEmitter.hpp"
#include "products/NetworkProductIO.hpp"
#include "products/PhaseVisibleStepTest.hpp"
#include "products/SsrCorrectionStore.hpp"

#include <filesystem>
#include <fstream>
#include <map>
#include <sstream>
#include <string>
#include <vector>
#include "support/TestTempDir.hpp"   // per-process, per-test scratch directory

namespace fs = std::filesystem;

namespace GnssProcessor {
namespace {

constexpr double kBar = 0.05;   // the flat gate used by every emitter below (m)

PhaseVisibleKey key(const std::string& sat, double change, bool votes = true,
                    const std::string& sig = "L1C", char cst = 'G') {
    PhaseVisibleKey k;
    k.sat = sat; k.signal = sig; k.constellation = cst;
    k.tested = true; k.votes = votes; k.change_m = change; k.bar_m = kBar;
    return k;
}

/// One epoch of satellites G01..Gnn, each with a clock and one L1C phase bias.
struct SatValue { std::string sat; double clock; double pb; bool has_clock = true; };

NetworkSolutionEpoch epochOf(double tow, const std::vector<SatValue>& sats) {
    NetworkSolutionEpoch sol;
    sol.epoch_time = GnssTime{ 2313, tow };
    sol.iod_ssr = 1; sol.provider_id = 1; sol.solution_id = 1;
    for (const auto& v : sats) {
        NetworkSatSolution ns;
        ns.sat = v.sat; ns.has_clock = v.has_clock; ns.clock_c0_m = v.clock;
        ns.phase_bias["L1C"] = NetworkPhaseBias{ v.pb, true, 1 };
        sol.sats.push_back(ns);
    }
    return sol;
}

std::vector<SatValue> five(double pb = 0.0, double clock = 0.0) {
    std::vector<SatValue> v;
    for (int i = 1; i <= 5; ++i) v.push_back({ "G0" + std::to_string(i), clock, pb });
    return v;
}

NetworkProductEmitter makeEmitter(int min_sats, double staleness = 0.0) {
    return NetworkProductEmitter(kBar, /*emit_clock_disc=*/false, staleness,
                                 /*code_bias_jump_test=*/false,
                                 /*clock_disc_on_set_change=*/false,
                                 /*disc_threshold_frac_cycles=*/0.0,
                                 /*disc_mark_scope_channel=*/false, min_sats);
}

/// The phase counters of every key after an emit.
std::map<std::string, int> counters(const NetworkProductEmitter& em, const NetworkSolutionEpoch& sol) {
    std::map<std::string, int> out;
    for (const auto& s : sol.sats)
        for (const auto& [sig, pb] : s.phase_bias) {
            (void)pb;
            out[s.sat + "|" + sig] = em.discontinuityCounter(s.sat, sig);
        }
    return out;
}

/// Emit a sequence of epochs; return the counters after the last.
std::map<std::string, int> run(NetworkProductEmitter& em, const std::vector<NetworkSolutionEpoch>& eps) {
    SsrCorrectionStore store;
    for (const auto& e : eps) em.emitToStore(e, store);
    return counters(em, eps.back());
}

fs::path writeConfig(const std::string& tag, const std::string& extra_network) {
    const fs::path p = gnss_test::tempDir() / ("pv_step_" + tag + ".json");
    std::ofstream f(p);
    f << "{\n"
         "  \"processing\": {\n"
         "    \"mode\": \"ppp-rtk-network\",\n"
         "    \"active_systems\": [ \"GPS\" ],\n"
         "    \"signal_priorities\": { \"GPS\": \"WC\" }\n"
         "  },\n"
         "  \"network\": {\n"
         "    \"clock_datum_station\": \"AAAA\",\n"
      << extra_network <<
         "    \"stations\": [\n"
         "      { \"name\": \"AAAA\", \"position_ecef\": [ -2493304.99, -4655214.79, 3565497.67 ] },\n"
         "      { \"name\": \"BBBB\", \"position_ecef\": [ -2281621.75, -1453585.08, 5756964.89 ] }\n"
         "    ]\n"
         "  }\n"
         "}\n";
    f.close();
    return p;
}

}  // namespace

// ---------------------------------------------------------------------------
// The pure rule.
// ---------------------------------------------------------------------------
TEST(PhaseVisibleStepRule, SharedMoveAloneDeclaresNothing) {
    std::vector<PhaseVisibleKey> k;
    for (int i = 1; i <= 5; ++i) k.push_back(key("G0" + std::to_string(i), 0.06));
    PhaseVisibleCounters c;
    const auto v = decidePhaseVisibleSteps(k, kPhaseVisibleMinSats, &c);
    for (const auto& x : v) {
        EXPECT_FALSE(x.step);
        EXPECT_TRUE(x.median_basis);
        EXPECT_NEAR(x.median_m, 0.06, 1e-12);
    }
    EXPECT_EQ(c.groups, 1); EXPECT_EQ(c.groups_median, 1); EXPECT_EQ(c.keys_stepped, 0);
    EXPECT_EQ(c.shared_over_bar, 1) << "the shared move exceeds the bar: a non-differencing user would need it";
}

TEST(PhaseVisibleStepRule, OneSatellitesOwnMoveDeclaresThatSatelliteOnly) {
    std::vector<PhaseVisibleKey> k = { key("G01", 0.0), key("G02", 0.001), key("G03", -0.001),
                                       key("G04", 0.0), key("G05", 0.07) };
    const auto v = decidePhaseVisibleSteps(k, kPhaseVisibleMinSats);
    for (std::size_t i = 0; i < 4; ++i) EXPECT_FALSE(v[i].step) << k[i].sat;
    EXPECT_TRUE(v[4].step);
    EXPECT_NEAR(v[4].deviation_m, 0.07, 1e-12);
}

TEST(PhaseVisibleStepRule, FewerVotersThanTheMinimumTestEachKeyOnItsOwnChange) {
    std::vector<PhaseVisibleKey> k = { key("G01", 0.06), key("G02", 0.06), key("G03", 0.01) };
    PhaseVisibleCounters c;
    const auto v = decidePhaseVisibleSteps(k, kPhaseVisibleMinSats, &c);
    EXPECT_TRUE(v[0].step); EXPECT_TRUE(v[1].step); EXPECT_FALSE(v[2].step);
    for (const auto& x : v) { EXPECT_FALSE(x.median_basis); EXPECT_EQ(x.median_m, 0.0); }
    EXPECT_EQ(c.groups_below_min, 1); EXPECT_EQ(c.keys_stepped_below_min, 2);
}

TEST(PhaseVisibleStepRule, UntestedKeysAreNeverDeclaredAndDoNotVote) {
    std::vector<PhaseVisibleKey> k = { key("G01", 0.0), key("G02", 0.0), key("G03", 0.0),
                                       key("G04", 0.0) };
    PhaseVisibleKey first = key("G05", 9.0);
    first.tested = false; first.votes = false;   // a first record
    k.push_back(first);
    PhaseVisibleKey ret = key("G06", 0.2, /*votes=*/false);   // a return: tested, not voting
    k.push_back(ret);
    const auto v = decidePhaseVisibleSteps(k, kPhaseVisibleMinSats);
    EXPECT_FALSE(v[4].step); EXPECT_FALSE(v[4].tested);
    EXPECT_TRUE(v[5].step);
    EXPECT_NEAR(v[5].median_m, 0.0, 1e-12) << "neither the untested key nor the return votes";
}

TEST(PhaseVisibleStepRule, GroupsArePerConstellationAndSignal) {
    std::vector<PhaseVisibleKey> k;
    for (int i = 1; i <= 4; ++i) k.push_back(key("G0" + std::to_string(i), 0.06, true, "L1C"));
    for (int i = 1; i <= 4; ++i) k.push_back(key("G0" + std::to_string(i), 0.0, true, "L2W"));
    for (int i = 1; i <= 4; ++i) k.push_back(key("E0" + std::to_string(i), -0.06, true, "L1C", 'E'));
    PhaseVisibleCounters c;
    const auto v = decidePhaseVisibleSteps(k, kPhaseVisibleMinSats, &c);
    for (const auto& x : v) EXPECT_FALSE(x.step);
    EXPECT_EQ(c.groups, 3);
}

TEST(PhaseVisibleStepRule, MedianOfAnEvenCountIsTheMeanOfTheTwoMiddleValues) {
    EXPECT_DOUBLE_EQ(phaseVisibleMedian({ 4.0, 1.0, 3.0, 2.0 }), 2.5);
    EXPECT_DOUBLE_EQ(phaseVisibleMedian({ 5.0, 1.0, 3.0 }), 3.0);
    EXPECT_DOUBLE_EQ(phaseVisibleMedian({}), 0.0);
}

// ---------------------------------------------------------------------------
// The emitter.
// ---------------------------------------------------------------------------
TEST(PhaseVisibleStepEmitter, OffIsTheLegacyTestOnThePhaseBiasAlone) {
    auto s2 = five(-0.06);   // every phase bias moves by -0.06 m, clocks still
    NetworkProductEmitter off = makeEmitter(0);
    const auto c_off = run(off, { epochOf(0.0, five()), epochOf(30.0, s2) });
    for (const auto& [k, v] : c_off) EXPECT_EQ(v, 1) << k << ": the legacy test declares every move";
    EXPECT_EQ(off.discPhaseVisibleMinSats(), 0);
    EXPECT_EQ(off.phaseVisibleCounters().keys_tested, 0) << "off, the test does not run";
}

TEST(PhaseVisibleStepEmitter, ASharedMoveAloneDeclaresNothing) {
    NetworkProductEmitter on = makeEmitter(kPhaseVisibleMinSats);
    const auto c = run(on, { epochOf(0.0, five()), epochOf(30.0, five(-0.06)) });
    for (const auto& [k, v] : c) EXPECT_EQ(v, 0) << k;
    EXPECT_EQ(on.phaseVisibleEdges().legacy_would_step, 5);
    EXPECT_EQ(on.phaseVisibleCounters().shared_over_bar, 1);
}

TEST(PhaseVisibleStepEmitter, OneSatellitesOwnMoveDeclaresThatSatelliteOnly) {
    auto s2 = five();
    s2[2].pb = 0.07;   // G03's phase bias alone
    NetworkProductEmitter on = makeEmitter(kPhaseVisibleMinSats);
    const auto c = run(on, { epochOf(0.0, five()), epochOf(30.0, s2) });
    for (const auto& [k, v] : c) EXPECT_EQ(v, k == "G03|L1C" ? 1 : 0) << k;
}

TEST(PhaseVisibleStepEmitter, APhaseBiasMoveMatchedByItsClockDeclaresNothing) {
    auto s2 = five();
    s2[1].pb = 0.10; s2[1].clock = 0.10;   // G02: clock and phase bias together, C - P still
    NetworkProductEmitter on = makeEmitter(kPhaseVisibleMinSats);
    const auto c = run(on, { epochOf(0.0, five()), epochOf(30.0, s2) });
    for (const auto& [k, v] : c) EXPECT_EQ(v, 0) << k;
    EXPECT_EQ(on.phaseVisibleEdges().legacy_would_step, 1) << "the legacy test would have declared G02";
    NetworkProductEmitter off = makeEmitter(0);
    EXPECT_EQ(run(off, { epochOf(0.0, five()), epochOf(30.0, s2) }).at("G02|L1C"), 1);
}

TEST(PhaseVisibleStepEmitter, FewerSatellitesThanTheMinimumTestEachOnItsOwnChange) {
    const std::vector<SatValue> three1 = { { "G01", 0.0, 0.0 }, { "G02", 0.0, 0.0 }, { "G03", 0.0, 0.0 } };
    const std::vector<SatValue> three2 = { { "G01", 0.0, -0.06 }, { "G02", 0.0, -0.06 }, { "G03", 0.0, 0.0 } };
    NetworkProductEmitter on = makeEmitter(kPhaseVisibleMinSats);
    const auto c = run(on, { epochOf(0.0, three1), epochOf(30.0, three2) });
    EXPECT_EQ(c.at("G01|L1C"), 1); EXPECT_EQ(c.at("G02|L1C"), 1); EXPECT_EQ(c.at("G03|L1C"), 0);
    EXPECT_EQ(on.phaseVisibleCounters().groups_below_min, 1);
    EXPECT_EQ(on.phaseVisibleEdges().below_min_entries, 1);
}

TEST(PhaseVisibleStepEmitter, ASatelliteAppearingLeavingAndReturning) {
    // Epoch 1: G01..G05 (first records).  Epoch 2: G05 leaves, G06 appears.  Epoch 3: G05
    // returns with an own move of 0.08 m (tested against its epoch-1 baseline, not voting)
    // and G06 votes for the first time.
    auto e1 = five();
    std::vector<SatValue> e2 = { { "G01", 0.0, 0.0 }, { "G02", 0.0, 0.0 }, { "G03", 0.0, 0.0 },
                                 { "G04", 0.0, 0.0 }, { "G06", 0.0, 5.0 } };
    std::vector<SatValue> e3 = e2;
    e3.push_back({ "G05", 0.0, 0.08 });
    NetworkProductEmitter on = makeEmitter(kPhaseVisibleMinSats);
    SsrCorrectionStore store;
    on.emitToStore(epochOf(0.0, e1), store);
    EXPECT_EQ(on.phaseVisibleEdges().first_records, 5);
    on.emitToStore(epochOf(30.0, e2), store);
    EXPECT_EQ(on.discontinuityCounter("G06", "L1C"), 0) << "a first record is seeded, never declared";
    EXPECT_EQ(on.phaseVisibleEdges().first_records, 6);
    EXPECT_EQ(on.phaseVisibleEdges().vote_entries, 4);
    on.emitToStore(epochOf(60.0, e3), store);
    EXPECT_EQ(on.discontinuityCounter("G05", "L1C"), 1) << "the return's own move is declared";
    EXPECT_EQ(on.discontinuityCounter("G06", "L1C"), 0);
    EXPECT_EQ(on.phaseVisibleEdges().returns_fresh, 1);
    EXPECT_EQ(on.phaseVisibleEdges().vote_entries, 5) << "G06 votes from its second record";
    EXPECT_EQ(on.phaseVisibleEdges().vote_exits, 0);
    // Epoch 4: G01 leaves: one exit.
    std::vector<SatValue> e4(e3.begin() + 1, e3.end());
    on.emitToStore(epochOf(90.0, e4), store);
    EXPECT_EQ(on.phaseVisibleEdges().vote_exits, 1);
}

TEST(PhaseVisibleStepEmitter, AKeyWithoutAClockKeepsTheLegacyTest) {
    auto e2 = five();
    e2[0].has_clock = false; e2[0].pb = 0.06;   // G01: no clock, its phase bias moves
    auto e3 = five();
    e3[0].pb = 0.06;                            // G01's clock back, phase bias as at epoch 2
    NetworkProductEmitter on = makeEmitter(kPhaseVisibleMinSats);
    SsrCorrectionStore store;
    on.emitToStore(epochOf(0.0, five()), store);
    on.emitToStore(epochOf(30.0, e2), store);
    EXPECT_EQ(on.discontinuityCounter("G01", "L1C"), 1) << "the legacy test declares the move";
    EXPECT_EQ(on.phaseVisibleEdges().no_clock, 1);
    on.emitToStore(epochOf(60.0, e3), store);
    EXPECT_EQ(on.discontinuityCounter("G01", "L1C"), 1) << "no phase-bias move: nothing new";
    EXPECT_EQ(on.phaseVisibleEdges().no_clock, 2) << "its previous emission had no clock";
}

TEST(PhaseVisibleStepEmitter, AForcedMarkIsDeclaredByTheMarkAndDoesNotVote) {
    NetworkProductEmitter on = makeEmitter(kPhaseVisibleMinSats);
    SsrCorrectionStore store;
    on.emitToStore(epochOf(0.0, five()), store);
    on.markSatDiscontinuity({ "G01" });
    on.emitToStore(epochOf(30.0, five()), store);
    EXPECT_EQ(on.discontinuityCounter("G01", "L1C"), 1);
    EXPECT_EQ(on.discontinuityCounter("G02", "L1C"), 0);
    EXPECT_EQ(on.phaseVisibleEdges().forced, 1);
}

TEST(PhaseVisibleStepEmitter, AReturnPastTheStalenessHorizonIsReseededNotTested) {
    const auto all5 = five();
    std::vector<SatValue> no5(all5.begin(), all5.begin() + 4);
    auto back = five();
    back[4].pb = 1.0;   // G05 returns far from its old value
    NetworkProductEmitter on = makeEmitter(kPhaseVisibleMinSats, /*staleness=*/60.0);
    SsrCorrectionStore store;
    on.emitToStore(epochOf(0.0, five()), store);
    on.emitToStore(epochOf(30.0, no5), store);
    on.emitToStore(epochOf(60.0, no5), store);
    on.emitToStore(epochOf(90.0, no5), store);
    on.emitToStore(epochOf(120.0, back), store);
    EXPECT_EQ(on.discontinuityCounter("G05", "L1C"), 0);
    EXPECT_EQ(on.phaseVisibleEdges().returns_stale, 1);
}

TEST(PhaseVisibleStepEmitter, SnapshotRoundTripsTheBaselinesAndRefusesAnUnarmedEmitter) {
    auto e2 = five(); e2[3].pb = 0.01;
    auto e3 = five(); e3[3].pb = 0.09;   // G04: an own move of 0.08 m from epoch 2
    NetworkProductEmitter a = makeEmitter(kPhaseVisibleMinSats);
    SsrCorrectionStore sa;
    a.emitToStore(epochOf(0.0, five()), sa);
    a.emitToStore(epochOf(30.0, e2), sa);
    std::stringstream snap;
    a.serializeState(snap);
    EXPECT_NE(snap.str().find("EMITTER,v4,"), std::string::npos);
    EXPECT_NE(snap.str().find("epv,G04|L1C,"), std::string::npos);

    NetworkProductEmitter b = makeEmitter(kPhaseVisibleMinSats);
    std::stringstream in(snap.str());
    ASSERT_TRUE(b.restoreState(in));
    SsrCorrectionStore sb;
    a.emitToStore(epochOf(60.0, e3), sa);
    b.emitToStore(epochOf(60.0, e3), sb);
    EXPECT_EQ(counters(a, epochOf(60.0, e3)), counters(b, epochOf(60.0, e3)));
    EXPECT_EQ(b.discontinuityCounter("G04", "L1C"), 1);

    NetworkProductEmitter off = makeEmitter(0);
    std::stringstream in2(snap.str());
    EXPECT_FALSE(off.restoreState(in2)) << "a v4 snapshot does not restore into the legacy test";
    std::stringstream legacy;
    off.serializeState(legacy);
    EXPECT_EQ(legacy.str().find("EMITTER,v4"), std::string::npos) << "off writes the earlier versions";
}

// ---------------------------------------------------------------------------
// The S contract, a file replay and the config key.
// ---------------------------------------------------------------------------
TEST(PhaseVisibleStepContract, SLineDeclaresTheTestAndOffIsByteIdentical) {
    const fs::path with_p    = gnss_test::tempDir() / "pv_discpv_with.txt";
    const fs::path without_p = gnss_test::tempDir() / "pv_discpv_without.txt";
    std::error_code ec; fs::remove(with_p, ec); fs::remove(without_p, ec);
    SbasisContract base;
    base.decl.reference_receiver_id = "MBAR00UGA";
    base.disc_threshold_m           = 0.05;
    base.present                    = true;
    SbasisContract armed = base;
    armed.disc_phase_visible_min_sats = kPhaseVisibleMinSats;
    { NetworkProductWriter w(without_p.string(), base);  ASSERT_TRUE(w.good()); }
    { NetworkProductWriter w(with_p.string(),    armed); ASSERT_TRUE(w.good()); }
    const auto pick = [](const fs::path& p, const char* prefix) {
        std::ifstream f(p);
        std::string ln;
        while (std::getline(f, ln))
            if (ln.rfind(prefix, 0) == 0) return ln;
        return std::string{};
    };
    const std::string a = pick(without_p, "S,"), b = pick(with_p, "S,");
    ASSERT_FALSE(a.empty());
    EXPECT_EQ(a.find("discpv="), std::string::npos) << "an OFF producer writes the S line byte-for-byte";
    const std::string token = ",discpv=" + std::to_string(kPhaseVisibleMinSats);
    const std::size_t at = b.find(token);
    ASSERT_NE(at, std::string::npos);
    EXPECT_EQ(b.substr(0, at) + b.substr(at + token.size()), a) << "the token is the only difference";
    EXPECT_NE(pick(without_p, "# S,").find("[,discpv=<n>]"), std::string::npos) << "the legend declares it";

    bool ok = false;
    SbasisContract on, off;
    NetworkProductReader::read(with_p.string(),    &on,  &ok);  ASSERT_TRUE(ok);
    NetworkProductReader::read(without_p.string(), &off, &ok);  ASSERT_TRUE(ok);
    EXPECT_EQ(on.disc_phase_visible_min_sats, kPhaseVisibleMinSats);
    EXPECT_EQ(off.disc_phase_visible_min_sats, 0);
    EXPECT_EQ(NetworkProductReader::makeReplayEmitter(on).discPhaseVisibleMinSats(), kPhaseVisibleMinSats);
    EXPECT_EQ(NetworkProductReader::makeReplayEmitter(off).discPhaseVisibleMinSats(), 0);
    std::vector<std::string> why;
    EXPECT_FALSE(NetworkProductReader::checkContract(on, off, &why));
    bool named = false;
    for (const auto& w : why) named = named || w.find("disc_phase_visible_min_sats") != std::string::npos;
    EXPECT_TRUE(named);
    fs::remove(with_p, ec); fs::remove(without_p, ec);
}

TEST(PhaseVisibleStepContract, AFileReplayReproducesTheProducersCountersEpochByEpoch) {
    const fs::path p = gnss_test::tempDir() / "pv_replay.txt";
    std::error_code ec; fs::remove(p, ec);
    SbasisContract c;
    c.decl.reference_receiver_id = "MBAR00UGA";
    c.disc_threshold_m           = kBar;
    c.disc_phase_visible_min_sats = kPhaseVisibleMinSats;
    c.present                    = true;
    // Five epochs: a shared move, an own move, a clock-matched move, a satellite leaving.
    std::vector<NetworkSolutionEpoch> eps;
    eps.push_back(epochOf(0.0, five()));
    eps.push_back(epochOf(30.0, five(-0.06)));
    auto s3 = five(-0.06); s3[2].pb = 0.02;
    eps.push_back(epochOf(60.0, s3));
    auto s4 = s3; s4[1].pb += 0.2; s4[1].clock += 0.2;
    eps.push_back(epochOf(90.0, s4));
    std::vector<SatValue> s5(s4.begin(), s4.begin() + 4);
    s5[0].pb += 0.07;
    eps.push_back(epochOf(120.0, s5));

    NetworkProductEmitter producer = NetworkProductReader::makeReplayEmitter(c);
    SsrCorrectionStore pstore;
    std::vector<std::map<std::string, int>> live;
    {
        NetworkProductWriter w(p.string(), c);
        ASSERT_TRUE(w.good());
        for (const auto& e : eps) {
            producer.emitToStore(e, pstore);
            live.push_back(counters(producer, e));
            w.write(e);
        }
    }
    bool ok = false;
    SbasisContract parsed;
    const auto recs = NetworkProductReader::read(p.string(), &parsed, &ok);
    ASSERT_TRUE(ok);
    ASSERT_EQ(recs.size(), eps.size());
    NetworkProductEmitter replay = NetworkProductReader::makeReplayEmitter(parsed);
    SsrCorrectionStore rstore;
    for (std::size_t i = 0; i < recs.size(); ++i) {
        NetworkProductReader::replay(recs[i], rstore, replay);
        EXPECT_EQ(counters(replay, eps[i]), live[i]) << "epoch " << i;
    }
    EXPECT_EQ(replay.phaseVisibleCounters().keys_stepped, producer.phaseVisibleCounters().keys_stepped);
    EXPECT_EQ(live[1].at("G01|L1C"), 0) << "the shared move is not declared";
    EXPECT_EQ(live[2].at("G03|L1C"), 1) << "the own move is declared";
    EXPECT_EQ(live[3].at("G02|L1C"), 0) << "the clock-matched move adds nothing";
    EXPECT_EQ(live[4].at("G01|L1C"), 1) << "G01's own move with G05 gone";
    fs::remove(p, ec);
}

TEST(PhaseVisibleStepContract, ConfigKeyParsesAndTheEmissionHoldDisarmsIt) {
    {
        GnssConfig d;
        EXPECT_FALSE(d.networkDiscPhaseVisible());
    }
    {
        LogManager log; GnssConfig cfg;
        const fs::path p = writeConfig("on", "    \"disc_phase_visible\": true,\n");
        ASSERT_TRUE(cfg.loadFromJson(p, log));
        EXPECT_TRUE(cfg.networkDiscPhaseVisible());
        std::error_code ec; fs::remove(p, ec);
    }
    {
        LogManager log; GnssConfig cfg;
        const fs::path p = writeConfig("hold", "    \"disc_phase_visible\": true,\n"
                                               "    \"emit_pb_hold\": true,\n");
        ASSERT_TRUE(cfg.loadFromJson(p, log));
        EXPECT_FALSE(cfg.networkDiscPhaseVisible()) << "the hold's generations declare the held steps";
        std::error_code ec; fs::remove(p, ec);
    }
}

}  // namespace GnssProcessor

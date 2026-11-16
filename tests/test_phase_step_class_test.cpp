/**
 * @file test_phase_step_class_test.cpp
 * @brief The phase step declaration by the class of the step a user sees
 *        (`network.disc_step_class_pairs`, products/PhaseStepClassTest.hpp).
 *
 * The tests lock:
 *   - the pure rule on hand-built families: a shared move alone is quiet; one satellite's
 *     whole step on one band declares that band only; a fraction step declares the bands that
 *     moved; an ionosphere-like move (ionosphere-free part kept) declares nothing; fewer
 *     tested satellites than the minimum classify nothing; the levels E_1, E_2;
 *   - the emitter: unarmed is the value test; armed, a one-cycle phase-bias step on one band
 *     raises that key's counter only, an ionosphere-like move of a satellite's biases (both
 *     bands, ionosphere-free phase kept) raises none although the value test would, a move
 *     shared by every satellite raises none, and a satellite returning after a missed
 *     emission keeps the value test.
 */

#include <gtest/gtest.h>

#include "products/NetworkProductEmitter.hpp"
#include "products/PhaseStepClassTest.hpp"
#include "products/SsrCorrectionStore.hpp"

#include <cmath>
#include <map>
#include <string>
#include <vector>

namespace GnssProcessor {
namespace {

constexpr double kC  = 299792458.0;
constexpr double kF1 = 1575.42e6;   // Galileo E1
constexpr double kF5 = 1176.45e6;   // Galileo E5a
const double     kL1 = kC / kF1;
const double     kL5 = kC / kF5;

StepClassSat sat(const std::string& id, double d1, double d2, bool tested = true) {
    StepClassSat s;
    s.sat = id; s.tested = tested; s.d1_cyc = d1; s.d2_cyc = d2;
    return s;
}

TEST(PhaseStepClass, ASharedMoveIsQuietAndOneSatellitesWholeStepDeclaresItsBandOnly) {
    std::vector<StepClassSat> in;
    for (int i = 1; i <= 5; ++i) in.push_back(sat("E0" + std::to_string(i), 0.37, -0.21));
    in[2].d2_cyc += 1.0;   // E03: one cycle on band 2 only
    StepClassCounters c;
    const auto v = classifyStepClasses(in, kF1, kF5, 0.15, kStepClassMinSats, &c);
    for (int i : {0, 1, 3, 4}) EXPECT_EQ(v[i].cls, StepClass::Quiet) << i;
    EXPECT_EQ(v[2].cls, StepClass::Whole);
    EXPECT_FALSE(v[2].step1);
    EXPECT_TRUE(v[2].step2);
    EXPECT_EQ(c.sats_tested, 5);
    EXPECT_EQ(c.whole, 1);
    EXPECT_EQ(c.signals_declared, 1);
}

TEST(PhaseStepClass, AFractionStepDeclaresTheBandsThatMovedAndAnIonosphereLikeMoveNothing) {
    std::vector<StepClassSat> in;
    // Nine satellites, three of them moving: the family's median step stays 0 on both bands.
    for (int i = 1; i <= 9; ++i) in.push_back(sat("E0" + std::to_string(i), 0.0, 0.0));
    in[0].d1_cyc = 0.4;                               // E01: band 1 by 0.4 cycle, band 2 still
    // E02: an ionosphere-like move, x1 f1 = x2 f2 (the ionosphere-free phase kept).
    in[1].d1_cyc = 0.5;
    in[1].d2_cyc = 0.5 * kF1 / kF5;
    in[2].d1_cyc = 0.3; in[2].d2_cyc = -0.3;          // E03: both bands, not ionosphere-like
    const auto v = classifyStepClasses(in, kF1, kF5, 0.15, kStepClassMinSats);
    EXPECT_EQ(v[0].cls, StepClass::Fraction);
    EXPECT_TRUE(v[0].step1);
    EXPECT_FALSE(v[0].step2);
    EXPECT_EQ(v[1].cls, StepClass::IonoLike);
    EXPECT_FALSE(v[1].step1 || v[1].step2);
    EXPECT_NEAR(v[1].dn_cyc, 0.0, 1e-9);
    EXPECT_EQ(v[2].cls, StepClass::Fraction);
    EXPECT_TRUE(v[2].step1 && v[2].step2);
}

TEST(PhaseStepClass, BelowTheMinimumOrUntestedNothingIsClassified) {
    std::vector<StepClassSat> in = { sat("E01", 1.0, 0.0), sat("E02", 0.0, 0.0), sat("E03", 0.0, 0.0),
                                     sat("E04", 5.0, 5.0, false) };
    StepClassCounters c;
    const auto v = classifyStepClasses(in, kF1, kF5, 0.15, kStepClassMinSats, &c);
    for (const auto& x : v) EXPECT_EQ(x.cls, StepClass::Untested);
    EXPECT_EQ(c.families, 1);
    EXPECT_EQ(c.families_below_min, 1);
    EXPECT_EQ(c.sats_tested, 0);
}

TEST(PhaseStepClass, TheLevelsReadTheClockLessThePhaseBiasWithTheCodeIonosphereTerm) {
    double e1 = 0.0, e2 = 0.0;
    const double gamma = (kF1 / kF5) * (kF1 / kF5);
    stepClassLevels(10.0, 2.0, 3.0, 1.0, 1.5, kF1, kF5, e1, e2);
    const double x = ((10.0 - 1.0) - (10.0 - 1.5)) / (1.0 - gamma);
    EXPECT_NEAR(e1, (10.0 - 2.0 + x) / kL1, 1e-12);
    EXPECT_NEAR(e2, (10.0 - 3.0 + gamma * x) / kL5, 1e-12);
    EXPECT_STREQ(stepClassName(StepClass::IonoLike), "iono_like");
}

// --- The emitter ----------------------------------------------------------------------------------------------

struct Biases { double p1{0.0}, p5{0.0}; };

NetworkSolutionEpoch epochOf(double tow, const std::map<std::string, Biases>& sats) {
    NetworkSolutionEpoch sol;
    sol.epoch_time = GnssTime{ 2313, tow };
    sol.iod_ssr = 1; sol.provider_id = 1; sol.solution_id = 1;
    for (const auto& [id, b] : sats) {
        NetworkSatSolution ns;
        ns.sat = id; ns.has_clock = true; ns.clock_c0_m = 0.0;
        ns.phase_bias["L1X"] = NetworkPhaseBias{ b.p1, true, 1 };
        ns.phase_bias["L5X"] = NetworkPhaseBias{ b.p5, true, 1 };
        ns.code_bias_m["C1X"] = 0.0;
        ns.code_bias_m["C5X"] = 0.0;
        sol.sats.push_back(ns);
    }
    return sol;
}

std::map<std::string, Biases> five() {
    std::map<std::string, Biases> m;
    for (int i = 1; i <= 5; ++i) m["E0" + std::to_string(i)] = Biases{};
    return m;
}

NetworkProductEmitter makeEmitter() {
    // Flat value gate 0.05 m: the value test declares any phase-bias move above 5 cm.
    return NetworkProductEmitter(0.05);
}

int ctr(const NetworkProductEmitter& em, const std::string& sat, const std::string& sig) {
    return em.discontinuityCounter(sat, sig);
}

TEST(PhaseStepClassEmitter, UnarmedTheValueTestDeclaresAnIonosphereLikeMove) {
    NetworkProductEmitter em = makeEmitter();
    SsrCorrectionStore store;
    em.emitToStore(epochOf(0.0, five()), store);
    auto m = five();
    m["E02"] = Biases{ -0.5 * kL1, -0.5 * (kF1 / kF5) * kL5 };   // ionosphere-like, as below
    em.emitToStore(epochOf(30.0, m), store);
    EXPECT_FALSE(em.stepClassArmed());
    EXPECT_EQ(ctr(em, "E02", "L1X"), 1);
    EXPECT_EQ(ctr(em, "E02", "L5X"), 1);
}

TEST(PhaseStepClassEmitter, ArmedOnlyWholeAndFractionStepsRaiseTheirSignalsCounters) {
    NetworkProductEmitter em = makeEmitter();
    em.setStepClassTest({ "E:L1X/L5X" }, 0.15);
    ASSERT_TRUE(em.stepClassArmed());
    SsrCorrectionStore store;
    em.emitToStore(epochOf(0.0, five()), store);
    // Epoch 2: E01 one cycle on L1X (its level E_1 = -P_1 / lambda_1 drops by one cycle);
    // E02 an ionosphere-like move: x1 = 0.5 cycle, x2 = 0.5 f1 / f2 cycle (P_b = -x_b lambda_b).
    auto m = five();
    m["E01"] = Biases{ kL1, 0.0 };
    m["E02"] = Biases{ -0.5 * kL1, -0.5 * (kF1 / kF5) * kL5 };
    em.emitToStore(epochOf(30.0, m), store);
    EXPECT_EQ(ctr(em, "E01", "L1X"), 1);
    EXPECT_EQ(ctr(em, "E01", "L5X"), 0);
    EXPECT_EQ(ctr(em, "E02", "L1X"), 0);
    EXPECT_EQ(ctr(em, "E02", "L5X"), 0);
    // Epoch 3: every satellite's biases move alike by 0.3 m: shared, quiet, nothing declared.
    auto s = m;
    for (auto& [id, b] : s) { b.p1 += 0.3; b.p5 += 0.3; }
    em.emitToStore(epochOf(60.0, s), store);
    for (const auto& [id, b] : s) {
        (void)b;
        EXPECT_EQ(ctr(em, id, "L1X"), id == "E01" ? 1 : 0) << id;
        EXPECT_EQ(ctr(em, id, "L5X"), 0) << id;
    }
    const StepClassCounters& c = em.stepClassCounters();
    EXPECT_EQ(c.whole, 1);
    EXPECT_EQ(c.iono_like, 1);
    EXPECT_EQ(em.stepClassKeysStepped(), 1);
    EXPECT_GE(em.stepClassValueOnly(), 2);   // the value test would have declared E02 (and the shared move)
}

TEST(PhaseStepClassEmitter, ASatelliteMissingFromThePreviousEmissionKeepsTheValueTest) {
    NetworkProductEmitter em = makeEmitter();
    em.setStepClassTest({ "E:L1X/L5X" }, 0.15);
    SsrCorrectionStore store;
    em.emitToStore(epochOf(0.0, five()), store);
    auto m = five();
    m.erase("E05");
    em.emitToStore(epochOf(30.0, m), store);   // E05 missed
    auto r = five();
    r["E05"] = Biases{ -0.5 * kL1, -0.5 * (kF1 / kF5) * kL5 };   // returns ionosphere-like moved
    em.emitToStore(epochOf(60.0, r), store);
    // Not classified (no baseline at the previous emission): the value test declares it.
    EXPECT_EQ(ctr(em, "E05", "L1X"), 1);
    EXPECT_EQ(ctr(em, "E05", "L5X"), 1);
}

TEST(PhaseStepClassEmitter, AMalformedFamilyOrToleranceIsRefused) {
    NetworkProductEmitter em = makeEmitter();
    EXPECT_THROW(em.setStepClassTest({ "E:L1X/L1C" }, 0.15), std::invalid_argument);
    EXPECT_THROW(em.setStepClassTest({ "E-L1X/L5X" }, 0.15), std::invalid_argument);
    EXPECT_THROW(em.setStepClassTest({ "E:L1X/L5X" }, 0.5), std::invalid_argument);
    EXPECT_FALSE(em.stepClassArmed());
}

}  // namespace
}  // namespace GnssProcessor

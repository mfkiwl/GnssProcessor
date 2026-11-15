/**
 * @file test_bad_epoch_response.cpp
 * @brief The response to a bad epoch: the measured break of each band, at a slip or at a return after a gap, and
 *        a float-vehicle drop that covers it (network.amb_float_drop_jump_k, network.amb_float_drop_gap_cover).
 *
 * A flagged slip of 288 cycles on L1 alone (about 55 m) used to be dropped to the arc's birth variance at its
 * pre-slip level, a prior about 80 sigma wrong that the epoch's solve spread into the line of sight's
 * ionosphere, the arc's other band and the receiver's wet delay and clock.  A band that returns after a gap with
 * a shifted level met the same drop.  The response measures each band's phase-minus-code change across the break
 * and lets the drop's variance cover it.
 *
 * The gap cases drive the compute and qualify passes over synthetic observations (the geometry of
 * test_gap_reentry_per_signal.cpp, duplicated so that a change to one fixture does not affect the other):
 * L_i = (R - I_i)/lambda_i + N_i cycles and C_i = R + I_i metres, so a band's phase minus code is
 * -2 I_i + lambda_i N_i and a step of dN cycles moves it by exactly dN lambda_i with the ionosphere constant.
 */
#include <gtest/gtest.h>

#include "common/Constants.hpp"
#include "common/PppObservation.hpp"
#include "common/PppUtils.hpp"
#include "logging/LogManager.hpp"
#include "network/ar/AmbFloat.hpp"
#include "network/driver/RunTypes.hpp"
#include "network/slip/RawObservables.hpp"

#include <cmath>
#include <cstddef>
#include <string>
#include <vector>

namespace GnssProcessor {
namespace {

const double kL1 = Constants::SPEED_OF_LIGHT / Constants::GPS_L1_FREQ;  // about 0.190294 m
const double kL2 = Constants::SPEED_OF_LIGHT / Constants::GPS_L2_FREQ;  // about 0.244210 m
const double kL5 = Constants::SPEED_OF_LIGHT / Constants::GPS_L5_FREQ;  // about 0.254828 m

constexpr double kRangeM  = 22'000'000.0;   ///< Nominal geometric range.
constexpr double kIonoL1M = 5.0;            ///< First-order L1 ionospheric delay.

/// First-order ionospheric delay at a band (m).
double ionoAt(double lambda_m) {
    const double ratio = lambda_m / kL1;
    return kIonoL1M * ratio * ratio;
}

/// One band of one epoch: its phase signal, wavelength and ambiguity (cycles).
struct Band {
    std::string sig;
    double      lambda_m;
    double      amb_cyc;
};

/// A GPS satellite carrying exactly @p bands with matching codes; @p code_bias_m moves every code.
PppObservation makeObs(const std::string& sat, const std::vector<Band>& bands, double code_bias_m) {
    PppObservation obs{};
    obs.satellite = sat;
    obs.system    = System::GPS;
    obs.time      = GnssTime{ 2400, 0.0 };
    obs.elevation = 45.0;
    for (const auto& b : bands) {
        const double iono = ionoAt(b.lambda_m);
        obs.raw_observed[b.sig] = (kRangeM - iono) / b.lambda_m + b.amb_cyc;
        obs.raw_observed["C" + b.sig.substr(1)] = kRangeM + iono + code_bias_m;
    }
    return obs;
}

std::vector<Band> triple(double n1, double n2, double n5) {
    return { { "L1C", kL1, n1 }, { "L2W", kL2, n2 }, { "L5Q", kL5, n5 } };
}

/// One station's compute and qualify passes with both gap tiers armed, as the run loop drives them.
struct GapHarness {
    LogManager                  log_manager;
    PppUtils                    utils{ log_manager };
    SlipQcParams                params;
    std::vector<RawSlipHistory> hist;
    RawSlipEpoch                epoch;
    SlipQcCounters              counters;
    long long                   epoch_idx{ 0 };

    GapHarness() {
        params.gap_reentry            = true;
        params.gap_reentry_per_signal = true;
    }

    void run(const std::vector<PppObservation>& obs) {
        const std::vector<std::vector<PppObservation>> modeled{ obs };
        epoch.reset(1);
        const std::vector<bool> present{ true };
        networkComputeRawObservables(modeled, present, 1, utils, epoch, params.gap_reentry_per_signal);
        networkQualifyRawObservables(modeled, present, 1, epoch_idx, params, hist, epoch, counters);
        ++epoch_idx;
    }
};

/// Two satellites tracked throughout, so the station's step scales come from clean rows.
std::vector<PppObservation> ballast(double code_bias_m) {
    return { makeObs("G03", triple(500.0, 380.0, 360.0), code_bias_m),
             makeObs("G04", triple(510.0, 390.0, 370.0), code_bias_m) };
}

}  // namespace

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
    std::map<std::pair<int, std::string>, BandBreak> out;
    networkRawSlipBandJumps(ep, out);
    ASSERT_EQ(out.size(), 2u);
    EXPECT_NEAR(out.at({1, "G20_L1C"}).step_m, 3.0, 1e-12);
    EXPECT_NEAR(out.at({1, "G20_L2W"}).step_m, 0.0, 1e-12);
    EXPECT_EQ(out.at({1, "G20_L1C"}).kind, BandBreakKind::Adjacent);
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

// A band lost for three epochs while its partner tracks through returns 63 cycles off: the per-signal tier
// carries the band's own phase-minus-code step across the gap, and the gap writer records it as a declared,
// shifted Gap break; the band that returned unshifted is recorded with a step near 0.
TEST(BadEpochResponse, ABandReturningShiftedAfterAGapCarriesItsOwnStep) {
    GapHarness h;
    constexpr double kStepCyc = 63.0;   // about 12 m of L1
    const std::vector<std::vector<Band>> g01 = {
        triple(100.0, 60.0, 40.0),
        { { "L5Q", kL5, 40.0 } },
        { { "L5Q", kL5, 40.0 } },
        { { "L5Q", kL5, 40.0 } },
        triple(100.0 + kStepCyc, 60.0, 40.0) };
    for (std::size_t k = 0; k < g01.size(); ++k) {
        const double wobble = 0.001 * static_cast<double>(k + 1);
        std::vector<PppObservation> ep = ballast(wobble);
        ep.insert(ep.begin(), makeObs("G01", g01[k], wobble));
        h.run(ep);
    }
    const SigResumption* l1 = nullptr;
    for (const auto& g : h.epoch.sig_resumptions)
        if (g.satellite == "G01" && g.signal == "L1C") l1 = &g;
    ASSERT_NE(l1, nullptr);
    ASSERT_TRUE(l1->lmc_measured);
    // The code moved by the wobble only (4 mm over the gap), so the step is the carrier step to that bound.
    EXPECT_NEAR(l1->lmc_step_m, kStepCyc * kL1, 0.01);

    std::map<std::pair<int, std::string>, BandBreak> out;
    networkGapBandBreaks(h.epoch, out);
    const BandBreak& b1 = out.at({0, "G01_L1C"});
    EXPECT_EQ(b1.kind, BandBreakKind::Gap);
    EXPECT_TRUE(b1.declared_shift);
    EXPECT_NEAR(b1.step_m, kStepCyc * kL1, 0.01);
    const BandBreak& b2 = out.at({0, "G01_L2W"});
    EXPECT_FALSE(b2.declared_shift);
    EXPECT_LT(b2.step_m, 0.01);
}

// A whole satellite gone for two epochs returns with a shift common to both bands (63 L1 cycles, 49 L2 cycles:
// 11.99 and 11.97 m).  Its GF change is 2 cm, below the GF gate, so GF alone would size nothing; MW declares the
// shift, and each band's own phase-minus-code step carries its 12 m.
TEST(BadEpochResponse, AWholeArcReturnWithACommonShiftIsSizedPerBandNotByGf) {
    GapHarness h;
    const std::vector<std::vector<Band>> g01 = {
        triple(100.0, 60.0, 40.0),
        {},
        {},
        triple(100.0 + 63.0, 60.0 + 49.0, 40.0) };
    for (std::size_t k = 0; k < g01.size(); ++k) {
        const double wobble = 0.001 * static_cast<double>(k + 1);
        std::vector<PppObservation> ep = ballast(wobble);
        if (!g01[k].empty()) ep.insert(ep.begin(), makeObs("G01", g01[k], wobble));
        h.run(ep);
    }
    ASSERT_EQ(h.epoch.resumptions.size(), 1u);
    const GapResumption& g = h.epoch.resumptions.front();
    EXPECT_LT(std::abs(g.d_gf), h.params.gf_floor_m);   // GF cannot see a common shift
    EXPECT_TRUE(g.shifted);                              // MW does
    EXPECT_NEAR(g.lmc_step_m.at("L1C"), 63.0 * kL1, 0.01);
    EXPECT_NEAR(g.lmc_step_m.at("L2W"), 49.0 * kL2, 0.01);

    std::map<std::pair<int, std::string>, BandBreak> out;
    networkGapBandBreaks(h.epoch, out);
    EXPECT_TRUE(out.at({0, "G01_L1C"}).declared_shift);
    EXPECT_NEAR(out.at({0, "G01_L2W"}).step_m, 49.0 * kL2, 0.01);
}

// The cover by kind and form: a step between adjacent epochs is read by the slip cover alone; a return after a
// gap by the gap cover alone, as a step or, freed, only when its shift was declared.
TEST(BadEpochResponse, TheCoverReadsTheBreakByItsKindAndTheGapForm) {
    const BandBreak adjacent{12.0, BandBreakKind::Adjacent, false};
    const BandBreak shifted{12.0, BandBreakKind::Gap, true};
    const BandBreak quiet{0.3, BandBreakKind::Gap, false};
    EXPECT_NEAR(ambDropCoverVar(adjacent, 1.0, NetworkAmbGapCover::Off), 144.0, 1e-12);
    EXPECT_EQ(ambDropCoverVar(adjacent, 0.0, NetworkAmbGapCover::Free), 0.0);
    EXPECT_EQ(ambDropCoverVar(shifted, 1.0, NetworkAmbGapCover::Off), 0.0);
    EXPECT_NEAR(ambDropCoverVar(shifted, 1.0, NetworkAmbGapCover::Step), 144.0, 1e-12);
    EXPECT_NEAR(ambDropCoverVar(quiet, 2.0, NetworkAmbGapCover::Step), 0.36, 1e-12);
    EXPECT_EQ(ambDropCoverVar(shifted, 0.0, NetworkAmbGapCover::Free), kAmbGapFreeVarM2);
    EXPECT_EQ(ambDropCoverVar(quiet, 1.0, NetworkAmbGapCover::Free), 0.0);
}

// The declared-break floor reads the latch's cause: a slip detector or the gap re-entry response declares a break;
// a RAIM refloat (T4, T3) or the wind-up restart alone does not, and neither does an unrecorded cause.
TEST(BadEpochResponse, OnlyADeclaredBreakTakesTheDeclaredFloor) {
    using R = RelevelEpochState;
    EXPECT_TRUE(ambDropLatchDeclared(R::kCauseMw));
    EXPECT_TRUE(ambDropLatchDeclared(R::kCauseLli));
    EXPECT_TRUE(ambDropLatchDeclared(R::kCauseIfTd));
    EXPECT_TRUE(ambDropLatchDeclared(R::kCauseGfJump));
    EXPECT_TRUE(ambDropLatchDeclared(R::kCauseGap));
    EXPECT_TRUE(ambDropLatchDeclared(R::kCauseT4Attrib | R::kCauseLli));
    EXPECT_FALSE(ambDropLatchDeclared(R::kCauseT4Attrib));
    EXPECT_FALSE(ambDropLatchDeclared(R::kCauseT4Consens));
    EXPECT_FALSE(ambDropLatchDeclared(R::kCauseWindup));
    EXPECT_FALSE(ambDropLatchDeclared(0u));
}

}  // namespace GnssProcessor

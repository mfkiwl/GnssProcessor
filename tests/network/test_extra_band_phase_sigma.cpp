/**
 * @file test_extra_band_phase_sigma.cpp
 * @brief Contract tests for `network.extra_band_phase_sigma_scale`, the phase twin of
 *        `network.extra_band_code_sigma_scale`: suite ExtraBandPhaseSigma.
 *
 * In the network solve, the phase rows of a signal whose band is neither band of the
 * constellation's ionosphere-free pin pair fold at sigma x scale; the code rows are left
 * as they are.  A diagnostic lever: with the third band's phase deweighted, its carried
 * ambiguities lose their pull on the shared states.
 *
 * Covered here: the loader contract (1.0 by default, a value below 1 reset to 1.0, a legal
 * value parsed, the two scales independent of each other) and the closed-loop consumer
 * pinned at 1.0.  The predicate is the code scale's (suite ExtraBandCodeSigma); the weight
 * arithmetic is graded on the arms by the `w` column of `network_pf_rows.csv`.
 */
#include <gtest/gtest.h>

#include "config/GnssConfig.hpp"
#include "logging/LogManager.hpp"

#include <filesystem>
#include <fstream>
#include <string>
#include <system_error>
#include "../support/TestTempDir.hpp"   // per-process, per-test scratch directory

namespace fs = std::filesystem;

using GnssProcessor::GnssConfig;
using GnssProcessor::LogManager;

namespace {

fs::path writeTempConfig(const std::string& tag, const std::string& body) {
    const fs::path p = gnss_test::tempDir() / ("ebp_cfg_" + tag + ".json");
    std::ofstream f(p);
    f << body;
    f.close();
    return p;
}

/// A minimal loadable PPP-RTK network config; @p network_extra splices into the network block.
std::string networkConfig(const std::string& network_extra) {
    return std::string("{\n") +
        "  \"processing\": {\n"
        "    \"mode\": \"ppp-rtk-network\",\n"
        "    \"active_systems\": [ \"GPS\" ],\n"
        "    \"signal_priorities\": { \"GPS\": \"WC\" }\n"
        "  },\n"
        "  \"network\": {\n"
        "    \"clock_datum_station\": \"AAAA\",\n"
        + network_extra +
        "    \"stations\": [\n"
        "      { \"name\": \"AAAA\", \"position_ecef\": [ -2493304.99, -4655214.79, 3565497.67 ] },\n"
        "      { \"name\": \"BBBB\", \"position_ecef\": [ -2281621.75, -1453585.08, 5756964.89 ] }\n"
        "    ]\n"
        "  }\n"
        "}\n";
}

double loadPhaseScale(const std::string& tag, const std::string& extra, double* code = nullptr) {
    LogManager log;
    const fs::path p = writeTempConfig(tag, networkConfig(extra));
    GnssConfig cfg;
    EXPECT_TRUE(cfg.loadFromJson(p, log));
    if (code) *code = cfg.networkExtraBandCodeSigmaScale();
    const double s = cfg.networkExtraBandPhaseSigmaScale();
    std::error_code ec;
    fs::remove(p, ec);
    return s;
}

}  // namespace

TEST(ExtraBandPhaseSigma, DefaultsToOneSoAnUnarmedRunIsUnscaled) {
    EXPECT_DOUBLE_EQ(loadPhaseScale("default", ""), 1.0);
}

TEST(ExtraBandPhaseSigma, ParsesALegalScale) {
    EXPECT_DOUBLE_EQ(loadPhaseScale("hundred", "    \"extra_band_phase_sigma_scale\": 100.0,\n"), 100.0);
}

TEST(ExtraBandPhaseSigma, RefusesAScaleBelowOne) {
    EXPECT_DOUBLE_EQ(loadPhaseScale("low", "    \"extra_band_phase_sigma_scale\": 0.5,\n"), 1.0);
}

TEST(ExtraBandPhaseSigma, TheTwoScalesAreIndependent) {
    double code = 0.0;
    EXPECT_DOUBLE_EQ(loadPhaseScale("phaseonly", "    \"extra_band_phase_sigma_scale\": 50.0,\n", &code), 50.0);
    EXPECT_DOUBLE_EQ(code, 1.0);
    EXPECT_DOUBLE_EQ(loadPhaseScale("codeonly", "    \"extra_band_code_sigma_scale\": 50.0,\n", &code), 1.0);
    EXPECT_DOUBLE_EQ(code, 50.0);
}

TEST(ExtraBandPhaseSigma, TheClosedLoopConsumerIsPinnedAtOne) {
    LogManager log;
    const fs::path p = writeTempConfig("consumer", networkConfig("    \"extra_band_phase_sigma_scale\": 100.0,\n"));
    GnssConfig cfg;
    ASSERT_TRUE(cfg.loadFromJson(p, log));
    ASSERT_DOUBLE_EQ(cfg.networkExtraBandPhaseSigmaScale(), 100.0);
    const GnssConfig consumer = cfg.deriveClosedLoopConsumerConfig();
    EXPECT_DOUBLE_EQ(consumer.networkExtraBandPhaseSigmaScale(), 1.0);
    std::error_code ec;
    fs::remove(p, ec);
}

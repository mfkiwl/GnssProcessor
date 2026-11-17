/**
 * @file test_mw_lli_slip_mask.cpp
 * @brief Contract tests for `estimation.cycle_slip.lli_slip_mask`: suite MwLliSlipMask.
 *
 * The Melbourne-Wubbena detector reads a phase observation's loss-of-lock indicator
 * through the mask: 7 (the default, the detector as built) counts any bit, 3 counts
 * bit 0 (lock lost) and bit 1 (half-cycle ambiguity) only.  RINEX 3 defines bit 2 for
 * Galileo as BOC tracking of an MBOC signal, not a loss of lock, and a receiver that
 * raises it at every epoch (a Leica GR50 on E1) has every Galileo ambiguity reset at every
 * epoch under the default.
 *
 * Covered here: the loader (7 by default, 3 parsed); the loss-of-lock test
 * (MwSlipDetector::hasAnyPhaseLockLoss: 4 is no loss under 3 and a loss under 7; 1 and 5
 * are a loss under both; a code observable never counts); and the two LLI band memories
 * of MwSlipDetectorEpoch.cpp (the combined path's eraseArcsOnLli_ and the uncombined
 * path's preserveArcsOnLli_), which record a band only when its indicator passes the mask.
 */
#include <gtest/gtest.h>

#include "common/PppObservation.hpp"
#include "config/GnssConfig.hpp"
#include "logging/LogManager.hpp"
#include "slip/MwDetectorWork.hpp"
#include "slip/MwSlipDetector.hpp"

#include <filesystem>
#include <fstream>
#include <map>
#include <set>
#include <string>
#include <system_error>
#include <vector>
#include "support/TestTempDir.hpp"   // per-process, per-test scratch directory

namespace GnssProcessor {

/// Befriended in MwSlipDetector.hpp; forwards to the loss-of-lock test and runs each LLI
/// policy on one observation, returning the bands its memory recorded.  Declared in this
/// namespace, as the friend declaration names GnssProcessor::MwLliSlipMaskTestAccess.
struct MwLliSlipMaskTestAccess {
    /// Forwards to MwSlipDetector::hasAnyPhaseLockLoss.
    static bool lockLoss(const MwSlipDetector& det, const PppObservation& obs) {
        return det.hasAnyPhaseLockLoss(obs);
    }

    /// Runs the combined path's LLI policy (no ionosphere-free pair to reset) and returns
    /// the bands the epoch's LLI memory holds for the satellite.
    static std::set<std::string> combinedBands(MwSlipDetector& det, LogManager& log,
                                               const PppObservation& obs) {
        MwSlipDetector::MwEpochWork w{ log.getLogger("mw_slip_detector") };
        det.eraseArcsOnLli_(w, obs, {});
        return det.cur_lli_bands_[obs.satellite];
    }

    /// Runs the uncombined path's LLI policy (no lane to keep a sample of) and returns the
    /// bands the epoch's LLI memory holds for the satellite.
    static std::set<std::string> uncombinedBands(MwSlipDetector& det, LogManager& log,
                                                 const PppObservation& obs) {
        MwSlipDetector::MwEpochWork w{ log.getLogger("mw_slip_detector") };
        det.preserveArcsOnLli_(w, obs, {});
        return det.cur_lli_bands_[obs.satellite];
    }
};

}  // namespace GnssProcessor

using namespace GnssProcessor;
using Access = MwLliSlipMaskTestAccess;

namespace {

namespace fs = std::filesystem;

/// Loads @p json into @p config through a scratch file.
void loadConfig(GnssConfig& config, LogManager& log, const std::string& tag, const std::string& json) {
    const fs::path p = gnss_test::tempDir() / ("gnss_mw_lli_mask_" + tag + ".json");
    {
        std::ofstream f(p);
        f << json;
    }
    ASSERT_TRUE(config.loadFromJson(p, log));
    std::error_code ec;
    fs::remove(p, ec);
}

/// A Galileo observation whose phases carry the given loss-of-lock indicators.
PppObservation galileo(const std::map<std::string, int>& lli) {
    PppObservation obs;
    obs.satellite = "E07";
    for (const auto& [code, v] : lli) {
        obs.lli_flags[code] = v;
        obs.raw_observed[code] = 1.0e8;
    }
    return obs;
}

/// One detector per mask: the detector keeps a reference to its configuration.
struct Masked {
    LogManager log;
    GnssConfig config;
    explicit Masked(const char* json, const char* tag) { loadConfig(config, log, tag, json); }
};

constexpr const char* kDefault = R"({ })";
constexpr const char* kMask3   = R"({ "estimation": { "cycle_slip": { "lli_slip_mask": 3 } } })";

}  // namespace

TEST(MwLliSlipMask, LoaderDefaultsToSevenAndParsesThree) {
    Masked d(kDefault, "default");
    EXPECT_EQ(d.config.getCycleSlipConfig().lli_slip_mask, 7);
    Masked m(kMask3, "mask3");
    EXPECT_EQ(m.config.getCycleSlipConfig().lli_slip_mask, 3);
}

TEST(MwLliSlipMask, BitTwoAloneIsNoLossUnderThreeAndALossUnderTheDefault) {
    Masked d(kDefault, "d4");
    Masked m(kMask3, "m4");
    const MwSlipDetector det_d(d.config, d.log);
    const MwSlipDetector det_m(m.config, m.log);
    const PppObservation obs = galileo({ { "L1C", 4 } });
    EXPECT_TRUE(Access::lockLoss(det_d, obs));
    EXPECT_FALSE(Access::lockLoss(det_m, obs));
}

TEST(MwLliSlipMask, BitZeroIsALossUnderBothMasks) {
    Masked d(kDefault, "d15");
    Masked m(kMask3, "m15");
    const MwSlipDetector det_d(d.config, d.log);
    const MwSlipDetector det_m(m.config, m.log);
    for (const int v : { 1, 5 }) {
        const PppObservation obs = galileo({ { "L1C", v } });
        EXPECT_TRUE(Access::lockLoss(det_d, obs)) << "LLI " << v;
        EXPECT_TRUE(Access::lockLoss(det_m, obs)) << "LLI " << v;
    }
}

TEST(MwLliSlipMask, ACodeIndicatorNeverCounts) {
    Masked d(kDefault, "dcode");
    const MwSlipDetector det(d.config, d.log);
    EXPECT_FALSE(Access::lockLoss(det, galileo({ { "C1C", 1 } })));
}

TEST(MwLliSlipMask, CombinedBandMemoryRecordsOnlyBandsThatPassTheMask) {
    // L1C carries bit 2 alone, L5Q bit 0, L7Q bits 0 and 2.
    const PppObservation obs = galileo({ { "L1C", 4 }, { "L5Q", 1 }, { "L7Q", 5 } });
    Masked d(kDefault, "dcomb");
    Masked m(kMask3, "mcomb");
    MwSlipDetector det_d(d.config, d.log);
    MwSlipDetector det_m(m.config, m.log);
    EXPECT_EQ(Access::combinedBands(det_d, d.log, obs), (std::set<std::string>{ "L1C", "L5Q", "L7Q" }));
    EXPECT_EQ(Access::combinedBands(det_m, m.log, obs), (std::set<std::string>{ "L5Q", "L7Q" }));
}

TEST(MwLliSlipMask, UncombinedBandMemoryRecordsOnlyBandsThatPassTheMask) {
    const PppObservation obs = galileo({ { "L1C", 4 }, { "L5Q", 1 }, { "L7Q", 5 } });
    Masked d(kDefault, "dunc");
    Masked m(kMask3, "munc");
    MwSlipDetector det_d(d.config, d.log);
    MwSlipDetector det_m(m.config, m.log);
    EXPECT_EQ(Access::uncombinedBands(det_d, d.log, obs), (std::set<std::string>{ "L1C", "L5Q", "L7Q" }));
    EXPECT_EQ(Access::uncombinedBands(det_m, m.log, obs), (std::set<std::string>{ "L5Q", "L7Q" }));
}

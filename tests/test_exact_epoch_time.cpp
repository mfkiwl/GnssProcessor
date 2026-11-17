// Unit tests of the calendar conversion's rule (math/TimeUtils.hpp, TimeUtils::setExactCalendarTime, config key
// processing.exact_epoch_time): suite ExactEpochTime.
//
//   - on: every 30 s epoch of GPS week 2420 converts with an error under 1 nanosecond, on the GPS and the UTC scale;
//   - off: the conversion as built, the Julian-date round trip, reproduced bit for bit, whose rounding drifts and
//     wraps every 675 s (zero at the multiples of 1/128 day, up to 20 microseconds between them);
//   - a fraction of a second keeps its value with the switch on.

#include "math/TimeUtils.hpp"

#include <gtest/gtest.h>

#include <cmath>

using namespace GnssProcessor;

namespace {

/// Restores the process-wide switch when a test ends.
struct ExactCalendarGuard {
    bool before;
    explicit ExactCalendarGuard(bool on) : before(TimeUtils::exactCalendarTime()) { TimeUtils::setExactCalendarTime(on); }
    ~ExactCalendarGuard() { TimeUtils::setExactCalendarTime(before); }
};

/// The conversion as built (the GPS scale): the fraction of the day added to the Julian date.
double legacyGpsSeconds(int y, int mo, int d, int h, int mi, double s) {
    const double jd = TimeUtils::gregorianToJulianDay(y, mo, d, h, mi, s);
    return (jd - TimeUtils::GPS_EPOCH_JD) * TimeUtils::SECONDS_IN_DAY;
}

constexpr int kWeek = 2420;         // GPS week 2420 starts on Sunday 2026-05-24
constexpr int kFirstDay = 24;       // 24 to 30 May 2026

}  // namespace

TEST(ExactEpochTime, EveryEpochOfAWeekIsExactWithTheSwitchOn) {
    ExactCalendarGuard guard(true);
    double worst = 0.0;
    for (int dd = 0; dd < 7; ++dd)
        for (int sod = 0; sod < 86400; sod += 30) {
            const GnssTime t = TimeUtils::gregorianGpsToGpsTime(2026, 5, kFirstDay + dd, sod / 3600, (sod % 3600) / 60,
                                                                static_cast<double>(sod % 60));
            ASSERT_EQ(t.week, kWeek);
            worst = std::max(worst, std::abs(t.tow - (dd * 86400.0 + sod)));
        }
    EXPECT_LT(worst, 1e-9);
}

TEST(ExactEpochTime, TheUtcScaleIsExactWithTheSwitchOn) {
    ExactCalendarGuard guard(true);
    double worst = 0.0;
    for (int dd = 0; dd < 7; ++dd)
        for (int sod = 0; sod < 86400; sod += 30) {
            const GnssTime t = TimeUtils::gregorianToGpsTime(2026, 5, kFirstDay + dd, sod / 3600, (sod % 3600) / 60,
                                                             static_cast<double>(sod % 60));
            // GPS = UTC + 18 s in 2026.
            const double want = dd * 86400.0 + sod + 18.0;
            worst = std::max(worst, std::abs((t.week - kWeek) * 604800.0 + t.tow - want));
        }
    EXPECT_LT(worst, 1e-9);
}

TEST(ExactEpochTime, TheSwitchOffKeepsTheJulianDateRoundTripAndItsSawtooth) {
    ExactCalendarGuard guard(false);
    double worst = 0.0;
    int wraps = 0;
    double prev = 0.0;
    for (int sod = 0; sod < 86400; sod += 30) {
        const int h = sod / 3600, mi = (sod % 3600) / 60;
        const double s = static_cast<double>(sod % 60);
        const GnssTime t = TimeUtils::gregorianGpsToGpsTime(2026, 5, kFirstDay, h, mi, s);
        // Bit for bit the conversion as built.
        const double legacy = legacyGpsSeconds(2026, 5, kFirstDay, h, mi, s);
        ASSERT_EQ(t.week * 604800.0 + t.tow, legacy) << "sod " << sod;
        const double err = t.tow - sod;
        worst = std::max(worst, std::abs(err));
        if (sod % 675 == 0) EXPECT_EQ(err, 0.0) << "a multiple of 1/128 day at sod " << sod;
        if (sod > 0 && err - prev > 3e-5) ++wraps;   // the +38 microsecond wrap
        prev = err;
        // The UTC path as built too.
        const GnssTime u = TimeUtils::gregorianToGpsTime(2026, 5, kFirstDay, h, mi, s);
        const double jd_utc = TimeUtils::gregorianToJulianDay(2026, 5, kFirstDay, h, mi, s);
        ASSERT_EQ(u.week * 604800.0 + u.tow, (jd_utc - TimeUtils::GPS_EPOCH_JD) * TimeUtils::SECONDS_IN_DAY + 18.0);
    }
    EXPECT_GT(worst, 1.9e-5);
    EXPECT_LT(worst, 2.02e-5);   // half the last-bit spacing of a Julian date near 2.46e6 (40.2 microseconds)
    EXPECT_EQ(wraps, 128);       // one wrap per 675 s
}

TEST(ExactEpochTime, AFractionOfASecondKeepsItsValue) {
    ExactCalendarGuard guard(true);
    const GnssTime t = TimeUtils::gregorianGpsToGpsTime(2026, 5, 27, 13, 47, 29.9999999);
    EXPECT_EQ(t.week, kWeek);
    EXPECT_NEAR(t.tow, 3 * 86400.0 + 13 * 3600.0 + 47 * 60.0 + 29.9999999, 1e-9);
}

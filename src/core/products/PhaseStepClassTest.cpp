#include "products/PhaseStepClassTest.hpp"

#include "products/PhaseVisibleStepTest.hpp"

#include <cmath>

namespace GnssProcessor {

namespace {
constexpr double kSpeedOfLight = 299792458.0;
}

void stepClassLevels(double clock_m, double p1_m, double p2_m, double b1_m, double b2_m,
                     double f1_hz, double f2_hz, double& e1_cyc, double& e2_cyc) {
    const double gamma = (f1_hz / f2_hz) * (f1_hz / f2_hz);
    const double x     = ((clock_m - b1_m) - (clock_m - b2_m)) / (1.0 - gamma);
    e1_cyc = (clock_m - p1_m + x) / (kSpeedOfLight / f1_hz);
    e2_cyc = (clock_m - p2_m + gamma * x) / (kSpeedOfLight / f2_hz);
}

std::vector<StepClassVerdict> classifyStepClasses(const std::vector<StepClassSat>& sats, double f1_hz,
                                                  double f2_hz, double tol_cyc, int min_sats,
                                                  StepClassCounters* counters) {
    std::vector<StepClassVerdict> out(sats.size());
    std::vector<double> d1, d2;
    for (const StepClassSat& s : sats) {
        if (!s.tested) continue;
        d1.push_back(s.d1_cyc);
        d2.push_back(s.d2_cyc);
    }
    if (d1.empty()) return out;
    if (counters) ++counters->families;
    if (static_cast<int>(d1.size()) < min_sats) {
        if (counters) ++counters->families_below_min;
        return out;
    }
    const double m1 = phaseVisibleMedian(d1);
    const double m2 = phaseVisibleMedian(d2);
    for (std::size_t i = 0; i < sats.size(); ++i) {
        if (!sats[i].tested) continue;
        StepClassVerdict& v = out[i];
        v.x1_cyc = sats[i].d1_cyc - m1;
        v.x2_cyc = sats[i].d2_cyc - m2;
        v.dn_cyc = (f1_hz * v.x1_cyc - f2_hz * v.x2_cyc) / (f1_hz - f2_hz);
        const double n1 = std::round(v.x1_cyc), n2 = std::round(v.x2_cyc);
        if (std::abs(v.x1_cyc) < tol_cyc && std::abs(v.x2_cyc) < tol_cyc) {
            v.cls = StepClass::Quiet;
        } else if (std::abs(v.x1_cyc - n1) < tol_cyc && std::abs(v.x2_cyc - n2) < tol_cyc) {
            v.cls   = StepClass::Whole;
            v.step1 = n1 != 0.0;
            v.step2 = n2 != 0.0;
        } else if (std::abs(v.dn_cyc) < tol_cyc) {
            v.cls = StepClass::IonoLike;
        } else {
            v.cls   = StepClass::Fraction;
            v.step1 = std::abs(v.x1_cyc) >= tol_cyc;
            v.step2 = std::abs(v.x2_cyc) >= tol_cyc;
        }
        if (counters) {
            ++counters->sats_tested;
            switch (v.cls) {
                case StepClass::Quiet:    ++counters->quiet; break;
                case StepClass::Whole:    ++counters->whole; break;
                case StepClass::IonoLike: ++counters->iono_like; break;
                case StepClass::Fraction: ++counters->fraction; break;
                default: break;
            }
            counters->signals_declared += (v.step1 ? 1 : 0) + (v.step2 ? 1 : 0);
        }
    }
    return out;
}

const char* stepClassName(StepClass c) {
    switch (c) {
        case StepClass::Untested: return "untested";
        case StepClass::Quiet:    return "quiet";
        case StepClass::Whole:    return "whole";
        case StepClass::IonoLike: return "iono_like";
        case StepClass::Fraction: return "fraction";
    }
    return "?";
}

} // namespace GnssProcessor

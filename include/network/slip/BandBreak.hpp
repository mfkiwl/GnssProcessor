#pragma once
/**
 * @file BandBreak.hpp
 * @brief The measured break of one band at one epoch: the size a detector measured, which the response reads.
 *
 * A band whose arc is latched this epoch (RelevelEpochState::free_ambs) is answered by the float vehicle's drop
 * (network/ar/AmbFloat.hpp).  The drop needs the size of the break the detector saw: a band that moved by metres
 * must not keep a prior at its old level.  Two instruments measure a break.  The raw-observable screen measures
 * the step between adjacent epochs; the gap instrument measures it across a tracking gap and declares whether the
 * return is shifted.  Both write this record, keyed like the latch, so the drop reads one size whichever detector
 * latched the band.
 */
#include <cstdint>

namespace GnssProcessor {

/// Where a band's break was measured.
enum class BandBreakKind : std::uint8_t {
    Adjacent,  ///< Between the epoch and the one immediately before it (a slip).
    Gap        ///< Across a tracking gap of at least one missed epoch (a return).
};

/**
 * @brief The measured break of one band (one carried arc) at this epoch.
 *
 * The step is the band's own phase-minus-code change across the break: its carrier step plus code noise, whatever
 * the other band did.  A shift common to both bands cancels in the geometry-free combination, so a GF change is
 * no bound on a band's shift; this record never takes its size from one.
 */
struct BandBreak {
    double        step_m{0.0};                    ///< |phase - code| change of the band across the break (m).
    BandBreakKind kind{BandBreakKind::Adjacent};  ///< Where it was measured.
    bool          declared_shift{false};          ///< The gap instrument declared the return shifted (Gap only).
};

}  // namespace GnssProcessor

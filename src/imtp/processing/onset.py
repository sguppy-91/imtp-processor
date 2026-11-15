"""Onset selection utilities.

Manual onset identification is the reference methodology for the IMTP:
the analyst visually identifies force onset for every trial (Guppy et
al., 2024). The manual helpers here resolve an analyst-chosen onset
time to sample indices and trim the force-time curve from it.

An opt-in automated branch is also provided: `detect_onset_auto`
identifies onset as the first sustained crossing of a bodyweight-plus-
noise threshold (BW + n SDs; Dos'Santos et al., 2017; Chavda et al.,
2020). It is never a silent replacement for the manual reference
method; the workflow records which method produced each exported row.
"""

import numpy as np

from .bodyweight import WEIGH_WINDOW_S
from .countermovement import up_to_peak

# Default persistence window for the automated onset rule: force must
# stay above the threshold for at least this long. Time-based, so the
# rule behaves identically at any sampling rate.
DEFAULT_PERSIST_S = 0.010


class OnsetError(Exception):
    """No sustainable force-onset crossing found in the search region."""


def detect_onset_auto(df, weight, stddev, sd_multiplier=5, persist_s=DEFAULT_PERSIST_S):
    """Automated force-onset detection: first sustained BW + n SD crossing.

    Opt-in alternative to manual onset (the reference method, Guppy et
    al., 2024). `df` is force data trimmed from the weighing start (the
    ``df`` from calculate_bodyweight). The threshold is derived from the
    weighing window, ``weight + sd_multiplier * stddev`` — computed from
    `stddev` directly so both 3 SD (Chavda et al., 2020) and 5 SD
    (Dos'Santos et al., 2017) are supported.

    Search region: from the end of the weighing window (first sample
    time + WEIGH_WINDOW_S) up to and including peak force. A rise inside
    the weighing window is therefore ignored — it contaminates BW and SD
    and must fail loudly rather than produce an onset.

    Onset rule: the first sample with Fz strictly above the threshold
    whose contiguous run of above-threshold samples spans at least
    `persist_s` seconds (time-based, so behaviour is identical at any
    sampling rate). Returns the onset time in seconds (the `Time` of
    that first sample).

    Raises OnsetError if no sample in the search region sustainably
    crosses the threshold: no fallback, no substituting the force
    minimum, no searching past peak force.
    """
    threshold = weight + sd_multiplier * stddev
    region = up_to_peak(df)
    weigh_end = region["Time"].iloc[0] + WEIGH_WINDOW_S
    region = region[region["Time"] > weigh_end]
    if region.empty:
        raise OnsetError(
            "No data between the end of the weighing window and peak force"
        )
    times = region["Time"].to_numpy()
    fz = region["Fz"].to_numpy()
    above = fz > threshold
    candidates = np.flatnonzero(above)
    if candidates.size == 0:
        raise OnsetError(
            f"Force never exceeds the BW + {sd_multiplier} SD threshold "
            f"({threshold:.1f} N) before peak force"
        )
    # End of each candidate's contiguous above-threshold run: the run
    # stops at the next below-threshold sample (or at peak force, since
    # the search region ends there — a crossing less than persist_s
    # before peak therefore cannot be verified and does not count).
    breaks = np.flatnonzero(~above)
    pos = np.searchsorted(breaks, candidates)
    run_end = np.where(
        pos < breaks.size, breaks[np.minimum(pos, breaks.size - 1)] - 1, times.size - 1
    )
    span = times[run_end] - times[candidates]
    sustained = span >= persist_s - 1e-9
    if not sustained.any():
        raise OnsetError(
            f"no crossing of {threshold:.1f} N sustained for at least "
            f"{persist_s * 1000:.0f} ms before peak force"
        )
    onset_i = candidates[np.argmax(sustained)]
    return float(times[onset_i])


def nearest_index(values, target):
    """Index of the sample nearest to `target`."""
    return (np.abs(values - target)).argmin()


def select_onset(data, df1, onset_time):
    """Resolve a chosen onset time to (onset_Fz, start_index).

    `data` is the full trial (Time/Fz); `df1` is the force data up to
    peak force, within which the onset must sit. `start_index` is a
    pandas index label into `df1`. Verbatim from the v1-monolith
    script's main().
    """
    time_values = data.Time.values
    onset_Fz = data["Fz"].iloc[nearest_index(time_values, onset_time)]
    start = df1.index[nearest_index(df1["Time"].values, onset_time)]
    return onset_Fz, start


def trim_to_onset(df1, start):
    """Trim `df1` from the onset index and add normalised time (`ntime`).

    Verbatim from the v1-monolith script's main() (force-time curve
    trimming). Returns a fresh DataFrame indexed from 0 with an added
    `ntime` column (seconds from onset).
    """
    df2 = df1.truncate(before=start).reset_index()
    df2["ntime"] = df2["Time"] - df2["Time"].iloc[0]
    return df2

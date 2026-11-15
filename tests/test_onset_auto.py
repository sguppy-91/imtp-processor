"""Automated onset detection tests: detect_onset_auto and OnsetError.

Synthetic Time/Fz curves with a known flat weighing window and a known
force rise. Core dependencies only (no matplotlib/PySimpleGUI), so the
whole file runs headless.
"""
import numpy as np
import pandas as pd
import pytest

from imtp.processing.bodyweight import WEIGH_WINDOW_S, calculate_bodyweight
from imtp.processing.countermovement import up_to_peak
from imtp.processing.onset import (DEFAULT_PERSIST_S, OnsetError,
                                   detect_onset_auto)

WEIGHT = 700.0
SD = 2.0
WEIGH_START = 1.0
RISE_START = 2.5
SLOPE = 3000.0
PEAK = 1600.0
DURATION = 5.0


def make_curve(fs, weight=WEIGHT, sd=SD, weigh_start=WEIGH_START,
               rise_start=RISE_START, slope=SLOPE, peak=PEAK,
               duration=DURATION, seed=0, dip=None, spike=None):
    """Synthetic force-time curve.

    Noisy flat weighing window at `weight`, exact-weight baseline after
    it, then a linear rise from `rise_start` up to `peak` followed by a
    linear decline (so peak force is inside the trial).

    dip:   (time, depth) — brief dip to weight - depth after the window
    spike: (time, height, width_s) — transient at weight + height before
           the rise (width_s < persist_s makes it a sub-persistence spike)
    rise_start=None suppresses the rise (flat-after-window curve).
    """
    n = int(round(duration * fs)) + 1
    t = np.arange(n) / fs
    rng = np.random.default_rng(seed)
    fz = np.full(n, float(weight))
    wmask = (t >= weigh_start) & (t <= weigh_start + WEIGH_WINDOW_S)
    fz[wmask] += rng.normal(0.0, sd, int(wmask.sum()))
    pre_rise = np.ones(n, bool) if rise_start is None else (t <= rise_start)
    if dip is not None:
        t_dip, depth = dip
        dmask = (t >= t_dip) & (t < t_dip + 0.05) & pre_rise
        fz[dmask] = weight - depth
    if spike is not None:
        t_sp, height, width_s = spike
        smask = (t >= t_sp) & (t < t_sp + width_s) & pre_rise
        fz[smask] = weight + height
    if rise_start is not None:
        rise = t > rise_start
        fz[rise] = weight + slope * (t[rise] - rise_start)
        t_peak = rise_start + (peak - weight) / slope
        past = t > t_peak
        fz[past] = np.maximum(peak - slope * (t[past] - t_peak), weight)
    return pd.DataFrame({'Time': t, 'Fz': fz})


def run_auto(curve, sd_multiplier=5, persist_s=DEFAULT_PERSIST_S,
             weigh_start=WEIGH_START):
    """calculate_bodyweight -> detect_onset_auto, as the workflow does."""
    bw = calculate_bodyweight(curve, weigh_start)
    onset = detect_onset_auto(bw['df'], bw['weight'], bw['stddev'],
                              sd_multiplier=sd_multiplier,
                              persist_s=persist_s)
    return onset, bw


def expected_rise_onset(bw, sd_multiplier, weight=WEIGHT, slope=SLOPE):
    """Analytic crossing time of the constructed ramp through the
    hand-computed BW + n SD threshold."""
    threshold = bw['weight'] + sd_multiplier * bw['stddev']
    return RISE_START + (threshold - weight) / slope


@pytest.mark.parametrize("fs", [500, 1000])
@pytest.mark.parametrize("sd_multiplier", [3, 5])
def test_correct_onset_both_multipliers(fs, sd_multiplier):
    """Onset lands within one sample interval of the constructed rise
    crossing, at 3 and 5 SDs."""
    curve = make_curve(fs)
    onset, bw = run_auto(curve, sd_multiplier=sd_multiplier)
    t_star = expected_rise_onset(bw, sd_multiplier)
    assert abs(onset - t_star) <= 1.0 / fs + 1e-9
    # search region starts after the weighing window
    assert onset > WEIGH_START + WEIGH_WINDOW_S


def test_default_multiplier_is_5_sd():
    curve = make_curve(1000)
    onset_default, _ = run_auto(curve)
    onset_5, _ = run_auto(curve, sd_multiplier=5)
    assert onset_default == onset_5


def test_multiplier_ordering():
    """On the same curve the 5 SD onset is later than or equal to 3 SD."""
    curve = make_curve(1000)
    onset_3, _ = run_auto(curve, sd_multiplier=3)
    onset_5, _ = run_auto(curve, sd_multiplier=5)
    assert onset_5 >= onset_3


@pytest.mark.parametrize("fs", [500, 1000])
def test_sub_persistence_spike_does_not_trigger(fs):
    """A single-sample / sub-persist_s spike above threshold is ignored;
    onset stays at the sustained rise."""
    plain = make_curve(fs)
    spiked = make_curve(fs, spike=(2.1, 50.0, 0.004))
    onset_plain, _ = run_auto(plain)
    onset_spiked, _ = run_auto(spiked)
    assert onset_spiked == onset_plain


def test_sustained_spike_triggers_at_two_sampling_rates():
    """A spike sustained >= persist_s does trigger, and the onset time
    agrees across sampling rates within one sample interval (the rule is
    time-based, not sample-based)."""
    onsets = {}
    for fs in (500, 1000):
        # the real rise stays later than the spike so the spike is not
        # the peak and its full run lies inside the search region
        curve = make_curve(fs, spike=(2.1, 50.0, 0.012))
        onset, _ = run_auto(curve)
        onsets[fs] = onset
        assert abs(onset - 2.1) <= 1.0 / fs + 1e-9
    assert abs(onsets[500] - onsets[1000]) <= 1.0 / 500 + 1e-9


def test_no_sustained_crossing_raises():
    """A sub-persistence spike and nothing else -> no sustainable
    crossing in the search region -> OnsetError."""
    curve = make_curve(1000, rise_start=None, spike=(2.1, 50.0, 0.004))
    bw = calculate_bodyweight(curve, WEIGH_START)
    with pytest.raises(OnsetError):
        detect_onset_auto(bw['df'], bw['weight'], bw['stddev'])


def test_flat_curve_raises():
    """No crossing anywhere in the search region -> OnsetError."""
    curve = make_curve(1000, rise_start=None)
    bw = calculate_bodyweight(curve, WEIGH_START)
    with pytest.raises(OnsetError):
        detect_onset_auto(bw['df'], bw['weight'], bw['stddev'])


def test_rise_inside_weighing_window_fails_loudly():
    """A rise during the weighing window contaminates BW/SD and is
    ignored: no onset is produced from it (OnsetError)."""
    fs = 1000
    n = int(round(DURATION * fs)) + 1
    t = np.arange(n) / fs
    fz = np.full(n, WEIGHT)
    wmask = (t >= WEIGH_START) & (t <= WEIGH_START + WEIGH_WINDOW_S)
    fz[wmask] = WEIGHT + SLOPE * (t[wmask] - WEIGH_START)  # rise inside the window
    curve = pd.DataFrame({'Time': t, 'Fz': fz})
    bw = calculate_bodyweight(curve, WEIGH_START)
    with pytest.raises(OnsetError):
        detect_onset_auto(bw['df'], bw['weight'], bw['stddev'])


def test_decline_after_peak_does_not_affect_onset():
    """The curve declines after peak force; onset is still the rise
    crossing (search is bounded at peak, decline is never searched)."""
    curve = make_curve(1000)  # includes a post-peak decline
    onset, bw = run_auto(curve)
    t_star = expected_rise_onset(bw, 5)
    assert abs(onset - t_star) <= 1.0 / 1000 + 1e-9
    peak_time = curve['Time'].iloc[curve['Fz'].idxmax()]
    assert onset < peak_time


def test_onset_is_first_sustained_sample_above_hand_computed_threshold():
    """Onset sample is above weight + multiplier*stddev and is the first
    sample of its run above the threshold (clean curve: the previous
    sample is at or below it)."""
    sd_multiplier = 5
    curve = make_curve(1000)
    onset, bw = run_auto(curve, sd_multiplier=sd_multiplier)
    threshold = bw['weight'] + sd_multiplier * bw['stddev']
    region = up_to_peak(bw['df'])
    region = region[region['Time'] > bw['df']['Time'].iloc[0] + WEIGH_WINDOW_S]
    times = region['Time'].to_numpy()
    fz = region['Fz'].to_numpy()
    i = int(np.flatnonzero(times == onset)[0])
    assert fz[i] > threshold
    assert i == 0 or fz[i - 1] <= threshold


def test_countermovement_shape_still_yields_rise_crossing():
    """A dip below BW before the rise is below threshold and cannot
    trigger onset; the first sustained crossing after the weighing
    window is returned."""
    plain = make_curve(1000)
    dipped = make_curve(1000, dip=(2.2, 100.0))
    onset_plain, _ = run_auto(plain, sd_multiplier=3)
    onset_dipped, bw = run_auto(dipped, sd_multiplier=3)
    assert onset_dipped == onset_plain
    assert abs(onset_dipped - expected_rise_onset(bw, 3)) <= 1.0 / 1000 + 1e-9
    assert onset_dipped > 2.25  # after the dip, at the rise


def test_persistence_window_truncated_by_peak_raises():
    """A crossing less than persist_s before peak force cannot be
    verified as sustained within the search region -> OnsetError."""
    fs = 1000
    base = make_curve(fs)
    bw = calculate_bodyweight(base, WEIGH_START)
    threshold = bw['weight'] + 5 * bw['stddev']
    # choose the slope so the ramp crosses the threshold only 5 ms
    # before peak force (persist_s = 10 ms)
    slope = (PEAK - threshold) / 0.005
    curve = make_curve(fs, slope=slope)
    bw2 = calculate_bodyweight(curve, WEIGH_START)
    with pytest.raises(OnsetError):
        detect_onset_auto(bw2['df'], bw2['weight'], bw2['stddev'],
                          sd_multiplier=5)


def test_persistence_window_just_long_enough_succeeds():
    """Same construction with the crossing 15 ms before peak: sustained
    for >= persist_s, so onset is found."""
    fs = 1000
    base = make_curve(fs)
    bw = calculate_bodyweight(base, WEIGH_START)
    threshold = bw['weight'] + 5 * bw['stddev']
    slope = (PEAK - threshold) / 0.015
    curve = make_curve(fs, slope=slope)
    bw2 = calculate_bodyweight(curve, WEIGH_START)
    onset = detect_onset_auto(bw2['df'], bw2['weight'], bw2['stddev'],
                              sd_multiplier=5)
    t_star = RISE_START + (threshold - WEIGHT) / slope
    assert abs(onset - t_star) <= 1.0 / fs + 1e-9

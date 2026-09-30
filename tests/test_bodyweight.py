"""Bodyweight calculation tests (priority 3).

Expected values are frozen from the golden-master reference.
"""
from pathlib import Path

import pandas as pd
import pytest

from imtp.processing.bodyweight import calculate_bodyweight

FIXTURES = Path(__file__).resolve().parent / "data" / "fixtures"

# (fixture, weigh_start, expected weight, expected mass)
CASES = [
    ("hawkin.csv", 1.0, 845.0327097824013, 86.13992964142724),
    ("generic.csv", 1.0, 865.0327097824013, 88.17866562511736),
    ("pasco_left_right.csv", 1.0, 875.0327097824013, 89.1980336169624),
]


@pytest.mark.parametrize("fixture,weigh_start,weight,mass", CASES)
def test_calculate_bodyweight(fixture, weigh_start, weight, mass):
    data, _ = read_trial(fixture)
    bw = calculate_bodyweight(data, weigh_start)
    assert bw["weight"] == pytest.approx(weight, rel=1e-12)
    assert bw["mass"] == pytest.approx(mass, rel=1e-12)
    assert bw["stddev"] == pytest.approx(2.325565763742634, rel=1e-12)
    assert bw["sd3"] == pytest.approx(6.976697291227902, rel=1e-12)
    assert bw["wsd_pos3"] == pytest.approx(weight + 6.976697291227902,
                                           rel=1e-12)
    assert bw["wsd_neg3"] == pytest.approx(weight - 6.976697291227902,
                                           rel=1e-12)
    # Trim: nearest sample to the clicked time, data kept from there on
    assert bw["trim_idx"] == 1000
    assert len(bw["df"]) == len(data) - 1000
    assert bw["df"]["Time"].iloc[0] == pytest.approx(1.0)


def read_trial(fixture):
    import imtp.io
    trial = imtp.io.read_force_csv(FIXTURES / fixture)[0][0]
    return trial, None


def test_weighing_window_too_short_raises():
    data = pd.DataFrame({"Time": [0.0, 1.5], "Fz": [800.0, 800.0]})
    with pytest.raises(ValueError, match="fewer than 2 samples"):
        calculate_bodyweight(data, 1.5)


def test_weighing_window_duration_is_configurable():
    data, _ = read_trial("hawkin.csv")
    bw_half = calculate_bodyweight(data, 1.0, duration_s=0.5)
    assert bw_half["weight"] == pytest.approx(845.0, abs=1.0)
    # 0.5 s window at 1 kHz = 500 samples + the trim start sample
    assert isinstance(bw_half["weight"], float)

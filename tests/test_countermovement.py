"""Countermovement detection tests (priority 4).

Expected flags are frozen from the synthetic trial recipes and the
golden-master reference.
"""
from pathlib import Path

import pytest

from imtp.io import read_force_csv
from imtp.processing.bodyweight import calculate_bodyweight
from imtp.processing.countermovement import (detect_countermovement,
                                              up_to_peak)

FIXTURES = Path(__file__).resolve().parent / "data" / "fixtures"

# Multirun recipes: run 1 is flat (no pull); runs with a designed
# countermovement dip are True.
EXPECTED_MULTIRUN = [False, True, True, False, False,
                     True, False, True, False]
EXPECTED_DISTRACTOR = [False, True, False, True, False]


def _load(name, index=0):
    data, system = read_force_csv(FIXTURES / name)[index]
    return data, system


def test_countermovement_detected_hawkin():
    data, _ = _load("hawkin.csv")
    bw = calculate_bodyweight(data, 1.0)
    assert detect_countermovement(bw["df"], bw["weight"]) is True


def test_no_countermovement_generic():
    data, _ = _load("generic.csv")
    bw = calculate_bodyweight(data, 1.0)
    assert detect_countermovement(bw["df"], bw["weight"]) is False


@pytest.mark.parametrize("index,expected",
                         list(enumerate(EXPECTED_MULTIRUN)))
def test_countermovement_multirun(index, expected):
    data, _ = _load("pasco_multirun.csv", index)
    bw = calculate_bodyweight(data, 1.0)
    assert detect_countermovement(bw["df"], bw["weight"]) is expected


@pytest.mark.parametrize("index,expected",
                         list(enumerate(EXPECTED_DISTRACTOR)))
def test_countermovement_distractor(index, expected):
    data, _ = _load("pasco_distractor.csv", index)
    bw = calculate_bodyweight(data, 1.0)
    assert detect_countermovement(bw["df"], bw["weight"]) is expected


def test_threshold_is_configurable():
    data, _ = _load("hawkin.csv")
    bw = calculate_bodyweight(data, 1.0)
    # An enormous threshold can never be exceeded by the ~85 N dip
    assert detect_countermovement(bw["df"], bw["weight"],
                                  threshold_N=10000) is False


def test_up_to_peak_truncates_at_peak():
    data, _ = _load("generic.csv")
    bw = calculate_bodyweight(data, 1.0)
    df1 = up_to_peak(bw["df"])
    peak_idx = bw["df"]["Fz"].idxmax()
    assert df1.index[-1] == peak_idx
    assert (df1["Fz"] <= bw["df"]["Fz"].max()).all()

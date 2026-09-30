"""Onset utility tests (select_onset, trim_to_onset).

Expected values are frozen from the golden-master reference.
"""
from pathlib import Path

import numpy as np
import pytest

from imtp.io import read_force_csv
from imtp.processing.bodyweight import calculate_bodyweight
from imtp.processing.countermovement import up_to_peak
from imtp.processing.onset import (nearest_index, select_onset,
                                   trim_to_onset)

FIXTURES = Path(__file__).resolve().parent / "data" / "fixtures"


def _prepare(fixture, weigh_start, index=0):
    data, _ = read_force_csv(FIXTURES / fixture)[index]
    bw = calculate_bodyweight(data, weigh_start)
    df1 = up_to_peak(bw["df"])
    return data, df1


def test_select_onset_hawkin():
    data, df1 = _prepare("hawkin.csv", 1.0)
    onset_Fz, start = select_onset(data, df1, 3.5)
    assert onset_Fz == pytest.approx(813.88471850323, rel=1e-12)
    assert start == 3500


def test_select_onset_generic():
    data, df1 = _prepare("generic.csv", 1.0)
    onset_Fz, start = select_onset(data, df1, 4.0)
    assert onset_Fz == pytest.approx(865.7444582877381, rel=1e-12)
    assert start == 4000


def test_select_onset_onset_past_peak_flat_trial():
    """Edge case (run 1 of the multirun fixture is a flat trial): an
    onset chosen after the peak clamps to the last pre-peak sample,
    reproducing the original script's behaviour."""
    data, df1 = _prepare("pasco_multirun.csv", 1.0, index=0)
    _, start = select_onset(data, df1, 2.0)
    assert start == 2000


def test_trim_to_onset_hawkin():
    data, df1 = _prepare("hawkin.csv", 1.0)
    _, start = select_onset(data, df1, 3.5)
    df2 = trim_to_onset(df1, start)
    assert len(df2) == 1924
    # Fresh index from zero and normalised time from zero
    assert df2.index[0] == 0
    assert df2["ntime"].iloc[0] == 0.0
    assert (df2["ntime"] == df2["Time"] - df2["Time"].iloc[0]).all()


def test_nearest_index():
    values = np.array([0.0, 0.1, 0.2, 0.3])
    assert nearest_index(values, 0.14) == 1   # nearer to 0.1 than 0.2
    assert nearest_index(values, 0.24) == 2   # nearer to 0.2 than 0.3
    assert nearest_index(values, 0.09) == 1

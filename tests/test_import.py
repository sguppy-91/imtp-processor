"""Import layer tests.

Priority 1 and 2 of the test plan: PASCO and Hawkin Dynamics imports
(including edge cases) must reproduce the frozen reference behaviour.
"""
from pathlib import Path

import pandas as pd
import pytest

from imtp.io import read_force_csv

FIXTURES = Path(__file__).resolve().parent / "data" / "fixtures"


def test_hawkin_import():
    trials = read_force_csv(FIXTURES / "hawkin.csv")
    assert len(trials) == 1
    data, system = trials[0]
    assert system == "Hawkin Dynamics"
    # Pre-existing behaviour (preserved deliberately): Hawkin trials
    # keep the lFz/rFz channels rather than only Time/Fz.
    assert list(data.columns) == ["Time", "lFz", "rFz", "Fz"]
    assert len(data) == 7800
    assert data["Time"].iloc[0] == 0.0
    assert data["Time"].iloc[-1] == pytest.approx(7.799)


def test_pasco_multirun_import():
    trials = read_force_csv(FIXTURES / "pasco_multirun.csv")
    assert [system for _, system in trials] == \
        [f"PASCO Run #{i}" for i in range(1, 10)]
    expected_n = [4500, 8000, 7500, 9000, 8500, 9500, 8800, 9200, 8200]
    for (data, _), n in zip(trials, expected_n):
        # Shorter runs are padded with blanks in the export; dropna must
        # trim them so each trial has exactly its own samples.
        assert list(data.columns) == ["Time", "Fz"]
        assert len(data) == n


def test_pasco_preamble_import():
    trials = read_force_csv(FIXTURES / "pasco_preamble.csv")
    assert [system for _, system in trials] == ["PASCO Run #1",
                                                "PASCO Run #2"]
    for data, _ in trials:
        assert len(data) == 5001
        assert data["Time"].iloc[-1] == pytest.approx(5.0)


def test_pasco_left_right_sum():
    """With no combined Fz column, left and right channels are summed."""
    data, system = read_force_csv(FIXTURES / "pasco_left_right.csv")[0]
    assert system == "PASCO Run #1"
    assert list(data.columns) == ["Time", "Fz"]
    assert len(data) == 7900
    # Recipe value: bw=875 N + deterministic noise at t=0
    # (2.5*sin(0) + 1.8*sin(1.0) + 1.2*sin(2.0) = 2.6058 N)
    assert data["Fz"].iloc[0] == pytest.approx(877.606, abs=1e-2)


def test_pasco_distractor_columns():
    """Non-force columns (mass, hangtime, jump height...) must be ignored
    and the combined Fz channel preferred over 'weight (N)'."""
    trials = read_force_csv(FIXTURES / "pasco_distractor.csv")
    assert len(trials) == 5
    raw = pd.read_csv(FIXTURES / "pasco_distractor.csv")
    for i, (data, system) in enumerate(trials, start=1):
        assert system == f"PASCO Run #{i}"
        expected = raw[f"Fz (N) Run #{i}"].dropna()
        assert data["Fz"].to_numpy() == pytest.approx(
            expected.to_numpy())


def test_generic_import():
    data, system = read_force_csv(FIXTURES / "generic.csv")[0]
    assert system == "generic (Time (s) + Force (N))"
    assert list(data.columns) == ["Time", "Fz"]
    assert len(data) == 8300


def test_unrecognised_columns_raise(tmp_path):
    csv = tmp_path / "unknown.csv"
    csv.write_text("alpha,beta\n1,2\n3,4\n")
    with pytest.raises(ValueError, match="Could not identify"):
        read_force_csv(csv)


def test_pasco_short_run_raises(tmp_path):
    csv = tmp_path / "short.csv"
    csv.write_text('"Time (s) Run #1","Fz (N) Run #1"\n0.0,100.0\n')
    with pytest.raises(ValueError, match="fewer than 2 samples"):
        read_force_csv(csv)


def test_generic_short_trial_raises(tmp_path):
    csv = tmp_path / "short_generic.csv"
    csv.write_text("Time (s),Force (N)\n0.0,100.0\n")
    with pytest.raises(ValueError, match="fewer than 2 samples"):
        read_force_csv(csv)


def test_parser_error_preamble_retry(tmp_path):
    """A ragged pre-header block raises ParserError; the preamble scan
    must locate the real header row and retry past it."""
    csv = tmp_path / "parser_error.csv"
    csv.write_text(
        "junk,a,b\n"
        "1,2,3,4\n"
        '"Time (s) Run #1","Fz (N) Run #1"\n'
        "0.0,100.0\n"
        "0.001,100.0\n")
    trials = read_force_csv(csv)
    assert len(trials) == 1
    data, system = trials[0]
    assert system == "PASCO Run #1"
    assert len(data) == 2

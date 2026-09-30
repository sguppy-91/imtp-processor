"""Data model tests: IMTPTrial, IMTPResults, default_trial_label."""
from pathlib import Path

import pytest

from imtp.io import load_trial, read_force_csv
from imtp.models import IMTPResults, IMTPTrial
from imtp.models.trial import default_trial_label

FIXTURES = Path(__file__).resolve().parent / "data" / "fixtures"


@pytest.mark.parametrize("system,expected", [
    ("PASCO Run #3", "3"),
    ("PASCO Run #12", "12"),
    ("Hawkin Dynamics", ""),
    ("generic (Time (s) + Force (N))", ""),
])
def test_default_trial_label(system, expected):
    assert default_trial_label(system) == expected


def test_load_trial_multirun():
    trials = load_trial(FIXTURES / "pasco_multirun.csv")
    assert len(trials) == 9
    for i, trial in enumerate(trials, start=1):
        assert isinstance(trial, IMTPTrial)
        assert trial.system == f"PASCO Run #{i}"
        assert trial.trial == str(i)          # run-number default
        assert trial.participant == ""        # metadata left to workflow
        assert trial.session == ""


def test_load_trial_matches_read_force_csv():
    trials = load_trial(FIXTURES / "hawkin.csv")
    data, system = read_force_csv(FIXTURES / "hawkin.csv")[0]
    assert trials[0].data.equals(data)
    assert trials[0].system == system
    assert trials[0].trial == ""             # single-trial system


def test_trial_metadata_is_mutable():
    trial = IMTPTrial(data=None, system="PASCO Run #1")
    trial.participant = "P001"
    trial.session = "T1"
    trial.trial = "1"
    assert (trial.participant, trial.session, trial.trial) == \
        ("P001", "T1", "1")


def test_results_dataclass_fields():
    r = IMTPResults(peak_force=1500.0, f50=10.0, f100=100.0,
                    f150=200.0, f200=300.0, f250=400.0)
    assert r.peak_force == 1500.0
    assert r.f250 == 400.0

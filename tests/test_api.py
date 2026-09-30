"""Public API tests.

The documented surface must stay small and stable, and analyse_trial
must reproduce the analyst workflow's metrics exactly.
"""
import json
from pathlib import Path

import pytest

import golden_master as gm  # the harness (on sys.path via conftest)
import imtp
from imtp import (IMTPResults, IMTPTrial, analyse_trial,
                  calculate_bodyweight, calculate_force_metrics,
                  detect_countermovement, load_trial, read_force_csv)

DATA_DIR = Path(__file__).resolve().parent / "data"
EXPECTED_SURFACE = {
    "IMTPResults",
    "IMTPTrial",
    "analyse_trial",
    "calculate_bodyweight",
    "calculate_force_metrics",
    "detect_countermovement",
    "load_trial",
    "read_force_csv",
}


def test_public_api_surface():
    assert set(imtp.__all__) == EXPECTED_SURFACE
    for name in imtp.__all__:
        assert hasattr(imtp, name), name
    assert imtp.__version__ == "1.1.0"


@pytest.mark.parametrize("case_id", sorted(gm.PARAMS))
def test_analyse_trial_reproduces_workflow(case_id, golden):
    """analyse_trial on weighing-trimmed data must reproduce the frozen
    golden metrics exactly (the GUI workflow's own calculation chain)."""
    path, idx = gm.collect_sources()[case_id]
    data, _ = read_force_csv(path)[idx]
    params = gm.PARAMS[case_id]
    expected = golden["trials"][case_id]["pipeline"]

    bw = calculate_bodyweight(data, params["weigh_start"])
    results = analyse_trial(bw["df"], bw["weight"], params["onset_time"])

    assert isinstance(results, IMTPResults)
    for field in ("peak_force", "f50", "f100", "f150", "f200", "f250"):
        assert getattr(results, field) == pytest.approx(
            expected[field], rel=1e-12), field


@pytest.mark.parametrize("case_id", ["hawkin", "generic",
                                     "pasco_multirun_r3"])
def test_analyse_trial_accepts_full_trial_data(case_id):
    """Documented guarantee: for real pulls (peak force after the
    weighing phase), full-trial input gives identical results to
    weighing-trimmed input."""
    path, idx = gm.collect_sources()[case_id]
    data, _ = read_force_csv(path)[idx]
    params = gm.PARAMS[case_id]
    bw = calculate_bodyweight(data, params["weigh_start"])
    from_trimmed = analyse_trial(bw["df"], bw["weight"], params["onset_time"])
    from_full = analyse_trial(data, bw["weight"], params["onset_time"])
    for field in ("peak_force", "f50", "f100", "f150", "f200", "f250"):
        assert getattr(from_full, field) == pytest.approx(
            getattr(from_trimmed, field), rel=1e-12), field


def test_public_api_programmatic_flow():
    """The whole GUI-free flow works through public names only:
    import -> bodyweight -> screening -> analysis."""
    trial, = load_trial(DATA_DIR / "fixtures" / "hawkin.csv")
    trial.participant, trial.session, trial.trial = "P001", "T1", "1"
    assert isinstance(trial, IMTPTrial)

    bw = calculate_bodyweight(trial.data, 1.0)
    assert detect_countermovement(bw["df"], bw["weight"]) is True
    results = analyse_trial(bw["df"], bw["weight"], onset_time=3.5)
    assert results.peak_force == pytest.approx(1540.3753126330405,
                                               rel=1e-12)

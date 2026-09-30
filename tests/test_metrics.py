"""Force metric calculation tests (priority 5).

Expected values are frozen from the golden-master reference; scientific
outputs must remain unchanged by the refactor.
"""
from pathlib import Path

import pytest

from imtp.io import read_force_csv
from imtp.models import IMTPResults
from imtp.processing.bodyweight import calculate_bodyweight
from imtp.processing.countermovement import up_to_peak
from imtp.processing.metrics import calculate_force_metrics
from imtp.processing.onset import select_onset, trim_to_onset

FIXTURES = Path(__file__).resolve().parent / "data" / "fixtures"


def _analyse(fixture, weigh_start, onset_time, index=0):
    data, _ = read_force_csv(FIXTURES / fixture)[index]
    bw = calculate_bodyweight(data, weigh_start)
    df1 = up_to_peak(bw["df"])
    _, start = select_onset(data, df1, onset_time)
    df2 = trim_to_onset(df1, start)
    return calculate_force_metrics(df2, bw["weight"])


def test_metrics_hawkin():
    r = _analyse("hawkin.csv", 1.0, 3.5)
    assert isinstance(r, IMTPResults)
    assert r.peak_force == pytest.approx(1540.3753126330405, rel=1e-12)
    assert r.f50 == pytest.approx(-0.45819396727654293, rel=1e-12)
    assert r.f100 == pytest.approx(159.90292367270206, rel=1e-12)
    assert r.f150 == pytest.approx(299.3999299037582, rel=1e-12)
    assert r.f200 == pytest.approx(501.5062378082598, rel=1e-12)
    assert r.f250 == pytest.approx(769.2701841751168, rel=1e-12)


def test_metrics_generic():
    r = _analyse("generic.csv", 1.0, 4.0)
    assert r.peak_force == pytest.approx(1660.3752253470045, rel=1e-12)
    assert r.f100 == pytest.approx(175.37131317260514, rel=1e-12)
    assert r.f250 == pytest.approx(829.0054625962664, rel=1e-12)


def test_metrics_pasco_multirun_run3():
    r = _analyse("pasco_multirun.csv", 1.0, 3.4, index=2)
    assert r.peak_force == pytest.approx(1645.3753126806857, rel=1e-12)
    assert r.f250 == pytest.approx(822.6516272572146, rel=1e-12)


def test_metrics_flat_trial_edge_case():
    """Run 1 of the multirun fixture has no pull: the onset sits past
    the peak, so all metrics collapse to near-zero noise around the
    single remaining sample (the original script's behaviour for flat
    trials, seen in real results files)."""
    r = _analyse("pasco_multirun.csv", 1.0, 2.0, index=0)
    assert r.peak_force == pytest.approx(5.390668235724661, rel=1e-12)
    assert r.f50 == pytest.approx(3.675506738311583, rel=1e-12)
    assert r.f100 == pytest.approx(-3.8985377824119496, rel=1e-12)
    assert abs(r.peak_force) < 10.0

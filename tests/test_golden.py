"""Golden-master regression tests.

Runs the extracted package pipeline against the frozen golden results
(tests/data/golden_results.json) for every fixture trial: any
behavioural drift in the analysis engine is caught at float precision.

The reference data was generated from the original monolithic script
(tag v1-monolith) with fixed analyst decisions; see
tools/golden_master.py for how it is produced and regenerated.
"""
import os
import subprocess
import sys
from pathlib import Path

import pytest

import golden_master as gm  # the harness (on sys.path via conftest)
from imtp.io import read_force_csv

REPO = Path(__file__).resolve().parents[1]
CASES = sorted(gm.PARAMS)


@pytest.mark.parametrize("case_id", CASES)
def test_package_pipeline_matches_golden(case_id, golden):
    path, trial_idx = gm.collect_sources()[case_id]
    data, system = read_force_csv(path)[trial_idx]
    expected = golden["trials"][case_id]
    assert system == expected["system"]

    pkg = gm.run_package_pipeline(data, **gm.PARAMS[case_id])
    failures = gm.compare(case_id, expected["pipeline"], pkg)
    assert not failures, "\n".join(failures)


def test_golden_fixture_files_exist():
    for path, _ in gm.collect_sources().values():
        assert path.exists(), f"missing fixture: {path}"


def test_monolith_delegates_to_workflow():
    """The launcher must delegate to the analyst workflow, not carry a
    duplicate copy of it."""
    import imtp.workflows.analyst as wf
    monolith = gm.load_monolith()
    assert monolith.run is wf.run


def test_core_imports_headless():
    """Architecture guard: importing io, processing, models and export
    in a fresh interpreter must not pull in any GUI, plotting or
    windowing dependency (the batch/automation use case)."""
    probe = (
        "import sys, importlib\n"
        "for name in ('imtp', 'imtp.io', 'imtp.processing', 'imtp.models',\n"
        "             'imtp.export', 'imtp.workflows.batch'):\n"
        "    importlib.import_module(name)\n"
        "bad = [m for m in sys.modules if m.startswith('imtp.gui')]\n"
        "assert not bad, f'core pulled in GUI: {bad}'\n"
        "assert 'PySimpleGUI' not in sys.modules\n"
        "assert 'matplotlib' not in sys.modules\n"
    )
    env = dict(os.environ, PYTHONPATH=str(REPO / "src"))
    result = subprocess.run([sys.executable, "-c", probe], env=env,
                            capture_output=True, text=True)
    assert result.returncode == 0, result.stderr

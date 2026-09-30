"""CLI tests.

`imtp` launches the analyst workflow; --help/--version must work
headless without any GUI dependency.
"""
import os
import subprocess
import sys
from pathlib import Path

import pytest

from imtp.cli import main

REPO = Path(__file__).resolve().parents[1]


def test_version_flag(capsys):
    with pytest.raises(SystemExit) as exc:
        main(["--version"])
    assert exc.value.code == 0
    assert "imtp 1.0.0" in capsys.readouterr().out


def test_help_flag(capsys):
    with pytest.raises(SystemExit) as exc:
        main(["--help"])
    assert exc.value.code == 0
    assert "usage" in capsys.readouterr().out.lower()


def test_main_launches_analyst_workflow(monkeypatch):
    import imtp.workflows.analyst as wf
    calls = []
    monkeypatch.setattr(wf, "run", lambda: calls.append(1))
    main([])  # must not raise; the real GUI run() is patched out
    assert calls == [1]


def test_cli_works_headless():
    """--version must succeed in a fresh interpreter with no GUI,
    plotting or windowing modules imported (core-only install)."""
    probe = (
        "import sys\n"
        "import imtp.cli\n"
        "assert 'PySimpleGUI' not in sys.modules\n"
        "assert 'matplotlib' not in sys.modules\n"
        "imtp.cli.main(['--version'])\n"
    )
    env = dict(os.environ, PYTHONPATH=str(REPO / "src"))
    result = subprocess.run([sys.executable, "-c", probe], env=env,
                            capture_output=True, text=True)
    assert result.returncode == 0, result.stderr


def test_installed_entry_point_version():
    """The installed `imtp` command (pip install -e .) reports its
    version."""
    result = subprocess.run(["imtp", "--version"],
                            capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    assert "imtp 1.0.0" in result.stdout

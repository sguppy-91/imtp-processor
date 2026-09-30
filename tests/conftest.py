"""Shared test configuration.

Puts the in-repo package (src/) and the golden-master harness (tools/)
on sys.path so the suite tests the repository source with or without an
editable install, and reuses the harness for golden regression tests.
"""
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]

for p in (REPO / "src", REPO / "tools"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

import pytest

DATA_DIR = Path(__file__).resolve().parent / "data"
FIXTURES = DATA_DIR / "fixtures"
GOLDEN_JSON = DATA_DIR / "golden_results.json"


@pytest.fixture(scope="session")
def golden():
    """The frozen golden-master reference results."""
    return json.loads(GOLDEN_JSON.read_text())

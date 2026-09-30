"""IMTP analysis script — analyst GUI entry point.

Thin launcher: the analysis engine and the analyst workflow live in the
imtp package (src/imtp/). Works with the package installed
(pip install -e ".[gui]") or straight from the repository. Run with:

    python IMTP_Analysis_Script.py
"""
import sys
from pathlib import Path

try:
    from imtp.workflows.analyst import run
except ImportError:
    # Package not installed: fall back to the in-repo copy under src/.
    sys.path.insert(0, str(Path(__file__).resolve().parent / 'src'))
    from imtp.workflows.analyst import run

if __name__ == '__main__':
    run()

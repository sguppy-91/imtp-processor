"""IMTP analysis script — analyst GUI entry point.

Thin launcher: the analysis engine and the analyst workflow now live in
the imtp package (src/imtp/). Run with:

    python IMTP_Analysis_Script.py
"""
import sys
from pathlib import Path

# Temporary path shim so the in-repo package (src/imtp) is importable
# before the project becomes pip-installable (a later refactor phase).
sys.path.insert(0, str(Path(__file__).resolve().parent / 'src'))

# Importing the workflow (via imtp.gui) selects the matplotlib backend
# and applies the PySimpleGUI theme, as the original script did at
# import time.
from imtp.workflows.analyst import run

if __name__ == '__main__':
    run()

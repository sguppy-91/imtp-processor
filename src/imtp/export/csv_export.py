"""CSV export of force-time results.

Output formatting and file writing only; no calculations, no GUI.
"""
import os

import numpy as np
import pandas as pd


def results_frame(trial, results):
    """Build the one-row results DataFrame in the export schema.

    Verbatim from the v1-monolith script's main() (force-variable
    DataFrame build and 1-decimal rounding), taking its values from an
    IMTPTrial's metadata and an IMTPResults.
    """
    force_vars = {
        'Participant': [trial.participant],
        'Session': [trial.session],
        'Trial': [trial.trial],
        'Variable': ['Net Force'],
        'Peak': [results.peak_force],
        '50 ms': [results.f50],
        '100 ms': [results.f100],
        '150 ms': [results.f150],
        '200 ms': [results.f200],
        '250 ms': [results.f250],
    }
    df3 = pd.DataFrame.from_dict(force_vars)
    df3 = np.round(df3, decimals=1)
    return df3


def append_csv(results_file, results):
    """Append a results DataFrame to the results CSV.

    Verbatim from the v1-monolith script's main(): the header row is
    written only when the file does not yet exist or is empty.
    """
    if os.path.exists(results_file):
        content = open(results_file, 'r', encoding='utf-8-sig').read().strip()
        write_header = len(content) == 0
    else:
        write_header = True
    results.to_csv(results_file, mode='a', header=write_header, index=False)

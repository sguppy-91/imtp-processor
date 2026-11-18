"""CSV export of force-time results.

Output formatting and file writing only; no calculations, no GUI.

Schema v2 appends an audit trail after the original columns: the onset
method and the parameters it was computed from are recorded per trial,
so an unrecorded method is impossible by construction.
"""
import os
from dataclasses import dataclass

import numpy as np
import pandas as pd

# Audit columns appended after the original export columns (schema v2).
AUDIT_COLUMNS = [
    'OnsetMethod',      # 'manual', 'bw+3sd' or 'bw+5sd'
    'OnsetTime_s',      # analyst selection (manual) or computed (automated)
    'WeighStart_s',     # analyst-selected weighing-start time
    'Bodyweight_N',     # mean force over the weighing window
    'BW_SD_N',          # SD of the weighing window
    'OnsetThreshold_N', # Bodyweight_N + multiplier x BW_SD_N (empty for manual)
]


@dataclass
class AuditRecord:
    """Per-trial audit trail for the exported row (internal API).

    Built by the workflow from the values it already has: the session's
    onset method, the onset time actually used, the weighing-start time,
    and the bodyweight statistics the threshold was derived from.
    `onset_threshold_n` is None for manual rows (no threshold applies).
    """
    onset_method: str
    onset_time_s: float
    weigh_start_s: float
    bodyweight_n: float
    bw_sd_n: float
    onset_threshold_n: float | None


class SchemaMismatchError(Exception):
    """The results file's header does not match the outgoing schema."""


def results_frame(trial, results, audit=None):
    """Build the one-row results DataFrame in the export schema.

    Verbatim from the v1-monolith script's main() (force-variable
    DataFrame build and 1-decimal rounding), taking its values from an
    IMTPTrial's metadata and an IMTPResults. With an `audit` AuditRecord
    the six audit columns are appended after the original ones (schema
    v2, what the workflow writes); without one the frame keeps the
    original v1 columns exactly (kept for the golden-master harness).
    The original columns keep their names, order and rounding either way.
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
    if audit is not None:
        force_vars.update({
            'OnsetMethod': [audit.onset_method],
            'OnsetTime_s': [audit.onset_time_s],
            'WeighStart_s': [audit.weigh_start_s],
            'Bodyweight_N': [audit.bodyweight_n],
            'BW_SD_N': [audit.bw_sd_n],
            'OnsetThreshold_N': [audit.onset_threshold_n],
        })
    df3 = pd.DataFrame.from_dict(force_vars)
    df3 = np.round(df3, decimals=1)
    return df3


def append_csv(results_file, results):
    """Append a results DataFrame to the results CSV.

    Verbatim from the v1-monolith script's main(): the header row is
    written only when the file does not yet exist or is empty. Schema
    guard: if the existing header differs from the outgoing frame's
    columns, nothing is appended and SchemaMismatchError is raised —
    v1 and v2 rows are never mixed silently in one file.
    """
    if os.path.exists(results_file):
        with open(results_file, 'r', encoding='utf-8-sig') as f:
            content = f.read().strip()
        write_header = len(content) == 0
        if not write_header:
            existing_header = content.splitlines()[0]
            outgoing_header = ','.join(results.columns)
            if existing_header != outgoing_header:
                raise SchemaMismatchError(
                    f'results file {results_file} has a different header '
                    f'than the outgoing schema — not appending. '
                    f'Expected: {outgoing_header}. '
                    f'Found: {existing_header}.')
    else:
        write_header = True
    results.to_csv(results_file, mode='a', header=write_header, index=False)

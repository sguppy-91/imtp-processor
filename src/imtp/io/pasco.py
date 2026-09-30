"""PASCO force-plate CSV import.

PASCO exports one column group per recorded run, labelled 'Run #N'
(e.g. 'Fz (N) Run #3'). Shorter runs are padded with blank cells, and
some exports put a few metadata lines before the header row.
"""
import re

import pandas as pd

PASCO_RUN_TOKEN = re.compile(r'\bRun #(?P<run>\d+)\b')


def _split_column(col):
    """Split a 'Name Run #N' column into (run number, base name), else None.

    The 'Run #N' token is matched anywhere in the column name, so both
    suffix ('Time (s) Run #1') and prefix ('Run #1 Time (s)') layouts work.
    """
    m = PASCO_RUN_TOKEN.search(str(col))
    if not m:
        return None
    base = PASCO_RUN_TOKEN.sub('', str(col)).strip()
    return int(m.group('run')), base


def _is_force_name(name):
    """True when a column name looks like a vertical-force measurement."""
    low = name.strip().lower()
    return ('force' in low or 'fz' in low or 'combined' in low
            or 'total' in low or low.endswith('(n)'))


def _is_combined_force_name(name):
    """True when a column already holds the combined (e.g. left+right) force."""
    low = name.strip().lower()
    return low.startswith('fz') or 'combined' in low or 'total' in low


def run_columns(columns):
    """Map run number -> (time column, force columns) for PASCO exports.

    A combined force column (e.g. 'Fz (N)') is preferred when present;
    otherwise every force-looking column in the run is returned so their
    sum can be used (e.g. separate left/right plate channels).
    """
    global_tcol = None
    groups = {}
    for col in columns:
        col = str(col)
        split = _split_column(col)
        if split is None:
            if global_tcol is None and 'time' in col.lower():
                global_tcol = col
            continue
        run, base = split
        groups.setdefault(run, []).append((col, base))

    resolved = {}
    for run, entries in sorted(groups.items()):
        tcol = next((c for c, b in entries if 'time' in b.lower()),
                    global_tcol)
        if tcol is None:
            continue
        forces = [(c, b) for c, b in entries
                  if c != tcol and _is_force_name(b)]
        if not forces:
            continue
        combined = next((c for c, b in forces
                         if _is_combined_force_name(b)), None)
        resolved[run] = (tcol, [combined] if combined
                         else [c for c, _ in forces])
    return resolved


def preamble_rows(csv_file, max_scan=25):
    """Count metadata rows before a PASCO header line, or None if none.

    Some PASCO exports start with run/file metadata lines; the real
    header is the first line naming both a run and a time column.
    """
    with open(csv_file, encoding='utf-8-sig', errors='replace') as f:
        for i, line in enumerate(f):
            if i >= max_scan:
                break
            low = line.lower()
            if 'run #' in low and 'time' in low and ',' in low:
                return i if i else None
    return None


def extract_trials(df, runs):
    """Build one (data, 'PASCO Run #N') trial per resolved run."""
    trials = []
    for run in sorted(runs):
        tcol, fcols = runs[run]
        sub = df[[tcol] + fcols].dropna()
        data = pd.DataFrame({'Time': sub[tcol].to_numpy(),
                             'Fz': sub[fcols].sum(axis=1).to_numpy()})
        if len(data) < 2:
            raise ValueError(f'PASCO run {run} has fewer than 2 samples')
        trials.append((data, f'PASCO Run #{run}'))
    return trials

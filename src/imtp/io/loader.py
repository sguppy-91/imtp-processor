"""Force-plate CSV import dispatcher.

Known export layouts are sniffed from the header and mapped to canonical
column names (Time, Fz); unrecognised files fall back to a generic
time/force column search, so a new plate system usually needs no code
change to be read. Everything downstream only uses Time and Fz.
"""
import pandas as pd

from . import generic, hawkin, pasco


def read_force_csv(csv_file):
    """Read a force-plate CSV export into canonical Time/Fz DataFrames.

    Returns a list of (data, system_name) trials — one entry for most
    exports, one per run for multi-run PASCO exports. Raises ValueError
    when no time and vertical force columns can be identified.
    """
    # Some PASCO exports start with metadata lines that break a naive
    # read; locate the real header row and start from there instead.
    try:
        df = pd.read_csv(csv_file, encoding='utf-8-sig')
        columns = [str(c) for c in df.columns]
    except pd.errors.ParserError:
        skip = pasco.preamble_rows(csv_file)
        if skip is None:
            raise
        df = pd.read_csv(csv_file, encoding='utf-8-sig', skiprows=skip)
        columns = [str(c) for c in df.columns]

    # Hawkin Dynamics export
    trials = hawkin.read_trials(df, columns)
    if trials:
        return trials

    # PASCO export: one trial per 'Run #N' column group. A header may
    # still sit below preamble lines that happen to parse cleanly, so
    # retry past them when no run columns are found.
    runs = pasco.run_columns(columns)
    if not runs:
        skip = pasco.preamble_rows(csv_file)
        if skip:
            df = pd.read_csv(csv_file, encoding='utf-8-sig', skiprows=skip)
            columns = [str(c) for c in df.columns]
            runs = pasco.run_columns(columns)
    if runs:
        return pasco.extract_trials(df, runs)

    # Unknown system: best-guess time and force columns
    trials = generic.read_trials(df, columns)
    if trials:
        return trials

    raise ValueError(
        f'Could not identify time and force columns. Found: {columns}')

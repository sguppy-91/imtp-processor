"""Onset selection utilities.

Currently only the resolution of an analyst-chosen (manual) onset time.
Designed for future expansion: automatic_onset(), threshold_onset(),
sd_method_onset().
"""
import numpy as np


def nearest_index(values, target):
    """Index of the sample nearest to `target`."""
    return (np.abs(values - target)).argmin()


def select_onset(data, df1, onset_time):
    """Resolve a chosen onset time to (onset_Fz, start_index).

    `data` is the full trial (Time/Fz); `df1` is the force data up to
    peak force, within which the onset must sit. `start_index` is a
    pandas index label into `df1`. Verbatim from the v1-monolith
    script's main().
    """
    time_values = data.Time.values
    onset_Fz = data['Fz'].iloc[nearest_index(time_values, onset_time)]
    start = df1.index[nearest_index(df1['Time'].values, onset_time)]
    return onset_Fz, start


def trim_to_onset(df1, start):
    """Trim `df1` from the onset index and add normalised time (`ntime`).

    Verbatim from the v1-monolith script's main() (force-time curve
    trimming). Returns a fresh DataFrame indexed from 0 with an added
    `ntime` column (seconds from onset).
    """
    df2 = df1.truncate(before=start).reset_index()
    df2['ntime'] = df2['Time'] - df2['Time'].iloc[0]
    return df2

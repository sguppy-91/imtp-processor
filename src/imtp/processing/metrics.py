"""Force-time metric calculations — the scientific core.

No plotting, no GUI, no import and no export logic in this module.
"""
import numpy as np


def calculate_force_metrics(df2, bodyweight):
    """Net force metrics from onset-trimmed data.

    `df2` must carry `Time`, `Fz` and `ntime` (seconds from onset), as
    produced by processing.onset.trim_to_onset. Force at specific points
    is found by time in ms, not sample index (verbatim from the
    v1-monolith script's main()).

    Returns a dict with peak_force (maximum net force above bodyweight)
    and f50/f100/f150/f200/f250 (net force at fixed times after onset).
    """
    net_Force = df2['Fz'] - bodyweight
    Peak_Force = net_Force.max()

    # Calculating Force at Specific Points (by time in ms, not sample index)
    ntime_values = df2['ntime'].values
    def force_at_ms(ms):
        idx = np.abs(ntime_values - ms / 1000).argmin()
        return net_Force.iloc[idx]
    return {
        'peak_force': Peak_Force,
        'f50': force_at_ms(50),
        'f100': force_at_ms(100),
        'f150': force_at_ms(150),
        'f200': force_at_ms(200),
        'f250': force_at_ms(250),
    }

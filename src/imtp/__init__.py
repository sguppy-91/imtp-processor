"""IMTP analysis package.

Isometric mid-thigh pull (IMTP) force-time analysis: data import,
scientific calculations, GUI, export and workflow orchestration.

The public API is intentionally small; these names are documented,
tested and stable:

    from imtp import read_force_csv, load_trial       # import
    from imtp import calculate_bodyweight             # weighing phase
    from imtp import detect_countermovement           # screening
    from imtp import analyse_trial                     # one-call analysis
    from imtp import calculate_force_metrics          # metrics only
    from imtp import IMTPTrial, IMTPResults           # data objects

Everything else lives in submodules and may change without notice.
"""
from .io import load_trial, read_force_csv
from .models import IMTPResults, IMTPTrial
from .processing.bodyweight import calculate_bodyweight
from .processing.countermovement import (detect_countermovement,
                                         up_to_peak)
from .processing.metrics import calculate_force_metrics
from .processing.onset import select_onset, trim_to_onset

__version__ = "1.1.0"

__all__ = [
    "IMTPResults",
    "IMTPTrial",
    "analyse_trial",
    "calculate_bodyweight",
    "calculate_force_metrics",
    "detect_countermovement",
    "load_trial",
    "read_force_csv",
]


def analyse_trial(force_data, bodyweight, onset_time):
    """Analyse one IMTP trial with a known bodyweight and onset time.

    Convenience wrapper for the analyst workflow's calculation chain:
    finds the onset sample, trims the force-time curve from it and
    returns the force-time variables. Performs no GUI interaction and
    makes no decisions beyond the ones given.

    Args:
        force_data: canonical Time/Fz force data, ideally from the
            weighing start onward (as the analyst workflow uses, e.g.
            the ``df`` from calculate_bodyweight). Full-trial data gives
            identical results whenever the peak force occurs after the
            weighing phase, i.e. for any real pull.
        bodyweight: estimated bodyweight in newtons (e.g. the ``weight``
            from calculate_bodyweight).
        onset_time: force onset in seconds, identified manually by the
            analyst (the reference methodology, by design).

    Returns:
        IMTPResults with peak_force and f50/f100/f150/f200/f250 (net
        force above bodyweight, in newtons).
    """
    df1 = up_to_peak(force_data)
    _, start = select_onset(force_data, df1, onset_time)
    df2 = trim_to_onset(df1, start)
    return calculate_force_metrics(df2, bodyweight)

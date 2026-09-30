"""Countermovement screening for the IMTP pull."""

# Force dip below bodyweight (N) that flags a countermovement.
# Preserves the original script's Weight - 50 N threshold exactly.
DEFAULT_THRESHOLD_N = 50


def up_to_peak(df):
    """Force data truncated at the sample of peak force.

    Verbatim from the v1-monolith script's main(): the countermovement
    screen and the manual onset search both operate on the segment up
    to peak force.
    """
    Fzmax = df.Fz.idxmax()
    return df.truncate(after=Fzmax)


def detect_countermovement(df, bodyweight, threshold_N=DEFAULT_THRESHOLD_N):
    """True when force dips more than `threshold_N` below bodyweight
    at any point before peak force (verbatim Weight - 50 N test).
    """
    df1 = up_to_peak(df)
    a = bodyweight - threshold_N
    return bool((df1['Fz'] < a).any())

"""Hawkin Dynamics force-plate CSV import."""

HAWKIN_COLUMNS = {'Time': 'Time (s)', 'lFz': 'Left (N)',
                  'rFz': 'Right (N)', 'Fz': 'Combined (N)'}


def read_trials(df, columns):
    """Return the Hawkin Dynamics trial, or None when the layout doesn't match."""
    if all(c in columns for c in HAWKIN_COLUMNS.values()):
        data = df[list(HAWKIN_COLUMNS.values())].copy()
        data.columns = list(HAWKIN_COLUMNS)
        return [(data, 'Hawkin Dynamics')]
    return None

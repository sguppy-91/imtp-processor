"""Generic fallback import for unknown force-plate CSV layouts."""


def _find_columns(columns):
    """Best-guess (time, force) column names for an unknown export."""
    tcol = next((c for c in columns if 'time' in c.lower()), None)
    if tcol is None:
        return None
    others = [c for c in columns if c != tcol]
    fzcol = next((c for c in others
                  if 'combined' in c.lower() or c.lower().startswith('fz')),
                 None) \
        or next((c for c in others
                 if 'force' in c.lower() and '(n)' in c.lower()), None) \
        or next((c for c in others if '(n)' in c.lower()), None)
    if fzcol is None:
        return None
    return tcol, fzcol


def read_trials(df, columns):
    """Return a single best-guess trial, or None when nothing matches."""
    generic = _find_columns(columns)
    if not generic:
        return None
    tcol, fzcol = generic
    data = df[[tcol, fzcol]].dropna().copy()
    data.columns = ['Time', 'Fz']
    if len(data) < 2:
        raise ValueError(f'fewer than 2 samples in {tcol}/{fzcol}')
    return [(data, f'generic ({tcol} + {fzcol})')]

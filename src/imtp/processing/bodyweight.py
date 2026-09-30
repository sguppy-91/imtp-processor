"""Bodyweight estimation from the analyst-selected weighing phase."""
import numpy as np

# Duration of the weighing phase averaged for body weight. Time-based so
# the window is identical at any sampling rate (a fixed sample count
# would only be 1 s at exactly 1000 Hz).
WEIGH_WINDOW_S = 1.0


def calculate_bodyweight(data, weigh_start, duration_s=WEIGH_WINDOW_S):
    """Estimate bodyweight from a fixed weighing window.

    `weigh_start` is the analyst-selected start of the weighing phase in
    seconds; the nearest sample is used (verbatim from the v1-monolith
    script's main()).

    Returns a dict with:
      df        force data trimmed from the weighing start onward
      trim_idx  index of the weighing-start sample in `data`
      weight    mean force over the weighing window (N)
      mass      weight / 9.81 (kg)
      stddev    standard deviation of the weighing window
      sd3       3 x stddev
      wsd_pos3  weight + sd3 (upper screening bound)
      wsd_neg3  weight - sd3 (lower screening bound)
    """
    # Clicked x-coordinate is the trim time in seconds; nearest sample
    trim_idx = int((np.abs(data.Time.values - weigh_start)).argmin())
    df = data.iloc[trim_idx:]
    weigh = df[df['Time'] <= df['Time'].iloc[0] + duration_s]['Fz']
    if len(weigh) < 2:
        raise ValueError('fewer than 2 samples in the weighing window')
    Weight = weigh.mean()
    Mass = Weight / 9.81
    stddev = weigh.std()
    SD3 = stddev * 3
    return {
        'df': df,
        'trim_idx': trim_idx,
        'weight': Weight,
        'mass': Mass,
        'stddev': stddev,
        'sd3': SD3,
        'wsd_pos3': Weight + SD3,
        'wsd_neg3': Weight - SD3,
    }

"""Weighing-phase selection plot."""
import matplotlib.pyplot as plt


def select_weighing_start(data):
    """Plot the trial and let the analyst click the start of the
    weighing phase (GUI verbatim from the v1-monolith script's main()).

    Returns the clicked x-coordinate (time in seconds), or None when
    the plot is closed without a selection.
    """
    plt.plot(data.Time, data.Fz)
    plt.title('Click the start of the weighing phase')
    plt.xlabel('Time (s)')
    plt.ylabel('Force (N)')
    plt.grid(True, alpha=0.3)
    clicked = plt.ginput(1, timeout=-1)
    plt.close('all')
    if not clicked:
        return None
    return clicked[0][0]

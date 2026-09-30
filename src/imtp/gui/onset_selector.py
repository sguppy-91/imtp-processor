"""Onset selection with a draggable vertical line."""
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.widgets import Button


def select_onset_time(data, wsd_neg3, wsd_pos3):
    """Show the force curve with a draggable onset line (GUI verbatim
    from the v1-monolith script's main()).

    Drag the red line (or click anywhere) to move it; the Save button
    confirms; closing the window also works. Returns the chosen onset
    time in seconds, snapped to the nearest sample time.
    """
    fig, ax = plt.subplots()
    fig.subplots_adjust(bottom=0.18)
    ax.plot(data.Time, data.Fz)
    ax.axhline(y=wsd_neg3, color='k', linestyle='--', label='3 SD')
    ax.axhline(y=wsd_pos3, color='k', linestyle='--')
    ax.set_title("Drag the red line to the onset point, then click Save")
    ax.set_xlabel("Time (s)")
    ax.set_ylabel("Force (N)")

    time_values = data.Time.values
    initial_x = time_values[len(time_values) // 2]
    vline = ax.axvline(x=initial_x, color='r', linestyle='-', linewidth=2, label='Onset')
    onset_time = [initial_x]
    dragging = [False]
    time_text = ax.text(0.02, 0.95, f"Onset: {initial_x:.3f} s", transform=ax.transAxes, fontsize=11, color='r', va='top')

    def on_press(event):
        if event.inaxes != ax or event.xdata is None:
            return
        xline = vline.get_xdata()[0]
        grab_radius = (ax.get_xlim()[1] - ax.get_xlim()[0]) * 0.05
        if abs(event.xdata - xline) < grab_radius:
            dragging[0] = True
        else:
            # Click away from line: jump line to clicked position
            nearest_idx = np.abs(time_values - event.xdata).argmin()
            new_x = time_values[nearest_idx]
            vline.set_xdata([new_x, new_x])
            onset_time[0] = new_x
            time_text.set_text(f"Onset: {new_x:.3f} s")
            fig.canvas.draw_idle()

    def on_release(event):
        dragging[0] = False

    def on_motion(event):
        if not dragging[0] or event.inaxes != ax or event.xdata is None:
            return
        nearest_idx = np.abs(time_values - event.xdata).argmin()
        new_x = time_values[nearest_idx]
        vline.set_xdata([new_x, new_x])
        onset_time[0] = new_x
        time_text.set_text(f"Onset: {new_x:.3f} s")
        fig.canvas.draw_idle()

    fig.canvas.mpl_connect('button_press_event', on_press)
    fig.canvas.mpl_connect('button_release_event', on_release)
    fig.canvas.mpl_connect('motion_notify_event', on_motion)

    # Save button: confirms the onset and continues processing.
    # Closing the window still works as a fallback.
    save_ax = fig.add_axes([0.81, 0.03, 0.16, 0.06])
    save_btn = Button(save_ax, 'Save')

    def on_save(event):
        plt.close(fig)

    save_btn.on_clicked(on_save)

    plt.show()
    return onset_time[0]

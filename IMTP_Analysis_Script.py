import os
import sys
from pathlib import Path
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('MacOSX')
import matplotlib.pyplot as plt
from matplotlib.widgets import Button
import PySimpleGUI as sg

sg.theme('DarkTeal6')

# Temporary path shim so the in-repo package (src/imtp) is importable
# before the project becomes pip-installable (a later refactor phase).
sys.path.insert(0, str(Path(__file__).resolve().parent / 'src'))

from imtp.io import load_trial
from imtp.processing.bodyweight import (WEIGH_WINDOW_S,
                                         calculate_bodyweight)
from imtp.processing.countermovement import (detect_countermovement,
                                              up_to_peak)
from imtp.processing.onset import select_onset, trim_to_onset
from imtp.processing.metrics import calculate_force_metrics

# WEIGH_WINDOW_S is re-exported for backward compatibility (external
# callers and the golden-master harness read it from this module).



def main():
    # Select results file once at startup
    results_file = sg.popup_get_file('Select results file to append to (or type a new name)',
                                     title='Results File', save_as=True,
                                     file_types=(('CSV Files', '*.csv'),))
    if results_file:
        if not results_file.endswith('.csv'):
            results_file += '.csv'

    # Main processing loop — repeat until user cancels CSV selection
    last_participant = ''
    last_session = ''
    while True:
        csv_file = sg.popup_get_file('Select a CSV File', title='File Selector',
                                    file_types=(('CSV Files', '*.csv'),))
        if not csv_file:
            break

        # Read the selected CSV file into trials (multi-run exports
        # yield one trial per run)
        try:
            trials = load_trial(csv_file)
        except Exception as e:
            sg.popup_error(f"Error reading CSV file: {str(e)}")
            continue

        for trial_obj in trials:
            # Per-trial error handling: one bad trial (bad click, odd
            # data) closes any open plots and skips to the next trial
            # instead of killing the whole session.
            try:
                data = trial_obj.data
                system = trial_obj.system
                print(f"Imported {system} data: {csv_file}")

                # Enter participant metadata for this trial
                participant = sg.popup_get_text('Enter participant code (e.g. P001)', title='Participant',
                                               default_text=last_participant)
                if participant is None:
                    break
                last_participant = participant
                trial_obj.participant = participant
                session = sg.popup_get_text('Enter session (e.g. T1)', title='Session',
                                            default_text=last_session)
                if session is None:
                    break
                last_session = session
                trial_obj.session = session
                trial = sg.popup_get_text('Enter trial number (e.g. 1)', title='Trial',
                                          default_text=trial_obj.trial)
                if trial is None:
                    break
                trial_obj.trial = trial

                # Create Graph to be Inspected — click the start of the weighing phase
                plt.plot(data.Time, data.Fz)
                plt.title('Click the start of the weighing phase')
                plt.xlabel('Time (s)')
                plt.ylabel('Force (N)')
                plt.grid(True, alpha=0.3)
                clicked = plt.ginput(1, timeout=-1)
                plt.close('all')
                if not clicked:
                    sg.popup_error('No point selected - skipping this trial.')
                    continue

                # Determining Weight & Beginning of Testing
                # Clicked x-coordinate is the trim time in seconds; nearest sample
                bw = calculate_bodyweight(data, clicked[0][0])
                df = bw['df']
                Weight = bw['weight']
                Mass = bw['mass']
                WSD_pos3 = bw['wsd_pos3']
                WSD_neg3 = bw['wsd_neg3']
                # To Detect a Countermovement
                df1 = up_to_peak(df)
                if detect_countermovement(df, Weight):
                    sg.popup_error('Countermovement detected')
                else:
                    sg.popup('No countermovement detected')

                # Create a plot with a draggable vertical line for onset selection
                fig, ax = plt.subplots()
                fig.subplots_adjust(bottom=0.18)
                ax.plot(data.Time, data.Fz)
                ax.axhline(y=WSD_neg3, color='k', linestyle='--', label='3 SD')
                ax.axhline(y=WSD_pos3, color='k', linestyle='--')
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

                onset_Fz, start = select_onset(data, df1, onset_time[0])
                print(f"onset_time = {onset_time[0]}")
                print(f"onset_Fz = {onset_Fz}")

                # Trimming Force-Time Curve
                df2 = trim_to_onset(df1, start)

                # Calculating force-time variables
                results_obj = calculate_force_metrics(df2, Weight)
                Peak_Force = results_obj.peak_force
                F50 = results_obj.f50
                F100 = results_obj.f100
                F150 = results_obj.f150
                F200 = results_obj.f200
                F250 = results_obj.f250

                # Create DataFrame for Force Variables
                force_vars = {
                    'Participant': [participant],
                    'Session': [session],
                    'Trial': [trial],
                    'Variable': ['Net Force'],
                    'Peak': [Peak_Force],
                    '50 ms': [F50],
                    '100 ms': [F100],
                    '150 ms': [F150],
                    '200 ms': [F200],
                    '250 ms': [F250],
                }
                df3 = pd.DataFrame.from_dict(force_vars)
                df3 = np.round(df3, decimals=1)

                # Display results
                results_str = df3.to_string(index=False)
                print(results_str)
                sg.popup(results_str, title='Force Variables')

                # Append results to the results file chosen at startup
                if results_file:
                    if os.path.exists(results_file):
                        content = open(results_file, 'r', encoding='utf-8-sig').read().strip()
                        write_header = len(content) == 0
                    else:
                        write_header = True
                    df3.to_csv(results_file, mode='a', header=write_header, index=False)
                    print(f'Results appended to {results_file}')
                    sg.popup(f'Results appended to {results_file}', title='Results Saved')

                plt.close('all')
            except Exception as e:
                plt.close('all')
                sg.popup_error(f"Error processing {system}: {str(e)}")
                continue


if __name__ == '__main__':
    main()

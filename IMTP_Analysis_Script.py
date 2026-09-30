import os
import sys
from pathlib import Path
import pandas as pd
import numpy as np

# Temporary path shim so the in-repo package (src/imtp) is importable
# before the project becomes pip-installable (a later refactor phase).
sys.path.insert(0, str(Path(__file__).resolve().parent / 'src'))

# Importing the gui package selects the matplotlib backend and applies
# the PySimpleGUI theme (as the original script did at import time), so
# it must be imported before matplotlib.pyplot.
from imtp.gui import (enter_metadata, select_onset_time,
                      select_weighing_start)

import matplotlib.pyplot as plt
import PySimpleGUI as sg

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
                last_participant, last_session, entered = enter_metadata(
                    trial_obj, last_participant, last_session)
                if not entered:
                    break

                # Create Graph to be Inspected — click the start of the weighing phase
                weigh_start = select_weighing_start(data)
                if weigh_start is None:
                    sg.popup_error('No point selected - skipping this trial.')
                    continue

                # Determining Weight & Beginning of Testing
                # Clicked x-coordinate is the trim time in seconds; nearest sample
                bw = calculate_bodyweight(data, weigh_start)
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

                # Select the force onset with the draggable-line plot
                onset = select_onset_time(data, WSD_neg3, WSD_pos3)

                onset_Fz, start = select_onset(data, df1, onset)
                print(f"onset_time = {onset}")
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
                    'Participant': [trial_obj.participant],
                    'Session': [trial_obj.session],
                    'Trial': [trial_obj.trial],
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

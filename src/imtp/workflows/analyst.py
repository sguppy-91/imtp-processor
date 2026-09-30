"""Analyst-in-the-loop workflow.

Replicates the original script's main() exactly: select a results file,
then for each selected CSV and each trial enter metadata, select the
weighing phase, screen for a countermovement, select the onset, and
append the force-time variables to the results CSV.

This is the GUI orchestration layer: it gathers analyst decisions from
imtp.gui, delegates every calculation to imtp.processing, imports
through imtp.io and writes outputs via imtp.export.
"""
import matplotlib.pyplot as plt
import PySimpleGUI as sg

from ..export.csv_export import append_csv, results_frame
from ..gui import (enter_metadata, select_onset_time,
                   select_weighing_start)
from ..io import load_trial
from ..processing.bodyweight import calculate_bodyweight
from ..processing.countermovement import (detect_countermovement,
                                          up_to_peak)
from ..processing.metrics import calculate_force_metrics
from ..processing.onset import select_onset, trim_to_onset


def run():
    """Run the analyst-in-the-loop workflow (the original main())."""
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

                # Create DataFrame for Force Variables
                df3 = results_frame(trial_obj, results_obj)

                # Display results
                results_str = df3.to_string(index=False)
                print(results_str)
                sg.popup(results_str, title='Force Variables')

                # Append results to the results file chosen at startup
                if results_file:
                    append_csv(results_file, df3)
                    print(f'Results appended to {results_file}')
                    sg.popup(f'Results appended to {results_file}', title='Results Saved')

                plt.close('all')
            except Exception as e:
                plt.close('all')
                sg.popup_error(f"Error processing {system}: {str(e)}")
                continue

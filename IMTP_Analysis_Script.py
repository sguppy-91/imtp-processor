import os
import re
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('MacOSX')
import matplotlib.pyplot as plt
from matplotlib.widgets import Button
import PySimpleGUI as sg

sg.theme('DarkTeal6')

# ---------------------------------------------------------------------------
# Force-plate system agnostic CSV import
# ---------------------------------------------------------------------------
# Known export layouts are sniffed from the header and mapped to canonical
# column names (Time, Fz); unrecognised files fall back to a generic
# time/force column search, so a new plate system usually needs no code
# change to be read. Everything downstream only uses Time and Fz.

# PASCO exports one column group per recorded run, labelled 'Run #N'
# (e.g. 'Fz (N) Run #3'). Shorter runs are padded with blank cells, and
# some exports put a few metadata lines before the header row.
PASCO_RUN_TOKEN = re.compile(r'\bRun #(?P<run>\d+)\b')

HAWKIN_COLUMNS = {'Time': 'Time (s)', 'lFz': 'Left (N)',
                  'rFz': 'Right (N)', 'Fz': 'Combined (N)'}


def _pasco_split_column(col):
    """Split a 'Name Run #N' column into (run number, base name), else None.

    The 'Run #N' token is matched anywhere in the column name, so both
    suffix ('Time (s) Run #1') and prefix ('Run #1 Time (s)') layouts work.
    """
    m = PASCO_RUN_TOKEN.search(str(col))
    if not m:
        return None
    base = PASCO_RUN_TOKEN.sub('', str(col)).strip()
    return int(m.group('run')), base


def _is_force_name(name):
    """True when a column name looks like a vertical-force measurement."""
    low = name.strip().lower()
    return ('force' in low or 'fz' in low or 'combined' in low
            or 'total' in low or low.endswith('(n)'))


def _is_combined_force_name(name):
    """True when a column already holds the combined (e.g. left+right) force."""
    low = name.strip().lower()
    return low.startswith('fz') or 'combined' in low or 'total' in low


def _pasco_run_columns(columns):
    """Map run number -> (time column, force columns) for PASCO exports.

    A combined force column (e.g. 'Fz (N)') is preferred when present;
    otherwise every force-looking column in the run is returned so their
    sum can be used (e.g. separate left/right plate channels).
    """
    global_tcol = None
    groups = {}
    for col in columns:
        col = str(col)
        split = _pasco_split_column(col)
        if split is None:
            if global_tcol is None and 'time' in col.lower():
                global_tcol = col
            continue
        run, base = split
        groups.setdefault(run, []).append((col, base))

    resolved = {}
    for run, entries in sorted(groups.items()):
        tcol = next((c for c, b in entries if 'time' in b.lower()),
                    global_tcol)
        if tcol is None:
            continue
        forces = [(c, b) for c, b in entries
                  if c != tcol and _is_force_name(b)]
        if not forces:
            continue
        combined = next((c for c, b in forces
                         if _is_combined_force_name(b)), None)
        resolved[run] = (tcol, [combined] if combined
                         else [c for c, _ in forces])
    return resolved


def _pasco_preamble_rows(csv_file, max_scan=25):
    """Count metadata rows before a PASCO header line, or None if none.

    Some PASCO exports start with run/file metadata lines; the real
    header is the first line naming both a run and a time column.
    """
    with open(csv_file, encoding='utf-8-sig', errors='replace') as f:
        for i, line in enumerate(f):
            if i >= max_scan:
                break
            low = line.lower()
            if 'run #' in low and 'time' in low and ',' in low:
                return i if i else None
    return None


def _generic_columns(columns):
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


def read_force_csv(csv_file):
    """Read a force-plate CSV export into canonical Time/Fz DataFrames.

    Returns a list of (data, system_name) trials — one entry for most
    exports, one per run for multi-run PASCO exports. Raises ValueError
    when no time and vertical force columns can be identified.
    """
    # Some PASCO exports start with metadata lines that break a naive
    # read; locate the real header row and start from there instead.
    try:
        df = pd.read_csv(csv_file, encoding='utf-8-sig')
        columns = [str(c) for c in df.columns]
    except pd.errors.ParserError:
        skip = _pasco_preamble_rows(csv_file)
        if skip is None:
            raise
        df = pd.read_csv(csv_file, encoding='utf-8-sig', skiprows=skip)
        columns = [str(c) for c in df.columns]

    # Hawkin Dynamics export
    if all(c in columns for c in HAWKIN_COLUMNS.values()):
        data = df[list(HAWKIN_COLUMNS.values())].copy()
        data.columns = list(HAWKIN_COLUMNS)
        return [(data, 'Hawkin Dynamics')]

    # PASCO export: one trial per 'Run #N' column group. A header may
    # still sit below preamble lines that happen to parse cleanly, so
    # retry past them when no run columns are found.
    pasco = _pasco_run_columns(columns)
    if not pasco:
        skip = _pasco_preamble_rows(csv_file)
        if skip:
            df = pd.read_csv(csv_file, encoding='utf-8-sig', skiprows=skip)
            columns = [str(c) for c in df.columns]
            pasco = _pasco_run_columns(columns)
    if pasco:
        trials = []
        for run in sorted(pasco):
            tcol, fcols = pasco[run]
            sub = df[[tcol] + fcols].dropna()
            data = pd.DataFrame({'Time': sub[tcol].to_numpy(),
                                 'Fz': sub[fcols].sum(axis=1).to_numpy()})
            if len(data) < 2:
                raise ValueError(f'PASCO run {run} has fewer than 2 samples')
            trials.append((data, f'PASCO Run #{run}'))
        return trials

    # Unknown system: best-guess time and force columns
    generic = _generic_columns(columns)
    if generic:
        tcol, fzcol = generic
        data = df[[tcol, fzcol]].dropna().copy()
        data.columns = ['Time', 'Fz']
        if len(data) < 2:
            raise ValueError(f'fewer than 2 samples in {tcol}/{fzcol}')
        return [(data, f'generic ({tcol} + {fzcol})')]

    raise ValueError(
        f'Could not identify time and force columns. Found: {columns}')

# Duration of the weighing phase averaged for body weight. Time-based so
# the window is identical at any sampling rate (a fixed sample count
# would only be 1 s at exactly 1000 Hz).
WEIGH_WINDOW_S = 1.0


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

        # Read the selected CSV file into canonical Time/Fz trials
        # (multi-run exports yield one trial per run)
        try:
            trials = read_force_csv(csv_file)
        except Exception as e:
            sg.popup_error(f"Error reading CSV file: {str(e)}")
            continue

        for data, system in trials:
            # Per-trial error handling: one bad trial (bad click, odd
            # data) closes any open plots and skips to the next trial
            # instead of killing the whole session.
            try:
                print(f"Imported {system} data: {csv_file}")
                trial_default = system.split('Run #')[-1] if 'Run #' in system else ''

                # Enter participant metadata for this trial
                participant = sg.popup_get_text('Enter participant code (e.g. P001)', title='Participant',
                                               default_text=last_participant)
                if participant is None:
                    break
                last_participant = participant
                session = sg.popup_get_text('Enter session (e.g. T1)', title='Session',
                                            default_text=last_session)
                if session is None:
                    break
                last_session = session
                trial = sg.popup_get_text('Enter trial number (e.g. 1)', title='Trial',
                                          default_text=trial_default)
                if trial is None:
                    break

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
                trim_idx = int((np.abs(data.Time.values - clicked[0][0])).argmin())
                df = data.iloc[trim_idx:]
                weigh = df[df['Time'] <= df['Time'].iloc[0] + WEIGH_WINDOW_S]['Fz']
                if len(weigh) < 2:
                    raise ValueError('fewer than 2 samples in the weighing window')
                Weight = weigh.mean()
                Mass = Weight / 9.81
                stddev = weigh.std()
                SD3 = stddev * 3
                WSD_pos3 = Weight + SD3
                WSD_neg3 = Weight - SD3
                # To Detect a Countermovement
                Fzmax = df.Fz.idxmax()
                df1 = df.truncate(after=Fzmax)
                a = Weight - 50
                if (df1['Fz'] < a).any():
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

                onset_Fz = data['Fz'].iloc[(np.abs(time_values - onset_time[0])).argmin()]
                print(f"onset_time = {onset_time[0]}")
                print(f"onset_Fz = {onset_Fz}")

                start = df1.index[(np.abs(df1['Time'].values - onset_time[0])).argmin()]

                # Trimming Force-Time Curve
                df2 = df1.truncate(before=start).reset_index()
                df2['ntime'] = df2['Time'] - df2['Time'].iloc[0]

                # Calculating Peak Force variables
                df2['net_Force'] = df2['Fz'] - Weight
                Peak_Force = df2['net_Force'].max()

                # Calculating Force at Specific Points (by time in ms, not sample index)
                ntime_values = df2['ntime'].values
                def force_at_ms(ms):
                    idx = np.abs(ntime_values - ms / 1000).argmin()
                    return df2['net_Force'].iloc[idx]
                F50 = force_at_ms(50)
                F100 = force_at_ms(100)
                F150 = force_at_ms(150)
                F200 = force_at_ms(200)
                F250 = force_at_ms(250)

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

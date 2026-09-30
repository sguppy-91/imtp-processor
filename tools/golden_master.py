"""Golden-master harness for the IMTP refactor (Phase 0).

Runs the current monolithic script's import and analysis pipeline with
fixed, recorded inputs (replacing the GUI interactions) and captures
every intermediate value and result. The saved output is the behavioural
reference that every refactor phase must reproduce.

The calculation blocks below are copied VERBATIM from IMTP_Analysis_Script.py
(tag v1-monolith) with exactly two substitutions: the ginput weighing click
becomes the fixed `weigh_start` parameter, and the draggable onset line
becomes the fixed `onset_time` parameter. Do not "improve" the copied code
here; its job is to freeze current behaviour, quirks included.

All fixtures are FULLY SYNTHETIC (deterministic force curves built from
closed-form math, no RNG), so no real participant data enters the repo.

Usage:
    python tools/golden_master.py                 # regenerate golden files
    python tools/golden_master.py --make-fixtures # (re)build synthetic CSVs
    python tools/golden_master.py --check         # compare against saved goldens
"""

import argparse
import hashlib
import importlib.util
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / "IMTP_Analysis_Script.py"
GOLDEN_DIR = REPO / "tools" / "golden"
FIXTURE_DIR = GOLDEN_DIR / "fixtures"
GOLDEN_JSON = GOLDEN_DIR / "golden_results.json"

# Make the in-repo package importable (mirrors the monolith's shim).
sys.path.insert(0, str(REPO / "src"))

# ---------------------------------------------------------------------------
# Synthetic force-curve generation (deterministic, closed-form; no RNG)
# ---------------------------------------------------------------------------

FS = 1000.0  # sampling rate (Hz)


def _noise(t):
    """Deterministic 'sensor noise' from mixed sinusoids."""
    return (2.5 * np.sin(2 * np.pi * 11.3 * t)
            + 1.8 * np.sin(2 * np.pi * 29.7 * t + 1.0)
            + 1.2 * np.sin(2 * np.pi * 53.1 * t + 2.0))


def synth_trial(bw, duration, t_on=None, peak=None, countermovement=False):
    """Synthetic IMTP force-time curve.

    Quiet standing at `bw` N for the first seconds, then (optionally) a
    sigmoid-shaped pull to `peak` N starting at `t_on`, preceded by an
    optional countermovement dip below bodyweight.
    """
    t = np.arange(0.0, duration, 1.0 / FS)
    fz = np.full_like(t, bw) + _noise(t)
    if t_on is not None:
        rise = (peak - bw) / (1.0 + np.exp(-(t - t_on - 0.15) / 0.07))
        rise[t < t_on] = 0.0
        fz += rise
        if countermovement:
            dip = -85.0 * np.sin(
                np.pi * (t - (t_on - 0.45)) / 0.4)
            mask = (t >= t_on - 0.45) & (t <= t_on - 0.05)
            fz[mask] += dip[mask]
    return pd.DataFrame({"Time": t, "Fz": fz})


# Trial recipes: (bw, duration, t_on, peak, countermovement)
MULTIRUN = [
    (830, 4.5, None, None, False),          # r1: flat, no pull (edge case)
    (850, 8.0, 3.9, 2450, True),
    (860, 7.5, 3.5, 2500, True),
    (840, 9.0, 4.2, 2350, False),
    (870, 8.5, 3.3, 2550, False),
    (835, 9.5, 4.5, 2400, True),
    (825, 8.8, 3.8, 2600, False),
    (855, 9.2, 4.9, 2450, True),
    (820, 8.2, 4.3, 2300, False),
]
DISTRACTOR = [  # extra non-force columns, like CMJ-style exports
    (800, 6.5, 3.5, 2200, False),
    (810, 6.5, 3.7, 2250, True),
    (820, 6.5, 3.9, 2300, False),
    (830, 6.5, 4.1, 2350, True),
    (840, 6.5, 4.3, 2400, False),
]
HAWKIN = (845, 7.8, 3.6, 2380, True)
GENERIC = (865, 8.3, 4.1, 2520, False)
LEFT_RIGHT = (875, 7.9, 3.4, 2470, True)
PREAMBLE = [  # sliced to <= 5.0 s in the fixture
    (850, 5.5, 3.9, 2450, True),
    (860, 5.5, 3.5, 2500, True),
]

# Fixed analyst decisions per case. weigh_start is always 1.000 s; onset
# was derived once from the synthetic data (first crossing of Weight+50 N
# after 2 s, minus 100 ms; flat trial -> 2.0 s) and hard-coded so the
# harness is fully deterministic.
PARAMS = {
    "pasco_multirun_r1": {"weigh_start": 1.0, "onset_time": 2.000},
    "pasco_multirun_r2": {"weigh_start": 1.0, "onset_time": 3.800},
    "pasco_multirun_r3": {"weigh_start": 1.0, "onset_time": 3.400},
    "pasco_multirun_r4": {"weigh_start": 1.0, "onset_time": 4.100},
    "pasco_multirun_r5": {"weigh_start": 1.0, "onset_time": 3.200},
    "pasco_multirun_r6": {"weigh_start": 1.0, "onset_time": 4.400},
    "pasco_multirun_r7": {"weigh_start": 1.0, "onset_time": 3.700},
    "pasco_multirun_r8": {"weigh_start": 1.0, "onset_time": 4.800},
    "pasco_multirun_r9": {"weigh_start": 1.0, "onset_time": 4.200},
    "pasco_distractor_r1": {"weigh_start": 1.0, "onset_time": 3.400},
    "pasco_distractor_r2": {"weigh_start": 1.0, "onset_time": 3.600},
    "pasco_distractor_r3": {"weigh_start": 1.0, "onset_time": 3.800},
    "pasco_distractor_r4": {"weigh_start": 1.0, "onset_time": 4.000},
    "pasco_distractor_r5": {"weigh_start": 1.0, "onset_time": 4.200},
    "hawkin": {"weigh_start": 1.0, "onset_time": 3.500},
    "generic": {"weigh_start": 1.0, "onset_time": 4.000},
    "pasco_left_right": {"weigh_start": 1.0, "onset_time": 3.300},
    "pasco_preamble_r1": {"weigh_start": 1.0, "onset_time": 3.800},
    "pasco_preamble_r2": {"weigh_start": 1.0, "onset_time": 3.400},
}


# ---------------------------------------------------------------------------
# Fixture builders
# ---------------------------------------------------------------------------

def make_fixtures():
    """Write the synthetic CSV fixtures."""
    FIXTURE_DIR.mkdir(parents=True, exist_ok=True)

    def pasco_frame(runs):
        """Multi-run PASCO layout; shorter runs padded with blank cells."""
        cols = {}
        n = max(len(d) for d, _ in runs)
        for i, (data, _) in enumerate(runs, start=1):
            pad = data.reindex(range(n))
            cols[f"Time (s) Run #{i}"] = pad["Time"].values
            cols[f"Right, Ch 2 (N) Run #{i}"] = pad["Fz"].values / 2
            cols[f"Left, Ch 1 (N) Run #{i}"] = pad["Fz"].values / 2
            cols[f"Fz (N) Run #{i}"] = pad["Fz"].values
        return pd.DataFrame(cols)

    # 9-run PASCO export, combined Fz preferred per run
    pasco_frame([(synth_trial(*r), None) for r in MULTIRUN]).to_csv(
        FIXTURE_DIR / "pasco_multirun.csv", index=False)

    # PASCO layout with distractor columns (only combined Fz is force-like)
    runs = [synth_trial(*r) for r in DISTRACTOR]
    n = max(len(d) for d in runs)
    cols = {}
    for i, d in enumerate(runs, start=1):
        pad = d.reindex(range(n))
        cols[f"Time (s) Run #{i}"] = pad["Time"].values
        cols[f"Right, Ch 2 (N) Run #{i}"] = pad["Fz"].values / 2
        cols[f"Left, Ch 1 (N) Run #{i}"] = pad["Fz"].values / 2
        cols[f"Fz (N) Run #{i}"] = pad["Fz"].values
        cols[f"weight (N) Run #{i}"] = pad["Fz"].values
        cols[f"test (units) Run #{i}"] = 0.0
        cols[f"hangtime (s) Run #{i}"] = 0.0
        cols[f"mass (kg) Run #{i}"] = 100.0
        cols[f"Jump Height (cm) Run #{i}"] = 0.0
    pd.DataFrame(cols).to_csv(
        FIXTURE_DIR / "pasco_distractor.csv", index=False)

    # Hawkin Dynamics layout (exact HAWKIN_COLUMNS header names)
    d = synth_trial(*HAWKIN)
    pd.DataFrame({
        "Time (s)": d["Time"],
        "Left (N)": d["Fz"] / 2,
        "Right (N)": d["Fz"] / 2,
        "Combined (N)": d["Fz"],
    }).to_csv(FIXTURE_DIR / "hawkin.csv", index=False)

    # Generic unknown layout
    d = synth_trial(*GENERIC)
    pd.DataFrame({"Time (s)": d["Time"], "Force (N)": d["Fz"]}).to_csv(
        FIXTURE_DIR / "generic.csv", index=False)

    # PASCO with NO combined Fz column -> left/right must be summed
    d = synth_trial(*LEFT_RIGHT)
    pd.DataFrame({
        "Time (s) Run #1": d["Time"],
        "Right, Ch 2 (N) Run #1": d["Fz"] / 2,
        "Left, Ch 1 (N) Run #1": d["Fz"] / 2,
    }).to_csv(FIXTURE_DIR / "pasco_left_right.csv", index=False)

    # PASCO with metadata preamble lines and two runs
    frame = pasco_frame([
        (synth_trial(*PREAMBLE[0]).pipe(
            lambda x: x[x["Time"] <= 5.0]), None),
        (synth_trial(*PREAMBLE[1]).pipe(
            lambda x: x[x["Time"] <= 5.0]), None),
    ])
    with open(FIXTURE_DIR / "pasco_preamble.csv", "w") as f:
        f.write("PASCO Capstone Export\n")
        f.write("Sample Rate: 1000.0 Hz\n")
        frame.to_csv(f, index=False)


def collect_sources():
    """Map case-id -> (fixture path, trial index within that file's trials)."""
    sources = {}
    for i in range(1, 10):
        sources[f"pasco_multirun_r{i}"] = (FIXTURE_DIR / "pasco_multirun.csv", i - 1)
    for i in range(1, 6):
        sources[f"pasco_distractor_r{i}"] = (FIXTURE_DIR / "pasco_distractor.csv", i - 1)
    sources["hawkin"] = (FIXTURE_DIR / "hawkin.csv", 0)
    sources["generic"] = (FIXTURE_DIR / "generic.csv", 0)
    sources["pasco_left_right"] = (FIXTURE_DIR / "pasco_left_right.csv", 0)
    sources["pasco_preamble_r1"] = (FIXTURE_DIR / "pasco_preamble.csv", 0)
    sources["pasco_preamble_r2"] = (FIXTURE_DIR / "pasco_preamble.csv", 1)
    return sources


def trial_idx_of(case_id):
    """Trial index (within its fixture file) for a golden case-id."""
    return collect_sources()[case_id][1]


# ---------------------------------------------------------------------------
# Verbatim calculation pipeline (frozen copy of v1-monolith main())
# ---------------------------------------------------------------------------

def load_monolith():
    spec = importlib.util.spec_from_file_location("monolith", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def data_fingerprint(data):
    """Stable content fingerprint of a canonical Time/Fz DataFrame."""
    return hashlib.md5(data.to_csv(index=False).encode()).hexdigest()


def run_pipeline(data, weigh_start, onset_time):
    """Verbatim copy of the calculation blocks in main()
    (v1-monolith lines 253-260, 262-270, 337-360, 362-376), with the GUI
    click (weighing) and dragged line (onset) replaced by fixed values.
    """
    # --- Determining Weight & Beginning of Testing (verbatim) ---
    # Clicked x-coordinate is the trim time in seconds; nearest sample
    trim_idx = int((np.abs(data.Time.values - weigh_start)).argmin())
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

    # --- To Detect a Countermovement (verbatim) ---
    Fzmax = df.Fz.idxmax()
    df1 = df.truncate(after=Fzmax)
    a = Weight - 50
    countermovement = bool((df1['Fz'] < a).any())

    # --- Onset selection values (verbatim) ---
    time_values = data.Time.values
    onset_Fz = data['Fz'].iloc[(np.abs(time_values - onset_time)).argmin()]
    start = df1.index[(np.abs(df1['Time'].values - onset_time)).argmin()]

    # --- Trimming Force-Time Curve (verbatim) ---
    df2 = df1.truncate(before=start).reset_index()
    df2['ntime'] = df2['Time'] - df2['Time'].iloc[0]

    # --- Calculating Peak Force variables (verbatim) ---
    df2['net_Force'] = df2['Fz'] - Weight
    Peak_Force = df2['net_Force'].max()

    # --- Calculating Force at Specific Points (verbatim) ---
    ntime_values = df2['ntime'].values
    def force_at_ms(ms):
        idx = np.abs(ntime_values - ms / 1000).argmin()
        return df2['net_Force'].iloc[idx]
    F50 = force_at_ms(50)
    F100 = force_at_ms(100)
    F150 = force_at_ms(150)
    F200 = force_at_ms(200)
    F250 = force_at_ms(250)

    # --- Create DataFrame for Force Variables (verbatim, incl. rounding) ---
    force_vars = {
        'Participant': ['GOLDEN'],
        'Session': ['G0'],
        'Trial': ['1'],
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
    rounded_row = df3.iloc[0].to_dict()

    return {
        "trim_idx": trim_idx,
        "weight": float(Weight),
        "mass": float(Mass),
        "stddev": float(stddev),
        "sd3": float(SD3),
        "wsd_pos3": float(WSD_pos3),
        "wsd_neg3": float(WSD_neg3),
        "countermovement": countermovement,
        "fzmax_index": int(Fzmax),
        "onset_fz": float(onset_Fz),
        "start_index": int(start),
        "n_df2": int(len(df2)),
        "peak_force": float(Peak_Force),
        "f50": float(F50),
        "f100": float(F100),
        "f150": float(F150),
        "f200": float(F200),
        "f250": float(F250),
        "export_row": {k: str(v) for k, v in rounded_row.items()},
    }


def _export_row(peak_force, f50, f100, f150, f200, f250):
    """The monolith's results-DataFrame build + rounding (verbatim)."""
    force_vars = {
        'Participant': ['GOLDEN'],
        'Session': ['G0'],
        'Trial': ['1'],
        'Variable': ['Net Force'],
        'Peak': [peak_force],
        '50 ms': [f50],
        '100 ms': [f100],
        '150 ms': [f150],
        '200 ms': [f200],
        '250 ms': [f250],
    }
    df3 = pd.DataFrame.from_dict(force_vars)
    df3 = np.round(df3, decimals=1)
    return {k: str(v) for k, v in df3.iloc[0].to_dict().items()}


def run_package_pipeline(data, weigh_start, onset_time):
    """Same pipeline as run_pipeline, but through the extracted imtp
    package. This is the system under test from Phase 1 onward: it must
    reproduce the frozen goldens exactly."""
    from imtp.io import read_force_csv  # noqa: F401  (import sanity)
    from imtp.models import IMTPResults, IMTPTrial
    from imtp.processing.bodyweight import calculate_bodyweight
    from imtp.processing.countermovement import (detect_countermovement,
                                                 up_to_peak)
    from imtp.processing.onset import select_onset, trim_to_onset
    from imtp.processing.metrics import calculate_force_metrics

    trial = IMTPTrial(data=data, system='golden')
    bw = calculate_bodyweight(trial.data, weigh_start)
    df = bw['df']
    countermovement = detect_countermovement(df, bw['weight'])
    df1 = up_to_peak(df)
    onset_Fz, start = select_onset(trial.data, df1, onset_time)
    df2 = trim_to_onset(df1, start)
    m = calculate_force_metrics(df2, bw['weight'])
    if not isinstance(m, IMTPResults):
        raise TypeError(f"calculate_force_metrics returned {type(m)}, "
                        "expected IMTPResults")
    return {
        "trim_idx": bw['trim_idx'],
        "weight": float(bw['weight']),
        "mass": float(bw['mass']),
        "stddev": float(bw['stddev']),
        "sd3": float(bw['sd3']),
        "wsd_pos3": float(bw['wsd_pos3']),
        "wsd_neg3": float(bw['wsd_neg3']),
        "countermovement": countermovement,
        "fzmax_index": int(df.Fz.idxmax()),
        "onset_fz": float(onset_Fz),
        "start_index": int(start),
        "n_df2": int(len(df2)),
        "peak_force": float(m.peak_force),
        "f50": float(m.f50),
        "f100": float(m.f100),
        "f150": float(m.f150),
        "f200": float(m.f200),
        "f250": float(m.f250),
        "export_row": _export_row(m.peak_force, m.f50, m.f100,
                                  m.f150, m.f200, m.f250),
    }


# ---------------------------------------------------------------------------
# Generate / check
# ---------------------------------------------------------------------------

def _read_all(monolith=None):
    """Yield case-id, path, data, system using the package import layer."""
    from imtp.io import read_force_csv
    for case_id, (path, trial_idx) in collect_sources().items():
        trials = read_force_csv(path)
        data, system = trials[trial_idx]
        yield case_id, path, data, system


def generate():
    monolith = load_monolith()
    global WEIGH_WINDOW_S
    WEIGH_WINDOW_S = monolith.WEIGH_WINDOW_S

    make_fixtures()

    results = {"trials": {}}
    for case_id, path, data, system in _read_all(monolith):
        entry = {
            "source": str(path.relative_to(REPO)),
            "system": system,
            "n_samples": int(len(data)),
            "time_first": float(data["Time"].iloc[0]),
            "time_last": float(data["Time"].iloc[-1]),
            "fingerprint": data_fingerprint(data),
            "params": dict(PARAMS[case_id]),
            "pipeline": run_pipeline(data, **PARAMS[case_id]),
        }
        results["trials"][case_id] = entry

    results["meta"] = {
        "monolith_sha256": hashlib.sha256(
            SCRIPT.read_bytes()).hexdigest(),
        "weigh_window_s": float(monolith.WEIGH_WINDOW_S),
        "python": sys.version.split()[0],
        "pandas": pd.__version__,
        "numpy": np.__version__,
    }
    GOLDEN_DIR.mkdir(parents=True, exist_ok=True)
    GOLDEN_JSON.write_text(json.dumps(results, indent=2, sort_keys=True))
    print(f"Wrote {len(results['trials'])} golden trials to {GOLDEN_JSON}")


def compare(path, expected, actual):
    """Recursive comparison; floats use tight isclose, everything else exact."""
    if isinstance(expected, dict):
        if not isinstance(actual, dict) or set(expected) != set(actual):
            return [f"{path}: keys differ"]
        out = []
        for k in sorted(expected):
            out += compare(f"{path}.{k}", expected[k], actual[k])
        return out
    if isinstance(expected, float) or isinstance(actual, float):
        import math
        if not math.isclose(expected, actual, rel_tol=1e-12, abs_tol=1e-12):
            return [f"{path}: {expected!r} != {actual!r}"]
        return []
    if expected != actual:
        return [f"{path}: {expected!r} != {actual!r}"]
    return []


def check():
    saved = json.loads(GOLDEN_JSON.read_text())
    if hashlib.sha256(SCRIPT.read_bytes()).hexdigest() != \
            saved["meta"]["monolith_sha256"]:
        print("NOTE: monolith file differs from the one that generated the "
              "golden file (expected during refactor phases).")
    monolith = load_monolith()
    global WEIGH_WINDOW_S
    WEIGH_WINDOW_S = monolith.WEIGH_WINDOW_S

    failures = []
    n = 0
    # The monolith must delegate every calculation to the package.
    import imtp.io
    import imtp.processing.bodyweight as bw_mod
    import imtp.processing.countermovement as cm_mod
    import imtp.processing.onset as onset_mod
    import imtp.processing.metrics as metrics_mod
    from imtp.models.trial import default_trial_label
    guards = {
        "load_trial": (monolith.load_trial, imtp.io.load_trial),
        "calculate_bodyweight": (monolith.calculate_bodyweight,
                                 bw_mod.calculate_bodyweight),
        "detect_countermovement": (monolith.detect_countermovement,
                                  cm_mod.detect_countermovement),
        "up_to_peak": (monolith.up_to_peak, cm_mod.up_to_peak),
        "select_onset": (monolith.select_onset, onset_mod.select_onset),
        "trim_to_onset": (monolith.trim_to_onset, onset_mod.trim_to_onset),
        "calculate_force_metrics": (monolith.calculate_force_metrics,
                                    metrics_mod.calculate_force_metrics),
    }
    for name, (mono_fn, pkg_fn) in guards.items():
        if mono_fn is not pkg_fn:
            failures.append(f"monolith.{name} does not delegate to the package")
    for case_id, path, data, system in _read_all():
        expected = saved["trials"][case_id]
        actual = {
            "source": str(path.relative_to(REPO)),
            "system": system,
            "n_samples": int(len(data)),
            "time_first": float(data["Time"].iloc[0]),
            "time_last": float(data["Time"].iloc[-1]),
            "fingerprint": data_fingerprint(data),
            "params": dict(PARAMS[case_id]),
            "pipeline": run_pipeline(data, **PARAMS[case_id]),
        }
        failures += compare(case_id, expected, actual)
        # From Phase 1 onward the extracted package must also reproduce
        # the frozen goldens.
        pkg = run_package_pipeline(data, **PARAMS[case_id])
        failures += compare(f"{case_id} [package]", expected["pipeline"], pkg)
        # Phase 2: IMTPTrial loading must match the import layer and the
        # monolith's original trial-default rule exactly.
        expected_default = (system.split('Run #')[-1]
                            if 'Run #' in system else '')
        if default_trial_label(system) != expected_default:
            failures.append(f"{case_id}: default_trial_label mismatch")
        pkg_trial = imtp.io.load_trial(path)[trial_idx_of(case_id)]
        if (pkg_trial.system != system
                or pkg_trial.trial != expected_default
                or data_fingerprint(pkg_trial.data) != expected["fingerprint"]):
            failures.append(f"{case_id}: load_trial mismatch")
        n += 1
    if failures:
        print(f"FAIL — {len(failures)} difference(s):")
        for f in failures:
            print("  " + f)
        sys.exit(1)
    print(f"PASS — all {n} golden trials match.")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--make-fixtures", action="store_true",
                    help="only (re)build the synthetic CSV fixtures")
    ap.add_argument("--check", action="store_true",
                    help="compare current behaviour against saved goldens")
    args = ap.parse_args()
    if args.check:
        check()
    elif args.make_fixtures:
        make_fixtures()
        print(f"Fixtures written to {FIXTURE_DIR}")
    else:
        generate()

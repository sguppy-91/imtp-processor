"""Primary trial object: one imported force trial plus its metadata."""
from dataclasses import dataclass

import pandas as pd


def default_trial_label(system):
    """Trial label an import suggests (e.g. '2' for 'PASCO Run #2').

    Preserves the original script's default for the trial-number entry:
    the run number for multi-run PASCO exports, empty for single-trial
    systems (Hawkin Dynamics, generic fallback).
    """
    return system.split('Run #')[-1] if 'Run #' in system else ''


@dataclass
class IMTPTrial:
    """One imported force trial and its analyst-entered metadata.

    Attributes:
        data: canonical Time/Fz force data (pandas DataFrame)
        system: force-plate system label from import
                (e.g. 'PASCO Run #2', 'Hawkin Dynamics')
        participant: participant code (e.g. 'P001')
        session: session label (e.g. 'T1')
        trial: trial number/label (e.g. '1')
    """

    data: pd.DataFrame
    system: str = ''
    participant: str = ''
    session: str = ''
    trial: str = ''

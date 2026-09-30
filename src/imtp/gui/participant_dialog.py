"""Participant/session/trial metadata entry dialogs."""
import PySimpleGUI as sg


def enter_metadata(trial, last_participant='', last_session=''):
    """Run the participant/session/trial dialogs for one trial.

    Fills trial.participant/session/trial from analyst input. Returns
    (last_participant, last_session, entered): the remember-last values
    updated as far as the dialogs got (matching the original script —
    cancelling at the session dialog still keeps the just-entered
    participant as the next default), and whether all three dialogs
    were completed.
    """
    participant = sg.popup_get_text('Enter participant code (e.g. P001)',
                                    title='Participant',
                                    default_text=last_participant)
    if participant is None:
        return last_participant, last_session, False
    last_participant = participant
    session = sg.popup_get_text('Enter session (e.g. T1)', title='Session',
                                default_text=last_session)
    if session is None:
        return last_participant, last_session, False
    last_session = session
    trial_number = sg.popup_get_text('Enter trial number (e.g. 1)',
                                     title='Trial', default_text=trial.trial)
    if trial_number is None:
        return last_participant, last_session, False
    trial.participant = participant
    trial.session = session
    trial.trial = trial_number
    return last_participant, last_session, True

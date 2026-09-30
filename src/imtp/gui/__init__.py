"""User interaction widgets.

Importing this package configures the matplotlib backend (MacOSX) and
applies the PySimpleGUI theme, exactly as the original script did at
import time — so it must be imported before matplotlib.pyplot.

GUI modules only gather analyst decisions; they contain no force
calculations, no data import and no export logic. (The GUI workflow is
macOS-only, matching the original script.)
"""
import matplotlib

matplotlib.use('MacOSX')

import PySimpleGUI as sg  # noqa: E402

sg.theme('DarkTeal6')

from .participant_dialog import enter_metadata  # noqa: E402
from .onset_selector import select_onset_time  # noqa: E402
from .weighing_selector import select_weighing_start  # noqa: E402

__all__ = ["enter_metadata", "select_onset_time", "select_weighing_start"]

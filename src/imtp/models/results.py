"""Primary results object: force-time variables for one trial."""
from dataclasses import dataclass


@dataclass
class IMTPResults:
    """Net-force (above bodyweight) results for one IMTP trial, in newtons.

    Attributes:
        peak_force: maximum net force after onset
        f50, f100, f150, f200, f250: net force at fixed times (ms) after
            onset; numerically identical to average rate of force
            development over the 0-t window (N / t)
    """

    peak_force: float
    f50: float
    f100: float
    f150: float
    f200: float
    f250: float

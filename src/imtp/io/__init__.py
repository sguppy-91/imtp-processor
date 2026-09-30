"""Force-plate CSV import (vendor sniffing only; no calculations)."""

from .loader import load_trial, read_force_csv

__all__ = ["load_trial", "read_force_csv"]

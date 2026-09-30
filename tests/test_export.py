"""Export layer tests: results_frame and append_csv."""
from pathlib import Path

import pytest

from imtp.export import append_csv, results_frame
from imtp.io import read_force_csv
from imtp.models import IMTPResults, IMTPTrial
from imtp.processing.bodyweight import calculate_bodyweight
from imtp.processing.countermovement import up_to_peak
from imtp.processing.metrics import calculate_force_metrics
from imtp.processing.onset import select_onset, trim_to_onset

FIXTURES = Path(__file__).resolve().parent / "data" / "fixtures"

EXPORT_COLUMNS = ["Participant", "Session", "Trial", "Variable", "Peak",
                  "50 ms", "100 ms", "150 ms", "200 ms", "250 ms"]


def _hawkin_export_row():
    data, _ = read_force_csv(FIXTURES / "hawkin.csv")[0]
    trial = IMTPTrial(data=data, system="Hawkin Dynamics",
                      participant="P001", session="T1", trial="1")
    bw = calculate_bodyweight(data, 1.0)
    df1 = up_to_peak(bw["df"])
    _, start = select_onset(data, df1, 3.5)
    results = calculate_force_metrics(trim_to_onset(df1, start),
                                      bw["weight"])
    return results_frame(trial, results)


def test_results_frame_schema_and_rounding():
    df = _hawkin_export_row()
    assert list(df.columns) == EXPORT_COLUMNS
    assert df.shape == (1, 10)
    row = df.iloc[0]
    # 1-decimal rounding, exactly as the original script exported
    assert row["Participant"] == "P001"
    assert row["Variable"] == "Net Force"
    assert str(row["Peak"]) == "1540.4"
    assert str(row["100 ms"]) == "159.9"


def test_append_csv_header_semantics(tmp_path):
    results_file = tmp_path / "results.csv"
    df = _hawkin_export_row()

    # New file: header written
    append_csv(results_file, df)
    content = results_file.read_text()
    assert content.splitlines()[0] == ",".join(EXPORT_COLUMNS)
    assert len(content.splitlines()) == 2

    # Existing file: appended without a second header
    append_csv(results_file, df)
    lines = results_file.read_text().splitlines()
    assert len(lines) == 3
    assert lines.count(",".join(EXPORT_COLUMNS)) == 1

    # Empty file: header written again (original script's rule)
    results_file.write_text("")
    append_csv(results_file, df)
    lines = results_file.read_text().splitlines()
    assert lines[0] == ",".join(EXPORT_COLUMNS)
    assert len(lines) == 2

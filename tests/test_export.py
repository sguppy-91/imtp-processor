"""Export layer tests: results_frame (schema v2) and append_csv."""
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from imtp.export import (AuditRecord, SchemaMismatchError, append_csv,
                         results_frame)
from imtp.io import read_force_csv
from imtp.models import IMTPResults, IMTPTrial
from imtp.processing.bodyweight import calculate_bodyweight
from imtp.processing.countermovement import up_to_peak
from imtp.processing.metrics import calculate_force_metrics
from imtp.processing.onset import (detect_onset_auto, select_onset,
                                   trim_to_onset)

FIXTURES = Path(__file__).resolve().parent / "data" / "fixtures"

EXPORT_COLUMNS = ["Participant", "Session", "Trial", "Variable", "Peak",
                  "50 ms", "100 ms", "150 ms", "200 ms", "250 ms",
                  "OnsetMethod", "OnsetTime_s", "WeighStart_s",
                  "Bodyweight_N", "BW_SD_N", "OnsetThreshold_N"]

V1_COLUMNS = EXPORT_COLUMNS[:10]


def _hawkin_chain():
    """The analyst workflow's calculation chain on the hawkin fixture."""
    data, _ = read_force_csv(FIXTURES / "hawkin.csv")[0]
    trial = IMTPTrial(data=data, system="Hawkin Dynamics",
                      participant="P001", session="T1", trial="1")
    bw = calculate_bodyweight(data, 1.0)
    df1 = up_to_peak(bw["df"])
    return trial, data, bw, df1


def _manual_row():
    trial, data, bw, df1 = _hawkin_chain()
    _, start = select_onset(data, df1, 3.5)
    results = calculate_force_metrics(trim_to_onset(df1, start),
                                      bw["weight"])
    audit = AuditRecord(onset_method="manual", onset_time_s=3.5,
                        weigh_start_s=1.0, bodyweight_n=bw["weight"],
                        bw_sd_n=bw["stddev"], onset_threshold_n=None)
    return results_frame(trial, results, audit), bw


def _automated_row(sd_multiplier=5):
    trial, data, bw, df1 = _hawkin_chain()
    onset = detect_onset_auto(bw["df"], bw["weight"], bw["stddev"],
                              sd_multiplier=sd_multiplier)
    _, start = select_onset(data, df1, onset)
    results = calculate_force_metrics(trim_to_onset(df1, start),
                                      bw["weight"])
    audit = AuditRecord(onset_method=f"bw+{sd_multiplier}sd",
                        onset_time_s=onset, weigh_start_s=1.0,
                        bodyweight_n=bw["weight"], bw_sd_n=bw["stddev"],
                        onset_threshold_n=bw["weight"] + sd_multiplier * bw["stddev"])
    return results_frame(trial, results, audit), bw, onset


def test_results_frame_schema_and_rounding():
    df, _ = _manual_row()
    assert list(df.columns) == EXPORT_COLUMNS
    assert df.shape == (1, 16)
    row = df.iloc[0]
    # original columns: 1-decimal rounding, exactly as the original script
    assert row["Participant"] == "P001"
    assert row["Variable"] == "Net Force"
    assert str(row["Peak"]) == "1540.4"
    assert str(row["100 ms"]) == "159.9"
    # audit columns: manual row records the method and parameters,
    # threshold empty (no threshold applies to manual onset)
    assert row["OnsetMethod"] == "manual"
    assert row["OnsetTime_s"] == 3.5
    assert row["WeighStart_s"] == 1.0
    assert pd.isna(row["OnsetThreshold_N"])


def test_results_frame_without_audit_keeps_v1_schema():
    """audit=None yields exactly the original 10-column frame (the
    golden-master harness calls results_frame this way)."""
    trial, data, bw, df1 = _hawkin_chain()
    _, start = select_onset(data, df1, 3.5)
    results = calculate_force_metrics(trim_to_onset(df1, start),
                                      bw["weight"])
    df = results_frame(trial, results)
    assert list(df.columns) == V1_COLUMNS
    assert df.shape == (1, 10)
    assert str(df.iloc[0]["Peak"]) == "1540.4"


def test_results_frame_automated_audit_populated():
    df, bw, onset = _automated_row(sd_multiplier=5)
    row = df.iloc[0]
    assert row["OnsetMethod"] == "bw+5sd"
    assert row["OnsetTime_s"] == round(onset, 1)
    assert row["Bodyweight_N"] == round(bw["weight"], 1)
    assert row["BW_SD_N"] == round(bw["stddev"], 1)
    expected_threshold = round(bw["weight"] + 5 * bw["stddev"], 1)
    assert row["OnsetThreshold_N"] == expected_threshold


def test_results_frame_3sd_method_label():
    df, bw, _ = _automated_row(sd_multiplier=3)
    assert df.iloc[0]["OnsetMethod"] == "bw+3sd"
    assert df.iloc[0]["OnsetThreshold_N"] == round(
        bw["weight"] + 3 * bw["stddev"], 1)


def test_append_csv_header_semantics(tmp_path):
    results_file = tmp_path / "results.csv"
    df, _ = _manual_row()

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


def test_append_csv_refuses_v1_file(tmp_path):
    """A v1 results file (10-column header) + a v2 frame: no append,
    clear error, file untouched."""
    results_file = tmp_path / "results.csv"
    v1_header = ",".join(V1_COLUMNS)
    v1_row = ",".join(["P001", "T1", "1", "Net Force", "1540.4",
                       "80.0", "159.9", "200.0", "240.0", "260.0"])
    results_file.write_text(v1_header + "\n" + v1_row + "\n")

    df, _ = _manual_row()
    with pytest.raises(SchemaMismatchError, match="different header"):
        append_csv(results_file, df)
    # nothing appended, original content intact
    assert results_file.read_text().splitlines() == [v1_header, v1_row]


def test_append_csv_refuses_any_header_mismatch(tmp_path):
    results_file = tmp_path / "results.csv"
    results_file.write_text("a,b,c\n1,2,3\n")
    df, _ = _manual_row()
    with pytest.raises(SchemaMismatchError):
        append_csv(results_file, df)
    assert results_file.read_text() == "a,b,c\n1,2,3\n"


def test_append_csv_empty_file_gets_v2_header(tmp_path):
    results_file = tmp_path / "results.csv"
    results_file.write_text("")
    df, _, _ = _automated_row()
    append_csv(results_file, df)
    lines = results_file.read_text().splitlines()
    assert lines[0] == ",".join(EXPORT_COLUMNS)
    # manual threshold emptiness survives the round trip as an empty cell
    results_file.write_text("")
    df_manual, _ = _manual_row()
    append_csv(results_file, df_manual)
    cells = results_file.read_text().splitlines()[1].split(",")
    assert cells[15] == ""  # OnsetThreshold_N empty for manual rows

from pathlib import Path

from tidegauge.calibration import CalibrationConfig
from tidegauge.calibration_store import load_calibration_config, save_calibration_config


def test_save_and_load_calibration_config_round_trip(tmp_path: Path) -> None:
    calibration_path = tmp_path / "calibration.json"
    original = CalibrationConfig(geometry_reference_m=2.5, datum_offset_m=0.2)

    save_calibration_config(path=calibration_path, config=original)
    loaded = load_calibration_config(path=calibration_path)

    assert loaded == original


def test_load_calibration_config_returns_uncalibrated_when_missing_file(
    tmp_path: Path,
) -> None:
    calibration_path = tmp_path / "missing.json"

    loaded = load_calibration_config(path=calibration_path)

    assert loaded == CalibrationConfig(geometry_reference_m=None, datum_offset_m=None)

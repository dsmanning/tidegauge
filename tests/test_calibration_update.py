from pathlib import Path

import pytest

from tidegauge.calibration import CalibrationConfig
from tidegauge.calibration_store import load_calibration_config
from tidegauge.calibration_update import compute_datum_offset_m, update_calibration_from_reference


def test_compute_datum_offset_m_from_reference_measurement() -> None:
    datum_offset_m = compute_datum_offset_m(
        geometry_reference_m=2.5,
        measured_distance_m=1.4,
        known_tide_height_m=0.9,
    )
    assert datum_offset_m == pytest.approx(0.2)


def test_update_calibration_from_reference_persists_config(tmp_path: Path) -> None:
    calibration_path = tmp_path / "calibration.json"

    config = update_calibration_from_reference(
        path=calibration_path,
        geometry_reference_m=2.5,
        measured_distance_m=1.4,
        known_tide_height_m=0.9,
    )
    loaded = load_calibration_config(path=calibration_path)

    assert config.geometry_reference_m == pytest.approx(2.5)
    assert config.datum_offset_m == pytest.approx(0.2)
    assert loaded == config


def test_update_calibration_from_reference_rejects_negative_distance(
    tmp_path: Path,
) -> None:
    with pytest.raises(ValueError, match="measured_distance_m must be >= 0"):
        update_calibration_from_reference(
            path=tmp_path / "calibration.json",
            geometry_reference_m=2.5,
            measured_distance_m=-0.1,
            known_tide_height_m=0.9,
        )

from pathlib import Path

from tidegauge.calibration import CalibrationConfig
from tidegauge.calibration_store import save_calibration_config


def compute_datum_offset_m(
    *,
    geometry_reference_m: float,
    measured_distance_m: float,
    known_tide_height_m: float,
) -> float:
    if measured_distance_m < 0:
        raise ValueError("measured_distance_m must be >= 0")

    return geometry_reference_m - measured_distance_m - known_tide_height_m


def update_calibration_from_reference(
    *,
    path: Path,
    geometry_reference_m: float,
    measured_distance_m: float,
    known_tide_height_m: float,
) -> CalibrationConfig:
    datum_offset_m = compute_datum_offset_m(
        geometry_reference_m=geometry_reference_m,
        measured_distance_m=measured_distance_m,
        known_tide_height_m=known_tide_height_m,
    )
    config = CalibrationConfig(
        geometry_reference_m=geometry_reference_m,
        datum_offset_m=datum_offset_m,
    )
    save_calibration_config(path=path, config=config)
    return config

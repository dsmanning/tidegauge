import pytest

from tidegauge.calibration import (
    CalibrationConfig,
    CalibrationNotSetError,
    compute_tide_height_from_config_m,
)


def test_compute_tide_height_from_config_m_raises_when_uncalibrated() -> None:
    config = CalibrationConfig(geometry_reference_m=None, datum_offset_m=None)

    with pytest.raises(CalibrationNotSetError, match="Calibration is not set"):
        compute_tide_height_from_config_m(measured_distance_m=1.2, config=config)


def test_compute_tide_height_from_config_m_uses_calibration_values() -> None:
    config = CalibrationConfig(geometry_reference_m=2.5, datum_offset_m=0.2)

    tide_height_m = compute_tide_height_from_config_m(
        measured_distance_m=1.4,
        config=config,
    )

    assert tide_height_m == pytest.approx(0.9)

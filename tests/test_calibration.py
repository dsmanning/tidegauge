import pytest

from tidegauge.calibration import compute_tide_height_m


def test_compute_tide_height_m_uses_geometry_and_datum_offset() -> None:
    geometry_reference_m = 2.5
    measured_distance_m = 1.4
    datum_offset_m = 0.2

    tide_height_m = compute_tide_height_m(
        geometry_reference_m=geometry_reference_m,
        measured_distance_m=measured_distance_m,
        datum_offset_m=datum_offset_m,
    )

    assert tide_height_m == pytest.approx(0.9)


def test_compute_tide_height_m_allows_negative_tide_height() -> None:
    tide_height_m = compute_tide_height_m(
        geometry_reference_m=1.0,
        measured_distance_m=1.4,
        datum_offset_m=0.2,
    )

    assert tide_height_m == pytest.approx(-0.6)


def test_compute_tide_height_m_rejects_negative_measured_distance() -> None:
    with pytest.raises(ValueError, match="measured_distance_m must be >= 0"):
        compute_tide_height_m(
            geometry_reference_m=2.5,
            measured_distance_m=-0.1,
            datum_offset_m=0.2,
        )

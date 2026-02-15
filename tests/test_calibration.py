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

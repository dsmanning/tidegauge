from dataclasses import dataclass


class CalibrationNotSetError(RuntimeError):
    """Raised when tide datum calibration is required but not configured."""


@dataclass(frozen=True)
class CalibrationConfig:
    geometry_reference_m: float | None
    datum_offset_m: float | None

    @property
    def is_calibrated(self) -> bool:
        return self.geometry_reference_m is not None and self.datum_offset_m is not None


def compute_tide_height_m(
    *,
    geometry_reference_m: float,
    measured_distance_m: float,
    datum_offset_m: float,
) -> float:
    """Convert sensor distance into tide height relative to datum."""
    if measured_distance_m < 0:
        raise ValueError("measured_distance_m must be >= 0")

    return geometry_reference_m - measured_distance_m - datum_offset_m


def compute_tide_height_from_config_m(
    *,
    measured_distance_m: float,
    config: CalibrationConfig,
) -> float:
    if not config.is_calibrated:
        raise CalibrationNotSetError("Calibration is not set")

    return compute_tide_height_m(
        geometry_reference_m=float(config.geometry_reference_m),
        measured_distance_m=measured_distance_m,
        datum_offset_m=float(config.datum_offset_m),
    )

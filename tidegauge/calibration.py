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

def compute_tide_height_m(
    *,
    geometry_reference_m: float,
    measured_distance_m: float,
    datum_offset_m: float,
) -> float:
    """Convert sensor distance into tide height relative to datum."""
    return geometry_reference_m - measured_distance_m - datum_offset_m

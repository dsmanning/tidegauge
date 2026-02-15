import argparse
from pathlib import Path
from typing import Callable, Sequence

from tidegauge.calibration_update import update_calibration_from_reference


def run_calibration_cli(
    *,
    argv: Sequence[str],
    update_fn: Callable[..., object] = update_calibration_from_reference,
) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--path", type=Path, required=True)
    parser.add_argument("--geometry-reference-m", type=float, required=True)
    parser.add_argument("--measured-distance-m", type=float, required=True)
    parser.add_argument("--known-tide-height-m", type=float, required=True)
    args = parser.parse_args(argv)

    update_fn(
        path=args.path,
        geometry_reference_m=args.geometry_reference_m,
        measured_distance_m=args.measured_distance_m,
        known_tide_height_m=args.known_tide_height_m,
    )
    return 0

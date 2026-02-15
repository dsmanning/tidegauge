import json
import os
from pathlib import Path
from typing import Union

from tidegauge.calibration import CalibrationConfig


PathValue = Union[str, Path]


def _path_str(path: PathValue) -> str:
    return str(path)


def load_calibration_config(*, path: PathValue) -> CalibrationConfig:
    path_str = _path_str(path)
    if not os.path.exists(path_str):
        return CalibrationConfig(geometry_reference_m=None, datum_offset_m=None)

    with open(path_str, "r", encoding="utf-8") as file:
        data = json.load(file)
    return CalibrationConfig(
        geometry_reference_m=data.get("geometry_reference_m"),
        datum_offset_m=data.get("datum_offset_m"),
    )


def save_calibration_config(*, path: PathValue, config: CalibrationConfig) -> None:
    path_str = _path_str(path)
    payload = {
        "geometry_reference_m": config.geometry_reference_m,
        "datum_offset_m": config.datum_offset_m,
    }

    parent = os.path.dirname(path_str)
    if parent:
        os.makedirs(parent, exist_ok=True)

    with open(path_str, "w", encoding="utf-8") as file:
        json.dump(payload, file, sort_keys=True)

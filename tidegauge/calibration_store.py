import json
import os
try:
    from pathlib import Path
except ImportError:  # pragma: no cover - CircuitPython compatibility
    Path = str
try:
    from typing import Union
except ImportError:  # pragma: no cover - CircuitPython compatibility
    Union = tuple

from tidegauge.calibration import CalibrationConfig


try:
    PathValue = Union[str, Path]
except Exception:  # pragma: no cover - CircuitPython compatibility
    PathValue = object


def _path_str(path: PathValue) -> str:
    return str(path)


def load_calibration_config(*, path: PathValue) -> CalibrationConfig:
    path_str = _path_str(path)
    try:
        with open(path_str, "r", encoding="utf-8") as file:
            data = json.load(file)
    except OSError:
        return CalibrationConfig(geometry_reference_m=None, datum_offset_m=None)
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

    try:
        parent = os.path.dirname(path_str)
        if parent:
            os.makedirs(parent, exist_ok=True)
    except AttributeError:
        # CircuitPython os module does not expose os.path helpers.
        pass

    with open(path_str, "w", encoding="utf-8") as file:
        json.dump(payload, file, sort_keys=True)

import json
from pathlib import Path

from tidegauge.calibration import CalibrationConfig


def load_calibration_config(*, path: Path) -> CalibrationConfig:
    if not path.exists():
        return CalibrationConfig(geometry_reference_m=None, datum_offset_m=None)

    data = json.loads(path.read_text())
    return CalibrationConfig(
        geometry_reference_m=data.get("geometry_reference_m"),
        datum_offset_m=data.get("datum_offset_m"),
    )


def save_calibration_config(*, path: Path, config: CalibrationConfig) -> None:
    payload = {
        "geometry_reference_m": config.geometry_reference_m,
        "datum_offset_m": config.datum_offset_m,
    }
    path.write_text(json.dumps(payload, sort_keys=True))

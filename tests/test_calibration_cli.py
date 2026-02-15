from pathlib import Path

from tidegauge.calibration_cli import run_calibration_cli


class RecordingUpdateCalibration:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def __call__(self, **kwargs: object):
        self.calls.append(kwargs)
        return object()


def test_run_calibration_cli_parses_args_and_calls_update(tmp_path: Path) -> None:
    calibration_path = tmp_path / "calibration.json"
    update = RecordingUpdateCalibration()

    exit_code = run_calibration_cli(
        argv=[
            "--path",
            str(calibration_path),
            "--geometry-reference-m",
            "2.5",
            "--measured-distance-m",
            "1.4",
            "--known-tide-height-m",
            "0.9",
        ],
        update_fn=update,
    )

    assert exit_code == 0
    assert len(update.calls) == 1
    assert update.calls[0]["path"] == calibration_path
    assert update.calls[0]["geometry_reference_m"] == 2.5
    assert update.calls[0]["measured_distance_m"] == 1.4
    assert update.calls[0]["known_tide_height_m"] == 0.9

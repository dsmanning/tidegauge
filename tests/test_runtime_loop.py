from pathlib import Path

from tidegauge.adapters.fakes import FakeRadioPort, FakeSleepPort, FakeUltrasonicSensorPort
from tidegauge.app.runtime_loop import run_runtime_iterations
from tidegauge.calibration import CalibrationConfig
from tidegauge.calibration_store import save_calibration_config


class SequenceScheduler:
    def __init__(self, due_sequence: list[bool]) -> None:
        self._due_sequence = due_sequence

    def is_due(self) -> bool:
        if not self._due_sequence:
            return False
        return self._due_sequence.pop(0)


def test_run_runtime_iterations_skips_send_when_uncalibrated(
    tmp_path: Path,
) -> None:
    calibration_path = tmp_path / "missing.json"
    scheduler = SequenceScheduler([True, True])
    sensor = FakeUltrasonicSensorPort(readings_m=[1.4, 1.4])
    radio = FakeRadioPort()
    sleeper = FakeSleepPort()

    sent_count = run_runtime_iterations(
        iterations=2,
        calibration_path=calibration_path,
        scheduler=scheduler,
        sensor=sensor,
        radio=radio,
        sleeper=sleeper,
        sleep_seconds=1,
    )

    assert sent_count == 0
    assert radio.sent_payloads == []
    assert sleeper.sleep_calls_s == [1, 1]


def test_run_runtime_iterations_sends_when_calibrated(tmp_path: Path) -> None:
    calibration_path = tmp_path / "calibration.json"
    save_calibration_config(
        path=calibration_path,
        config=CalibrationConfig(geometry_reference_m=2.5, datum_offset_m=0.2),
    )
    scheduler = SequenceScheduler([False, True, True])
    sensor = FakeUltrasonicSensorPort(readings_m=[1.4, 1.5])
    radio = FakeRadioPort()
    sleeper = FakeSleepPort()

    sent_count = run_runtime_iterations(
        iterations=3,
        calibration_path=calibration_path,
        scheduler=scheduler,
        sensor=sensor,
        radio=radio,
        sleeper=sleeper,
        sleep_seconds=1,
    )

    assert sent_count == 2
    assert radio.sent_payloads == [bytes([0x03, 0x84]), bytes([0x03, 0x20])]
    assert sleeper.sleep_calls_s == [1, 1, 1]

from pathlib import Path

import pytest

from tidegauge.adapters.fakes import FakeRadioPort, FakeSleepPort, FakeUltrasonicSensorPort
from tidegauge.adapters.radio import RadioSendError
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


class FailingRadio:
    def __init__(self) -> None:
        self.calls = 0

    def send(self, payload: bytes) -> None:
        self.calls += 1
        raise RadioSendError("simulated uplink failure")


class FlakyRadio:
    def __init__(self, fail_count: int) -> None:
        self.fail_count = fail_count
        self.calls = 0
        self.sent_payloads: list[bytes] = []

    def send(self, payload: bytes) -> None:
        self.calls += 1
        if self.calls <= self.fail_count:
            raise RadioSendError("transient failure")
        self.sent_payloads.append(payload)


class FailingSensor:
    def read_distance_m(self) -> float:
        raise RuntimeError("sensor timeout")


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


def test_run_runtime_iterations_continues_after_radio_send_failure(
    tmp_path: Path,
) -> None:
    calibration_path = tmp_path / "calibration.json"
    save_calibration_config(
        path=calibration_path,
        config=CalibrationConfig(geometry_reference_m=2.5, datum_offset_m=0.2),
    )
    scheduler = SequenceScheduler([True, True, True])
    sensor = FakeUltrasonicSensorPort(readings_m=[1.4, 1.4, 1.4])
    radio = FailingRadio()
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

    assert sent_count == 0
    assert radio.calls == 3
    assert sleeper.sleep_calls_s == [1, 1, 1]


def test_run_runtime_iterations_retries_send_within_cycle_until_success(
    tmp_path: Path,
) -> None:
    calibration_path = tmp_path / "calibration.json"
    save_calibration_config(
        path=calibration_path,
        config=CalibrationConfig(geometry_reference_m=2.5, datum_offset_m=0.2),
    )
    scheduler = SequenceScheduler([True])
    sensor = FakeUltrasonicSensorPort(readings_m=[1.4])
    radio = FlakyRadio(fail_count=2)
    sleeper = FakeSleepPort()

    sent_count = run_runtime_iterations(
        iterations=1,
        calibration_path=calibration_path,
        scheduler=scheduler,
        sensor=sensor,
        radio=radio,
        sleeper=sleeper,
        sleep_seconds=1,
        max_send_attempts=3,
    )

    assert sent_count == 1
    assert radio.calls == 3
    assert radio.sent_payloads == [bytes([0x03, 0x84])]


def test_run_runtime_iterations_stops_retrying_after_attempt_limit(
    tmp_path: Path,
) -> None:
    calibration_path = tmp_path / "calibration.json"
    save_calibration_config(
        path=calibration_path,
        config=CalibrationConfig(geometry_reference_m=2.5, datum_offset_m=0.2),
    )
    scheduler = SequenceScheduler([True])
    sensor = FakeUltrasonicSensorPort(readings_m=[1.4])
    radio = FlakyRadio(fail_count=5)
    sleeper = FakeSleepPort()

    sent_count = run_runtime_iterations(
        iterations=1,
        calibration_path=calibration_path,
        scheduler=scheduler,
        sensor=sensor,
        radio=radio,
        sleeper=sleeper,
        sleep_seconds=1,
        max_send_attempts=3,
    )

    assert sent_count == 0
    assert radio.calls == 3
    assert radio.sent_payloads == []


def test_run_runtime_iterations_continues_when_sensor_read_raises(
    tmp_path: Path,
) -> None:
    calibration_path = tmp_path / "calibration.json"
    save_calibration_config(
        path=calibration_path,
        config=CalibrationConfig(geometry_reference_m=2.5, datum_offset_m=0.2),
    )
    scheduler = SequenceScheduler([True, True])
    sensor = FailingSensor()
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


def test_run_runtime_iterations_emits_diagnostics_for_sensor_failure(
    tmp_path: Path,
) -> None:
    calibration_path = tmp_path / "calibration.json"
    save_calibration_config(
        path=calibration_path,
        config=CalibrationConfig(geometry_reference_m=2.5, datum_offset_m=0.2),
    )
    scheduler = SequenceScheduler([True])
    sensor = FailingSensor()
    radio = FakeRadioPort()
    sleeper = FakeSleepPort()
    logs: list[str] = []

    sent_count = run_runtime_iterations(
        iterations=1,
        calibration_path=calibration_path,
        scheduler=scheduler,
        sensor=sensor,
        radio=radio,
        sleeper=sleeper,
        sleep_seconds=1,
        log_fn=logs.append,
    )

    assert sent_count == 0
    assert any("sensor timeout" in line for line in logs)


def test_run_runtime_iterations_logs_radio_send_error_reason(
    tmp_path: Path,
) -> None:
    calibration_path = tmp_path / "calibration.json"
    save_calibration_config(
        path=calibration_path,
        config=CalibrationConfig(geometry_reference_m=2.5, datum_offset_m=0.2),
    )
    scheduler = SequenceScheduler([True])
    sensor = FakeUltrasonicSensorPort(readings_m=[1.4])
    radio = FailingRadio()
    sleeper = FakeSleepPort()
    logs: list[str] = []

    run_runtime_iterations(
        iterations=1,
        calibration_path=calibration_path,
        scheduler=scheduler,
        sensor=sensor,
        radio=radio,
        sleeper=sleeper,
        sleep_seconds=1,
        max_send_attempts=1,
        log_fn=logs.append,
    )

    assert any("simulated uplink failure" in line for line in logs)

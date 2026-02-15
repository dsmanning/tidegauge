from pathlib import Path

from tidegauge.adapters.radio import RadioSendError
from tidegauge.app.service import SchedulerPort, run_cycle_if_due
from tidegauge.calibration import CalibrationNotSetError
from tidegauge.calibration_store import load_calibration_config
from tidegauge.ports import RadioPort, SleepPort, UltrasonicSensorPort


def run_runtime_iterations(
    *,
    iterations: int,
    calibration_path: Path,
    scheduler: SchedulerPort,
    sensor: UltrasonicSensorPort,
    radio: RadioPort,
    sleeper: SleepPort,
    sleep_seconds: int,
) -> int:
    config = load_calibration_config(path=calibration_path)
    sent_count = 0

    for _ in range(iterations):
        try:
            payload = run_cycle_if_due(
                scheduler=scheduler,
                sensor=sensor,
                radio=radio,
                config=config,
            )
        except CalibrationNotSetError:
            payload = None
        except RadioSendError:
            payload = None

        if payload is not None:
            sent_count += 1

        sleeper.sleep_s(sleep_seconds)

    return sent_count

from pathlib import Path

from tidegauge.adapters.radio import RadioSendError
from tidegauge.app.service import SchedulerPort
from tidegauge.calibration import CalibrationNotSetError, compute_tide_height_from_config_m
from tidegauge.calibration_store import load_calibration_config
from tidegauge.payload import encode_tide_height_payload
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
    max_send_attempts: int = 1,
) -> int:
    config = load_calibration_config(path=calibration_path)
    sent_count = 0

    for _ in range(iterations):
        if scheduler.is_due():
            try:
                measured_distance_m = sensor.read_distance_m()
                tide_height_m = compute_tide_height_from_config_m(
                    measured_distance_m=measured_distance_m,
                    config=config,
                )
                payload = encode_tide_height_payload(tide_height_m=tide_height_m)

                for _attempt in range(max_send_attempts):
                    try:
                        radio.send(payload)
                        sent_count += 1
                        break
                    except RadioSendError:
                        pass
            except CalibrationNotSetError:
                pass

        sleeper.sleep_s(sleep_seconds)

    return sent_count

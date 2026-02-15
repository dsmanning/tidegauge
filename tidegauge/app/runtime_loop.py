try:
    from pathlib import Path
except ImportError:  # pragma: no cover - CircuitPython compatibility
    Path = str
try:
    from typing import Callable
except ImportError:  # pragma: no cover - CircuitPython compatibility
    class Callable:  # type: ignore[no-redef]
        def __class_getitem__(cls, _item):
            return cls

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
    log_fn: Callable[[str], None] | None = None,
) -> int:
    if log_fn is None:
        def log_fn(_msg: str) -> None:
            return None

    config = load_calibration_config(path=calibration_path)
    sent_count = 0

    for _ in range(iterations):
        if scheduler.is_due():
            log_fn("cycle due")
            try:
                measured_distance_m = sensor.read_distance_m()
                log_fn("distance_m=" + str(measured_distance_m))
                tide_height_m = compute_tide_height_from_config_m(
                    measured_distance_m=measured_distance_m,
                    config=config,
                )
                log_fn("tide_height_m=" + str(tide_height_m))
                payload = encode_tide_height_payload(tide_height_m=tide_height_m)
                log_fn("payload=" + repr(payload))

                for _attempt in range(max_send_attempts):
                    try:
                        radio.send(payload)
                        sent_count += 1
                        log_fn("send ok")
                        break
                    except RadioSendError as exc:
                        log_fn("send retry: " + str(exc))
                        pass
            except CalibrationNotSetError:
                log_fn("calibration missing")
                pass
            except Exception as exc:
                log_fn("cycle error: " + str(exc))
        else:
            log_fn("cycle not due")

        sleeper.sleep_s(sleep_seconds)

    return sent_count

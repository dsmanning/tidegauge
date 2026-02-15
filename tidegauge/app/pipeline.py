from tidegauge.calibration import CalibrationConfig, compute_tide_height_from_config_m
from tidegauge.payload import encode_tide_height_payload
from tidegauge.ports import RadioPort, UltrasonicSensorPort


def run_measurement_cycle(
    *,
    sensor: UltrasonicSensorPort,
    radio: RadioPort,
    config: CalibrationConfig,
) -> bytes:
    measured_distance_m = sensor.read_distance_m()
    tide_height_m = compute_tide_height_from_config_m(
        measured_distance_m=measured_distance_m,
        config=config,
    )
    payload = encode_tide_height_payload(tide_height_m=tide_height_m)
    radio.send(payload)
    return payload

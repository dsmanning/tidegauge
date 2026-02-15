import pytest

from tidegauge.adapters.fakes import FakeRadioPort, FakeUltrasonicSensorPort
from tidegauge.ports import RadioPort, UltrasonicSensorPort


def read_sensor(sensor: UltrasonicSensorPort) -> float:
    return sensor.read_distance_m()


def send_payload(radio: RadioPort, payload: bytes) -> None:
    radio.send(payload)


def test_fake_ultrasonic_sensor_port_returns_configured_readings() -> None:
    sensor = FakeUltrasonicSensorPort(readings_m=[1.2, 1.25])

    assert read_sensor(sensor) == pytest.approx(1.2)
    assert read_sensor(sensor) == pytest.approx(1.25)


def test_fake_ultrasonic_sensor_port_raises_when_no_readings_left() -> None:
    sensor = FakeUltrasonicSensorPort(readings_m=[])

    with pytest.raises(RuntimeError, match="No sensor readings remaining"):
        read_sensor(sensor)


def test_fake_radio_port_captures_sent_payloads() -> None:
    radio = FakeRadioPort()

    send_payload(radio, b"\x01\x02")
    send_payload(radio, b"\xAA\xBB")

    assert radio.sent_payloads == [b"\x01\x02", b"\xAA\xBB"]

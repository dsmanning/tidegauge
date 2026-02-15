import pytest

from tidegauge.adapters.fakes import FakeRadioPort, FakeUltrasonicSensorPort
from tidegauge.app.pipeline import run_measurement_cycle
from tidegauge.calibration import CalibrationConfig, CalibrationNotSetError


def test_run_measurement_cycle_sends_encoded_payload() -> None:
    sensor = FakeUltrasonicSensorPort(readings_m=[1.4])
    radio = FakeRadioPort()
    config = CalibrationConfig(geometry_reference_m=2.5, datum_offset_m=0.2)

    payload = run_measurement_cycle(sensor=sensor, radio=radio, config=config)

    assert payload == bytes([0x03, 0x84])
    assert radio.sent_payloads == [bytes([0x03, 0x84])]


def test_run_measurement_cycle_raises_when_uncalibrated_and_does_not_send() -> None:
    sensor = FakeUltrasonicSensorPort(readings_m=[1.4])
    radio = FakeRadioPort()
    config = CalibrationConfig(geometry_reference_m=None, datum_offset_m=None)

    with pytest.raises(CalibrationNotSetError, match="Calibration is not set"):
        run_measurement_cycle(sensor=sensor, radio=radio, config=config)

    assert radio.sent_payloads == []

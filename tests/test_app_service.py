from tidegauge.adapters.fakes import FakeRadioPort, FakeUltrasonicSensorPort
from tidegauge.app.service import run_cycle_if_due
from tidegauge.calibration import CalibrationConfig


class DueScheduler:
    def is_due(self) -> bool:
        return True


class NotDueScheduler:
    def is_due(self) -> bool:
        return False


def test_run_cycle_if_due_runs_pipeline_when_due() -> None:
    scheduler = DueScheduler()
    sensor = FakeUltrasonicSensorPort(readings_m=[1.4])
    radio = FakeRadioPort()
    config = CalibrationConfig(geometry_reference_m=2.5, datum_offset_m=0.2)

    payload = run_cycle_if_due(
        scheduler=scheduler,
        sensor=sensor,
        radio=radio,
        config=config,
    )

    assert payload == bytes([0x03, 0x84])
    assert radio.sent_payloads == [bytes([0x03, 0x84])]


def test_run_cycle_if_due_skips_pipeline_when_not_due() -> None:
    scheduler = NotDueScheduler()
    sensor = FakeUltrasonicSensorPort(readings_m=[])
    radio = FakeRadioPort()
    config = CalibrationConfig(geometry_reference_m=2.5, datum_offset_m=0.2)

    payload = run_cycle_if_due(
        scheduler=scheduler,
        sensor=sensor,
        radio=radio,
        config=config,
    )

    assert payload is None
    assert radio.sent_payloads == []

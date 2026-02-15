from tidegauge.adapters.fakes import FakeRadioPort, FakeSleepPort, FakeUltrasonicSensorPort
from tidegauge.app.main_loop import run_main_loop_iterations
from tidegauge.calibration import CalibrationConfig


class SequenceScheduler:
    def __init__(self, due_sequence: list[bool]) -> None:
        self._due_sequence = due_sequence

    def is_due(self) -> bool:
        if not self._due_sequence:
            return False
        return self._due_sequence.pop(0)


def test_run_main_loop_iterations_runs_due_cycles_and_sleeps_every_iteration() -> None:
    scheduler = SequenceScheduler([False, True, False])
    sensor = FakeUltrasonicSensorPort(readings_m=[1.4])
    radio = FakeRadioPort()
    sleeper = FakeSleepPort()
    config = CalibrationConfig(geometry_reference_m=2.5, datum_offset_m=0.2)

    run_main_loop_iterations(
        iterations=3,
        scheduler=scheduler,
        sensor=sensor,
        radio=radio,
        config=config,
        sleeper=sleeper,
        sleep_seconds=1,
    )

    assert radio.sent_payloads == [bytes([0x03, 0x84])]
    assert sleeper.sleep_calls_s == [1, 1, 1]

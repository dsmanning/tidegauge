from typing import Protocol

from tidegauge.app.pipeline import run_measurement_cycle
from tidegauge.calibration import CalibrationConfig
from tidegauge.ports import RadioPort, UltrasonicSensorPort


class SchedulerPort(Protocol):
    def is_due(self) -> bool:
        """Return True when a measurement cycle should run."""


def run_cycle_if_due(
    *,
    scheduler: SchedulerPort,
    sensor: UltrasonicSensorPort,
    radio: RadioPort,
    config: CalibrationConfig,
) -> bytes | None:
    if not scheduler.is_due():
        return None

    return run_measurement_cycle(sensor=sensor, radio=radio, config=config)

from tidegauge.app.service import SchedulerPort, run_cycle_if_due
from tidegauge.calibration import CalibrationConfig
from tidegauge.ports import RadioPort, SleepPort, UltrasonicSensorPort


def run_main_loop_iterations(
    *,
    iterations: int,
    scheduler: SchedulerPort,
    sensor: UltrasonicSensorPort,
    radio: RadioPort,
    config: CalibrationConfig,
    sleeper: SleepPort,
    sleep_seconds: int,
) -> None:
    for _ in range(iterations):
        run_cycle_if_due(
            scheduler=scheduler,
            sensor=sensor,
            radio=radio,
            config=config,
        )
        sleeper.sleep_s(sleep_seconds)

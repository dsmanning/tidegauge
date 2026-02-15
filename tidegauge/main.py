from pathlib import Path
from typing import Any, Callable

from tidegauge.board import run_device_loop
from tidegauge.hardware import HardwareConfig


def run_main(
    *,
    machine_module: Any,
    time_module: Any,
    lora_client: Any,
    trigger_pin_id: int,
    echo_pin_id: int,
    calibration_path: Path,
    measurement_interval_s: int = 60,
    max_send_attempts: int = 3,
    max_loops: int | None = None,
    run_device_loop_fn: Callable[..., int] = run_device_loop,
) -> int:
    hardware_config = HardwareConfig(
        trigger_pin_id=trigger_pin_id,
        echo_pin_id=echo_pin_id,
        measurement_interval_s=measurement_interval_s,
        max_send_attempts=max_send_attempts,
    )
    return run_device_loop_fn(
        machine_module=machine_module,
        time_module=time_module,
        lora_client=lora_client,
        hardware_config=hardware_config,
        calibration_path=calibration_path,
        max_loops=max_loops,
    )

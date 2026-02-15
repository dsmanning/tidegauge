try:
    from typing import Any, Callable
except ImportError:  # pragma: no cover - CircuitPython compatibility
    Any = object
    class Callable:  # type: ignore[no-redef]
        def __class_getitem__(cls, _item):
            return cls

from tidegauge.app.runtime_loop import run_runtime_iterations
from tidegauge.hardware import HardwareConfig, RuntimeDependencies, build_runtime_dependencies


def run_device_loop(
    *,
    machine_module: Any,
    time_module: Any,
    lora_client: Any,
    hardware_config: HardwareConfig,
    calibration_path: Any,
    max_loops: int | None = None,
    log_fn: Callable[[str], None] = print,
    build_dependencies: Callable[..., RuntimeDependencies] = build_runtime_dependencies,
    run_iterations: Callable[..., int] = run_runtime_iterations,
) -> int:
    deps = build_dependencies(
        machine_module=machine_module,
        time_module=time_module,
        lora_client=lora_client,
        config=hardware_config,
    )

    sent_count_total = 0
    loop_count = 0
    while max_loops is None or loop_count < max_loops:
        sent_count_total += run_iterations(
            iterations=1,
            calibration_path=calibration_path,
            scheduler=deps.scheduler,
            sensor=deps.sensor,
            radio=deps.radio,
            sleeper=deps.sleeper,
            sleep_seconds=1,
            max_send_attempts=deps.max_send_attempts,
            log_fn=log_fn,
        )
        loop_count += 1

    return sent_count_total

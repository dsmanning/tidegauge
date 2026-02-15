from pathlib import Path

from tidegauge.board import run_device_loop
from tidegauge.hardware import HardwareConfig, RuntimeDependencies


class FakeScheduler:
    def is_due(self) -> bool:
        return True


class FakeSleeper:
    def sleep_s(self, seconds: int) -> None:
        return None


class FakeSensor:
    def read_distance_m(self) -> float:
        return 1.0


class FakeRadio:
    def __init__(self) -> None:
        self.payloads: list[bytes] = []

    def send(self, payload: bytes) -> None:
        self.payloads.append(payload)


class RecordingRunIterations:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def __call__(self, **kwargs: object) -> int:
        self.calls.append(kwargs)
        return 1


class RecordingBuildDeps:
    def __init__(self, deps: RuntimeDependencies) -> None:
        self.deps = deps
        self.calls: list[dict[str, object]] = []

    def __call__(self, **kwargs: object) -> RuntimeDependencies:
        self.calls.append(kwargs)
        return self.deps


def test_run_device_loop_builds_dependencies_and_runs_iterations() -> None:
    deps = RuntimeDependencies(
        sensor=FakeSensor(),
        radio=FakeRadio(),
        scheduler=FakeScheduler(),
        clock=None,  # not used by run_device_loop directly
        sleeper=FakeSleeper(),
        max_send_attempts=4,
    )
    build_deps = RecordingBuildDeps(deps)
    run_iterations = RecordingRunIterations()
    calibration_path = Path("/tmp/calibration.json")
    config = HardwareConfig(trigger_pin_id=6, echo_pin_id=7)

    sent_count = run_device_loop(
        machine_module=object(),
        time_module=object(),
        lora_client=object(),
        hardware_config=config,
        calibration_path=calibration_path,
        max_loops=1,
        build_dependencies=build_deps,
        run_iterations=run_iterations,
    )

    assert sent_count == 1
    assert len(build_deps.calls) == 1
    assert len(run_iterations.calls) == 1
    assert run_iterations.calls[0]["iterations"] == 1
    assert run_iterations.calls[0]["max_send_attempts"] == 4
    assert run_iterations.calls[0]["calibration_path"] == calibration_path


def test_run_device_loop_accumulates_sent_count_over_multiple_loops() -> None:
    deps = RuntimeDependencies(
        sensor=FakeSensor(),
        radio=FakeRadio(),
        scheduler=FakeScheduler(),
        clock=None,
        sleeper=FakeSleeper(),
        max_send_attempts=2,
    )
    build_deps = RecordingBuildDeps(deps)

    class TwoThenOneRunIterations:
        def __init__(self) -> None:
            self.calls = 0

        def __call__(self, **kwargs: object) -> int:
            self.calls += 1
            return 2 if self.calls == 1 else 1

    run_iterations = TwoThenOneRunIterations()

    sent_count = run_device_loop(
        machine_module=object(),
        time_module=object(),
        lora_client=object(),
        hardware_config=HardwareConfig(trigger_pin_id=6, echo_pin_id=7),
        calibration_path=Path("/tmp/calibration.json"),
        max_loops=2,
        build_dependencies=build_deps,
        run_iterations=run_iterations,
    )

    assert sent_count == 3

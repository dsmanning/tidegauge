from pathlib import Path

from tidegauge.main import run_main


class FakeRunDeviceLoop:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def __call__(self, **kwargs: object) -> int:
        self.calls.append(kwargs)
        return 7


def test_run_main_passes_config_and_returns_sent_count() -> None:
    run_device_loop = FakeRunDeviceLoop()

    sent_count = run_main(
        machine_module=object(),
        time_module=object(),
        lora_client=object(),
        trigger_pin_id=6,
        echo_pin_id=7,
        calibration_path=Path("/tmp/calibration.json"),
        measurement_interval_s=60,
        max_send_attempts=3,
        run_device_loop_fn=run_device_loop,
        max_loops=2,
    )

    assert sent_count == 7
    assert len(run_device_loop.calls) == 1
    config = run_device_loop.calls[0]["hardware_config"]
    assert config.trigger_pin_id == 6
    assert config.echo_pin_id == 7
    assert config.measurement_interval_s == 60
    assert config.max_send_attempts == 3

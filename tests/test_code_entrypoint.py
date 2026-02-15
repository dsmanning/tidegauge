import importlib

import pytest


def test_main_uses_circuitpython_compat_modules(monkeypatch: pytest.MonkeyPatch) -> None:
    board_main = importlib.import_module("main")
    captured: dict[str, object] = {}

    class FakeBoard:
        D6 = object()
        D7 = object()

    class FakeDirection:
        INPUT = "input"
        OUTPUT = "output"

    class FakeDigitalInOut:
        def __init__(self, pin: object) -> None:
            self.pin = pin
            self.direction = None
            self.value = False

    class FakeDigitalio:
        Direction = FakeDirection
        DigitalInOut = FakeDigitalInOut

    class FakeTime:
        def sleep(self, seconds: float) -> None:
            return None

        def monotonic_ns(self) -> int:
            return 0

        def monotonic(self) -> float:
            return 0.0

    def fake_run_main(**kwargs: object) -> int:
        captured.update(kwargs)
        return 11

    monkeypatch.setitem(__import__("sys").modules, "board", FakeBoard)
    monkeypatch.setitem(__import__("sys").modules, "digitalio", FakeDigitalio)
    monkeypatch.setitem(__import__("sys").modules, "time", FakeTime())
    monkeypatch.setattr(board_main, "create_lora_client", lambda: object())
    monkeypatch.setattr(board_main, "run_main", fake_run_main)

    exit_code = board_main.main()

    assert exit_code == 11
    assert hasattr(captured["machine_module"], "Pin")
    assert hasattr(captured["time_module"], "sleep_us")
    assert captured["trigger_pin_id"] == 6
    assert captured["echo_pin_id"] == 5

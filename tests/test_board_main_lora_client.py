import importlib

import pytest

from tidegauge.adapters.lorawan_client import LoRaWanClientAdapter


class FakeDriver:
    def __init__(self) -> None:
        self.join_calls = 0
        self.sent_payloads: list[bytes] = []

    def join(self) -> None:
        self.join_calls += 1

    def send(self, payload: bytes) -> bool:
        self.sent_payloads.append(payload)
        return True


class FakeCredentials:
    def __init__(self) -> None:
        self.dev_eui = "0011223344556677"
        self.app_eui = "8899AABBCCDDEEFF"
        self.app_key = "00112233445566778899AABBCCDDEEFF"


def test_create_lora_client_wraps_driver_factory_in_adapter() -> None:
    board_main = importlib.import_module("main")
    fake_driver = FakeDriver()
    fake_credentials = FakeCredentials()
    seen_credentials: list[object] = []

    def build_driver(*, credentials: object) -> FakeDriver:
        seen_credentials.append(credentials)
        return fake_driver

    client = board_main.create_lora_client(
        driver_factory=build_driver,
        credentials_loader=lambda: fake_credentials,
    )

    assert isinstance(client, LoRaWanClientAdapter)
    assert client.send(b"\x01\x02") is True
    assert fake_driver.join_calls == 1
    assert fake_driver.sent_payloads == [b"\x01\x02"]
    assert seen_credentials == [fake_credentials]


def test_create_lora_client_uses_default_feather_driver_factory(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    board_main = importlib.import_module("main")
    feather_lorawan = importlib.import_module("tidegauge.adapters.feather_lorawan")
    fake_driver = FakeDriver()
    fake_credentials = FakeCredentials()

    monkeypatch.setattr(
        feather_lorawan,
        "create_feather_lorawan_driver",
        lambda *, credentials: fake_driver,
    )

    ttn_credentials = importlib.import_module("tidegauge.ttn_credentials")
    monkeypatch.setattr(
        ttn_credentials,
        "load_ttn_credentials",
        lambda: fake_credentials,
    )

    client = board_main.create_lora_client()

    assert isinstance(client, LoRaWanClientAdapter)
    assert client.send(b"\xAA") is True
    assert fake_driver.join_calls == 1
    assert fake_driver.sent_payloads == [b"\xAA"]

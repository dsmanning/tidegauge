import importlib

import pytest

from tidegauge.ttn_credentials import TtnCredentials


class FakeTinyLoRaRadio:
    def __init__(self) -> None:
        self.join_calls = 0
        self.sent_payloads: list[bytes] = []

    def join(self) -> None:
        self.join_calls += 1

    def send_data(self, payload: bytes, *, length: int) -> bool:
        self.sent_payloads.append(payload[:length])
        return True


def test_create_feather_lorawan_driver_uses_radio_factory_and_credentials() -> None:
    feather_lorawan = importlib.import_module("tidegauge.adapters.feather_lorawan")
    credentials = TtnCredentials(
        dev_eui="0011223344556677",
        app_eui="8899AABBCCDDEEFF",
        app_key="00112233445566778899AABBCCDDEEFF",
    )
    seen_credentials: list[TtnCredentials] = []

    def radio_factory(*, credentials: TtnCredentials) -> FakeTinyLoRaRadio:
        seen_credentials.append(credentials)
        return FakeTinyLoRaRadio()

    driver = feather_lorawan.create_feather_lorawan_driver(
        credentials=credentials,
        radio_factory=radio_factory,
    )

    assert seen_credentials == [credentials]
    assert driver.send(b"\x01\x02") is True


def test_feather_lorawan_driver_delegates_join_and_send_data() -> None:
    feather_lorawan = importlib.import_module("tidegauge.adapters.feather_lorawan")
    raw_client = FakeTinyLoRaRadio()
    driver = feather_lorawan.FeatherLoRaWanDriver(raw_radio=raw_client)

    driver.join()
    sent = driver.send(b"\x10\x20")

    assert sent is True
    assert raw_client.join_calls == 1
    assert raw_client.sent_payloads == [b"\x10\x20"]


def test_feather_lorawan_driver_uses_noop_join_when_raw_radio_has_no_join() -> None:
    feather_lorawan = importlib.import_module("tidegauge.adapters.feather_lorawan")

    class SendOnlyRadio:
        def send_data(self, payload: bytes, *, length: int) -> bool:
            return bool(payload[:length])

    driver = feather_lorawan.FeatherLoRaWanDriver(raw_radio=SendOnlyRadio())

    driver.join()
    assert driver.send(b"\x33") is True


def test_feather_lorawan_driver_falls_back_to_positional_send_data_signature() -> None:
    feather_lorawan = importlib.import_module("tidegauge.adapters.feather_lorawan")

    class PositionalSendRadio:
        def send_data(self, payload: bytes, length: int, /) -> bool:
            return payload[:length] == b"\x10\x20"

    driver = feather_lorawan.FeatherLoRaWanDriver(raw_radio=PositionalSendRadio())

    assert driver.send(b"\x10\x20") is True


def test_feather_lorawan_driver_supports_send_data_with_frame_counter() -> None:
    feather_lorawan = importlib.import_module("tidegauge.adapters.feather_lorawan")

    class CounterSendRadio:
        def __init__(self) -> None:
            self.frame_counter = 7
            self.calls: list[tuple[bytes, int, int]] = []

        def send_data(self, payload: bytes, length: int, frame_counter: int, /) -> bool:
            self.calls.append((payload, length, frame_counter))
            return True

    raw = CounterSendRadio()
    driver = feather_lorawan.FeatherLoRaWanDriver(raw_radio=raw)

    assert driver.send(b"\xAA\xBB") is True
    assert raw.calls == [(b"\xAA\xBB", 2, 7)]


def test_create_tinylora_radio_builds_board_spi_and_radio_stack(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    feather_lorawan = importlib.import_module("tidegauge.adapters.feather_lorawan")
    credentials = TtnCredentials(
        dev_eui="0011223344556677",
        app_eui="8899AABBCCDDEEFF",
        app_key="00112233445566778899AABBCCDDEEFF",
    )
    calls: list[tuple[str, tuple[object, ...], dict[str, object]]] = []

    class FakeBoard:
        SCK = object()
        MOSI = object()
        MISO = object()
        RFM95_CS = object()
        RFM95_INT = object()
        RFM95_RST = object()

    class FakeDigitalInOut:
        def __init__(self, pin: object) -> None:
            calls.append(("DigitalInOut", (pin,), {}))

    class FakeDigitalio:
        DigitalInOut = FakeDigitalInOut

    class FakeBusio:
        @staticmethod
        def SPI(clock: object, *, MOSI: object, MISO: object) -> object:
            calls.append(("SPI", (clock,), {"MOSI": MOSI, "MISO": MISO}))
            return object()

    class FakeTinyLoRaModule:
        class TTN:
            def __init__(self, *, dev_eui: str, app_eui: str, app_key: str) -> None:
                calls.append(
                    (
                        "TTN",
                        (),
                        {
                            "dev_eui": dev_eui,
                            "app_eui": app_eui,
                            "app_key": app_key,
                        },
                    )
                )

        class TinyLoRa:
            def __init__(self, spi: object, cs: object, irq: object, reset: object, ttn: object) -> None:
                calls.append(("TinyLoRa", (spi, cs, irq, reset, ttn), {}))

    monkeypatch.setitem(__import__("sys").modules, "board", FakeBoard)
    monkeypatch.setitem(__import__("sys").modules, "digitalio", FakeDigitalio)
    monkeypatch.setitem(__import__("sys").modules, "busio", FakeBusio)
    feather_lorawan.create_tinylora_radio(
        credentials=credentials,
        tinylora_module=FakeTinyLoRaModule,
    )

    assert any(call[0] == "SPI" for call in calls)
    assert any(call[0] == "TTN" for call in calls)
    assert any(call[0] == "TinyLoRa" for call in calls)


def test_create_tinylora_radio_supports_abp_credentials(monkeypatch: pytest.MonkeyPatch) -> None:
    feather_lorawan = importlib.import_module("tidegauge.adapters.feather_lorawan")
    credentials = TtnCredentials(
        dev_addr="26011BEE",
        nwk_skey="00112233445566778899AABBCCDDEEFF",
        app_skey="FFEEDDCCBBAA99887766554433221100",
    )
    ttn_kwargs: dict[str, object] = {}

    class FakeBoard:
        SCK = object()
        MOSI = object()
        MISO = object()
        RFM95_CS = object()
        RFM95_INT = object()
        RFM95_RST = object()

    class FakeDigitalInOut:
        def __init__(self, pin: object) -> None:
            self.pin = pin

    class FakeDigitalio:
        DigitalInOut = FakeDigitalInOut

    class FakeBusio:
        @staticmethod
        def SPI(clock: object, *, MOSI: object, MISO: object) -> object:
            return object()

    class FakeTinyLoRaModule:
        class TTN:
            def __init__(self, **kwargs: object) -> None:
                ttn_kwargs.update(kwargs)

        class TinyLoRa:
            def __init__(self, spi: object, cs: object, irq: object, reset: object, ttn: object) -> None:
                return None

    monkeypatch.setitem(__import__("sys").modules, "board", FakeBoard)
    monkeypatch.setitem(__import__("sys").modules, "digitalio", FakeDigitalio)
    monkeypatch.setitem(__import__("sys").modules, "busio", FakeBusio)
    feather_lorawan.create_tinylora_radio(
        credentials=credentials,
        tinylora_module=FakeTinyLoRaModule,
    )

    assert "dev_addr" in ttn_kwargs
    assert "nwk_skey" in ttn_kwargs
    assert "app_skey" in ttn_kwargs


def test_create_tinylora_radio_accepts_rfm_pin_aliases(monkeypatch: pytest.MonkeyPatch) -> None:
    feather_lorawan = importlib.import_module("tidegauge.adapters.feather_lorawan")
    credentials = TtnCredentials(
        dev_addr="26011BEE",
        nwk_skey="00112233445566778899AABBCCDDEEFF",
        app_skey="FFEEDDCCBBAA99887766554433221100",
    )
    used_pins: list[object] = []

    class FakeBoard:
        SCK = object()
        MOSI = object()
        MISO = object()
        RFM_CS = object()
        RFM_IO0 = object()
        RFM_RST = object()

    class FakeDigitalInOut:
        def __init__(self, pin: object) -> None:
            used_pins.append(pin)

    class FakeDigitalio:
        DigitalInOut = FakeDigitalInOut

    class FakeBusio:
        @staticmethod
        def SPI(clock: object, *, MOSI: object, MISO: object) -> object:
            return object()

    class FakeTinyLoRaModule:
        class TTN:
            def __init__(self, **kwargs: object) -> None:
                return None

        class TinyLoRa:
            def __init__(self, spi: object, cs: object, irq: object, reset: object, ttn: object) -> None:
                return None

    monkeypatch.setitem(__import__("sys").modules, "board", FakeBoard)
    monkeypatch.setitem(__import__("sys").modules, "digitalio", FakeDigitalio)
    monkeypatch.setitem(__import__("sys").modules, "busio", FakeBusio)

    feather_lorawan.create_tinylora_radio(
        credentials=credentials,
        tinylora_module=FakeTinyLoRaModule,
    )

    assert FakeBoard.RFM_CS in used_pins
    assert FakeBoard.RFM_IO0 in used_pins
    assert FakeBoard.RFM_RST in used_pins


def test_create_tinylora_radio_falls_back_to_abp_positional_ttn_ctor(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    feather_lorawan = importlib.import_module("tidegauge.adapters.feather_lorawan")
    credentials = TtnCredentials(
        dev_addr="26011BEE",
        nwk_skey="00112233445566778899AABBCCDDEEFF",
        app_skey="FFEEDDCCBBAA99887766554433221100",
    )
    captured: dict[str, object] = {}

    class FakeBoard:
        SCK = object()
        MOSI = object()
        MISO = object()
        RFM_CS = object()
        RFM_IO0 = object()
        RFM_RST = object()

    class FakeDigitalInOut:
        def __init__(self, pin: object) -> None:
            self.pin = pin

    class FakeDigitalio:
        DigitalInOut = FakeDigitalInOut

    class FakeBusio:
        @staticmethod
        def SPI(clock: object, *, MOSI: object, MISO: object) -> object:
            return object()

    class FakeTinyLoRaModule:
        class TTN:
            def __init__(self, *args: object, **kwargs: object) -> None:
                if kwargs:
                    raise TypeError("unexpected keyword argument")
                captured["args"] = args
                captured["kwargs"] = kwargs

        class TinyLoRa:
            def __init__(self, spi: object, cs: object, irq: object, reset: object, ttn: object) -> None:
                return None

    monkeypatch.setitem(__import__("sys").modules, "board", FakeBoard)
    monkeypatch.setitem(__import__("sys").modules, "digitalio", FakeDigitalio)
    monkeypatch.setitem(__import__("sys").modules, "busio", FakeBusio)

    feather_lorawan.create_tinylora_radio(
        credentials=credentials,
        tinylora_module=FakeTinyLoRaModule,
    )

    assert captured["args"] == (
        "26011BEE",
        "00112233445566778899AABBCCDDEEFF",
        "FFEEDDCCBBAA99887766554433221100",
    )


def test_create_tinylora_radio_falls_back_to_otaa_positional_ttn_ctor(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    feather_lorawan = importlib.import_module("tidegauge.adapters.feather_lorawan")
    credentials = TtnCredentials(
        dev_eui="0011223344556677",
        app_eui="8899AABBCCDDEEFF",
        app_key="00112233445566778899AABBCCDDEEFF",
    )
    captured: dict[str, object] = {}

    class FakeBoard:
        SCK = object()
        MOSI = object()
        MISO = object()
        RFM_CS = object()
        RFM_IO0 = object()
        RFM_RST = object()

    class FakeDigitalInOut:
        def __init__(self, pin: object) -> None:
            self.pin = pin

    class FakeDigitalio:
        DigitalInOut = FakeDigitalInOut

    class FakeBusio:
        @staticmethod
        def SPI(clock: object, *, MOSI: object, MISO: object) -> object:
            return object()

    class FakeTinyLoRaModule:
        class TTN:
            def __init__(self, *args: object, **kwargs: object) -> None:
                if kwargs:
                    raise TypeError("unexpected keyword argument")
                captured["args"] = args
                captured["kwargs"] = kwargs

        class TinyLoRa:
            def __init__(self, spi: object, cs: object, irq: object, reset: object, ttn: object) -> None:
                return None

    monkeypatch.setitem(__import__("sys").modules, "board", FakeBoard)
    monkeypatch.setitem(__import__("sys").modules, "digitalio", FakeDigitalio)
    monkeypatch.setitem(__import__("sys").modules, "busio", FakeBusio)

    feather_lorawan.create_tinylora_radio(
        credentials=credentials,
        tinylora_module=FakeTinyLoRaModule,
    )

    assert captured["args"] == (
        "0011223344556677",
        "8899AABBCCDDEEFF",
        "00112233445566778899AABBCCDDEEFF",
    )

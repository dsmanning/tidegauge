from tidegauge.adapters.lorawan_client import LoRaWanClientAdapter


class FakeLoRaWanDriver:
    def __init__(self, *, send_results: list[bool] | None = None) -> None:
        self.join_calls = 0
        self.sent_payloads: list[bytes] = []
        self.send_results = send_results or [True]

    def join(self) -> None:
        self.join_calls += 1

    def send(self, payload: bytes) -> bool:
        self.sent_payloads.append(payload)
        if not self.send_results:
            return True
        return self.send_results.pop(0)


def test_lorawan_client_adapter_joins_before_first_send() -> None:
    driver = FakeLoRaWanDriver()
    client = LoRaWanClientAdapter(driver=driver)

    sent = client.send(b"\x01\x02")

    assert sent is True
    assert driver.join_calls == 1
    assert driver.sent_payloads == [b"\x01\x02"]


def test_lorawan_client_adapter_joins_only_once() -> None:
    driver = FakeLoRaWanDriver(send_results=[True, True])
    client = LoRaWanClientAdapter(driver=driver)

    first = client.send(b"\x01")
    second = client.send(b"\x02")

    assert first is True
    assert second is True
    assert driver.join_calls == 1
    assert driver.sent_payloads == [b"\x01", b"\x02"]


def test_lorawan_client_adapter_passes_through_send_failures() -> None:
    driver = FakeLoRaWanDriver(send_results=[False])
    client = LoRaWanClientAdapter(driver=driver)

    sent = client.send(b"\x01")

    assert sent is False

import pytest

from tidegauge.adapters.radio import RadioSendError, Rfm95RadioAdapter


class FakeLoRaClient:
    def __init__(self, *, send_results: list[bool] | None = None) -> None:
        self._send_results = send_results or [True]
        self.sent_payloads: list[bytes] = []

    def send(self, payload: bytes) -> bool:
        self.sent_payloads.append(payload)
        if not self._send_results:
            return True
        return self._send_results.pop(0)


class ExplodingLoRaClient:
    def send(self, payload: bytes) -> bool:
        raise RuntimeError("radio failure")


def test_rfm95_radio_adapter_sends_payload_via_client() -> None:
    client = FakeLoRaClient()
    adapter = Rfm95RadioAdapter(client=client)

    adapter.send(b"\x01\x02")

    assert client.sent_payloads == [b"\x01\x02"]


def test_rfm95_radio_adapter_raises_when_client_reports_send_failure() -> None:
    client = FakeLoRaClient(send_results=[False])
    adapter = Rfm95RadioAdapter(client=client)

    with pytest.raises(RadioSendError, match="Radio client reported send failure"):
        adapter.send(b"\xAA")


def test_rfm95_radio_adapter_wraps_client_exceptions() -> None:
    client = ExplodingLoRaClient()
    adapter = Rfm95RadioAdapter(client=client)

    with pytest.raises(RadioSendError, match="radio failure"):
        adapter.send(b"\xAA")

try:
    from typing import Any, Callable
except ImportError:  # pragma: no cover - CircuitPython compatibility
    Any = object
    class Callable:  # type: ignore[no-redef]
        def __class_getitem__(cls, _item):
            return cls

from tidegauge.ttn_credentials import TtnCredentials


class FeatherLoRaWanDriver:
    def __init__(self, *, raw_radio: Any) -> None:
        self._raw_radio = raw_radio

    def join(self) -> None:
        join_fn = getattr(self._raw_radio, "join", None)
        if callable(join_fn):
            join_fn()

    def send(self, payload: bytes) -> bool:
        send_data_fn = getattr(self._raw_radio, "send_data", None)
        if callable(send_data_fn):
            try:
                return bool(send_data_fn(payload, length=len(payload)))
            except TypeError:
                try:
                    return bool(send_data_fn(payload, len(payload)))
                except TypeError:
                    frame_counter = int(getattr(self._raw_radio, "frame_counter", 0))
                    return bool(send_data_fn(payload, len(payload), frame_counter))

        send_fn = getattr(self._raw_radio, "send", None)
        if callable(send_fn):
            return bool(send_fn(payload))

        raise RuntimeError("TinyLoRa radio does not expose send/send_data")


def _get_board_pin(board_module: Any, *names: str) -> Any:
    for name in names:
        if hasattr(board_module, name):
            return getattr(board_module, name)
    raise AttributeError("No supported RFM pin alias found")


def create_tinylora_radio(*, credentials: TtnCredentials, tinylora_module: Any = None) -> Any:
    import board
    import busio
    import digitalio

    if tinylora_module is None:
        from adafruit_tinylora.adafruit_tinylora import TTN, TinyLoRa
    else:
        TTN = getattr(tinylora_module, "TTN")
        TinyLoRa = getattr(tinylora_module, "TinyLoRa")

    spi = busio.SPI(board.SCK, MOSI=board.MOSI, MISO=board.MISO)
    cs = digitalio.DigitalInOut(
        _get_board_pin(board, "RFM95_CS", "RFM_CS", "D16")
    )
    irq = digitalio.DigitalInOut(
        _get_board_pin(board, "RFM95_INT", "RFM_IO0", "D21")
    )
    reset = digitalio.DigitalInOut(
        _get_board_pin(board, "RFM95_RST", "RFM_RST", "D17")
    )
    if (
        credentials.dev_eui is not None
        and credentials.app_eui is not None
        and credentials.app_key is not None
    ):
        try:
            ttn = TTN(
                dev_eui=credentials.dev_eui,
                app_eui=credentials.app_eui,
                app_key=credentials.app_key,
            )
        except TypeError:
            # Some TinyLoRa builds expect positional OTAA credentials.
            ttn = TTN(
                credentials.dev_eui,
                credentials.app_eui,
                credentials.app_key,
            )
    elif (
        credentials.dev_addr is not None
        and credentials.nwk_skey is not None
        and credentials.app_skey is not None
    ):
        try:
            ttn = TTN(
                dev_addr=credentials.dev_addr,
                nwk_skey=credentials.nwk_skey,
                app_skey=credentials.app_skey,
            )
        except TypeError:
            # Some TinyLoRa builds expect positional ABP credentials.
            ttn = TTN(
                credentials.dev_addr,
                credentials.nwk_skey,
                credentials.app_skey,
            )
    else:
        raise RuntimeError("Unsupported TTN credentials shape")
    return TinyLoRa(spi, cs, irq, reset, ttn)


def create_feather_lorawan_driver(
    *,
    credentials: TtnCredentials,
    radio_factory: Callable[..., Any] | None = None,
) -> FeatherLoRaWanDriver:
    factory = radio_factory or create_tinylora_radio
    raw_radio = factory(credentials=credentials)
    return FeatherLoRaWanDriver(raw_radio=raw_radio)

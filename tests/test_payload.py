import pytest

from tidegauge.payload import encode_tide_height_payload


def test_encode_tide_height_payload_encodes_signed_millimeters_big_endian() -> None:
    payload = encode_tide_height_payload(tide_height_m=0.9)
    assert payload == bytes([0x03, 0x84])


def test_encode_tide_height_payload_supports_negative_heights() -> None:
    payload = encode_tide_height_payload(tide_height_m=-0.6)
    assert payload == bytes([0xFD, 0xA8])


def test_encode_tide_height_payload_rejects_out_of_range_values() -> None:
    with pytest.raises(ValueError, match="tide_height_m out of encodable range"):
        encode_tide_height_payload(tide_height_m=100.0)

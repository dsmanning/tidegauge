def encode_tide_height_payload(*, tide_height_m: float) -> bytes:
    """Encode tide height as signed millimeters, big-endian int16."""
    tide_height_mm = int(round(tide_height_m * 1000))

    if tide_height_mm < -32768 or tide_height_mm > 32767:
        raise ValueError("tide_height_m out of encodable range")

    return tide_height_mm.to_bytes(2, byteorder="big", signed=True)

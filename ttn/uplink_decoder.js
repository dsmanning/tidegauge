function decodeUplink(input) {
  const bytes = input.bytes || [];
  if (bytes.length !== 10) {
    return { errors: [`Expected 10-byte payload, got ${bytes.length}`] };
  }

  function readInt16BE(msb, lsb) {
    let value = (msb << 8) | lsb;
    if (value & 0x8000) {
      value -= 0x10000;
    }
    return value;
  }

  function readUInt16BE(msb, lsb) {
    return (msb << 8) | lsb;
  }

  function decodeSignedWithInvalid(msb, lsb, scale) {
    const raw = readInt16BE(msb, lsb);
    if (raw === -32768) {
      return { raw: null, scaled: null };
    }
    return { raw, scaled: raw / scale };
  }

  function decodeUnsignedWithInvalid(msb, lsb, scale) {
    const raw = readUInt16BE(msb, lsb);
    if (raw === 0xffff) {
      return { raw: null, scaled: null };
    }
    return { raw, scaled: raw / scale };
  }

  const tide = decodeSignedWithInvalid(bytes[0], bytes[1], 1000);
  const distance = decodeUnsignedWithInvalid(bytes[2], bytes[3], 1000);
  const batteryMv = readUInt16BE(bytes[4], bytes[5]);
  const stddev = decodeUnsignedWithInvalid(bytes[6], bytes[7], 1000);
  const temperature = decodeSignedWithInvalid(bytes[8], bytes[9], 100);

  return {
    data: {
      tide_height_mm: tide.raw,
      tide_height_m: tide.scaled,
      raw_distance_mm: distance.raw,
      raw_distance_m: distance.scaled,
      battery_mv: batteryMv,
      battery_v: batteryMv / 1000,
      distance_stddev_mm: stddev.raw,
      distance_stddev_m: stddev.scaled,
      temperature_centi_c: temperature.raw,
      temperature_c: temperature.scaled,
    }
  };
}

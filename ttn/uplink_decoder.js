function decodeUplink(input) {
  const bytes = input.bytes || [];
  if (bytes.length !== 10 && bytes.length !== 26) {
    return { errors: [`Expected 10- or 26-byte payload, got ${bytes.length}`] };
  }
  if (bytes.length === 26 && bytes[10] !== 1) {
    return { errors: ['Unsupported diagnostic schema'] };
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
  const battery = decodeUnsignedWithInvalid(bytes[4], bytes[5], 1000);
  const stddev = decodeUnsignedWithInvalid(bytes[6], bytes[7], 1000);
  const temperature = decodeSignedWithInvalid(bytes[8], bytes[9], 100);

  const result = {
    data: {
      tide_height_mm: tide.raw,
      tide_height_m: tide.scaled,
      raw_distance_mm: distance.raw,
      raw_distance_m: distance.scaled,
      battery_mv: battery.raw,
      battery_v: battery.scaled,
      distance_stddev_mm: stddev.raw,
      distance_stddev_m: stddev.scaled,
      temperature_centi_c: temperature.raw,
      temperature_c: temperature.scaled,
    }
  };
  if (bytes.length === 26) {
    Object.assign(result.data, {
      diagnostic_version: bytes[10],
      fault_flags: bytes[11],
      reset_reason: bytes[12],
      firmware_revision: bytes[13],
      uptime_s: bytes[14] * 16777216 + bytes[15] * 65536 + bytes[16] * 256 + bytes[17],
      recovery_count: readUInt16BE(bytes[18], bytes[19]),
      valid_samples: bytes[20],
      timeout_samples: bytes[21],
      watchdog_boots: readUInt16BE(bytes[22], bytes[23]),
      measurement_sequence: readUInt16BE(bytes[24], bytes[25]),
    });
  }
  return result;
}

function decodeUplink(input) {
  if (!input.bytes || input.bytes.length < 6) {
    return { errors: ["Need 6-byte payload"] };
  }

  let tide_mm = (input.bytes[0] << 8) | input.bytes[1];
  if (tide_mm & 0x8000) tide_mm -= 0x10000;

  const raw_distance_mm = (input.bytes[2] << 8) | input.bytes[3];
  const battery_mv = (input.bytes[4] << 8) | input.bytes[5];

  return {
    data: {
      tide_height_mm: tide_mm,
      tide_height_m: tide_mm / 1000,
      raw_distance_mm,
      raw_distance_m: raw_distance_mm / 1000,
      battery_mv,
      battery_v: battery_mv / 1000
    }
  };
}

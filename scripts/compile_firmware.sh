#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
# Dependencies must already be installed; this script never installs anything.
# Pin these flags for every compilation unit, including the LMIC C sources.
lmic_flags='-DARDUINO_LMIC_PROJECT_CONFIG_H_SUPPRESS -DCFG_us915=1 -DCFG_sx1276_radio=1'
exec arduino-cli compile \
  -b rp2040:rp2040:adafruit_feather_rfm:flash=8388608_65536 \
  --build-property "compiler.c.extra_flags=$lmic_flags" \
  --build-property "compiler.cpp.extra_flags=$lmic_flags" \
  "${TIDEGAUGE_SKETCH:-arduino/ttn_otaa_lmic}" "$@"

#!/usr/bin/env bash
set -euo pipefail

# Offline field deployment for the Adafruit Feather RP2040 RFM.
# All Arduino cores/libraries must already be installed on this computer.
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SKETCH_DIR="$ROOT_DIR/arduino/ttn_otaa_lmic"
FQBN="${FQBN:-rp2040:rp2040:adafruit_feather_rfm}"
PORT="${PORT:-/dev/ttyACM0}"

fail() {
    echo "ERROR: $*" >&2
    exit 1
}

command -v arduino-cli >/dev/null 2>&1 || fail "arduino-cli is not installed"
[[ -d "$SKETCH_DIR" ]] || fail "firmware sketch not found: $SKETCH_DIR"
[[ -f "$SKETCH_DIR/config.h" ]] || fail "missing local config.h; copy the device credentials into the ignored config.h before leaving"
[[ -e "$PORT" ]] || fail "Feather serial device not found at $PORT; connect the board and set PORT=/dev/ttyACM<N> if needed"

echo "Compiling locally for $FQBN"
arduino-cli compile --fqbn "$FQBN" "$SKETCH_DIR"

echo "Uploading and verifying on $PORT"
arduino-cli upload --fqbn "$FQBN" --port "$PORT" --verify "$SKETCH_DIR"

echo "Firmware installed successfully. Monitor serial logs with:"
echo "  stty -F \"$PORT\" 115200 raw -echo"
echo "  cat \"$PORT\""

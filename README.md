# Remote Tide Gauge (Feather RP2040 + TTN)

This project builds a remote tide gauge using an Adafruit Feather RP2040 RFM, an RFM95 LoRa radio, and an HC-SR04 ultrasonic sensor.

The sensor is mounted at the top of a tube and measures water height inside the tube. The Feather samples once per minute, packages the reading, and sends it through LoRaWAN to The Things Network (TTN) via your local TTN gateway.

Current radio/uplink path is Arduino LMIC OTAA firmware in `arduino/ttn_otaa_lmic`.

## Hardware

- Adafruit Feather RP2040
- RFM95 LoRa radio module
- HC-SR04 ultrasonic module
- TTN gateway
- Development host: Raspberry Pi 5
- USB connection to Feather:
  - Mass storage device (for file transfer): `/dev/sda`
  - Serial console: `/dev/ttyACM0`

## Development approach

We use strict test-driven development (TDD):

1. Write a failing test first.
2. Run tests to confirm failure.
3. Implement the smallest code change to pass.
4. Re-run tests.
5. Refactor while keeping tests green.
6. Repeat in small increments.

Code is designed for testability:

- Hardware access is isolated behind interfaces/adapters.
- Core logic is pure and mockable.
- Time, I/O, and radio boundaries are injected dependencies.

## Data flow

1. Trigger measurement every 60 seconds.
2. Read distance from HC-SR04.
3. Convert distance to water height using calibration constants.
4. Build payload as signed millimeters (`int16`, big-endian).
5. Transmit payload through RFM95/LoRaWAN to TTN.
6. Log status/errors to serial for diagnostics.

## Tide Datum Calibration (Post-Install)

The device must support datum calibration after physical installation at the final site.

- Raw measurement from the ultrasonic sensor is distance from sensor-to-water surface.
- Tide height requires a site-specific datum offset that is not final until installation.
- The software should apply:
  - `tide_height = geometry_reference - measured_distance - datum_offset`
  - Where `geometry_reference` (sensor-to-reference geometry) and `datum_offset` are configurable calibration values.

Recommended calibration workflow:

1. Install and mechanically secure the sensor in final position.
2. Take one or more manual reference readings against known local tide datum.
3. Compute/update `datum_offset` (and `geometry_reference` if needed).
4. Persist calibration values in device configuration.
5. Verify reported tide height against reference observations.

TDD impact:

- Add tests first for calibration math and configuration handling.
- Verify behavior before calibration is set (safe defaults/error handling).
- Verify updated calibration changes only conversion output, not transport logic.
- Keep calibration logic in pure, testable code paths with hardware mocked.

## Testing strategy

- Host-side unit tests validate:
  - Distance-to-height conversion
  - Payload encoding
  - Scheduler behavior (1-minute cadence)
  - Error handling and retries
- Hardware integrations are wrapped so they can be replaced with mocks/fakes in tests.
- On-device validation is done only after host tests pass.

## Project status

Repository documentation initialized. Implementation will proceed in TDD cycles using the constraints and workflow defined in `AGENTS.md`.

## Pi-to-Feather Workflow

Use this sequence for deployment and runtime verification from the Raspberry Pi host.

1. Run host tests:
   `python3 -m pytest -q`
2. Confirm device connectivity:
   `lsblk -f` and verify `/dev/sda` (mounted volume) plus `/dev/ttyACM0` (serial).
3. Compile Arduino firmware:
   - First copy/edit config:
     `cp arduino/ttn_otaa_lmic/config.example.h arduino/ttn_otaa_lmic/config.h`
   - Set `DEV_EUI_HEX`, `APP_EUI_HEX`, `APP_KEY_HEX`, `US915_SUBBAND`, `GEOMETRY_REFERENCE_M`, and `DATUM_OFFSET_M` in `arduino/ttn_otaa_lmic/config.h`.
   - `config.h` is git-ignored by design; keep real credentials only in that local file.
   `arduino-cli compile -b rp2040:rp2040:adafruit_feather_rfm arduino/ttn_otaa_lmic`
4. Upload Arduino firmware:
   `arduino-cli upload -b rp2040:rp2040:adafruit_feather_rfm -p /dev/ttyACM0 arduino/ttn_otaa_lmic`
5. Monitor serial runtime logs on `/dev/ttyACM0` and verify a measurement/send cycle appears once per minute.
6. Confirm uplinks in TTN for the same time window as serial logs.

## TTN Credentials (Arduino LMIC)

Set OTAA credentials in `arduino/ttn_otaa_lmic/config.h`:

- `DEV_EUI_HEX`
- `APP_EUI_HEX`
- `APP_KEY_HEX`
- `US915_SUBBAND` (typically `2` for TTN US915 setups)

These are parsed at startup; invalid hex length/content aborts boot with a serial error.

## TTN Payload Formatter

Use `ttn/uplink_decoder.js` as the TTN JavaScript uplink payload formatter.

Current uplink payload format is 6 bytes:

- Bytes `0-1`: `tide_height_mm` (signed int16, big-endian)
- Bytes `2-3`: `raw_distance_mm` (unsigned uint16, big-endian)
- Bytes `4-5`: `battery_mv` (unsigned uint16, big-endian)

## Sensor Wiring And Calibration

HC-SR04 pinout (Feather labels):

- `TRIG` -> `D6`
- `ECHO` -> `D5`
- `VCC` -> `5V`
- `GND` -> `GND`

Firmware calibration constants are in `arduino/ttn_otaa_lmic/config.h`:

- `GEOMETRY_REFERENCE_M`
- `DATUM_OFFSET_M`

Conversion formula:
`tide_height_m = geometry_reference_m - measured_distance_m - datum_offset_m`

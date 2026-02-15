# Remote Tide Gauge (MicroPython + TTN)

This project builds a remote tide gauge using an Adafruit Feather RP2040 with an RFM95 LoRa radio and an HC-SR04 ultrasonic sensor.

The sensor is mounted at the top of a tube and measures water height inside the tube. The Feather samples once per minute, packages the reading, and sends it through LoRaWAN to The Things Network (TTN) via your local TTN gateway.

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
4. Build payload with reading + metadata.
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

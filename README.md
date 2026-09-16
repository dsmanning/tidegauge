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

The production path is Arduino LMIC. The older Python/CircuitPython modules are
retained for reference; their tests do not validate the deployed Arduino scheduler.
Firmware orchestration is in `arduino/ttn_otaa_lmic/src/app`, hardware adapters in
`src/adapters`, and injected contracts in `src/ports`. Pure payload/calibration
logic is in `measurement.h` and `tide_math.h`.

## Pi-to-Feather Workflow

Use this sequence for deployment and runtime verification from the Raspberry Pi host.

1. Run host tests:
   `python3 -m pytest -q`
2. Confirm device connectivity:
   `lsblk -f` and verify `/dev/sda` (mounted volume) plus `/dev/ttyACM0` (serial).
3. Compile Arduino firmware:
   - First copy/edit config:
     `cp -n arduino/ttn_otaa_lmic/config.example.h arduino/ttn_otaa_lmic/config.h`
   - Set `DEV_EUI_HEX`, `APP_EUI_HEX`, `APP_KEY_HEX`, `US915_SUBBAND`, `GEOMETRY_REFERENCE_M`, and `DATUM_OFFSET_M` in `arduino/ttn_otaa_lmic/config.h`.
   - `config.h` is git-ignored by design; keep real credentials only in that local file.
   `bash scripts/compile_firmware.sh --output-dir build/firmware`
   The build script explicitly selects US915/RFM95 and allocates **64 KB** of
   LittleFS flash for the join-nonce journal. The default board setting has no
   filesystem and cannot operate the persistent join allocator.
4. Upload Arduino firmware:
   Update the TTN decoder below first, then:
   `arduino-cli upload -b rp2040:rp2040:adafruit_feather_rfm:flash=8388608_65536 -p /dev/ttyACM0 --input-dir build/firmware arduino/ttn_otaa_lmic`
5. Monitor serial runtime logs on `/dev/ttyACM0` and verify a measurement/send cycle appears once per minute.
6. Confirm uplinks in TTN for the same time window as serial logs.

## Firmware Watchdog

The hardware watchdog is armed before startup waits and peripheral initialization.
It resets the RP2040 after **8 seconds** without a feed; unsupported delays above
8388 ms fail compilation. The prior 20-second setting was invalid for RP2040.
Ultrasonic acquisition now advances one pulse at a time (45 ms maximum blocking
wait); settling, sample gaps and temperature conversion are scheduled stages.
LMIC receives service between stages, and acquisition yields around radio deadlines.

The supervisor also detects failures that leave the CPU running: a measurement
cycle exceeding 30 seconds resets the sensor state, a second consecutive stall
reboots; a joined radio with no progress for 3 minutes restarts joining, and a
subsequent radio stall reboots. Joining receives a 30-minute progress deadline.
Deliberate retry backoff (1 minute increasing to 1 hour) does not cause reboots.
Normal join attempts count as local progress even when the gateway is offline.
Local transmit completion does not prove network reception.

Measurements start on a fixed 60-second schedule independent of radio joining.
The latest completed measurement replaces older unsent data; there is no historical
backfill. Invalid readings still produce a packet containing working fields.
Default quality requirements are at least 16 valid samples out of 64 and a
cluster of at least three. Physical echo bounds default to 0.02–6 m; customize
`TIDEGAUGE_MIN_DISTANCE_M` / `TIDEGAUGE_MAX_DISTANCE_M` in local configuration.
After three temperature failures the bus is rediscovered and reconfigured.

ADR owns transmit power while enabled; the configured 10 dBm value applies only
when ADR is disabled. LMIC link recovery is enabled. Verify link margin at the
installed location and calculate airtime for the actual data rate; sampling once
per minute need not imply that every network permits transmitting that often.

Validated toolchain: Arduino CLI 1.4.1, Arduino-Pico 5.5.0, MCCI LMIC 5.0.1,
OneWire 2.3.8, DallasTemperature 4.0.6. Host checks use pytest, g++, Node.js,
PyYAML and Jinja2 already present on the development host. Build/test commands
do not install dependencies. Physical acceptance procedures and remaining
limitations are in [docs/reliability-validation.md](docs/reliability-validation.md).

## TTN Credentials (Arduino LMIC)

Set OTAA credentials in `arduino/ttn_otaa_lmic/config.h`:

- `DEV_EUI_HEX`
- `APP_EUI_HEX`
- `APP_KEY_HEX`
- `US915_SUBBAND`: human numbering **1–8**, converted to LMIC **0–7**. Value `2`
  selects channels 8–15 (LMIC index 1). Confirm against the gateway frequency plan.

Invalid credential syntax disables radio operation while sampling continues.
Channel fallback visits every group and returns to the preferred group.

Join nonces are reserved in blocks of 32 in `/join-nonce.bin` before use, using
an atomic LittleFS replacement and read-back verification. Reboots skip unused
reserved nonces. Preserve this filesystem and its allocation when updating
firmware; never erase it for ordinary recovery. Only a completely blank allocated
region is formatted automatically. Missing allocation, corrupt storage, failed
writes, or exhausted 16-bit nonce space stop joins with a serial error, rather
than silently reusing nonces. These faults require maintenance, not reboot loops.
First migration from the old random-nonce firmware must be checked against TTN's
stored nonce history and configured LoRaWAN version. Do not disable replay
protection to make joins succeed; coordinate reprovisioning if necessary.

## TTN Payload Formatter

Use `ttn/uplink_decoder.js` as the TTN JavaScript uplink payload formatter.

Normal uplinks on FPort 1 retain the 10-byte payload:

- Bytes `0-1`: `tide_height_mm` (signed int16, big-endian)
- Bytes `2-3`: `raw_distance_mm` (unsigned uint16, big-endian)
- Bytes `4-5`: `battery_mv` (unsigned uint16, big-endian)
- Bytes `6-7`: `distance_stddev_mm` (unsigned uint16, big-endian)
- Bytes `8-9`: `temperature_centi_c` (signed int16, big-endian)

Invalid optional measurements use sentinel values so one failed sensor reading
does not block the whole uplink:

- signed invalid sentinel: `0x8000`
- unsigned invalid sentinel: `0xFFFF`

Battery now also uses `0xFFFF` for unavailable, decoded as `null`.
The first queued packet and every 15th thereafter attempt a diagnostic extension
on FPort 2: **26 bytes** total, with the same first 10 bytes. Deploy the new decoder
before the firmware. If the current data rate cannot carry the extension, the
radio sends the 10-byte measurement at that data rate; diagnostic details may
therefore be unavailable on a weak link.

| Bytes | Diagnostic field (big-endian) |
| --- | --- |
| 10 | Schema version: 1 |
| 11 | Fault bits: 0 height, 1 temperature, 2 battery, 3 echo stuck high |
| 12 | Reset reason: 0 other/power-on, 1 sensor stall, 2 radio stall, 3 watchdog/other watchdog reset |
| 13 | Firmware revision: 2 |
| 14–17 | Uptime seconds (continues across `millis()` rollover) |
| 18–19 | Recovery count since boot |
| 20–21 | Valid echo count, timeout count |
| 22–23 | Watchdog reset count retained across watchdog resets; clears on cold start |
| 24–25 | Measurement sequence modulo 65536 |

## Home Assistant Filtering

The optional Home Assistant configuration in `homeassistant/tide_gauge_filter.yaml`
adds a post-TTN filtering pipeline for the decoded tide-height sensor.

Its purpose is to clean occasional ultrasonic outliers while preserving the slow
water-level trend:

1. hold the last valid numeric reading
2. compute a 10-minute rolling median
3. reject remaining outlier values outside recent history
4. apply light low-pass smoothing

This filter runs in Home Assistant, not on the RP2040. It should be merged into
an existing Home Assistant configuration carefully if that installation already
has top-level `template:` or `sensor:` sections.

Add `homeassistant/tide_gauge_freshness.yaml` to track last packet, last valid
height, and last valid temperature separately. It requires the actual TTN uplink
MQTT topic bridged into Home Assistant's broker; replace the placeholder topic
and merge the template lists. No account connection is configured by this repo.
Stale indicators turn on after five minutes without the relevant report, even
if filtering retains an old value. Use `sensor.tide_height_current` for the
freshness-gated dashboard reading. The templates use the server's `received_at`
timestamp, not MQTT replay/arrival time. See the official
[MQTT trigger documentation](https://www.home-assistant.io/docs/automation/templating/)
and [template integration](https://www.home-assistant.io/integrations/template).

## Sensor Wiring And Calibration

### Payload compatibility

The TTN decoder accepts the deployed 10-byte measurement payload, the compact
11-byte session-marker payload, the earlier 12-byte sequence payload, and the
26-byte diagnostic payload produced by firmware revision 2. For 11-byte
payloads, byte 10 uses bit 7 as `session_start` and bits 0–6 as the rolling
sample sequence. For 12-byte payloads, bytes 10–11 contain the sequence as an
unsigned big-endian integer. Keep the decoder installed before changing the
firmware payload format.

### Electrical safety

The HC-SR04 is powered from 5V. Its ECHO output must pass through a level
shifter or resistor divider before reaching RP2040 D5; never connect a 5V ECHO
signal directly to the RP2040. The DS18B20 data line uses D9 with a 4.7k pullup
to 3.3V.

HC-SR04 pinout (Feather labels):

- `TRIG` -> `D6`
- `ECHO` -> `D5`
- `VCC` -> `5V`
- `GND` -> `GND`

Firmware calibration constants are in `arduino/ttn_otaa_lmic/config.h`:

- `DISTANCE_SCALE`
- `DISTANCE_OFFSET_M`
- `GEOMETRY_REFERENCE_M`
- `DATUM_OFFSET_M`

Conversion formula:
`corrected_distance_m = measured_distance_m * distance_scale + distance_offset_m`
`tide_height_m = geometry_reference_m - corrected_distance_m - datum_offset_m`

Important electrical note:
`HC-SR04 ECHO` is a 5V signal and must be level-shifted (or resistor-divided) before feeding RP2040 `D5` (3.3V-only input).

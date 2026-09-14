# Unattended-node acceptance

Host tests and a successful compile do not establish that a radio, sensor power
switch, supply, or enclosure will recover in the field. Complete these checks
on the real Feather before installing it somewhere inaccessible.

## Build and migration

Use `bash scripts/compile_firmware.sh --output-dir build/firmware` with the
versions recorded in README. This pins regional compilation flags for both C
and C++, rather than relying on edits inside an installed LMIC library.
Keep local `config.h`, binaries, and TTN credentials out of git.

Verify US915 group 2 means LMIC index 1 and matches the actual gateway channel
plan. Confirm TTN MAC/PHY settings match the installed LMIC version. Firmware
does not become LoRaWAN 1.0.4/1.1 merely by using persistent nonces.

Install the new TTN decoder before firmware revision 2. Reserve the documented
64 KB filesystem and preserve it on future uploads. On first migration, check
TTN join events for previously used/non-increasing DevNonce errors: the old
firmware used random nonces and this release cannot infer the server's history.
If necessary, plan credential/device reprovisioning before field installation.
Do not erase the journal or weaken replay checks as an unattended workaround.

## Fault-injection acceptance

| Test | Required observation |
| --- | --- |
| Cold boot without USB console | Joins and reports without waiting indefinitely for serial |
| MCU stall in an isolated test build | Hardware reset within about 8 seconds; diagnostic reset reason 3 |
| Suppressed TX-complete event in test build | Radio recovery after about 3 minutes; samples continue |
| Radio progress remains absent after recovery | Reboot after join grace period, with reason 2 |
| Gateway off for several hours, then restored | Bounded join retries; no rapid reboot loop; reports resume |
| Echo disconnected or held high | Invalid height, timeout/echo flags; temperature and battery still transmit |
| Temperature sensor absent at boot, then reattached | Discovery retry restores temperature within roughly four sample cycles |
| Power interrupted during a nonce reservation | Next boot never reuses a nonce emitted before interruption |
| Corrupt nonce file (bench copy only) | Joining stops with explicit storage error; no autoformat |
| Weak radio link / lowest data rate | Measurements continue even when diagnostic extension does not fit |
| No MQTT packets for five minutes | Link and data stale; dashboard current height becomes unavailable |
| Packets with invalid height but valid temperature | Link remains current; height becomes stale independently |

Run a minimum 72-hour soak with the final wiring, battery supply, sensors,
enclosure and antenna. Include gateway outage/recovery, repeated sensor faults,
and cold starts. Inspect TTN frame counters, join failures, uplink spacing,
diagnostic resets and sample quality. Host simulations cover clock rollover,
long outages and failure escalation, but do not replace these measurements.

## Electrical checks

Measure supply voltage during radio TX and sensor startup; a healthy unloaded
battery does not establish adequate transient supply margin. Confirm echo level
shifting and pull-ups, power-switch polarity, a safe sensor-off state during MCU
reset, and actual sensor rail discharge when switched off. Inspect moisture
protection and cable strain relief. Verify radio reset wiring.

If a fault survives MCU and radio reset, evaluate an independent supervisor
that cycles power to the entire node with controlled backoff. That is a hardware
change requiring bench validation; it is not supplied by firmware alone.

## Operational limits

Only the latest measurement is queued, not an outage history. Diagnostic packets
are unconfirmed and can be lost, particularly at low data rates. A local TX
completion proves the radio cycle ended, not gateway/cloud reception. Persistent
nonce ranges consume 32 values per cold/recovery boot at minimum and eventually
exhaust the 16-bit namespace; avoid periodic gratuitous rebooting and monitor
join failures. The stored reset counter is retained SRAM, not a lifetime count.

Compute daily airtime at the deployed data rate, including joins and status
packets. TTN Community's fair-use allowance is 30 seconds uplink airtime/day and
10 downlinks/day. A private gateway connected to the community network does not
remove that allowance. If necessary, keep minute sampling but batch or reduce
transmissions as a separately tested site policy. See
[TTN duty-cycle and fair-use guidance](https://www.thethingsnetwork.org/docs/lorawan/duty-cycle/).

import path from "node:path";
import { fileURLToPath } from "node:url";
import express from "express";
import { config } from "./config.js";
import { connectMqtt } from "./mqtt.js";
import { openReadings } from "./readings.js";

const app = express();
const readings = openReadings(config.dbPath);
let mqttStatus = { connected: false, error: null };
let currentReading = null;
let currentTemperature = null;
let nextTide = null;
let currentBattery = null;

const mqttClient = connectMqtt(
  config.mqtt,
  (kind, value) => {
    if (kind === "height") currentReading = { height: value + config.heightOffsetMeters, recordedAt: Date.now() };
    if (kind === "temperature") currentTemperature = { temperature: value, temperatureRecordedAt: Date.now() };
    if (kind === "nextTide") {
      nextTide = value;
      readings.addTideEvent(value);
    }
    if (kind === "battery") currentBattery = { batteryVoltage: value, batteryRecordedAt: Date.now() };
  },
  (status) => { mqttStatus = status; }
);

app.disable("x-powered-by");
app.set("trust proxy", 1);
app.use(express.static(path.join(path.dirname(fileURLToPath(import.meta.url)), "../public"), {
  maxAge: 0,
  etag: true
}));

app.get("/api/status", (_request, response) => {
  response.json({
    mqtt: mqttStatus,
    unit: config.unit,
    temperatureUnit: "C",
    location: config.location,
    latest: withConversions(currentSnapshot()),
    tideState: tideState()
  });
});

app.get("/api/current", (_request, response) => {
  const reading = currentSnapshot();
  if (!reading) {
    return response.status(503).json({ error: "No tide reading has been received yet" });
  }
  response.json({
    ...withConversions(reading), unit: config.unit, temperatureUnit: "C",
    location: config.location, tideState: tideState()
  });
});

app.get("/api/history", (request, response) => {
  const hours = Math.min(Math.max(Number(request.query.hours) || 24, 1), 24 * 31);
  const start = Date.now() - hours * 3_600_000;
  const bucketMs = Math.max(1, Math.ceil((hours * 3_600_000) / 1_500));
  response.json({
    unit: config.unit,
    temperatureUnit: "C",
    location: config.location,
    readings: readings.since(start, bucketMs).map(withConversions)
  });
});

app.get("/api/export.csv", (request, response) => {
  const hours = Math.min(Math.max(Number(request.query.hours) || config.retentionDays * 24, 1), config.retentionDays * 24);
  const rows = readings.exportSince(Date.now() - hours * 3_600_000);
  const csv = [
    "timestamp_utc,tide_height_m,tide_height_ft,water_temperature_c,water_temperature_f,battery_voltage_v,battery_percent",
    ...rows.map((reading) => {
      const converted = withConversions(reading);
      return [
        new Date(converted.recordedAt).toISOString(),
        converted.height,
        converted.heightFeet,
        converted.temperature ?? "",
        converted.temperatureFahrenheit ?? "",
        converted.batteryVoltage ?? "",
        converted.batteryPercent ?? ""
      ].join(",");
    })
  ].join("\n");
  const date = new Date().toISOString().slice(0, 10);
  response
    .type("text/csv")
    .attachment(`church-creek-tide-gauge-${date}.csv`)
    .send(csv);
});

app.get("/health", (_request, response) => {
  response.status(mqttStatus.connected ? 200 : 503).json({ ok: mqttStatus.connected });
});

const server = app.listen(config.port, "0.0.0.0", () => {
  console.log(`Tide Gauge listening on port ${config.port}`);
});

function currentSnapshot() {
  const stored = readings.latest();
  if (!currentReading) return stored;
  return {
    ...currentReading,
    ...(currentTemperature || (stored?.temperature != null ? { temperature: stored.temperature } : {})),
    ...(currentBattery || {})
  };
}

function withConversions(reading) {
  if (!reading) return null;
  return {
    ...reading,
    heightFeet: reading.height * 3.28084,
    ...(reading.temperature == null ? {} : {
      temperatureFahrenheit: reading.temperature * 9 / 5 + 32
    }),
    ...(reading.batteryVoltage == null ? {} : {
      batteryPercent: Math.round(Math.min(100, Math.max(0, (reading.batteryVoltage - 3.0) / (4.2 - 3.0) * 100)))
    })
  };
}

function tideState() {
  const now = Date.now();
  const lastTide = readings.lastTideBefore(now);
  let rate = "slack";
  let cycleProgress = null;
  if (nextTide && lastTide && nextTide.nextTime > lastTide.eventTime) {
    cycleProgress = Math.min(1, Math.max(0, (now - lastTide.eventTime) / (nextTide.nextTime - lastTide.eventTime)));
    const strength = Math.sin(Math.PI * cycleProgress);
    rate = strength < 0.2 ? "slack" : strength < 0.65 ? "slow" : "rapid";
  }
  const flow = nextTide?.flow || "slack";
  return {
    flow,
    rate,
    cycleProgress,
    lastTide,
    nextTide: nextTide && {
      ...nextTide,
      nextHeight: nextTide.nextHeightFeet / 3.28084
    }
  };
}

// MQTT is push-based. Cache every message, then persist the newest value at a
// fixed cadence so the database contains regular time/height samples.
const sampleTimer = setInterval(() => {
  if (currentReading) {
    readings.add(
      currentReading.height,
      currentTemperature?.temperature ?? null,
      currentBattery?.batteryVoltage ?? null,
      Date.now()
    );
  }
}, config.sampleIntervalSeconds * 1_000);
sampleTimer.unref();

function pruneExpiredReadings() {
  readings.pruneBefore(Date.now() - config.retentionDays * 86_400_000);
}
pruneExpiredReadings();
const pruneTimer = setInterval(pruneExpiredReadings, 86_400_000);
pruneTimer.unref();

function shutdown() {
  clearInterval(sampleTimer);
  server.close(() => {
    mqttClient.end(true, () => {
      readings.close();
      process.exit(0);
    });
  });
  setTimeout(() => process.exit(1), 10_000).unref();
}
process.on("SIGINT", shutdown);
process.on("SIGTERM", shutdown);

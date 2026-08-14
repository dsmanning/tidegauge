import path from "node:path";

function number(name, fallback) {
  const value = process.env[name];
  if (value === undefined || value === "") return fallback;
  const parsed = Number(value);
  if (!Number.isFinite(parsed)) throw new Error(`${name} must be a number`);
  return parsed;
}

export const config = {
  port: number("PORT", 3000),
  dbPath: process.env.DB_PATH || path.resolve("data/tidegauge.sqlite"),
  retentionDays: number("RETENTION_DAYS", 30),
  sampleIntervalSeconds: number("SAMPLE_INTERVAL_SECONDS", 300),
  heightOffsetMeters: number("TIDE_HEIGHT_OFFSET_METERS", 0),
  unit: process.env.TIDE_UNIT || "ft",
  location: process.env.TIDE_LOCATION || "Church Creek",
  nextTideTimeZone: process.env.NEXT_TIDE_TIME_ZONE || "America/New_York",
  mqtt: {
    url: process.env.MQTT_URL || "mqtt://homeassistant.local:1883",
    topic: process.env.MQTT_TOPIC || "home/tide/current_height",
    temperatureTopic: process.env.MQTT_TEMPERATURE_TOPIC || "home/tide/water_temperature",
    nextTideTopic: process.env.MQTT_NEXT_TIDE_TOPIC || "home/tide/edgewater/next_tide",
    batteryTopic: process.env.MQTT_BATTERY_TOPIC || "home/tide/battery_voltage",
    nextTideTimeZone: process.env.NEXT_TIDE_TIME_ZONE || "America/New_York",
    username: process.env.MQTT_USERNAME || undefined,
    password: process.env.MQTT_PASSWORD || undefined,
    caFile: process.env.MQTT_CA_FILE || undefined,
    rejectUnauthorized: process.env.MQTT_REJECT_UNAUTHORIZED !== "false",
    format: process.env.MQTT_PAYLOAD_FORMAT || "plain",
    valuePath: process.env.MQTT_VALUE_PATH || "height",
    scale: number("MQTT_VALUE_SCALE", 1),
    temperatureScale: number("MQTT_TEMPERATURE_SCALE", 1),
    batteryScale: number("MQTT_BATTERY_SCALE", 1),
    temperatureFormat: process.env.MQTT_TEMPERATURE_PAYLOAD_FORMAT || "plain",
    temperatureValuePath: process.env.MQTT_TEMPERATURE_VALUE_PATH || "temperature"
  }
};

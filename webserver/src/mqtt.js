import fs from "node:fs";
import mqtt from "mqtt";

function nestedValue(object, valuePath) {
  return valuePath.split(".").reduce((value, key) => value?.[key], object);
}

export function parsePayload(payload, options) {
  const text = payload.toString("utf8").trim();
  let raw;
  if (options.format === "json") {
    raw = nestedValue(JSON.parse(text), options.valuePath);
  } else {
    raw = text;
  }
  const value = Number(raw) * options.scale;
  if (!Number.isFinite(value)) throw new Error("payload does not contain a finite number");
  return value;
}

export function parseNextTidePayload(payload, timeZone) {
  const value = JSON.parse(payload.toString("utf8"));
  if (!["high", "low"].includes(value.next_tide) || !["flooding", "ebbing"].includes(value.flow)) {
    throw new Error("payload has an invalid tide type or flow direction");
  }
  const heightFeet = Number(value.next_height_ft);
  if (!Number.isFinite(heightFeet)) throw new Error("payload does not contain a finite next_height_ft");
  const nextTime = zonedTimestamp(value.next_time, timeZone);
  if (!Number.isFinite(nextTime)) throw new Error("payload has an invalid next_time");
  return { nextTide: value.next_tide, nextTime, nextHeightFeet: heightFeet, flow: value.flow };
}

function zonedTimestamp(value, timeZone) {
  const match = /^(\d{4})-(\d{2})-(\d{2}) (\d{2}):(\d{2})$/.exec(value);
  if (!match) return Number.NaN;
  const [, year, month, day, hour, minute] = match.map(Number);
  const localAsUtc = Date.UTC(year, month - 1, day, hour, minute);
  const parts = new Intl.DateTimeFormat("en-US", {
    timeZone, timeZoneName: "longOffset", hour: "2-digit"
  }).formatToParts(new Date(localAsUtc));
  const offset = parts.find((part) => part.type === "timeZoneName")?.value;
  const offsetMatch = /^GMT([+-])(\d{2}):(\d{2})$/.exec(offset || "");
  if (!offsetMatch) return Number.NaN;
  const minutes = Number(offsetMatch[2]) * 60 + Number(offsetMatch[3]);
  return localAsUtc - (offsetMatch[1] === "+" ? minutes : -minutes) * 60_000;
}

export function connectMqtt(options, onReading, onStatus) {
  const connectionOptions = {
    username: options.username,
    password: options.password,
    rejectUnauthorized: options.rejectUnauthorized,
    reconnectPeriod: 5_000,
    connectTimeout: 15_000
  };
  if (options.caFile) connectionOptions.ca = fs.readFileSync(options.caFile);

  const client = mqtt.connect(options.url, connectionOptions);
  client.on("connect", () => {
    onStatus({ connected: true, error: null });
    client.subscribe([options.topic, options.temperatureTopic, options.nextTideTopic, options.batteryTopic], { qos: 1 }, (error) => {
      if (error) onStatus({ connected: true, error: error.message });
    });
  });
  client.on("reconnect", () => onStatus({ connected: false, error: null }));
  client.on("offline", () => onStatus({ connected: false, error: null }));
  client.on("error", (error) => onStatus({ connected: false, error: error.message }));
  client.on("message", (topic, payload) => {
    try {
      if (topic === options.topic) {
        onReading("height", parsePayload(payload, options));
      } else if (topic === options.temperatureTopic) {
        onReading("temperature", parsePayload(payload, {
          ...options,
          format: options.temperatureFormat,
          valuePath: options.temperatureValuePath,
          scale: options.temperatureScale
        }));
      } else if (topic === options.nextTideTopic) {
        onReading("nextTide", parseNextTidePayload(payload, options.nextTideTimeZone));
      } else if (topic === options.batteryTopic) {
        onReading("battery", parsePayload(payload, { ...options, format: "plain", scale: options.batteryScale }));
      }
    } catch (error) {
      onStatus({ connected: true, error: `Invalid MQTT payload: ${error.message}` });
    }
  });
  return client;
}

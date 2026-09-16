import fs from "node:fs";
import path from "node:path";
import Database from "better-sqlite3";

export function openReadings(dbPath) {
  fs.mkdirSync(path.dirname(dbPath), { recursive: true });
  const db = new Database(dbPath);
  db.pragma("journal_mode = WAL");
  db.exec(`
    CREATE TABLE IF NOT EXISTS readings (
      recorded_at INTEGER PRIMARY KEY,
      height REAL NOT NULL,
      water_temperature REAL,
      battery_voltage REAL
    );
    CREATE INDEX IF NOT EXISTS readings_recorded_at
      ON readings(recorded_at);
    CREATE TABLE IF NOT EXISTS tide_events (
      event_time INTEGER PRIMARY KEY,
      tide_type TEXT NOT NULL,
      height_feet REAL NOT NULL
    );
  `);
  const columns = db.prepare("PRAGMA table_info(readings)").all();
  if (!columns.some((column) => column.name === "water_temperature")) {
    db.exec("ALTER TABLE readings ADD COLUMN water_temperature REAL");
  }
  if (!columns.some((column) => column.name === "battery_voltage")) {
    db.exec("ALTER TABLE readings ADD COLUMN battery_voltage REAL");
  }

  const insert = db.prepare(`
    INSERT INTO readings (recorded_at, height, water_temperature, battery_voltage) VALUES (?, ?, ?, ?)
    ON CONFLICT(recorded_at) DO UPDATE SET
      height = excluded.height,
      water_temperature = excluded.water_temperature,
      battery_voltage = excluded.battery_voltage
  `);
  const latest = db.prepare(`
    SELECT recorded_at AS recordedAt, height, water_temperature AS temperature,
      battery_voltage AS batteryVoltage
    FROM readings ORDER BY recorded_at DESC LIMIT 1
  `);
  const history = db.prepare(`
    SELECT CAST(AVG(recorded_at) AS INTEGER) AS recordedAt,
      AVG(height) AS height,
      AVG(water_temperature) AS temperature,
      AVG(battery_voltage) AS batteryVoltage
    FROM readings
    WHERE recorded_at >= ?
    GROUP BY CAST(recorded_at / ? AS INTEGER)
    ORDER BY recordedAt
  `);
  const exportReadings = db.prepare(`
    SELECT recorded_at AS recordedAt, height, water_temperature AS temperature,
      battery_voltage AS batteryVoltage
    FROM readings
    WHERE recorded_at >= ?
    ORDER BY recorded_at
  `);
  const pruneReadings = db.prepare("DELETE FROM readings WHERE recorded_at < ?");
  const pruneTideEvents = db.prepare("DELETE FROM tide_events WHERE event_time < ?");
  const recent = db.prepare(`
    SELECT recorded_at AS recordedAt, height
    FROM readings ORDER BY recorded_at DESC LIMIT ?
  `);
  const addTideEvent = db.prepare(`
    INSERT INTO tide_events (event_time, tide_type, height_feet) VALUES (?, ?, ?)
    ON CONFLICT(event_time) DO UPDATE SET
      tide_type = excluded.tide_type,
      height_feet = excluded.height_feet
  `);
  const lastTideBefore = db.prepare(`
    SELECT event_time AS eventTime, tide_type AS tideType, height_feet AS heightFeet
    FROM tide_events WHERE event_time <= ? ORDER BY event_time DESC LIMIT 1
  `);

  return {
    add(height, temperature = null, batteryVoltage = null, recordedAt = Date.now()) {
      insert.run(Math.round(recordedAt), height, temperature, batteryVoltage);
    },
    latest() {
      return latest.get() || null;
    },
    since(timestamp, bucketMs = 1) {
      return history.all(timestamp, bucketMs);
    },
    exportSince(timestamp) {
      return exportReadings.all(timestamp);
    },
    pruneBefore(timestamp) {
      return {
        readings: pruneReadings.run(timestamp).changes,
        tideEvents: pruneTideEvents.run(timestamp).changes
      };
    },
    recent(limit = 2) {
      return recent.all(limit);
    },
    addTideEvent(event) {
      addTideEvent.run(event.nextTime, event.nextTide, event.nextHeightFeet);
    },
    lastTideBefore(timestamp) {
      return lastTideBefore.get(timestamp) || null;
    },
    close() {
      db.close();
    }
  };
}

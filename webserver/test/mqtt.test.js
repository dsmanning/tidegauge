import assert from "node:assert/strict";
import test from "node:test";
import { parsePayload } from "../src/mqtt.js";

test("parses and scales a plain numeric payload", () => {
  assert.equal(parsePayload(Buffer.from("1.5"), { format: "plain", scale: 2 }), 3);
});

test("reads a nested value from JSON", () => {
  const options = { format: "json", valuePath: "state.height", scale: 1 };
  assert.equal(parsePayload(Buffer.from('{"state":{"height":4.27}}'), options), 4.27);
});

test("rejects a non-numeric payload", () => {
  assert.throws(() => parsePayload(Buffer.from("unknown"), { format: "plain", scale: 1 }), /finite number/);
});

import { test } from "node:test";
import assert from "node:assert/strict";
import worker from "./index.js";

function envWithObject(value) {
  const requested = [];
  return {
    requested,
    env: { LIVE_DATA: { async get(key) {
      requested.push(key);
      return value;
    } } },
  };
}

test("GET serves only api/screens with JSON and no-store headers", async () => {
  const payload = '{"screens":[]}';
  const { env, requested } = envWithObject({
    body: payload,
    httpEtag: '"abc"',
    writeHttpMetadata(headers) { headers.set("Content-Type", "application/json"); },
  });
  const response = await worker.fetch(new Request("https://led.alf-broadcast.co.uk/api/screens"), env);
  assert.equal(response.status, 200);
  assert.equal(await response.text(), payload);
  assert.equal(response.headers.get("Content-Type"), "application/json");
  assert.equal(response.headers.get("Cache-Control"), "no-store, max-age=0");
  assert.ok(Number.isFinite(Date.parse(response.headers.get("Date"))));
  assert.equal(response.headers.get("ETag"), '"abc"');
  assert.deepEqual(requested, ["api/screens"]);
});

test("HEAD serves headers without a body", async () => {
  const { env } = envWithObject({ body: "secret", writeHttpMetadata() {} });
  const response = await worker.fetch(new Request("https://led.alf-broadcast.co.uk/api/screens", { method: "HEAD" }), env);
  assert.equal(response.status, 200);
  assert.equal(await response.text(), "");
});

test("other paths and methods never read R2", async () => {
  const { env, requested } = envWithObject(null);
  assert.equal((await worker.fetch(new Request("https://led.alf-broadcast.co.uk/api/other"), env)).status, 404);
  assert.equal((await worker.fetch(new Request("https://led.alf-broadcast.co.uk/api/screens", { method: "POST" }), env)).status, 405);
  assert.deepEqual(requested, []);
});

test("missing screen object returns 503", async () => {
  const { env } = envWithObject(null);
  assert.equal((await worker.fetch(new Request("https://led.alf-broadcast.co.uk/api/screens"), env)).status, 503);
});

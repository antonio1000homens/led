import assert from "node:assert/strict";
import { afterEach, test } from "node:test";

import worker from "../cloud/slicer-worker/src/index.js";

const originalFetch = globalThis.fetch;

afterEach(() => {
  globalThis.fetch = originalFetch;
});

function environment() {
  return {
    GITHUB_CODESPACES_TOKEN: "github-token",
    MCP_CLIENT_TOKEN: "client-token",
    ORIGIN_BEARER_TOKEN: "origin-token",
    CODESPACE_NAME: "test-codespace",
    CODESPACE_PORT: "8000",
    CODESPACE_ORIGIN: "https://origin.example.test",
    STARTUP_POLLS: "3",
    STARTUP_POLL_MS: "0",
    PORT_POLLS: "3",
    PORT_POLL_MS: "0",
    HEALTH_POLLS: "1",
    HEALTH_POLL_MS: "0",
  };
}

test("rejects missing and invalid client tokens before calling upstreams", async () => {
  globalThis.fetch = async () => {
    throw new Error("upstream should not be called");
  };

  for (const authorization of [undefined, "Bearer invalid"]) {
    const headers = authorization ? { authorization } : {};
    const response = await worker.fetch(
      new Request("https://slicer.example.test/health", { headers }),
      environment(),
    );
    assert.equal(response.status, 401);
  }
});

test("waits for the Codespace port to appear before making it public and proxying", async () => {
  const calls = [];
  let visibilityAttempts = 0;
  globalThis.fetch = async (input, init = {}) => {
    const url = String(input);
    calls.push({ url, method: init.method || "GET" });

    if (url === "https://api.github.com/user/codespaces/test-codespace") {
      return Response.json({ state: "available" });
    }
    if (url === "https://api.github.com/user/codespaces/test-codespace?internal=true&refresh=true") {
      return Response.json({
        connection: {
          tunnelProperties: {
            serviceUri: "https://global.rel.tunnels.api.visualstudio.com/",
            clusterId: "uks1",
            tunnelId: "test-tunnel",
            managePortsAccessToken: "manage-ports-token",
          },
        },
      });
    }
    if (url === "https://uks1.rel.tunnels.api.visualstudio.com/tunnels/test-tunnel/ports/8000?api-version=2023-09-27-preview") {
      visibilityAttempts += 1;
      assert.equal(init.method, "PUT");
      const headers = new Headers(init.headers);
      assert.equal(headers.get("authorization"), "Tunnel manage-ports-token");
      assert.equal(headers.get("if-match"), "*");
      assert.deepEqual(JSON.parse(init.body), {
        portNumber: 8000,
        accessControl: { entries: [{ type: "Anonymous", subjects: [], scopes: ["connect"] }] },
      });
      return new Response(null, { status: visibilityAttempts === 1 ? 404 : 204 });
    }
    if (url === "https://origin.example.test/health") {
      return new Response("healthy", { status: 200 });
    }
    if (url === "https://origin.example.test/mcp") {
      assert.equal(new Headers(init.headers).get("authorization"), "Bearer origin-token");
      return new Response("mcp response", { status: 200 });
    }
    throw new Error(`unexpected fetch: ${url}`);
  };

  const response = await worker.fetch(
    new Request("https://slicer.example.test/mcp", {
      method: "POST",
      headers: {
        authorization: "Bearer client-token",
        "content-type": "application/json",
      },
      body: JSON.stringify({ jsonrpc: "2.0", id: 1, method: "initialize" }),
    }),
    environment(),
  );

  assert.equal(response.status, 200);
  assert.equal(await response.text(), "mcp response");
  assert.equal(visibilityAttempts, 2);
  assert.ok(calls.findIndex((call) => call.url.includes("/tunnels/test-tunnel/ports/8000")) <
    calls.findIndex((call) => call.url === "https://origin.example.test/health"));
});

test("starts a stopped Codespace before configuring its port", async () => {
  const calls = [];
  let lookupCount = 0;
  globalThis.fetch = async (input, init = {}) => {
    const url = String(input);
    const method = init.method || "GET";
    calls.push({ url, method });

    if (url === "https://api.github.com/user/codespaces/test-codespace") {
      lookupCount += 1;
      return Response.json({ state: lookupCount === 1 ? "shutdown" : "available" });
    }
    if (url === "https://api.github.com/user/codespaces/test-codespace/start") {
      assert.equal(method, "POST");
      return new Response(null, { status: 202 });
    }
    if (url === "https://api.github.com/user/codespaces/test-codespace?internal=true&refresh=true") {
      return Response.json({
        connection: {
          tunnelProperties: {
            serviceUri: "https://global.rel.tunnels.api.visualstudio.com/",
            clusterId: "uks1",
            tunnelId: "test-tunnel",
            managePortsAccessToken: "manage-ports-token",
          },
        },
      });
    }
    if (url === "https://uks1.rel.tunnels.api.visualstudio.com/tunnels/test-tunnel/ports/8000?api-version=2023-09-27-preview") {
      assert.equal(method, "PUT");
      return new Response(null, { status: 200 });
    }
    if (url === "https://origin.example.test/health") return new Response("healthy", { status: 200 });
    if (url === "https://origin.example.test/mcp") return new Response("mcp response", { status: 200 });
    throw new Error(`unexpected fetch: ${url}`);
  };

  const response = await worker.fetch(
    new Request("https://slicer.example.test/health", {
      headers: { authorization: "Bearer client-token" },
    }),
    environment(),
  );

  assert.equal(response.status, 200);
  const startIndex = calls.findIndex((call) => call.url.endsWith("/start"));
  const tunnelIndex = calls.findIndex((call) => call.url.includes("/tunnels/test-tunnel/ports/8000"));
  assert.ok(startIndex >= 0);
  assert.ok(tunnelIndex > startIndex);
});

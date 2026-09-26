const GITHUB_API = "https://api.github.com";

function json(body, status = 200) {
  return new Response(JSON.stringify(body), { status, headers: { "content-type": "application/json" } });
}

function safeEqual(a, b) {
  if (typeof a !== "string" || typeof b !== "string" || a.length !== b.length) return false;
  let diff = 0;
  for (let i = 0; i < a.length; i += 1) diff |= a.charCodeAt(i) ^ b.charCodeAt(i);
  return diff === 0;
}

function bearer(request) {
  const value = request.headers.get("authorization") || "";
  return value.startsWith("Bearer ") ? value.slice(7) : "";
}

async function github(env, path, init = {}) {
  const headers = new Headers(init.headers || {});
  headers.set("authorization", "Bearer " + env.GITHUB_CODESPACES_TOKEN);
  headers.set("accept", "application/vnd.github+json");
  headers.set("x-github-api-version", "2022-11-28");
  headers.set("user-agent", "led-cloud-slicer");
  return fetch(GITHUB_API + path, { ...init, headers });
}

async function getCodespace(env) {
  const response = await github(env, "/user/codespaces/" + encodeURIComponent(env.CODESPACE_NAME));
  if (!response.ok) throw new Error("codespace lookup failed: " + response.status);
  return response.json();
}

async function ensurePublicPort(env) {
  const port = Number(env.CODESPACE_PORT || "8000");
  const path = "/user/codespaces/" + encodeURIComponent(env.CODESPACE_NAME) + "/ports/" + port + "/visibility";
  const response = await github(env, path, {
    method: "PUT",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ visibility: "public" }),
  });
  if (!response.ok) throw new Error("port visibility update failed: " + response.status);
}

async function startCodespace(env) {
  const path = "/user/codespaces/" + encodeURIComponent(env.CODESPACE_NAME) + "/start";
  const response = await github(env, path, { method: "POST" });
  if (!response.ok && response.status !== 409) throw new Error("codespace start failed: " + response.status);
}

function origin(env) {
  if (env.CODESPACE_ORIGIN) return env.CODESPACE_ORIGIN.replace(/\/$/, "");
  const port = env.CODESPACE_PORT || "8000";
  const domain = env.CODESPACE_FORWARDING_DOMAIN || "app.github.dev";
  return "https://" + env.CODESPACE_NAME + "-" + port + "." + domain;
}

async function sleep(ms) { await new Promise((resolve) => setTimeout(resolve, ms)); }

async function originHealthy(env) {
  try {
    const response = await fetch(origin(env) + "/health", {
      headers: { authorization: "Bearer " + env.ORIGIN_BEARER_TOKEN },
    });
    return response.ok;
  } catch {
    return false;
  }
}

async function ensureReady(env) {
  let codespace = await getCodespace(env);
  let state = String(codespace.state || "").toLowerCase();

  if (state !== "available") {
    if (!["starting", "rebuilding"].includes(state)) await startCodespace(env);
    const maxPolls = Number(env.STARTUP_POLLS || "12");
    const delayMs = Number(env.STARTUP_POLL_MS || "3000");
    for (let i = 0; i < maxPolls; i += 1) {
      await sleep(delayMs);
      codespace = await getCodespace(env);
      state = String(codespace.state || "").toLowerCase();
      if (state === "available") break;
    }
  }

  if (state !== "available") return { ok: false, state, error: "workspace_starting" };
  await ensurePublicPort(env);

  const healthPolls = Number(env.HEALTH_POLLS || "10");
  const healthDelayMs = Number(env.HEALTH_POLL_MS || "2000");
  for (let i = 0; i < healthPolls; i += 1) {
    if (await originHealthy(env)) return { ok: true, state };
    await sleep(healthDelayMs);
  }
  return { ok: false, state, error: "workspace_unavailable" };
}

async function proxy(request, env) {
  const incoming = new URL(request.url);
  const target = new URL(incoming.pathname + incoming.search, origin(env));
  const headers = new Headers(request.headers);
  headers.set("authorization", "Bearer " + env.ORIGIN_BEARER_TOKEN);
  headers.delete("host");
  headers.delete("cf-connecting-ip");
  headers.delete("cf-ray");
  return fetch(target.toString(), {
    method: request.method, headers,
    body: ["GET", "HEAD"].includes(request.method) ? undefined : request.body,
    redirect: "manual",
  });
}

export default {
  async fetch(request, env) {
    if (!env.MCP_CLIENT_TOKEN || !env.ORIGIN_BEARER_TOKEN || !env.GITHUB_CODESPACES_TOKEN || !env.CODESPACE_NAME) {
      return json({ ok: false, error: "proxy_not_configured" }, 503);
    }
    if (!safeEqual(bearer(request), env.MCP_CLIENT_TOKEN)) return json({ ok: false, error: "unauthorized" }, 401);
    const url = new URL(request.url);
    if (!["/mcp", "/health"].includes(url.pathname)) return json({ ok: false, error: "not_found" }, 404);
    let ready;
    try { ready = await ensureReady(env); }
    catch { return json({ ok: false, error: "workspace_control_failed" }, 502); }
    if (!ready.ok) return json(ready, 503);
    return proxy(request, env);
  },
};

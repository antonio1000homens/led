const SCREEN_KEY = "api/screens";

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    if (url.pathname !== "/api/screens") {
      return new Response("Not found", { status: 404 });
    }
    if (request.method !== "GET" && request.method !== "HEAD") {
      return new Response("Method not allowed", {
        status: 405,
        headers: { Allow: "GET, HEAD", "Cache-Control": "no-store" },
      });
    }

    const object = await env.LIVE_DATA.get(SCREEN_KEY);
    if (!object) {
      return new Response("Screen data unavailable", {
        status: 503,
        headers: { "Cache-Control": "no-store", "Content-Type": "text/plain; charset=utf-8" },
      });
    }

    const headers = new Headers();
    object.writeHttpMetadata(headers);
    headers.set("Content-Type", "application/json");
    headers.set("Cache-Control", "no-store, max-age=0");
    headers.set("Date", new Date().toUTCString());
    if (object.httpEtag) headers.set("ETag", object.httpEtag);
    return new Response(request.method === "HEAD" ? null : object.body, { status: 200, headers });
  },
};

// Cloudflare Worker — bypasses Daytona preview warning page.
// Forwards all traffic to the sandbox and injects the skip-warning header.

const DAYTONA_HOST = "8091-26f0e993-32b4-45f2-af64-a392bee6cc43.daytonaproxy01.eu";

export default {
  async fetch(request) {
    const url = new URL(request.url);
    const target = new URL(`https://${DAYTONA_HOST}${url.pathname}${url.search}`);

    const headers = new Headers(request.headers);
    headers.set("X-Daytona-Skip-Preview-Warning", "true");
    headers.set("Host", DAYTONA_HOST);

    return fetch(new Request(target.toString(), {
      method: request.method,
      headers,
      body: request.body,
      redirect: "follow",
    });
  },
};

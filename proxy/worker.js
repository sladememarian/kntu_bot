const DAYTONA_HOST = "8091-26f0e993-32b4-45f2-af64-a392bee6cc43.daytonaproxy01.eu";

addEventListener("fetch", function(event) {
  event.respondWith(handleRequest(event.request));
});

async function handleRequest(request) {
  var url = new URL(request.url);
  var target = new URL("https://" + DAYTONA_HOST + url.pathname + url.search);

  var headers = new Headers(request.headers);
  headers.set("X-Daytona-Skip-Preview-Warning", "true");
  headers.set("Host", DAYTONA_HOST);

  return fetch(new Request(target.toString(), {
    method: request.method,
    headers: headers,
    body: request.body,
    redirect: "follow",
  }));
}

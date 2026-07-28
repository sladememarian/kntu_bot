const DAYTONA_HOST = "8091-8365a2c3-5e86-45fc-bf95-6b58a1f6a309.daytonaproxy01.eu";

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

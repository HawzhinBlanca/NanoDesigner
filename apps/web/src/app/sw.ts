// Minimal SW: cache shell + thumbnails
self.addEventListener("install", (event: ExtendableEvent) => {
  event.waitUntil(caches.open("sgd-v1").then((c)=> c.addAll(["/", "/manifest.json"])))
});

self.addEventListener("fetch", (event: FetchEvent) => {
  const url = new URL(event.request.url);
  if (url.pathname.includes("/thumbnails/")) {
    event.respondWith((async () => {
      const cache = await caches.open("sgd-thumbs");
      const cached = await cache.match(event.request);
      if (cached) return cached;
      const res = await fetch(event.request);
      cache.put(event.request, res.clone());
      return res;
    })());
  }
});


const CACHE = "citizens-v1";
const OFFLINE_QUEUE_KEY = "offline-submissions";

// Cache shell on install
self.addEventListener("install", e => {
  e.waitUntil(
    caches.open(CACHE).then(c => c.addAll(["/", "/static/js/main.chunk.js"]))
      .catch(() => {}) // don't fail install if chunks not found yet
  );
  self.skipWaiting();
});

self.addEventListener("activate", e => {
  e.waitUntil(
    caches.keys().then(keys =>
      Promise.all(keys.filter(k => k !== CACHE).map(k => caches.delete(k)))
    )
  );
  self.clients.claim();
});

// Network-first for API, cache-first for assets
self.addEventListener("fetch", e => {
  const url = new URL(e.request.url);

  // Intercept submission POSTs when offline — queue them
  if (url.pathname.startsWith("/submissions/") && e.request.method === "POST") {
    e.respondWith(
      fetch(e.request.clone()).catch(async () => {
        const body = await e.request.clone().json().catch(() => ({}));
        const queue = JSON.parse(self.localStorage?.getItem(OFFLINE_QUEUE_KEY) || "[]");
        queue.push({ url: url.pathname, body, timestamp: Date.now() });
        // Store in IndexedDB via client message
        self.clients.matchAll().then(clients =>
          clients.forEach(c => c.postMessage({ type: "OFFLINE_QUEUED", count: queue.length }))
        );
        return new Response(JSON.stringify({
          status: "queued_offline",
          message: "Saved locally. Will submit when connection is restored."
        }), { headers: { "Content-Type": "application/json" } });
      })
    );
    return;
  }

  // Cache-first for static assets
  if (url.pathname.startsWith("/static/")) {
    e.respondWith(
      caches.match(e.request).then(cached => cached || fetch(e.request)
        .then(res => {
          const clone = res.clone();
          caches.open(CACHE).then(c => c.put(e.request, clone));
          return res;
        })
      )
    );
    return;
  }

  // Default: network with fallback to cache
  e.respondWith(
    fetch(e.request).catch(() => caches.match(e.request))
  );
});

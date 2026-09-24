const CACHE = "mai-os-v1";
const ASSETS = [
  "/",
  "/index.html",
  "/css/style.css",
  "/css/orb.css",
  "/css/animations.css",
  "/css/mobile.css",
  "/js/page-redirect.js",
  "/js/graph-toggle.js",
  "/js/desktop-nav.js",
  "/manifest.json",
];

self.addEventListener("install", (e) => {
  e.waitUntil(
    caches.open(CACHE).then((c) => c.addAll(ASSETS)).then(() => self.skipWaiting())
  );
});

self.addEventListener("activate", (e) => {
  e.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k)))
    ).then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", (e) => {
  if (e.request.url.startsWith("http")) {
    e.respondWith(
      caches.match(e.request).then((cached) => cached || fetch(e.request))
    );
  }
});

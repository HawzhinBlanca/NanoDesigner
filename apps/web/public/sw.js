/* global workbox */
self.addEventListener('install', (event) => {
  event.waitUntil(self.skipWaiting());
});

self.addEventListener('activate', (event) => {
  event.waitUntil(self.clients.claim());
});

importScripts('https://storage.googleapis.com/workbox-cdn/releases/6.5.4/workbox-sw.js');

if (self.workbox) {
  workbox.core.setCacheNameDetails({ prefix: 'sgd' });

  // Precache minimal shell files if needed
  // workbox.precaching.precacheAndRoute(self.__WB_MANIFEST || []);

  // Runtime cache: thumbnails with LRU 50 entries, 7 days
  workbox.routing.registerRoute(
    ({ url }) => url.pathname.includes('/thumbnails/'),
    new workbox.strategies.StaleWhileRevalidate({
      cacheName: 'sgd-thumbnails',
      plugins: [
        new workbox.expiration.ExpirationPlugin({ maxEntries: 50, maxAgeSeconds: 7 * 24 * 60 * 60 })
      ]
    })
  );

  // Images general
  workbox.routing.registerRoute(
    ({ request }) => request.destination === 'image',
    new workbox.strategies.StaleWhileRevalidate({ cacheName: 'sgd-images' })
  );
}


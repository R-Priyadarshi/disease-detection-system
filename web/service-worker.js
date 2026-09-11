/**
 * ALVEON PACS - Enterprise Progressive Web App (PWA) Service Worker
 * Provides offline caching, instantaneous sub-second application loading,
 * and clinical workstation resilience across hospital tablets & edge nodes.
 */

const CACHE_NAME = 'alveon-pacs-v5.2.0';
const STATIC_SHELL_ASSETS = [
  '/',
  '/workstation',
  '/landing',
  '/viewer',
  '/style.css',
  '/landing.css',
  '/app.js',
  '/manifest.json'
];

// 1. Install Event: Pre-cache static workstation shell
self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      return cache.addAll(STATIC_SHELL_ASSETS);
    }).then(() => self.skipWaiting())
  );
});

// 2. Activate Event: Clean up legacy caches
self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) => {
      return Promise.all(
        keys.map((key) => {
          if (key !== CACHE_NAME) {
            return caches.delete(key);
          }
        })
      );
    }).then(() => self.clients.claim())
  );
});

// 3. Fetch Event: Network-First for API calls, Stale-While-Revalidate for static assets
self.addEventListener('fetch', (event) => {
  const url = new URL(event.request.url);

  // Always use network for live API, DICOM, and prediction routes
  if (url.pathname.startsWith('/api/') || url.pathname.startsWith('/dicomweb/')) {
    return;
  }

  event.respondWith(
    caches.match(event.request).then((cachedResponse) => {
      const fetchPromise = fetch(event.request).then((networkResponse) => {
        if (networkResponse && networkResponse.status === 200) {
          const responseClone = networkResponse.clone();
          caches.open(CACHE_NAME).then((cache) => {
            cache.put(event.request, responseClone);
          });
        }
        return networkResponse;
      }).catch(() => {
        // Fallback to offline cached shell if available
        return cachedResponse;
      });

      return cachedResponse || fetchPromise;
    })
  );
});

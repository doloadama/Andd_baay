/**
 * Service Worker — Andd Baay PWA
 * Strategy: stale-while-revalidate for static assets,
 *            network-first for HTML pages.
 */
const CACHE_NAME = 'andd-baay-v1';
const STATIC_ASSETS = [
  '/static/css/base.css',
  '/static/css/dashboard.css',
  '/static/css/projects.css',
  '/static/css/mobile.css',
  '/static/js/base.js',
  '/static/js/main.js',
  '/static/js/pjax.js',
  '/static/js/tour.js',
  '/static/js/gps-button.js',
  '/static/js/image-compress.js',
  '/static/js/sw-update.js',
  '/static/manifest.json',
  '/static/images/logo.jpg',
  '/static/icons/icon-192x192.png',
  '/static/icons/icon-512x512.png',
  '/offline/',
  'https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css',
  'https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js',
  'https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css',
  'https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700;800&family=Space+Grotesk:wght@400;500;600;700&display=swap',
];

const OFFLINE_PAGE = '/offline/';

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      return cache.addAll(STATIC_ASSETS).catch(() => {
        // Some external assets may fail; don't block install
      });
    }).then(() => self.skipWaiting())
  );
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(
        keys.filter((k) => k !== CACHE_NAME).map((k) => caches.delete(k))
      )
    ).then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', (event) => {
  const { request } = event;
  const url = new URL(request.url);

  // Skip non-GET and external origins (unless it's a known CDN asset)
  if (request.method !== 'GET') return;

  const isSameOrigin = url.origin === self.location.origin;
  const isStaticAsset =
    url.pathname.startsWith('/static/') ||
    url.pathname.startsWith('/media/') ||
    url.host.includes('cdn.jsdelivr.net') ||
    url.host.includes('cdnjs.cloudflare.com') ||
    url.host.includes('fonts.googleapis.com') ||
    url.host.includes('fonts.gstatic.com');

  // 1. Static assets: stale-while-revalidate
  if (isStaticAsset) {
    event.respondWith(
      caches.open(CACHE_NAME).then(async (cache) => {
        const cached = await cache.match(request);
        const fetchPromise = fetch(request).then((response) => {
          if (response.ok) cache.put(request, response.clone());
          return response;
        }).catch(() => cached);
        return cached || fetchPromise;
      })
    );
    return;
  }

  // 2. HTML pages (same-origin, not API): network-first with offline fallback
  if (isSameOrigin && request.headers.get('accept')?.includes('text/html')) {
    event.respondWith(
      fetch(request)
        .then((response) => {
          if (response.ok) {
            const clone = response.clone();
            caches.open(CACHE_NAME).then((cache) => cache.put(request, clone));
          }
          return response;
        })
        .catch(() =>
          caches.match(request).then((cached) => {
            if (cached) return cached;
            return caches.match(OFFLINE_PAGE);
          })
        )
    );
    return;
  }

  // 3. Everything else: cache-first, fallback to network
  event.respondWith(
    caches.match(request).then((cached) => {
      if (cached) return cached;
      return fetch(request).catch(() => {
        // Silently fail for non-critical requests
      });
    })
  );
});

self.addEventListener('message', (event) => {
  if (event.data && event.data.action === 'skipWaiting') {
    self.skipWaiting();
  }
});

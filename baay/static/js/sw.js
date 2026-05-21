/**
 * Service Worker — Andd Baay PWA
 * Strategy: stale-while-revalidate for static assets,
 *            network-first for HTML pages.
 * v10: Ajout support offline Baay Simple (tâches + messagerie vocale).
 */
const CACHE_NAME = 'andd-baay-v10';

/** Toujours mis en cache (page hors ligne + PWA). */
const PRECACHE_CRITICAL = [
  '/offline/',
  '/dashboard/simple/',
  '/static/manifest.json',
  '/static/icons/icon-192x192.png',
  '/static/icons/icon-512x512.png',
  '/static/images/anddbaay-mark.svg',
  '/static/images/anddbaay-logo-wordmark.svg',
];

/** Ressources utiles ; l'échec d'un seul fichier ne bloque pas le reste. */
const PRECACHE_OPTIONAL = [
  '/static/css/base.css',
  '/static/css/dashboard.css',
  '/static/css/dashboard_cockpit.css',
  '/static/css/projects.css',
  '/static/css/projet-detail-modern.css',
  '/static/css/weather-widget.css',
  '/static/js/weather-widget.js',
  '/static/css/mobile.css',
  '/static/css/mobile-agri-pages.css',
  '/static/css/finance_hub_ft.css',
  '/static/css/semis-cards.css',
  '/static/css/messagerie-conversation.css',
  '/static/css/messagerie-drawer.css',
  '/static/css/home.css',
  '/static/js/base.js',
  '/static/js/main.js',
  '/static/js/pjax.js',
  '/static/js/tour.js',
  '/static/js/gps-button.js',
  '/static/js/image-compress.js',
  '/static/js/sw-update.js',
  '/static/vendor/bootstrap-5.3.0.min.css',
  '/static/vendor/bootstrap-5.3.0.bundle.min.js',
  '/static/vendor/chartjs-4.4.0.umd.min.js',
  '/static/vendor/chartjs-plugin-zoom-2.0.1.min.js',
  '/static/vendor/apexcharts-3.54.1.min.js',
  '/static/vendor/leaflet-1.9.4.min.js',
  '/static/vendor/leaflet-1.9.4.min.css',
  '/static/css/fa-subset.css',
  '/static/css/base-inline.css',
  '/static/css/animate-subset.css',
  '/static/css/tailwind.css',
  '/static/webfonts/fa-solid-900.woff2',
  '/static/webfonts/fa-brands-400.woff2',
  'https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;700&family=Space+Grotesk:wght@400;500;600;700&family=Inter:wght@400;500;600;700&display=swap',
];

const OFFLINE_PAGE = '/offline/';

/**
 * URLs POST interceptées hors-ligne et mises en file d'attente IndexedDB.
 * Rejoué automatiquement au retour du réseau (Background Sync).
 */
const OFFLINE_QUEUE_PATHS = [
  '/dashboard/simple/tache/',   // tache_terminer_simple
];

const QUEUE_DB  = 'baay_sw_queue';
const QUEUE_STR = 'post_queue';

// ── IndexedDB helpers ─────────────────────────────────────────────────────────

async function openQueueDB() {
  return new Promise((resolve, reject) => {
    const req = indexedDB.open(QUEUE_DB, 1);
    req.onupgradeneeded = e => e.target.result.createObjectStore(QUEUE_STR, { autoIncrement: true });
    req.onsuccess = e => resolve(e.target.result);
    req.onerror   = e => reject(e.target.error);
  });
}

async function queueRequest(url, method, body, headers) {
  const db = await openQueueDB();
  return new Promise((resolve, reject) => {
    const tx    = db.transaction(QUEUE_STR, 'readwrite');
    const store = tx.objectStore(QUEUE_STR);
    store.add({ url, method, body, headers, ts: Date.now() });
    tx.oncomplete = resolve;
    tx.onerror    = e => reject(e.target.error);
  });
}

async function replayQueue() {
  const db    = await openQueueDB();
  const tx    = db.transaction(QUEUE_STR, 'readwrite');
  const store = tx.objectStore(QUEUE_STR);

  const all  = await new Promise(res => { const r = store.getAll();     r.onsuccess = e => res(e.target.result); });
  const keys = await new Promise(res => { const r = store.getAllKeys(); r.onsuccess = e => res(e.target.result); });

  for (let i = 0; i < all.length; i++) {
    const item = all[i];
    try {
      await fetch(item.url, { method: item.method, body: item.body, headers: item.headers });
      store.delete(keys[i]);
    } catch (_) { /* conserver pour la prochaine tentative */ }
  }
}

// ── Cache helpers ─────────────────────────────────────────────────────────────

async function cacheOne(cache, url) {
  try {
    await cache.add(url);
  } catch (e) {
    console.warn('[sw] precache skip', url, e && e.message);
  }
}

// ── Lifecycle ─────────────────────────────────────────────────────────────────

self.addEventListener('install', (event) => {
  event.waitUntil(
    (async () => {
      const cache = await caches.open(CACHE_NAME);
      for (const url of PRECACHE_CRITICAL) {
        await cacheOne(cache, url);
      }
      await Promise.all(PRECACHE_OPTIONAL.map(url => cacheOne(cache, url)));
      await self.skipWaiting();
    })()
  );
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys()
      .then(keys => Promise.all(keys.filter(k => k !== CACHE_NAME).map(k => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

// ── Fetch ─────────────────────────────────────────────────────────────────────

self.addEventListener('fetch', (event) => {
  const { request } = event;
  const url = new URL(request.url);

  // Intercepter les POST vers les endpoints Baay Simple : file d'attente hors-ligne
  if (request.method === 'POST') {
    const isSimpleAction = OFFLINE_QUEUE_PATHS.some(p => url.pathname.startsWith(p));
    if (isSimpleAction) {
      event.respondWith(
        fetch(request.clone()).catch(async () => {
          const body    = await request.clone().text();
          const headers = {};
          request.headers.forEach((v, k) => { headers[k] = v; });
          await queueRequest(url.href, 'POST', body, headers);
          return new Response(
            JSON.stringify({ queued: true, message: 'Action sauvegardée hors-ligne.' }),
            { status: 202, headers: { 'Content-Type': 'application/json' } }
          );
        })
      );
      return;
    }
    return; // Autres POST : pas d'interception
  }

  if (request.method !== 'GET') return;

  const isSameOrigin  = url.origin === self.location.origin;
  const isStaticAsset =
    url.pathname.startsWith('/static/') ||
    url.pathname.startsWith('/media/') ||
    url.host.includes('fonts.googleapis.com') ||
    url.host.includes('fonts.gstatic.com');

  // Statique : stale-while-revalidate
  if (isStaticAsset) {
    event.respondWith(
      caches.open(CACHE_NAME).then(async (cache) => {
        const cached       = await cache.match(request);
        const fetchPromise = fetch(request).then(response => {
          if (response.ok) cache.put(request, response.clone());
          return response;
        }).catch(() => cached);
        return cached || fetchPromise;
      })
    );
    return;
  }

  // HTML : network-first avec fallback cache puis /offline/
  if (isSameOrigin && request.headers.get('accept')?.includes('text/html')) {
    event.respondWith(
      fetch(request)
        .then(response => {
          if (response.ok) {
            caches.open(CACHE_NAME).then(cache => cache.put(request, response.clone()));
          }
          return response;
        })
        .catch(async () => {
          const cached = await caches.match(request);
          if (cached) return cached;
          return caches.match(OFFLINE_PAGE);
        })
    );
    return;
  }

  // Autres : cache-first
  event.respondWith(
    caches.match(request).then(cached => {
      if (cached) return cached;
      return fetch(request).catch(() => new Response('', { status: 503, statusText: 'Service Unavailable' }));
    })
  );
});

// ── Messages ──────────────────────────────────────────────────────────────────

self.addEventListener('message', (event) => {
  if (event.data && event.data.action === 'skipWaiting') {
    self.skipWaiting();
  }
});

// ── Background Sync ───────────────────────────────────────────────────────────

self.addEventListener('sync', (event) => {
  if (event.tag === 'baay-offline-queue') {
    event.waitUntil(replayQueue());
  }
});

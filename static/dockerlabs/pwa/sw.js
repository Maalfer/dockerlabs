/* DockerLabs service worker.
 * - /static/*  : cache-first (las URLs llevan ?v=<mtime>, así que son inmutables).
 * - /img/*     : stale-while-revalidate con tope de entradas.
 * - navegación : red primero; sin red -> /offline. El HTML nunca se cachea
 *                (lleva CSRF y datos de sesión).
 * - /api/ y resto de métodos que no son GET: siempre a la red, sin tocar.
 */
const VERSION = 'v1';
const STATIC_CACHE = 'dl-static-' + VERSION;
const IMG_CACHE = 'dl-img-' + VERSION;
const PAGE_CACHE = 'dl-pages-' + VERSION;
const OFFLINE_URL = '/offline';
const IMG_MAX = 120;
const NAV_TIMEOUT_MS = 8000;

const PRECACHE = [
  OFFLINE_URL,
  '/static/dockerlabs/images/pwa/icon-192.png',
];

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(PAGE_CACHE).then((c) => c.addAll(PRECACHE)).then(() => self.skipWaiting())
  );
});

self.addEventListener('activate', (event) => {
  const keep = [STATIC_CACHE, IMG_CACHE, PAGE_CACHE];
  event.waitUntil(
    caches.keys()
      .then((keys) => Promise.all(keys.filter((k) => k.startsWith('dl-') && !keep.includes(k)).map((k) => caches.delete(k))))
      .then(() => self.registration.navigationPreload && self.registration.navigationPreload.enable())
      .then(() => self.clients.claim())
  );
});

async function trim(cacheName, max) {
  const cache = await caches.open(cacheName);
  const keys = await cache.keys();
  for (let i = 0; i < keys.length - max; i++) await cache.delete(keys[i]);
}

async function cacheFirst(request) {
  const cache = await caches.open(STATIC_CACHE);
  const hit = await cache.match(request);
  if (hit) return hit;
  const res = await fetch(request);
  if (res.ok) cache.put(request, res.clone());
  return res;
}

async function staleWhileRevalidate(request, cacheName, max) {
  const cache = await caches.open(cacheName);
  const hit = await cache.match(request);
  const net = fetch(request).then((res) => {
    if (res.ok) { cache.put(request, res.clone()).then(() => trim(cacheName, max)); }
    return res;
  }).catch(() => hit);
  return hit || net;
}

async function navigate(event) {
  try {
    const preload = event.preloadResponse && await event.preloadResponse;
    if (preload) return preload;
    const ctrl = new AbortController();
    const t = setTimeout(() => ctrl.abort(), NAV_TIMEOUT_MS);
    try {
      return await fetch(event.request, { signal: ctrl.signal });
    } finally {
      clearTimeout(t);
    }
  } catch (_) {
    const cache = await caches.open(PAGE_CACHE);
    return (await cache.match(OFFLINE_URL)) || Response.error();
  }
}

self.addEventListener('fetch', (event) => {
  const req = event.request;
  if (req.method !== 'GET') return;
  const url = new URL(req.url);
  if (url.origin !== self.location.origin) return;

  if (req.mode === 'navigate') {
    event.respondWith(navigate(event));
    return;
  }
  if (url.pathname.startsWith('/static/')) {
    event.respondWith(cacheFirst(req).catch(() => fetch(req)));
    return;
  }
  if (url.pathname.startsWith('/img/')) {
    event.respondWith(staleWhileRevalidate(req, IMG_CACHE, IMG_MAX));
  }
});

self.addEventListener('message', (event) => {
  if (event.data === 'SKIP_WAITING') self.skipWaiting();
});

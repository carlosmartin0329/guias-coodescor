// Service Worker para Guías Coodescor - PWA
// Versión incrementada cada fix para invalidar cache viejo
const CACHE_NAME = 'guias-coodescor-v20260922-b';
const OFFLINE_URL = '/login';
// Bypass TOTAL para: JS/CSS/HTML, rutas /firma/* (token publico SIN login),
// /api/* (APIs nunca cachear), /static_file/* (adjuntos).
// Esto evita que el SW intercepté llamadas sin sesión y caiga en OFFLINE_URL /login.
const BYPASS_SW_RE = /\.(js|css|html)$|^\/firma\/|^\/api\/|^\/static_file\//i;

const ASSETS_TO_CACHE = [
  '/',
  '/login',
  '/static/manifest.json',
  '/static/icons/icon-192x192.png',
  '/static/icons/icon-512x512.png'
];

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then((cache) => {
        console.log('SW: instalado, cache inicial', CACHE_NAME);
        return cache.addAll(ASSETS_TO_CACHE);
      })
      .then(() => self.skipWaiting())
      .catch((err) => console.warn('SW: install falló', err))
  );
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) => Promise.all(
      keys.filter((k) => k !== CACHE_NAME).map((k) => {
        console.log('SW: borrando cache viejo', k);
        return caches.delete(k);
      })
    )).then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', (event) => {
  const url = new URL(event.request.url);
  // Bypass total: SIEMPRE a red SIN pasar por cache SW.
  // Obligatorio para /firma/<token> (pública) y /api/* (dinámico)
  if (BYPASS_SW_RE.test(url.pathname)) {
    event.respondWith(fetch(event.request).catch(() => caches.match(OFFLINE_URL)));
    return;
  }
  if (event.request.method === 'GET') {
    event.respondWith(
      caches.match(event.request).then((cached) => {
        if (cached) return cached;
        return fetch(event.request).then((resp) => {
          if (resp && resp.ok && resp.type === 'basic' && !BYPASS_SW_RE.test(url.pathname)) {
            const clone = resp.clone();
            caches.open(CACHE_NAME).then((c) => c.put(event.request, clone)).catch(()=>{});
          }
          return resp;
        }).catch(() => caches.match(OFFLINE_URL));
      })
    );
  } else {
    event.respondWith(fetch(event.request).catch(() => new Response('Sin conexión', {status: 502})));
  }
});

self.addEventListener('message', (ev) => {
  if (ev.data && ev.data.action === 'skipWaiting') self.skipWaiting();
});

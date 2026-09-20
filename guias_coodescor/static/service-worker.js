// Service Worker para Guías Coodescor - PWA
// Permite funcionamiento offline básico y caching de recursos

const CACHE_NAME = 'guias-coodescor-v2';
const OFFLINE_URL = '/login';

// Archivos esenciales para cachear
const ASSETS_TO_CACHE = [
  '/',
  '/login',
  '/tablero',
  '/guias',
  '/static/style.css',
  '/static/app.js',
  '/static/manifest.json',
  '/static/icons/icon-192x192.png',
  '/static/icons/icon-512x512.png'
];

// Instalación: cachea recursos esenciales
self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then((cache) => {
        console.log('Service Worker: Cache abierto');
        return cache.addAll(ASSETS_TO_CACHE);
      })
      .then(() => {
        console.log('Service Worker: Recursos cacheados');
        return self.skipWaiting();
      })
      .catch((error) => {
        console.error('Service Worker: Error al cachear', error);
      })
  );
});

// Activación: limpia caches antiguos
self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((cacheNames) => {
      return Promise.all(
        cacheNames.map((cacheName) => {
          if (cacheName !== CACHE_NAME) {
            console.log('Service Worker: Eliminando cache antiguo', cacheName);
            return caches.delete(cacheName);
          }
        })
      );
    })
      .then(() => {
        console.log('Service Worker: Activado');
        return self.clients.claim();
      })
  );
});

// Intercepción de peticiones
self.addEventListener('fetch', (event) => {
  // Para peticiones GET, intentamos servir desde cache primero
  if (event.request.method === 'GET') {
    event.respondWith(
      caches.match(event.request)
        .then((cachedResponse) => {
          // Si está en cache, lo devolvemos
          if (cachedResponse) {
            console.log('Service Worker: Sirviendo desde cache', event.request.url);
            return cachedResponse;
          }
          
          // Si no está en cache, lo buscamos en la red y cacheamos
          return fetch(event.request)
            .then((response) => {
              // Cacheamos solo respuestas exitosas
              if (response && response.status === 200 && response.type === 'basic') {
                const responseToCache = response.clone();
                caches.open(CACHE_NAME)
                  .then((cache) => {
                    cache.put(event.request, responseToCache);
                    console.log('Service Worker: Cacheando', event.request.url);
                  });
              }
              return response;
            })
            .catch((error) => {
              console.error('Service Worker: Error al fetch', error);
              // Si falla la red y no hay cache, mostramos página offline
              return caches.match(OFFLINE_URL) || 
                     new Response('<h1>Sin conexión</h1><p>Intenta más tarde.</p>', {
                       status: 200,
                       headers: { 'Content-Type': 'text/html' }
                     });
            });
        })
    );
  } else {
    // Para POST y otras peticiones, vamos directamente a la red
    event.respondWith(fetch(event.request));
  }
});

// Mensajes del cliente
self.addEventListener('message', (event) => {
  if (event.data.action === 'skipWaiting') {
    self.skipWaiting();
  }
});

// Service Worker de transición.
//
// La PWA anterior cacheaba / y /login con la interfaz HTML vieja. Desde el
// rediseño la aplicación se sirve como SPA React, así que este trabajador se
// limita a desregistrarse y borrar las cachés antiguas para que el navegador
// cargue siempre la interfaz nueva.
self.addEventListener('install', () => {
  self.skipWaiting();
});

self.addEventListener('activate', (event) => {
  event.waitUntil((async () => {
    try {
      const keys = await caches.keys();
      await Promise.all(keys.map((key) => caches.delete(key)));
    } catch (err) {
      // Sin Cache API disponible: no impide el desregistro.
    }
    try {
      await self.registration.unregister();
    } catch (err) {
      // El navegador puede no permitir el desregistro desde el SW.
    }
    const clientes = await self.clients.matchAll({ type: 'window' });
    clientes.forEach((cliente) => {
      if (cliente.url) {
        try { cliente.navigate(cliente.url); } catch (e) { /* sin permiso */ }
      }
    });
  })());
});

const CACHE_NAME = 'studywawa-cache-v4';
const ASSETS = [
  '/styles.css',
  '/atlas-theme.css',
  '/components.css',
  '/script.js',
  '/atlas.js',
  '/components.js',
  '/logo.png',
  '/apple-touch-icon.png',
  '/icon-512.png',
  '/manifest.webmanifest'
];

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => cache.addAll(ASSETS))
  );
  self.skipWaiting();
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(
        keys.filter((key) => key !== CACHE_NAME).map((key) => caches.delete(key))
      )
    )
  );
  self.clients.claim();
});

self.addEventListener('fetch', (event) => {
  if (event.request.method !== 'GET' || event.request.url.includes('/api/')) return;

  // Páginas HTML (navegación): SIEMPRE de red primero. Es la única forma de
  // asegurar que la app se actualice sola en cada visita — antes esto se
  // guardaba en caché para siempre y una vez cacheada una página vieja/rota,
  // Ctrl+Shift+R no la sacaba nunca (el service worker intercepta el pedido
  // antes de que llegue a la red). Solo si no hay conexión, cae al caché
  // como último recurso para que la app no quede totalmente en blanco.
  if (event.request.mode === 'navigate') {
    event.respondWith(
      fetch(event.request).catch(() => caches.match(event.request))
    );
    return;
  }

  // Assets estáticos (css/js/imágenes): caché primero, y de paso los
  // actualiza en segundo plano para la próxima vez (stale-while-revalidate).
  event.respondWith(
    caches.match(event.request).then((cached) => {
      const fetchPromise = fetch(event.request).then((response) => {
        const clone = response.clone();
        caches.open(CACHE_NAME).then((cache) => cache.put(event.request, clone));
        return response;
      });
      return cached || fetchPromise;
    })
  );
});

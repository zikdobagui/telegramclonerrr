const CACHE_NAME = 'telegram-automation-v2.2.9';
const urlsToCache = [
  '/',
  '/static/style.css',
  '/static/script.js',
  '/static/manifest.json',
  'https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css',
  'https://cdn.socket.io/4.5.4/socket.io.min.js'
];

// Instalação do Service Worker
self.addEventListener('install', event => {
  console.log('[Service Worker] Instalando...');
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then(cache => {
        console.log('[Service Worker] Cache aberto');
        return cache.addAll(urlsToCache);
      })
      .catch(err => {
        console.error('[Service Worker] Erro ao cachear:', err);
      })
  );
  self.skipWaiting();
});

// Ativação do Service Worker
self.addEventListener('activate', event => {
  console.log('[Service Worker] Ativando...');
  event.waitUntil(
    caches.keys().then(cacheNames => {
      return Promise.all(
        cacheNames.map(cacheName => {
          if (cacheName !== CACHE_NAME) {
            console.log('[Service Worker] Removendo cache antigo:', cacheName);
            return caches.delete(cacheName);
          }
        })
      );
    })
  );
  self.clients.claim();
});

// Estratégia de cache: Network First, fallback para Cache
self.addEventListener('fetch', event => {
  // Ignora requisições que não são GET
  if (event.request.method !== 'GET') {
    return;
  }

  // Ignora requisições de API e Socket.IO
  if (event.request.url.includes('/api/') || 
      event.request.url.includes('/socket.io/')) {
    return;
  }

  event.respondWith(
    fetch(event.request)
      .then(response => {
        // Se a resposta é válida, clona e salva no cache
        if (response && response.status === 200) {
          const responseToCache = response.clone();
          caches.open(CACHE_NAME)
            .then(cache => {
              cache.put(event.request, responseToCache);
            });
        }
        return response;
      })
      .catch(() => {
        // Se falhar, tenta buscar do cache
        return caches.match(event.request)
          .then(response => {
            if (response) {
              return response;
            }
            // Se não encontrar no cache, retorna página offline
            if (event.request.mode === 'navigate') {
              return caches.match('/');
            }
          });
      })
  );
});

// Notificações Push (opcional)
self.addEventListener('push', event => {
  const options = {
    body: event.data ? event.data.text() : 'Nova notificação',
    icon: '/static/icon-192.png',
    badge: '/static/icon-72.png',
    vibrate: [200, 100, 200],
    tag: 'telegram-automation',
    requireInteraction: false
  };

  event.waitUntil(
    self.registration.showNotification('Telegram Automation', options)
  );
});

// Click em notificação
self.addEventListener('notificationclick', event => {
  event.notification.close();
  event.waitUntil(
    clients.openWindow('/')
  );
});

// Sincronização em background (opcional)
self.addEventListener('sync', event => {
  if (event.tag === 'sync-data') {
    event.waitUntil(syncData());
  }
});

async function syncData() {
  try {
    // Implementar sincronização de dados aqui
    console.log('[Service Worker] Sincronizando dados...');
  } catch (error) {
    console.error('[Service Worker] Erro na sincronização:', error);
  }
}

console.log('[Service Worker] Carregado com sucesso!');

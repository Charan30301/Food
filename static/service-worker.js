
const CACHE_NAME = 'food-centre-pwa-v2';
const APP_SHELL = [
  '/static/icons/customer-192.png',
  '/static/icons/reception-192.png',
  '/static/icons/chef-192.png'
];

self.addEventListener('install', event => {
  event.waitUntil(caches.open(CACHE_NAME).then(cache => cache.addAll(APP_SHELL)).then(() => self.skipWaiting()));
});

self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys().then(keys => Promise.all(keys.filter(k => k !== CACHE_NAME).map(k => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', event => {
  const request = event.request;
  if (request.method !== 'GET') return;
  const url = new URL(request.url);
  if (url.origin !== self.location.origin) return;

  // Network-first for pages/API data so order information is never stale.
  if (request.mode === 'navigate' || url.pathname.startsWith('/api/')) {
    event.respondWith(
      fetch(request).catch(() => caches.match(request).then(r => r || new Response('Offline', {status:503})))
    );
    return;
  }

  event.respondWith(
    fetch(request).then(response => {
      const copy = response.clone();
      caches.open(CACHE_NAME).then(cache => cache.put(request, copy));
      return response;
    }).catch(() => caches.match(request))
  );
});

self.addEventListener('push', event => {
  let data = {};
  try { data = event.data ? event.data.json() : {}; } catch (_) {}
  const title = data.title || 'Food Centre';
  const options = {
    body: data.body || 'You have a new update.',
    icon: data.icon || '/static/icons/customer-192.png',
    badge: data.badge || '/static/icons/customer-192.png',
    tag: data.tag || 'food-centre',
    renotify: true,
    requireInteraction: true,
    data: {url: data.url || '/'}
  };
  event.waitUntil(self.registration.showNotification(title, options));
});

self.addEventListener('notificationclick', event => {
  event.notification.close();
  const target = event.notification.data?.url || '/';
  event.waitUntil(
    clients.matchAll({type:'window', includeUncontrolled:true}).then(list => {
      for (const client of list) {
        if ('focus' in client) {
          client.navigate(target);
          return client.focus();
        }
      }
      return clients.openWindow(target);
    })
  );
});

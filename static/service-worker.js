self.addEventListener('push', event => {
  let data = { title: 'Food order update', body: 'Your order has been updated.', url: '/' };
  try { if (event.data) data = { ...data, ...event.data.json() }; } catch (_) {}
  event.waitUntil(self.registration.showNotification(data.title || 'Food order update', {
    body: data.body || 'Your order has been updated.', icon: '/static/icon-192.png',
    badge: '/static/icon-192.png', data: { url: data.url || '/' },
    tag: 'food-order-update', renotify: true
  }));
});
self.addEventListener('notificationclick', event => {
  event.notification.close();
  const url = new URL(event.notification.data?.url || '/', self.location.origin).href;
  event.waitUntil(clients.matchAll({ type: 'window', includeUncontrolled: true }).then(list => {
    for (const client of list) if (client.url.startsWith(self.location.origin) && 'focus' in client) { client.navigate(url); return client.focus(); }
    return clients.openWindow ? clients.openWindow(url) : undefined;
  }));
});

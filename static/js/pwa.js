
(() => {
  const role = window.PWA_ROLE || document.body?.dataset?.pwaRole || (
    location.pathname.startsWith('/chef') ? 'chef' :
    location.pathname.startsWith('/admin') ? 'reception' : 'customer'
  );

  function b64ToUint8Array(base64) {
    const padding = '='.repeat((4 - base64.length % 4) % 4);
    const raw = atob((base64 + padding).replace(/-/g, '+').replace(/_/g, '/'));
    return Uint8Array.from([...raw].map(c => c.charCodeAt(0)));
  }

  async function registerSW() {
    if (!('serviceWorker' in navigator)) return null;
    try { return await navigator.serviceWorker.register('/service-worker.js', {scope:'/'}); }
    catch (e) { console.warn('Service worker registration failed', e); return null; }
  }

  async function getPushConfig() {
    const res = await fetch('/api/push/config', {cache:'no-store'});
    if (!res.ok) throw new Error('Notification service unavailable');
    return res.json();
  }

  async function subscribeNotifications() {
    if (!('Notification' in window) || !('PushManager' in window)) {
      throw new Error('This browser does not support push notifications.');
    }
    const permission = await Notification.requestPermission();
    if (permission !== 'granted') throw new Error('Notification permission was not granted.');

    const config = await getPushConfig();
    if (!config.enabled || !config.public_key) {
      throw new Error('Push notifications are not configured on the server yet.');
    }

    const registration = await registerSW();
    if (!registration) throw new Error('Service worker is unavailable.');

    let subscription = await registration.pushManager.getSubscription();
    if (!subscription) {
      subscription = await registration.pushManager.subscribe({
        userVisibleOnly: true,
        applicationServerKey: b64ToUint8Array(config.public_key)
      });
    }

    const res = await fetch('/api/push/subscribe', {
      method:'POST',
      headers:{'Content-Type':'application/json'},
      body:JSON.stringify({role, subscription:subscription.toJSON()})
    });
    const data = await res.json();
    if (!res.ok || !data.success) throw new Error(data.error || 'Could not save notification subscription.');
    localStorage.setItem(`push-enabled-${role}`, '1');
    return true;
  }

  function foregroundNotification(title, body, url) {
    if (!('Notification' in window) || Notification.permission !== 'granted') return;
    if (document.visibilityState === 'visible') {
      try {
        const n = new Notification(title, {body, icon:`/static/icons/${role}-192.png`, tag:`foreground-${role}`});
        n.onclick = () => { window.focus(); if (url) location.href = url; };
      } catch (_) {}
    }
  }

  window.enableAppNotifications = async () => {
    return subscribeNotifications();
  };
  window.appPopupNotification = foregroundNotification;

  registerSW();


  function updateNotificationButton(button) {
    if (!button || !('Notification' in window)) return;
    const statusEl = button.querySelector('[data-notification-status]');
    const setLabel = (text) => {
      if (statusEl) statusEl.textContent = text;
      else button.textContent = text;
    };
    if (Notification.permission === 'granted') {
      setLabel('Notifications ON');
      button.dataset.enabled = '1';
      button.disabled = false;
      return;
    }
    if (Notification.permission === 'denied') {
      setLabel('Notifications blocked');
      button.dataset.enabled = '0';
      button.disabled = false;
      return;
    }
    setLabel('Enable notifications');
    button.dataset.enabled = '0';
    button.disabled = false;
  }

  async function bindNotificationButton(button) {
    if (!button) return;
    updateNotificationButton(button);
    button.addEventListener('click', async () => {
      if (Notification.permission === 'granted') {
        updateNotificationButton(button);
        return;
      }
      button.disabled = true;
      try {
        await subscribeNotifications();
        const statusEl = button.querySelector('[data-notification-status]');
        if (statusEl) statusEl.textContent = 'Notifications ON';
        else button.textContent = '🔔 Notifications ON';
        button.dataset.enabled = '1';
      } catch (e) {
        button.disabled = false;
        updateNotificationButton(button);
        console.warn(e);
      }
    });
  }

  window.updateAppNotificationButton = updateNotificationButton;
  window.bindAppNotificationButton = bindNotificationButton;

  document.addEventListener('DOMContentLoaded', () => {
    const installButton = document.getElementById('installButton');
    const notificationButton = document.getElementById('notificationButton');
    const status = document.getElementById('status');

    let deferredPrompt = null;

    window.addEventListener('beforeinstallprompt', e => {
      e.preventDefault();
      deferredPrompt = e;
      if (installButton) {
        installButton.disabled = false;
        installButton.textContent = `Install ${role[0].toUpperCase()+role.slice(1)} App`;
      }
      if (status) status.textContent = 'Ready to install.';
    });

    if (installButton) {
      installButton.addEventListener('click', async () => {
        if (deferredPrompt) {
          deferredPrompt.prompt();
          const choice = await deferredPrompt.userChoice;
          deferredPrompt = null;
          if (status) status.textContent = choice.outcome === 'accepted' ? 'App installed.' : 'Installation cancelled.';
          return;
        }
        if (window.matchMedia('(display-mode: standalone)').matches) {
          if (status) status.textContent = 'This application is already installed.';
        } else {
          if (status) status.textContent = 'If your browser does not show the install prompt, use the browser menu and choose Install app.';
        }
      });
    }

    if (notificationButton) {
      bindNotificationButton(notificationButton);
    }
  });
})();

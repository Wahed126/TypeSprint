const PREFIX = 'typesprint-' + new URL(self.registration.scope).pathname + '-';
const CACHE = PREFIX + '__CACHE_VERSION__';
const ASSETS = ['./', './index.html', './styles.css', './app.js', './engine.js', './storage.js', './feedback.js', './data/exercises.json', './data/feedback.json', './icon.svg', './manifest.webmanifest'];
self.addEventListener('install', event => { event.waitUntil(caches.open(CACHE).then(cache => cache.addAll(ASSETS))); });
self.addEventListener('activate', event => {
  event.waitUntil(caches.keys().then(keys => Promise.all(keys.filter(key => key.startsWith(PREFIX) && key !== CACHE).map(key => caches.delete(key)))).then(() => self.clients.claim()));
});
self.addEventListener('fetch', event => {
  if (event.request.method !== 'GET' || new URL(event.request.url).origin !== self.location.origin) return;
  // Cache only the declared app files, so unrelated sites on this origin stay separate.
  event.respondWith(caches.open(CACHE).then(async cache => {
    const cached = await cache.match(event.request, { ignoreSearch: true });
    if (cached) return cached;
    try { return await fetch(event.request); }
    catch (error) { if (event.request.mode === 'navigate') return Response.redirect(self.registration.scope, 302); throw error; }
  }));
});

/* Online-only installable shell. Never cache authenticated API, media or HTML. */
self.addEventListener('install',event=>event.waitUntil(self.skipWaiting()));
self.addEventListener('activate',event=>event.waitUntil(self.clients.claim()));
// No fetch handler and no Cache Storage / IndexedDB: requests go to the network.

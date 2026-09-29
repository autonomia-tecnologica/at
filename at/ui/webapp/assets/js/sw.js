// sw — the shell's offline mouth (TASK-162, fatia 2/2). Every GET of this
// origin passes through here before it reaches the network, and what it
// caches on the way is what "avião ligado" still has to show.
//
// REGISTERED AT THE ROOT (`/sw.js`, not `/js/sw.js`): a Service Worker's scope
// is its own folder unless the server widens it with a header, and `/js/`
// would leave everything outside it — the document, `/theme.css`, the API —
// unintercepted. `main.ts` registers it with no `scope` of its own for the
// same reason: the default IS the root, from here.
//
// WHAT IT CACHES, and nothing past it: the shell (the document, the module
// graph or the built bundle, the look, the icons, the vendored files) and the
// four GETs the boot and the Tasks screen make (`/api/session`, `/api/state`,
// `/api/table/task`, `/api/table/project`) — TASK-162's own scope (Ressalvas:
// "Arquivos offline… é outro item"). A GET this list does not name is asked of
// the network like there was no Service Worker at all — a secret's value or an
// audit line served STALE from here would be a promise this file cannot keep
// honestly.
//
// WRITES ARE NEVER ANSWERED FROM HERE. `lib/offline.ts` is the one place a
// write made without a network is allowed to live — a POST this file faked
// would be a write the fila never saw, and a write it swallowed silently
// would be an edit that looked saved and was not.

const CACHE = "at-shell-v1";

function cacheable(pathname) {
  if (pathname.startsWith("/src/")) return true;
  if (pathname.startsWith("/assets/")) return true;
  if (pathname.startsWith("/icons/")) return true;
  if (pathname.startsWith("/vendor/")) return true;
  if (pathname.startsWith("/js/")) return true;
  if (pathname === "/theme.css" || pathname === "/base.css") return true;
  if (pathname === "/manifest.webmanifest") return true;
  if (pathname === "/api/session" || pathname === "/api/state") return true;
  if (pathname === "/api/table/task" || pathname === "/api/table/project") return true;
  return false;
}

self.addEventListener("install", () => {
  // No precache list on purpose (item "O que a fatia decide" is silent on
  // one, and a build-time manifest would have to know Vite's hashed output
  // names): what a first ONLINE visit touches is what gets cached, and that
  // is everything the boot touches by the time it is done.
  self.skipWaiting();
});

self.addEventListener("activate", event => {
  event.waitUntil(self.clients.claim());
});

// NETWORK FIRST, THE CACHE AS THE FALLBACK. Online, the page always sees what
// the server has NOW — offline is the exception this file exists for, not the
// common case it optimizes for — and every answer that lands refreshes the
// cache for the next time the network is the one that is gone.
self.addEventListener("fetch", event => {
  const request = event.request;
  if (request.method !== "GET") return; // a write is the fila's, never a cache's
  const url = new URL(request.url);
  if (url.origin !== self.location.origin) return;

  // A NAVIGATION (a reload, an address typed, a link followed) is answered
  // with the SHELL regardless of the path: the document is the same one
  // `/tasks`, `/board` and `/` all serve server-side (the SPA fallback,
  // `app.py`'s `_route`), and the app's own router (`App.vue`) reads
  // `location.pathname` once it is running — never the response body — so the
  // one shell cached under `/` answers every address honestly.
  const navigating = request.mode === "navigate";
  if (!navigating && !cacheable(url.pathname)) return;
  const key = navigating ? "/" : request;

  event.respondWith(
    fetch(request)
      .then(response => {
        if (response.ok) {
          const copy = response.clone();
          caches.open(CACHE).then(cache => cache.put(key, copy));
        }
        return response;
      })
      .catch(async () => {
        const cached = await caches.match(key);
        if (cached) return cached;
        throw new Error("offline, sem cache ainda para " + url.pathname);
      }),
  );
});

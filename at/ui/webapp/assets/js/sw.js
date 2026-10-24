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

const CACHE = "at-shell-v3";

// THE PORTAL IS NOT OURS. The identity provider lives on the SAME origin under
// `/authelia` (`at/services/caddy.py`'s `PORTAL`), and a Service Worker at the
// root sees its navigations too. Answering them here once poisoned the shell
// cache with the portal's login page (and a blank screen in Firefox): nothing
// under that prefix is intercepted, answered or cached by this file.
const PORTAL = "/authelia";

function portal(pathname) {
  return pathname === PORTAL || pathname.startsWith(PORTAL + "/");
}

// Only a response that IS the AT shell may be kept as the shell: a 200 HTML
// document, not redirected (the gate's 302 to the portal lands there), and not
// from the portal's path.
function shell(response) {
  if (!response.ok || response.redirected) return false;
  try {
    if (portal(new URL(response.url).pathname)) return false;
  } catch (error) {
    return false;
  }
  const type = response.headers.get("content-type") || "";
  return type.indexOf("text/html") !== -1;
}

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
  // Caches under any other name are older shells (possibly poisoned): gone.
  event.waitUntil(
    caches
      .keys()
      .then(names => Promise.all(names.filter(name => name !== CACHE).map(name => caches.delete(name))))
      .then(() => self.clients.claim()),
  );
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
  if (portal(url.pathname)) return; // the provider's, straight to the network

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
        if (navigating ? shell(response) : response.ok) {
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

// O PUSH — a notificação do PRÓPRIO PWA, e o que substituiu o ntfy. O AT manda
// um payload `{title, body}` cifrado (Web Push, `at/core/push.py`); o push
// service entrega ao navegador, e é AQUI que a notificação do sistema nasce.
// Sem este listener o navegador não mostra nada, e a inscrição seria muda.
self.addEventListener("push", event => {
  let payload = {};
  try {
    payload = event.data ? event.data.json() : {};
  } catch (error) {
    payload = {}; // um payload ilegível ainda vale um aviso, e nunca um estouro
  }
  const title = typeof payload.title === "string" && payload.title ? payload.title : "AT";
  const body = typeof payload.body === "string" ? payload.body : "";
  event.waitUntil(
    self.registration.showNotification(title, {
      body,
      data: { url: "/" },
    }),
  );
});

// CLICAR na notificação traz o app para a frente — a janela que já existe é
// focada, e só quando não há nenhuma é que uma nova se abre.
self.addEventListener("notificationclick", event => {
  event.notification.close();
  const url = (event.notification.data && event.notification.data.url) || "/";
  event.waitUntil(
    self.clients
      .matchAll({ type: "window", includeUncontrolled: true })
      .then(clients => {
        for (const client of clients) {
          if (client.url.indexOf(self.location.origin) === 0 && "focus" in client) {
            return client.focus();
          }
        }
        if (self.clients.openWindow) return self.clients.openWindow(url);
        return undefined;
      }),
  );
});

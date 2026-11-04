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

// B-28 fatia 1 — THE FILES THE PERSON OPENED. Two reads only: `GET /api/file`
// (text) and `GET /api/file/bytes` (image, PDF, attachment), both keyed by the
// full URL (the `?path=` is the identity). The folder listing/tree is NOT
// kept, and a write (POST) is never answered from here.
//
// They live in their OWN cache (`FILES`), apart from the shell's, so that
// bumping `CACHE` does not throw the person's files away; `activate` spares
// both names. Network first, as everything here: online always wins and
// refreshes the copy (so a file deleted/renamed through the write routes is
// never served stale online — a 404 is not cached and the old copy only
// answers when the network is gone).
//
// LRU over a limit the PERSON sets (item 21, default 500 MB). Cache API entries
// carry no size or access time, so the simplest metadata that works inside a SW
// is ONE JSON entry in the same cache (`INDEX`: {url: {size, at}}), rewritten on
// each touch. No IndexedDB: a single small document, and it can be tested
// without a browser. Writes to it are chained (`queue`) so two concurrent
// fetches do not lose each other's update. "Marked by hand is never evicted" is
// slice 2 (item 22), not here.
//
// THE CONFIG is per browser: the page keeps `{mode, limitMb}` in its `prefs`
// and sends it here by `postMessage`; it is stored as ONE JSON entry in the same
// cache (`CONFIG`), so a SW that wakes up again reads it back. Nothing stored
// means the defaults. `mode` "never" keeps nothing NEW; what is already kept
// still answers offline.
const FILES = "at-files-v1";
const INDEX = "/__at_files_index__";
const CONFIG = "/__at_files_config__";
const DEFAULT_LIMIT_MB = 500;
const DEFAULT_MODE = "kept";
const MODES = ["never", "kept"];
const FILE_PATHS = ["/api/file", "/api/file/bytes"];

function validMb(value) {
  return Number.isInteger(value) && value >= 1;
}

function fileRead(pathname) {
  return FILE_PATHS.indexOf(pathname) !== -1;
}

let queue = Promise.resolve();
function serial(job) {
  const run = queue.then(job, job);
  queue = run.catch(() => undefined);
  return run;
}

async function readIndex(cache) {
  const hit = await cache.match(INDEX);
  if (!hit) return {};
  try {
    const data = await hit.json();
    return data && typeof data === "object" && !Array.isArray(data) ? data : {};
  } catch (error) {
    return {};
  }
}

function writeIndex(cache, index) {
  return cache.put(INDEX, new Response(JSON.stringify(index), { headers: { "Content-Type": "application/json" } }));
}

async function readConfig(cache) {
  const hit = await cache.match(CONFIG);
  let data = null;
  if (hit) {
    try {
      data = await hit.json();
    } catch (error) {
      data = null;
    }
  }
  const mode = data && MODES.indexOf(data.mode) !== -1 ? data.mode : DEFAULT_MODE;
  const limitMb = data && validMb(data.limitMb) ? data.limitMb : DEFAULT_LIMIT_MB;
  return { mode, limit: limitMb * 1024 * 1024 };
}

// Evict the least recently accessed until the sum fits the limit. `keep` (the
// entry just written) is never its own victim.
async function evict(cache, index, limit, keep) {
  let total = 0;
  for (const name of Object.keys(index)) total += index[name].size;
  const order = Object.keys(index)
    .filter(name => name !== keep)
    .sort((a, b) => index[a].at - index[b].at);
  for (const name of order) {
    if (total <= limit) break;
    total -= index[name].size;
    delete index[name];
    await cache.delete(name);
  }
}

// Keep a fresh answer; then evict to the configured limit. A file larger than
// the whole limit is simply not kept, and mode "never" keeps nothing new.
function keepFile(key, response, size) {
  return serial(async () => {
    const cache = await caches.open(FILES);
    const config = await readConfig(cache);
    if (config.mode === "never") return;
    if (size > config.limit) return;
    const index = await readIndex(cache);
    await cache.put(key, response);
    index[key] = { size, at: Date.now() };
    await evict(cache, index, config.limit, key);
    await writeIndex(cache, index);
  });
}

// The page's new config: stored first, then applied at once, so lowering the
// limit evicts now (LRU) rather than at the next file.
function setConfig(config) {
  return serial(async () => {
    const cache = await caches.open(FILES);
    await cache.put(CONFIG, new Response(JSON.stringify(config), { headers: { "Content-Type": "application/json" } }));
    const index = await readIndex(cache);
    await evict(cache, index, config.limitMb * 1024 * 1024, null);
    await writeIndex(cache, index);
  });
}

self.addEventListener("message", event => {
  const data = event.data;
  if (!data || data.type !== "at:files-config") return;
  const mode = MODES.indexOf(data.mode) !== -1 ? data.mode : DEFAULT_MODE;
  const limitMb = validMb(data.limitMb) ? data.limitMb : DEFAULT_LIMIT_MB;
  event.waitUntil(setConfig({ mode, limitMb }));
});

// A hit with no network also counts as an access.
function touchFile(key) {
  return serial(async () => {
    const cache = await caches.open(FILES);
    const index = await readIndex(cache);
    if (!index[key]) return;
    index[key].at = Date.now();
    await writeIndex(cache, index);
  });
}

async function fileAnswer(request) {
  const key = request.url;
  try {
    const response = await fetch(request);
    if (response.ok) {
      const copy = response.clone();
      const blob = await response.clone().blob();
      keepFile(key, copy, blob.size).catch(() => undefined);
    }
    return response;
  } catch (error) {
    const cache = await caches.open(FILES);
    const cached = await cache.match(key);
    if (cached) {
      touchFile(key).catch(() => undefined);
      return cached;
    }
    throw error;
  }
}

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
      .then(names => Promise.all(names.filter(name => name !== CACHE && name !== FILES).map(name => caches.delete(name))))
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
  if (fileRead(url.pathname)) {
    event.respondWith(fileAnswer(request));
    return;
  }
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
// um payload `{title, body, data, actions}` cifrado (Web Push,
// `at/core/push.py`); o push service entrega ao navegador, e é AQUI que a
// notificação do sistema nasce. Sem este listener o navegador não mostra nada,
// e a inscrição seria muda.
//
// O QUE VAI PARA A NOTIFICAÇÃO é o que o AT mandou, e nada inventado: `data`
// (um objeto, o que o clique carrega consigo — aqui, `reminder` e `instance`) e
// `actions` (no máximo dois botões, e só os que têm `action` e `title` string,
// porque é o que a API desenha). O `url` do clique normal é acrescentado ao
// `data`, e é ele que a notificação leva sem botão.
function pushedData(raw) {
  const data = raw && typeof raw === "object" && !Array.isArray(raw) ? raw : {};
  return { ...data, url: "/" };
}

function pushedActions(raw) {
  if (!Array.isArray(raw)) return [];
  return raw
    .filter(item => item && typeof item.action === "string" && typeof item.title === "string")
    .slice(0, 2)
    .map(item => ({ action: item.action, title: item.title }));
}

self.addEventListener("push", event => {
  let payload = {};
  try {
    payload = event.data ? event.data.json() : {};
  } catch (error) {
    payload = {}; // um payload ilegível ainda vale um aviso, e nunca um estouro
  }
  const title = typeof payload.title === "string" && payload.title ? payload.title : "AT";
  const body = typeof payload.body === "string" ? payload.body : "";
  const options = { body, data: pushedData(payload.data) };
  const actions = pushedActions(payload.actions);
  if (actions.length) options.actions = actions;
  event.waitUntil(self.registration.showNotification(title, options));
});

// A ROTA DA SEÇÃO, e não a raiz: o clique abre a tela de Lembretes, do mesmo
// jeito que `/tasks` é a tela de Tarefas. A janela que já existe é focada, e só
// quando não há nenhuma é que uma nova se abre nesse endereço.
const REMINDERS = "/reminders";

function bringApp() {
  return self.clients
    .matchAll({ type: "window", includeUncontrolled: true })
    .then(clients => {
      for (const client of clients) {
        if (client.url.indexOf(self.location.origin) === 0 && "focus" in client) {
          return client.focus();
        }
      }
      if (self.clients.openWindow) return self.clients.openWindow(REMINDERS);
      return undefined;
    });
}

// O BOTÃO "CONCLUIR" fecha a ocorrência DIRETO da notificação, e faz isso pela
// MESMA porta que a tela usa: a rota `POST /api/reminders/close`, que deixa a
// linha de auditoria e a versão. Este arquivo não escreve nada por conta
// própria — ele chama a rota, e é o resultado dela que decide o que acontece.
// O SUCESSO É O DA ROTA: HTTP ok, e o corpo sem `ok: false`. O `reminder` pode
// vir `null` — um `once` fechado não deixa instância —, e isso ainda é um
// fechamento que deu certo; um corpo ausente com HTTP 200 também vale. Só a
// falha de HTTP, a rede que não responde ou um corpo que diz `ok: false` caem
// no comportamento de sempre (focar ou abrir), porque fechar não aconteceu.
function closeOccurrence(id, instance) {
  return fetch("/api/reminders/close", {
    method: "POST",
    credentials: "same-origin",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ id, instance }),
  })
    .then(response => {
      if (!response.ok) return false;
      return response
        .json()
        .then(answer => !answer || answer.ok !== false)
        .catch(() => true); // HTTP 200 sem corpo legível ainda é sucesso
    })
    .catch(() => false);
}

// Fechou dali: as janelas abertas do app são avisadas para recarregarem os
// lembretes (a tela escuta `at:reminders`), e nenhuma é aberta — a pessoa
// resolveu na notificação e não pediu a tela.
function tellTheApp() {
  return self.clients
    .matchAll({ type: "window", includeUncontrolled: true })
    .then(clients => {
      for (const client of clients) {
        if (client.url.indexOf(self.location.origin) === 0 && "postMessage" in client) {
          client.postMessage({ type: "at:reminders" });
        }
      }
    });
}

// CLICAR na notificação: com o botão `close`, fecha a ocorrência e avisa o
// app; sem ele (ou quando fechar falhou), traz o app para a frente.
self.addEventListener("notificationclick", event => {
  event.notification.close();
  const data = event.notification.data || {};
  if (event.action === "close" && data.reminder != null && data.instance) {
    event.waitUntil(
      closeOccurrence(data.reminder, data.instance).then(closed => (closed ? tellTheApp() : bringApp())),
    );
    return;
  }
  event.waitUntil(bringApp());
});

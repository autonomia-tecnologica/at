"""O Service Worker (`assets/js/sw.js`) não toca o que não é do AT: o portal
do Authelia (`/authelia`) passa direto, só o shell de verdade vira shell no
cache, e o `activate` apaga os caches de outro nome. Roda a lógica no node."""
import json
import shutil
import subprocess
import unittest
from pathlib import Path

from at.services import caddy

SW = Path(__file__).resolve().parents[1] / "ui" / "webapp" / "assets" / "js" / "sw.js"

HARNESS = r"""
const fs = require("fs");
const handlers = {};
const store = {"at-shell-v2": 1, "outro": 1};
const puts = [];
const caches = {
  keys: async () => Object.keys(store),
  delete: async n => { delete store[n]; },
  open: async () => ({ put: async (k, r) => { puts.push(String(k)); } }),
  match: async () => undefined,
};
global.self = { location: { origin: "https://h" }, addEventListener: (t, f) => { handlers[t] = f; },
  skipWaiting() {}, clients: { claim: async () => {} } };
global.caches = caches;
eval(fs.readFileSync(process.argv[1], "utf8") + "\n;globalThis.__sw = { CACHE };");
function resp(o) {
  return { ok: o.ok !== false, redirected: !!o.redirected, url: o.url,
    headers: { get: () => o.type || "text/html; charset=utf-8" }, clone() { return this; } };
}
async function fetchEvent(path, mode, answer) {
  let responded = false;
  global.fetch = async () => resp(answer);
  const ev = { request: { method: "GET", mode, url: "https://h" + path },
    respondWith: p => { responded = true; ev.p = p; } };
  handlers.fetch(ev);
  if (ev.p) await ev.p;
  await new Promise(r => setTimeout(r, 5));
  return responded;
}
(async () => {
  const out = {};
  let w; handlers.activate({ waitUntil: p => { w = p; } }); await w;
  out.caches = Object.keys(store);
  out.cache = globalThis.__sw.CACHE;
  out.portalNav = await fetchEvent("/authelia/?rd=x&rm=GET", "navigate", { url: "https://h/authelia/" });
  out.portalGet = await fetchEvent("/authelia/static/a.js", "no-cors", { url: "https://h/authelia/static/a.js" });
  out.puts0 = puts.length;
  out.nav = await fetchEvent("/tasks", "navigate", { url: "https://h/tasks" });
  out.puts1 = puts.length;
  await fetchEvent("/tasks", "navigate", { url: "https://h/authelia/", redirected: true });
  out.puts2 = puts.length;
  await fetchEvent("/tasks", "navigate", { url: "https://h/tasks", type: "application/json" });
  out.puts3 = puts.length;
  console.log(JSON.stringify(out));
})();
"""


FILES_HARNESS = r"""
const fs = require("fs");
const handlers = {};
const stores = {};
class Resp {
  constructor(body, init) { this.body = body; this.ok = true; this.headers = { get: () => "x" }; }
  clone() { return this; }
  async blob() { return { size: typeof this.body === "string" ? this.body.length : this.size }; }
  async json() { return JSON.parse(this.body); }
}
global.Response = Resp;
global.caches = {
  keys: async () => Object.keys(stores),
  delete: async n => { delete stores[n]; },
  match: async () => undefined,
  open: async n => {
    const m = stores[n] = stores[n] || new Map();
    return { put: async (k, r) => { m.set(String(k), r); }, match: async k => m.get(String(k)),
      delete: async k => m.delete(String(k)) };
  },
};
global.self = { location: { origin: "https://h" }, addEventListener: (t, f) => { handlers[t] = f; },
  skipWaiting() {}, clients: { claim: async () => {} } };
eval(fs.readFileSync(process.argv[1], "utf8") + "\n;globalThis.__sw = { DEFAULT_LIMIT_MB, FILES, INDEX };");
let online = true;
let size = 10;
global.fetch = async req => {
  if (!online) throw new Error("offline");
  const r = new Resp("x".repeat(size)); r.size = size; return r;
};
async function get(path, method) {
  let p = null;
  const ev = { request: { method: method || "GET", mode: "cors", url: "https://h" + path },
    respondWith: x => { p = x; } };
  handlers.fetch(ev);
  let status = "passed";
  if (p) { try { await p; status = "answered"; } catch (e) { status = "failed"; } }
  await new Promise(r => setTimeout(r, 20));
  return status;
}
const sleep = ms => new Promise(r => setTimeout(r, ms));
(async () => {
  const out = { limit: globalThis.__sw.DEFAULT_LIMIT_MB };
  out.text = await get("/api/file?path=a.md");
  out.bytes = await get("/api/file/bytes?path=b.png");
  out.tree = await get("/api/files?path=");
  out.tree2 = await get("/api/file/list?path=");
  out.post = await get("/api/file", "POST");
  out.portal = await get("/authelia/api/file?path=a");
  const idx = () => JSON.parse(stores[globalThis.__sw.FILES].get(globalThis.__sw.INDEX).body);
  out.kept = Object.keys(idx()).length;
  online = false;
  out.offlineOpened = await get("/api/file?path=a.md");
  out.offlineNever = await get("/api/file?path=zzz.md");
  online = true;
  // LRU: three files of 200 MB, the limit is 500 MB: the oldest goes
  size = 200 * 1024 * 1024;
  await get("/api/file?path=big1"); await sleep(5);
  await get("/api/file?path=big2"); await sleep(5);
  online = false;
  await get("/api/file?path=big1"); await sleep(5); // big1 touched: big2 is now the oldest
  online = true;
  await get("/api/file?path=big3");
  out.after = Object.keys(idx()).map(k => k.split("path=")[1]).sort();
  console.log(JSON.stringify(out));
})();
"""


CONFIG_HARNESS = r"""
const fs = require("fs");
const vm = require("vm");
const src = fs.readFileSync(process.argv[1], "utf8");
const scenario = process.argv[2];
const stores = {};
let online = true;
let size = 10;
class Resp {
  constructor(body) { this.body = body; this.ok = true; this.headers = { get: () => "x" }; }
  clone() { return this; }
  async blob() { return { size: this.size !== undefined ? this.size : this.body.length }; }
  async json() { return JSON.parse(this.body); }
}
const cachesApi = {
  keys: async () => Object.keys(stores),
  delete: async n => { delete stores[n]; },
  match: async () => undefined,
  open: async n => {
    const m = stores[n] = stores[n] || new Map();
    return { put: async (k, r) => { m.set(String(k), r); }, match: async k => m.get(String(k)),
      delete: async k => m.delete(String(k)) };
  },
};
// A "boot" is a fresh global (a SW that wakes up again) over the SAME caches.
function boot() {
  const handlers = {};
  const sandbox = {
    Response: Resp, URL, JSON, Object, Array, Number, Promise, Date, Math, Map, Set, String, Boolean, Error, console,
    setTimeout,
    caches: cachesApi,
    self: { location: { origin: "https://h" }, addEventListener: (t, f) => { handlers[t] = f; },
      skipWaiting() {}, clients: { claim: async () => {} } },
    fetch: async () => {
      if (!online) throw new Error("offline");
      const r = new Resp(""); r.size = size; return r;
    },
  };
  vm.createContext(sandbox);
  vm.runInContext(src + "\n;globalThis.__sw = { DEFAULT_LIMIT_MB, FILES, INDEX, CONFIG };", sandbox);
  return { handlers, sw: sandbox.__sw };
}
const sleep = ms => new Promise(r => setTimeout(r, ms));
async function get(h, path) {
  let p = null;
  h.handlers.fetch({ request: { method: "GET", mode: "cors", url: "https://h" + path }, respondWith: x => { p = x; } });
  let status = "passed";
  if (p) { try { await p; status = "answered"; } catch (e) { status = "failed"; } }
  await sleep(20);
  return status;
}
async function setConfig(h, mode, limitMb) {
  let work = null;
  h.handlers.message({ data: { type: "at:files-config", mode, limitMb }, waitUntil: p => { work = p; } });
  if (work) await work;
  await sleep(10);
}
function kept() {
  const m = stores["at-files-v1"];
  const idx = m && m.get("/__at_files_index__");
  return idx ? Object.keys(JSON.parse(idx.body)).map(k => k.split("path=")[1]).sort() : [];
}
function storedConfig() {
  const m = stores["at-files-v1"];
  const cfg = m && m.get("/__at_files_config__");
  return cfg ? JSON.parse(cfg.body) : null;
}
const MB = 1024 * 1024;
(async () => {
  const out = {};
  if (scenario === "modo") {
    const h = boot();
    await setConfig(h, "kept", 500);
    await get(h, "/api/file?path=a");
    out.keptMode = kept();
    await setConfig(h, "never", 500);
    await get(h, "/api/file?path=b");
    out.neverMode = kept();
    online = false;
    out.offlineA = await get(h, "/api/file?path=a");
    out.offlineB = await get(h, "/api/file?path=b");
    online = true;
  } else if (scenario === "reinicio") {
    const h1 = boot();
    await get(h1, "/api/file?path=a");
    await setConfig(h1, "never", 500);
    const h2 = boot();
    await get(h2, "/api/file?path=c");
    out.afterRestart = kept();
  } else if (scenario === "limite") {
    const h1 = boot();
    size = 200 * MB;
    await get(h1, "/api/file?path=big1"); await sleep(5);
    await get(h1, "/api/file?path=big2"); await sleep(5);
    out.before = kept();
    await setConfig(h1, "kept", 300);
    out.lowered = kept();
    const h2 = boot();
    await get(h2, "/api/file?path=big3");
    out.afterRestart = kept();
  } else if (scenario === "invalido") {
    const h = boot();
    await setConfig(h, "kept", 1.5);
    out.afterFraction = storedConfig();
    await setConfig(h, "bogus", 0);
    out.afterBogus = storedConfig();
  }
  console.log(JSON.stringify(out));
})();
"""


def _run_config(scenario):
    run = subprocess.run(
        ["node", "-e", CONFIG_HARNESS, str(SW), scenario],
        capture_output=True, text=True, timeout=60,
    )
    if run.returncode != 0:
        raise AssertionError(run.stderr)
    return json.loads(run.stdout)


PIN_HARNESS = r"""
const fs = require("fs");
const handlers = {};
const stores = {};
let online = true;
let sizes = {};
let opens = {};
class Resp {
  constructor(body) { this.body = body; this.ok = true; this.headers = { get: () => "x" }; this.size = undefined; }
  clone() { return this; }
  async blob() { return { size: this.size !== undefined ? this.size : this.body.length }; }
  async json() { return JSON.parse(this.body); }
}
global.Response = Resp;
global.caches = {
  keys: async () => Object.keys(stores),
  delete: async n => { delete stores[n]; },
  match: async () => undefined,
  open: async n => {
    const m = stores[n] = stores[n] || new Map();
    return { put: async (k, r) => { m.set(String(k), r); }, match: async k => m.get(String(k)),
      delete: async k => m.delete(String(k)) };
  },
};
global.self = { location: { origin: "https://h" }, addEventListener: (t, f) => { handlers[t] = f; },
  skipWaiting() {}, clients: { claim: async () => {} } };
eval(fs.readFileSync(process.argv[1], "utf8") + "\n;globalThis.__sw = { FILES, INDEX };");
global.fetch = async req => {
  const url = new URL(typeof req === "string" ? req : req.url);
  if (!online) throw new Error("offline");
  const path = url.searchParams.get("path");
  const r = new Resp(JSON.stringify({ open: opens[path] || "text", path }));
  r.size = sizes[path] !== undefined ? sizes[path] : 10;
  return r;
};
const sleep = ms => new Promise(r => setTimeout(r, ms));
async function get(path) {
  let p = null;
  handlers.fetch({ request: { method: "GET", mode: "cors", url: "https://h" + path }, respondWith: x => { p = x; } });
  if (p) { try { await p; } catch (e) { /* a failed answer is the case under test */ } }
  await sleep(20);
}
function ask(data) {
  return new Promise(resolve => {
    handlers.message({ data, ports: [{ postMessage: resolve }], waitUntil: () => {} });
  });
}
async function config(mode, limitMb) {
  let work = null;
  handlers.message({ data: { type: "at:files-config", mode, limitMb }, waitUntil: p => { work = p; } });
  if (work) await work;
  await sleep(10);
}
function index() {
  const m = stores["at-files-v1"];
  const idx = m && m.get("/__at_files_index__");
  return idx ? JSON.parse(idx.body) : {};
}
function kept() {
  return Object.keys(index()).map(k => k.split("path=")[1]).sort();
}
function pinned() {
  const idx = index();
  return Object.keys(idx).filter(k => idx[k].pinned).map(k => k.split("path=")[1]).sort();
}
function reset() {
  for (const k of Object.keys(stores)) delete stores[k];
  online = true;
  sizes = {};
  opens = {};
}
const pin = path => ask({ type: "at:files-pin", path, pinned: true });
const unpin = path => ask({ type: "at:files-pin", path, pinned: false });
const state = path => ask({ type: "at:files-state", path });
const MB = 1024 * 1024;
(async () => {
  const out = {};

  // A marked file is not evicted; its bytes count in the sum like any other.
  reset();
  sizes = { fixo: 300 * MB, a: 200 * MB, b: 200 * MB };
  await pin("fixo");
  await get("/api/file?path=a");
  out.sumKept = kept(); // 500 MB: fits
  await get("/api/file?path=b"); // 700 MB: the oldest NOT marked goes
  out.lruKept = kept();
  out.lruPinned = pinned();

  // Unmarking returns the file to the LRU, and the limit is applied at once.
  reset();
  sizes = { fixo: 200 * MB, b: 200 * MB, c: 200 * MB };
  await pin("fixo");
  await get("/api/file?path=b");
  out.unpinAtOnce = (await unpin("fixo")).ok;
  out.unpinKept = kept(); // 400 MB: nothing goes yet
  out.unpinState = (await state("fixo")).pinned;
  await get("/api/file?path=c"); // 600 MB: fixo is the oldest now
  out.unpinAfter = kept();

  // Marked alone over the limit: the mark is still kept, the page is told, and
  // no NEW opened file is kept; a refresh of a marked file goes on.
  reset();
  sizes = { p1: 300 * MB, p2: 300 * MB, a: 10 };
  out.overflow1 = (await pin("p1")).overflow;
  out.overflow2 = (await pin("p2")).overflow;
  await get("/api/file?path=a");
  out.blockedKept = kept();
  await get("/api/file?path=p1");
  out.refreshKept = kept();
  out.refreshPinned = pinned();

  // A file alone bigger than the limit can be marked: it is kept and it overflows.
  reset();
  sizes = { gigante: 600 * MB };
  const big = await pin("gigante");
  out.giantOk = big.ok;
  out.giantOverflow = big.overflow;
  out.giantKept = kept();

  // Mode "never" keeps nothing new, but a mark is kept.
  reset();
  await config("never", 500);
  await pin("z");
  await get("/api/file?path=y");
  out.neverKept = kept();
  out.neverPinned = pinned();

  // An image: the view also reads the bytes door, so both entries are marked.
  reset();
  opens = { img: "image" };
  sizes = { img: 50 * MB };
  await pin("img");
  out.imageKeys = Object.keys(index()).map(k => k.replace("https://h", "")).sort();
  out.imagePinned = pinned();

  // Offline with no copy: the mark fails, and nothing is kept.
  reset();
  online = false;
  out.failed = (await pin("nunca")).ok;
  out.failedKept = kept();

  console.log(JSON.stringify(out));
})();
"""


PUSH_HARNESS = r"""
const fs = require("fs");
const handlers = {};
const shown = [];
const opened = [];
const posted = [];
const calls = [];
let focused = 0;
let windows = [];
let answer = { ok: true, body: { ok: true, reminder: { id: 7 } } };

const client = {
  url: "https://h/reminders",
  focus: async () => { focused += 1; },
  postMessage: message => { posted.push(message); },
};

global.self = {
  location: { origin: "https://h" },
  addEventListener: (type, handler) => { handlers[type] = handler; },
  skipWaiting() {},
  registration: { showNotification: async (title, options) => { shown.push({ title, options }); } },
  clients: {
    claim: async () => {},
    matchAll: async () => windows,
    openWindow: async url => { opened.push(url); },
  },
};
global.caches = { keys: async () => [], open: async () => ({ put: async () => {} }), match: async () => undefined };
global.fetch = async (url, init) => {
  calls.push({ url, init });
  return {
    ok: answer.ok !== false,
    redirected: false,
    url: "https://h" + url,
    headers: { get: () => "application/json" },
    json: async () => answer.body,
  };
};
eval(fs.readFileSync(process.argv[1], "utf8"));

function firePush(payload) {
  let work;
  handlers.push({ data: { json: () => payload }, waitUntil: promise => { work = promise; } });
  return work;
}
function click(data, action) {
  let work;
  handlers.notificationclick({
    action: action || "",
    notification: { data, close() {} },
    waitUntil: promise => { work = promise; },
  });
  return work;
}
(async () => {
  const out = {};
  await firePush({
    title: "AT",
    body: "Vence hoje",
    data: { reminder: 7, instance: "2026-10-05 09:00" },
    actions: [
      { action: "close", title: "Concluir" },
      { action: "snooze" },
      { action: "x", title: "y" },
      { action: "z", title: "w" },
    ],
  });
  out.shown = shown.map(entry => ({
    title: entry.title,
    body: entry.options.body,
    data: entry.options.data,
    actions: entry.options.actions,
  }));

  const data = { reminder: 7, instance: "2026-10-05 09:00", url: "/" };

  windows = [client];
  await click(data, "close");
  out.closeCall = calls.length
    ? {
        url: calls[0].url,
        method: calls[0].init.method,
        credentials: calls[0].init.credentials,
        contentType: calls[0].init.headers["Content-Type"],
        body: JSON.parse(calls[0].init.body),
      }
    : null;
  out.closeOpened = opened.length;
  out.closePosted = posted.slice();
  out.closeFocused = focused;
  out.afterCloseFetches = calls.length;

  windows = [];
  await click(data, "");
  out.plainOpened = opened.slice();
  out.plainFetches = calls.length;

  windows = [];
  answer = { ok: false, body: { ok: false } };
  await click(data, "close");
  out.failedOpened = opened.slice(out.plainOpened.length);
  out.failedFetches = calls.length;

  // Um `once` fechado não deixa instância: `{"ok": true, "reminder": null}` é
  // sucesso, e não pode abrir o app como se tivesse falhado.
  windows = [client];
  posted.length = 0;
  answer = { ok: true, body: { ok: true, reminder: null } };
  const beforeOnce = opened.length;
  await click(data, "close");
  out.onceOpened = opened.slice(beforeOnce);
  out.oncePosted = posted.slice();
  out.onceFocused = focused;
  out.onceFetches = calls.length;

  // HTTP ok com o corpo dizendo `ok: false` é falha, e cai na abertura.
  windows = [];
  answer = { ok: true, body: { ok: false } };
  const beforeBodyFalse = opened.length;
  await click(data, "close");
  out.bodyFalseOpened = opened.slice(beforeBodyFalse);
  out.bodyFalseFetches = calls.length;

  console.log(JSON.stringify(out));
})();
"""


@unittest.skipUnless(shutil.which("node"), "sem node")
class ServiceWorkerTests(unittest.TestCase):
    def test_portal_passa_direto_e_so_o_shell_vira_shell(self):
        run = subprocess.run(["node", "-e", HARNESS, str(SW)], capture_output=True, text=True, timeout=30)
        self.assertEqual(run.returncode, 0, run.stderr)
        out = json.loads(run.stdout)
        self.assertEqual(out["cache"], "at-shell-v3")
        self.assertEqual(out["caches"], ["at-shell-v3"] if "at-shell-v3" in out["caches"] else [])
        self.assertNotIn("at-shell-v2", out["caches"])
        self.assertNotIn("outro", out["caches"])
        self.assertFalse(out["portalNav"])
        self.assertFalse(out["portalGet"])
        self.assertEqual(out["puts0"], 0)
        self.assertTrue(out["nav"])
        self.assertEqual(out["puts1"], 1)  # o shell do AT é guardado
        self.assertEqual(out["puts2"], 1)  # redirecionada ao portal: não
        self.assertEqual(out["puts3"], 1)  # não-HTML: não

    def test_arquivos_acessados_vao_ao_cache_com_lru_de_500mb(self):
        run = subprocess.run(["node", "-e", FILES_HARNESS, str(SW)], capture_output=True, text=True, timeout=30)
        self.assertEqual(run.returncode, 0, run.stderr)
        out = json.loads(run.stdout)
        self.assertEqual(out["limit"], 500)  # MB: o padrão, sem configuração
        self.assertEqual(out["text"], "answered")
        self.assertEqual(out["bytes"], "answered")
        self.assertEqual(out["tree"], "passed")  # a listagem nao entra
        self.assertEqual(out["tree2"], "passed")
        self.assertEqual(out["post"], "passed")  # escrita nunca e do SW
        self.assertEqual(out["portal"], "passed")
        self.assertEqual(out["kept"], 2)
        self.assertEqual(out["offlineOpened"], "answered")  # ja aberto: abre sem rede
        self.assertEqual(out["offlineNever"], "failed")  # nao aberto: falha como hoje
        # big1 foi tocado; big2 era o menos recente e saiu
        self.assertNotIn("big2", out["after"])
        self.assertIn("big1", out["after"])
        self.assertIn("big3", out["after"])

    def test_acessados_guarda_e_nunca_nao_guarda_mas_o_guardado_abre_offline(self):
        out = _run_config("modo")
        self.assertEqual(out["keptMode"], ["a"])  # acessados: o arquivo aberto entra
        self.assertEqual(out["neverMode"], ["a"])  # nunca: o novo não entra
        self.assertEqual(out["offlineA"], "answered")  # o que já estava abre sem rede
        self.assertEqual(out["offlineB"], "failed")  # o que nunca entrou falha como antes

    def test_modo_nunca_sobrevive_a_sw_reiniciado(self):
        out = _run_config("reinicio")
        self.assertEqual(out["afterRestart"], ["a"])  # o `c` não entrou: a config foi lida de novo

    def test_limite_alterado_despeja_pelo_lru_no_novo_valor(self):
        out = _run_config("limite")
        self.assertEqual(out["before"], ["big1", "big2"])  # 400 MB cabem em 500
        self.assertEqual(out["lowered"], ["big2"])  # 300 MB: sai o menos recente
        self.assertEqual(out["afterRestart"], ["big3"])  # o limite de 300 MB sobreviveu ao reinício

    def test_limite_invalido_volta_a_500_mb(self):
        out = _run_config("invalido")
        self.assertEqual(out["afterFraction"], {"mode": "kept", "limitMb": 500})
        self.assertEqual(out["afterBogus"], {"mode": "kept", "limitMb": 500})

    def test_prefixo_e_o_do_portal(self):
        self.assertIn(f'const PORTAL = "{caddy.PORTAL}";', SW.read_text())

    def test_o_push_repasse_a_data_e_os_botoes_e_o_clique_feche_a_ocorrencia(self):
        run = subprocess.run(
            ["node", "-e", PUSH_HARNESS, str(SW)], capture_output=True, text=True, timeout=30
        )
        self.assertEqual(run.returncode, 0, run.stderr)
        out = json.loads(run.stdout)

        # (a) o `push` leva `data` (com o `url` do clique normal) e `actions`,
        # já saneado: só entradas com `action` e `title` string, no máximo duas.
        shown = out["shown"][0]
        self.assertEqual(shown["title"], "AT")
        self.assertEqual(shown["body"], "Vence hoje")
        self.assertEqual(
            shown["data"],
            {"reminder": 7, "instance": "2026-10-05 09:00", "url": "/"},
        )
        self.assertEqual(
            shown["actions"],
            [{"action": "close", "title": "Concluir"}, {"action": "x", "title": "y"}],
        )

        # (b) o botão `close` faz o POST da rota, avisa as janelas e NÃO abre o app.
        call = out["closeCall"]
        self.assertEqual(call["url"], "/api/reminders/close")
        self.assertEqual(call["method"], "POST")
        self.assertEqual(call["credentials"], "same-origin")
        self.assertEqual(call["contentType"], "application/json")
        self.assertEqual(call["body"], {"id": 7, "instance": "2026-10-05 09:00"})
        self.assertEqual(out["closeOpened"], 0)
        self.assertEqual(out["closeFocused"], 0)
        self.assertEqual(out["closePosted"], [{"type": "at:reminders"}])

        # (c) o clique sem action abre a seção, não a raiz.
        self.assertEqual(out["plainOpened"], ["/reminders"])
        self.assertEqual(out["plainFetches"], out["afterCloseFetches"])

        # (d) com `close` e resposta não-ok, cai no foco/abertura de sempre.
        self.assertEqual(out["failedOpened"], ["/reminders"])
        self.assertEqual(out["failedFetches"], out["afterCloseFetches"] + 1)

        # (e) `{"ok": true, "reminder": null}` é sucesso (um `once` sem
        # instância): avisa as janelas e NÃO abre o app.
        self.assertEqual(out["onceFetches"], out["failedFetches"] + 1)
        self.assertEqual(out["onceOpened"], [])
        self.assertEqual(out["onceFocused"], 0)
        self.assertEqual(out["oncePosted"], [{"type": "at:reminders"}])

        # (f) HTTP ok com o corpo dizendo `ok: false` é falha e abre.
        self.assertEqual(out["bodyFalseFetches"], out["onceFetches"] + 1)
        self.assertEqual(out["bodyFalseOpened"], ["/reminders"])

    @classmethod
    def _pin(cls):
        if not hasattr(cls, "_pin_out"):
            run = subprocess.run(["node", "-e", PIN_HARNESS, str(SW)], capture_output=True, text=True, timeout=60)
            if run.returncode != 0:
                raise AssertionError(run.stderr)
            cls._pin_out = json.loads(run.stdout)
        return cls._pin_out

    def test_marcado_nao_sai_pelo_lru_e_conta_na_soma(self):
        out = self._pin()
        self.assertEqual(out["sumKept"], ["a", "fixo"])  # 500 MB cabem no limite
        self.assertEqual(out["lruKept"], ["b", "fixo"])  # 700 MB: sai o `a`, o não marcado mais antigo
        self.assertEqual(out["lruPinned"], ["fixo"])

    def test_desmarcar_devolve_ao_lru(self):
        out = self._pin()
        self.assertTrue(out["unpinAtOnce"])
        self.assertEqual(out["unpinKept"], ["b", "fixo"])  # 400 MB: o limite ainda não estourou
        self.assertFalse(out["unpinState"])
        self.assertEqual(out["unpinAfter"], ["b", "c"])  # o `fixo` virou o mais antigo e sai

    def test_so_o_marcado_sozinho_acima_do_limite_bloqueia_novos_e_avisa(self):
        out = self._pin()
        self.assertFalse(out["overflow1"])  # 300 MB: cabe
        self.assertTrue(out["overflow2"])  # 600 MB de marcados: avisa a tela
        self.assertEqual(out["blockedKept"], ["p1", "p2"])  # o `a`, novo, não entra
        self.assertEqual(out["refreshKept"], ["p1", "p2"])  # regravar um marcado não é novo
        self.assertEqual(out["refreshPinned"], ["p1", "p2"])

    def test_arquivo_maior_que_o_limite_marcado_fica_e_avisa(self):
        out = self._pin()
        self.assertTrue(out["giantOk"])
        self.assertTrue(out["giantOverflow"])
        self.assertEqual(out["giantKept"], ["gigante"])

    def test_modo_nunca_nao_impede_o_marcado(self):
        out = self._pin()
        self.assertEqual(out["neverKept"], ["z"])  # o `y`, novo, não entra; o `z` marcado entra
        self.assertEqual(out["neverPinned"], ["z"])

    def test_imagem_marca_as_duas_portas_que_a_tela_le(self):
        out = self._pin()
        self.assertEqual(
            out["imageKeys"],
            ["/api/file/bytes?path=img", "/api/file?path=img"],
        )
        self.assertEqual(out["imagePinned"], ["img", "img"])

    def test_marcar_sem_rede_e_sem_copia_falha_e_nada_entra(self):
        out = self._pin()
        self.assertFalse(out["failed"])
        self.assertEqual(out["failedKept"], [])


if __name__ == "__main__":
    unittest.main()

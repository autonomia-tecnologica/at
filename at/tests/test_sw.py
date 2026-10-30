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


if __name__ == "__main__":
    unittest.main()

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


if __name__ == "__main__":
    unittest.main()

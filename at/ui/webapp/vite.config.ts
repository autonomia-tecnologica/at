import { defineConfig } from "vite";
import vue from "@vitejs/plugin-vue";
import type { Plugin } from "vite";

// AT's look, injected into the `head` AFTER Vite is done with index.html.
// The three files are the SERVER's (`app.py`), on the same origin — and Vite
// would remove them: it resolves `<link rel="stylesheet">` against the disk,
// does not find `/theme.css` or `/base.css` in the project, and makes them
// disappear. In the first build the page came out without `base.css` — that is,
// without a single rule — and with no error at all.
// THE ORDER IS theme, base, SCRIPT, and it is load-bearing twice: the base
// stylesheet must still come AFTER the theme (the two both write `:root`, and
// the later one wins), and `boot.js` must run after BOTH links exist — it moves
// the two of them, and a script that reaches for a link the parser has not
// written yet moves nothing.
const LOOK = [
  '<link id="theme" rel="stylesheet" href="/theme.css">',
  '<link id="base" rel="stylesheet" href="/base.css">',
  '<script src="/js/boot.js"></script>',
].join("\n");

const lookFromTheServer = (): Plugin => ({
  name: "at-look-do-servidor",
  transformIndexHtml: {
    order: "post",
    handler: (html: string) => html.replace("<!--at:look-->", LOOK),
  },
});

// WHERE THE AT SERVER IS, for `npm run dev`. Vite serves the app — the modules,
// the hot reload — and the server behind it keeps everything that is NOT the
// app: the words, the tables, the look (`/theme.css`, `/base.css`), the icons
// and the vendored files. One origin, two processes, and the page changes as
// the source does, which is the whole reason to run it this way.
//
// The default is AT's own port (`app.DEFAULT_PORT`). A session running its
// instance elsewhere says so on the command line:
//
//     AT_WEBAPP_PORT=12399 npm run dev
// `process` is Node's, and this file is CONFIGURATION — it runs in Node, never
// in the page — so it is declared here instead of dragging `@types/node` into a
// project whose only runtime dependency is Vue. It is the smallest declaration
// that reads one variable.
declare const process: { env: Record<string, string | undefined> };

const AT = `http://127.0.0.1:${process.env.AT_WEBAPP_PORT || "12345"}`;

// The doors that belong to the AT server and not to Vite. `/src`, `@vite` and
// `/node_modules` are Vite's own and must NOT be proxied — they are the app
// itself, and the server has never heard of them.
const SERVER_DOORS = ["/api", "/theme.css", "/base.css", "/icons", "/vendor", "/js"];

export default defineConfig({
  base: "/",
  plugins: [vue(), lookFromTheServer()],
  server: {
    port: 5173,
    proxy: Object.fromEntries(SERVER_DOORS.map(door => [door, AT])),
  },
  build: {
    outDir: "dist",
    emptyOutDir: true,
    // The server's policy is `default-src 'self'` (app.py): no inline script and
    // no `data:`. The modulepreload polyfill IS an inline `<script>`, and the
    // inline asset limit would become a `data:` in the CSS — both would violate
    // the policy, so both are turned off (fail-closed, like everything else).
    modulePreload: { polyfill: false },
    assetsInlineLimit: 0,
  },
});

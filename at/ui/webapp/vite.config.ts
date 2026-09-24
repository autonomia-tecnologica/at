import { defineConfig } from "vite";
import vue from "@vitejs/plugin-vue";
import type { Plugin } from "vite";

// AT's look, injected into the `head` AFTER Vite is done with index.html.
// The three files are the SERVER's (`app.py`), on the same origin — and Vite
// would remove them: it resolves `<link rel="stylesheet">` against the disk,
// does not find `/theme.css` or `/base.css` in the project, and makes them
// disappear. In the first build the page came out without `base.css` — that is,
// without a single rule — and with no error at all.
const LOOK = [
  '<link id="theme" rel="stylesheet" href="/theme.css">',
  '<script src="/js/boot.js"></script>',
  '<link rel="stylesheet" href="/base.css">',
].join("\n");

const lookFromTheServer = (): Plugin => ({
  name: "at-look-do-servidor",
  transformIndexHtml: {
    order: "post",
    handler: (html: string) => html.replace("<!--at:look-->", LOOK),
  },
});

export default defineConfig({
  base: "/",
  plugins: [vue(), lookFromTheServer()],
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

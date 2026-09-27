// markdown — the text a markdown cell shows, and the prose a markdown field is.
//
// THE RENDERER IS HOSTED, AND IT IS `marked`: AT serves it byte for byte through
// the `/vendor/` door, with the version on the `X-Hosted` header — the entry is
// pinned in `at/ui/webapp/vendor/manifest.json`, by sha256, and the file travels
// inside the binary with the rest of the WebApp. This module is the door's
// client: `ensureRenderer` pulls `/vendor/marked` ONCE, and every field re-reads
// when it lands (`rendererReady`). No CDN, and no dependency invented on this
// side — the file is the vendor's own build.
//
// THE RENDERED HTML IS SANITIZED, and the reason is written down because the
// choice is a decision and not an oversight. `marked` does NOT sanitize: it
// hands back whatever raw HTML the source carried, and the source is not AT's —
// the prose is a file somebody else's folder holds, or a backlog body somebody
// typed. The CSP (`default-src 'self'`, app.py) is a SECOND net and not the
// only one: it stops an inline handler, a `data:` image and an outbound script,
// and this allow-list stops the markup from ever arriving. What survives is
// what the renderer's own output uses — headings, lists, links, code, tables —,
// and a tag outside the list is dropped whole.
//
// `plainText` keeps its job: the notation taken out for the CELL, which is a
// glimpse and not a page. The renderer does not replace it.

import { ref } from "vue";
import type { Ref } from "vue";

// Where the hosted renderer is served from. The key is the file's own name
// (`vendor/manifest.json`), never a path.
const RENDERER = "/vendor/marked";

// The signal a cell re-reads when the renderer lands. It is born FALSE: there is
// nothing to parse with until `/vendor/marked` arrives, and the honest answer
// until then is the source the field already has.
export const rendererReady: Ref<boolean> = ref(false);

// The door for the renderer: asking for it once, here, is what keeps every
// caller from waiting for a script that may never come.
let asking: Promise<void> | null = null;

export function ensureRenderer(): Promise<void> {
  if (asking) return asking;
  asking = new Promise<void>((resolve) => {
    const script = document.createElement("script");
    script.src = RENDERER;
    script.async = true;
    // A script that does NOT arrive resolves all the same, and `rendererReady`
    // stays false: the field then draws its own source, which is the honest
    // answer with no renderer — and no retry, because a page that keeps asking
    // for a door that is not there is noise.
    script.onload = () => {
      rendererReady.value = true;
      resolve();
    };
    script.onerror = () => resolve();
    document.head.appendChild(script);
  });
  return asking;
}

// The text a cell shows for a markdown value: the notation taken out. It is NOT
// a parser — it is the shape of the notation this table's own fields use, so
// that a cell reads as a sentence instead of as its source.
export function plainText(source: string | null | undefined): string {
  if (!source) return "";
  return String(source)
    .replace(/```[\s\S]*?```/g, " ")          // fenced blocks
    .replace(/`([^`]+)`/g, "$1")              // inline code
    .replace(/!\[([^\]]*)\]\([^)]*\)/g, "$1") // images
    .replace(/\[([^\]]+)\]\([^)]*\)/g, "$1")  // links
    .replace(/^\s{0,3}#{1,6}\s+/gm, "")       // headings
    .replace(/^\s{0,3}>\s?/gm, "")            // quotes
    .replace(/^\s{0,3}[-*+]\s+/gm, "")        // bullets
    .replace(/\*\*([^*]+)\*\*/g, "$1")        // bold
    .replace(/__([^_]+)__/g, "$1")
    .replace(/\*([^*]+)\*/g, "$1")            // emphasis
    .replace(/_([^_]+)_/g, "$1")
    .replace(/\s+/g, " ")
    .trim();
}

// The prose, as HTML. NULL is the honest answer while the renderer has not
// landed: the field then draws the text it has, which is what the page knows
// how to do.
export async function proseHtml(source: string): Promise<string | null> {
  const renderer = marked();
  if (!source || !rendererReady.value || !renderer) return null;
  const html = await renderer.parse(source, { async: false });
  return sanitize(String(html));
}

// The renderer as the hosted script leaves it on the global. `marked.umd.js`
// assigns `globalThis.marked`; asking for it here keeps the global's shape in
// one place instead of at every call.
interface Marked {
  parse(source: string, options?: { async?: boolean }): string | Promise<string>;
}

function marked(): Marked | null {
  const found = (globalThis as unknown as { marked?: Marked }).marked;
  return found && typeof found.parse === "function" ? found : null;
}

// ------------------------------------------------------------------ the net --

// What the renderer's OWN output uses, and the attributes each tag may carry.
// This is an ALLOW-LIST, and that is the point: `marked` generates exactly these
// tags, so an element outside them was RAW HTML written in the source — the part
// nobody on this side wrote and the part that has to prove itself.
const KEEP: Record<string, readonly string[]> = {
  a: ["href", "title"],
  blockquote: [],
  br: [],
  code: ["class"],
  dd: [],
  del: [],
  dl: [],
  dt: [],
  em: [],
  h1: [], h2: [], h3: [], h4: [], h5: [], h6: [],
  hr: [],
  img: ["src", "alt", "title"],
  li: [],
  ol: ["start"],
  p: [],
  pre: [],
  strong: [],
  sub: [],
  sup: [],
  table: [], tbody: [], td: ["align"], th: ["align"], thead: [], tr: [], ul: [],
};

// The schemes a URL may wear. Everything WITH a scheme is named out loud, and a
// URL with NO scheme is relative — relative is ours. `javascript:` and `data:`
// are the two that would run or embed something; `vbscript:` and `file:` are
// the same intent on other grounds.
const SCHEME = /^([a-z][a-z0-9+.-]*):/i;
const SAFE_SCHEMES = ["http", "https", "mailto"];

function safeUrl(value: string): boolean {
  const cleaned = value.replace(/[\u0000-\u0020]+/g, "");
  const scheme = SCHEME.exec(cleaned);
  return scheme === null || SAFE_SCHEMES.includes(scheme[1].toLowerCase());
}

// The renderer's HTML, with everything the allow-list does not know DROPPED. The
// parsing document is INERT: no script runs, no image loads and no link is
// followed while the tree is walked — the browser builds it detached from the
// page, and only the pruned copy is ever assigned.
function sanitize(html: string): string {
  const doc = new DOMParser().parseFromString(html, "text/html");
  prune(doc.body);
  return doc.body.innerHTML;
}

function prune(node: Node): void {
  for (const child of Array.from(node.childNodes)) {
    // A comment never paints; it goes, so nothing hidden travels with the copy.
    if (child.nodeType === Node.COMMENT_NODE) {
      child.parentNode?.removeChild(child);
      continue;
    }
    if (child.nodeType !== Node.ELEMENT_NODE) continue;
    const element = child as Element;
    const tag = element.tagName.toLowerCase();
    const allowed: readonly string[] | undefined = KEEP[tag];
    // An element the renderer does not produce: it came from raw HTML, and it
    // leaves WITH its subtree — unknown markup is not something to keep half of.
    if (!allowed) {
      element.remove();
      continue;
    }
    for (const attr of Array.from(element.attributes)) {
      const name = attr.name.toLowerCase();
      if (!allowed.includes(name)) {
        element.removeAttribute(attr.name);
        continue;
      }
      if ((name === "href" || name === "src") && !safeUrl(attr.value)) {
        element.removeAttribute(attr.name);
      }
      // The renderer's only class is the code fence's language; anything else
      // was written by hand.
      if (name === "class" && !/^language-[\w+#.-]+$/i.test(attr.value.trim())) {
        element.removeAttribute(attr.name);
      }
    }
    // A link the person follows leaves the page; the referrer does not go with.
    if (tag === "a") element.setAttribute("rel", "noopener noreferrer");
    prune(element);
  }
}

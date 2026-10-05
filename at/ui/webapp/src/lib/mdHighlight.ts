// mdHighlight — a light, line-based colouring of markdown's OWN syntax, for a
// source view that stays SOURCE: no token here is removed or rewritten, each
// is only wrapped in a span the write page's own CSS colours
// (`WriteView.vue`). The text a browser would read out of the result,
// `<span>` tags stripped, is character-for-character the input — which is
// what lets this sit in a mirror behind a transparent textarea without the
// two ever drifting a pixel apart: wrapping only depends on the characters,
// never on which of them a span happens to wrap.

const ESCAPE: Record<string, string> = { "&": "&amp;", "<": "&lt;", ">": "&gt;" };

function escapeHtml(text: string): string {
  return text.replace(/[&<>]/g, ch => ESCAPE[ch]);
}

// Walked on the ALREADY-ESCAPED line: none of these characters are among
// `&<>`, so escaping first never breaks a match.
const INLINE: [RegExp, string][] = [
  [/`[^`\n]+`/g, "md-code"],
  [/\*\*[^*\n]+\*\*/g, "md-strong"],
  [/__[^_\n]+__/g, "md-strong"],
  [/\*[^*\n]+\*/g, "md-em"],
  [/\[[^\]\n]*\]\([^)\n]*\)/g, "md-link"],
];

// ONE PASS, LEFT TO RIGHT, AND A SPAN NEVER REOPENS INSIDE ANOTHER: naive
// replacement, rule by rule, lets `**bold `code` bold**` have the CODE rule
// split a STRONG span in two — tags crossing, which is a browser's own soup
// past that point. Every rule's matches are collected first, sorted by where
// they START, and a match that starts inside a span an EARLIER rule already
// claimed is dropped rather than drawn a second time.
function inline(line: string): string {
  const spans: { start: number; end: number; cls: string }[] = [];
  for (const [pattern, cls] of INLINE) {
    pattern.lastIndex = 0;
    let found: RegExpExecArray | null;
    while ((found = pattern.exec(line))) {
      spans.push({ start: found.index, end: found.index + found[0].length, cls });
    }
  }
  spans.sort((a, b) => a.start - b.start);
  let out = "";
  let cursor = 0;
  for (const span of spans) {
    if (span.start < cursor) continue;
    out += line.slice(cursor, span.start);
    out += `<span class="${span.cls}">${line.slice(span.start, span.end)}</span>`;
    cursor = span.end;
  }
  out += line.slice(cursor);
  return out;
}

const HEADING = /^(#{1,6})(\s.*)?$/;
const QUOTE = /^(>+)(\s?.*)$/;
const LIST = /^(\s*(?:[-*+]|\d+[.)])\s)(.*)$/;
const FENCE = /^(```|~~~)/;

export function highlightMarkdown(text: string): string {
  let inFence = false;
  return text
    .split("\n")
    .map(raw => {
      if (FENCE.test(raw)) {
        inFence = !inFence;
        return `<span class="md-fence">${escapeHtml(raw)}</span>`;
      }
      if (inFence) return `<span class="md-code-block">${escapeHtml(raw)}</span>`;

      const heading = HEADING.exec(raw);
      if (heading) {
        const mark = escapeHtml(heading[1]);
        const rest = inline(escapeHtml(heading[2] || ""));
        return `<span class="md-heading"><span class="md-mark">${mark}</span>${rest}</span>`;
      }
      const quote = QUOTE.exec(raw);
      if (quote) {
        const mark = escapeHtml(quote[1]);
        const rest = inline(escapeHtml(quote[2]));
        return `<span class="md-quote"><span class="md-mark">${mark}</span>${rest}</span>`;
      }
      const list = LIST.exec(raw);
      if (list) {
        const mark = escapeHtml(list[1]);
        const rest = inline(escapeHtml(list[2]));
        return `<span class="md-mark">${mark}</span>${rest}`;
      }
      return inline(escapeHtml(raw));
    })
    .join("\n");
}

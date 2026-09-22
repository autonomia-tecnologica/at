// markdown — the text a markdown cell shows, and the prose a markdown field is.
//
// THE RENDERER IS NOT HERE YET, and that is a decision, not an oversight: the
// bill HOSTS `marked` through the `/vendor/` door, byte for byte, with the
// version on the header — and this session built the door for the typefaces
// only. Until `marked` comes through it, a markdown field reads as its own
// source: `plainText` takes the notation out for the CELL (a cell is a glimpse,
// and asterisks are not what it is showing), and the record draws the raw text.
//
// It is a named debt, and it is written here because the alternative — a
// dependency invented on this side — is the thing the Manifesto refuses.

import { ref } from "vue";
import type { Ref } from "vue";

// The signal a cell re-reads when the renderer lands. It is born TRUE, because
// there is no renderer to wait for: the text is already as plain as it gets.
export const rendererReady: Ref<boolean> = ref(true);

// The door for the day the renderer arrives: asking for it once, here, is what
// keeps every caller from waiting for a script that may never come.
export async function ensureRenderer(): Promise<void> {
  return;
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

// The prose, as HTML. NULL is the honest answer while there is no renderer: the
// field then draws the text it has, which is what the page knows how to do.
export async function proseHtml(_source: string): Promise<string | null> {
  return null;
}

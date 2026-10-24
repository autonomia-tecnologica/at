// search — THE GLOBAL SEARCH'S STATE (B-21, fatia 2).
//
// One overlay, opened by `/` (never inside a field), that asks the SERVER's
// engine — the same one `at-cli search` walks — and so finds what the CLI finds.
// The page invents no matching of its own: it debounces the typing, asks, and
// draws what came back.

import { reactive } from "vue";
import { api } from "./api";
import { FILE_PREFIX, open, openRef } from "./views";

export interface Hit {
  kind: "file" | "row";
  where: string;
  id: string | null;
  field: string;
  line: number | null;
  snippet: string;
}

export const DEBOUNCE_MS = 200;

export const searchState = reactive({
  open: false,
  term: "",
  hits: [] as Hit[],
  asked: false, // an answer for the CURRENT term has arrived
  busy: false,
  error: "",
  active: 0,
});

let timer: ReturnType<typeof setTimeout> | undefined;
let sequence = 0; // an answer that is not the last question's is dropped

export function openSearch(): void {
  searchState.open = true;
}

export function closeSearch(): void {
  clearTimeout(timer);
  sequence++;
  searchState.open = false;
  searchState.term = "";
  searchState.hits = [];
  searchState.asked = false;
  searchState.busy = false;
  searchState.error = "";
  searchState.active = 0;
}

async function ask(term: string): Promise<void> {
  const mine = ++sequence;
  searchState.busy = true;
  try {
    const answer = await api<{ hits: Hit[] }>("/api/search?q=" + encodeURIComponent(term));
    if (mine !== sequence) return;
    searchState.hits = answer.hits;
    searchState.error = "";
  } catch (err) {
    if (mine !== sequence) return;
    searchState.hits = [];
    searchState.error = (err as Error).message;
  }
  searchState.asked = true;
  searchState.active = 0;
  searchState.busy = false;
}

// Every keystroke lands here; only the last one, DEBOUNCE_MS later, asks.
export function typed(term: string): void {
  searchState.term = term;
  clearTimeout(timer);
  if (!term.trim()) {
    sequence++;
    searchState.hits = [];
    searchState.asked = false;
    searchState.busy = false;
    searchState.error = "";
    return;
  }
  timer = setTimeout(() => { void ask(term.trim()); }, DEBOUNCE_MS);
}

export function move(step: number): void {
  const n = searchState.hits.length;
  if (n) searchState.active = (searchState.active + step + n) % n;
}

// The row id a hit carries is the one a person reads (`TASK-3`); the page's
// route wants the number at its end.
export function rowNumber(id: string | null): number | null {
  const found = /(\d+)$/.exec(id ?? "");
  return found ? Number(found[1]) : null;
}

export function pick(hit: Hit | undefined): void {
  if (!hit) return;
  closeSearch();
  if (hit.kind === "file") {
    open(FILE_PREFIX + hit.where, null);
    return;
  }
  const number = rowNumber(hit.id);
  if (number !== null) openRef({ key: hit.where, id: number });
}

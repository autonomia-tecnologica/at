// store — what the SERVER said, and the words the page draws with.
//
// The rule that matters: the state belongs to the SERVER. This is a MIRROR of
// what came from `/api/state`, never a second source of truth. Whoever writes
// to it is `applyState`; nobody else.

import { reactive } from "vue";

// A word of the catalog, already written out in every language the server
// supports — the page picks by the language on screen and never invents one.
export type Labels = Record<string, string>;

export interface Kind {
  key: string;
  label: string;
  type: string | null; // the type the table DECLARES, which is what a page asks for
  count: number;
}

export interface ThemeRow {
  id: string;
  label: string;
  // WHICH FILES THE THEME ACTUALLY HAS, read off disk server-side — one
  // entry means no choice to offer (only `at` ever answers both, today).
  sides: ("light" | "dark")[];
  // The theme describes ITSELF, one description per side.
  desc: { light?: string; dark?: string } | null;
  // Almost always null: the shared `base.css`. A theme walking its own design
  // system names the file here (`theme.ts` swaps the second link on it).
  base: string | null;
}

// A mark of the risk ruler: one catalogue entry and the number it is MEASURED
// at (§4/§5) — the catalogue's own risk, adjusted by what the folder wrote. The
// ruler draws what it is handed rather than inventing a number.
export interface RiskMark {
  key: string;
  risk: number;
}

export interface Risk {
  threshold: number;
  marks: RiskMark[];
}

export interface FieldSpec {
  name: string;
  labels: Labels | null;
  enum: Record<string, Labels | null>;
  type: string | null;
  primary: boolean;
  filterable: boolean;
  searchable: boolean;
  narrow: boolean;
  editable: boolean;
  required: boolean;
  max_length: number | null;
  hide: string[];
  refs: { key: string; labels: Labels | null }[];
}

export const store = reactive({
  lang: "en_US",      // the language the page draws in
  origin: "",         // where it came from (env|folder|locale|default)
  labels: {} as Record<string, Labels>, // the page's own words, per language
  theme: null as string | null, // the theme the server wears with no choice saved
  themes: [] as ThemeRow[],
  tables: [] as Kind[], // the tables the panel shows, in the server's order
  types: {} as Record<string, string>, // a DECLARED type → the table declaring it
  fields: [] as FieldSpec[], // the schema of the table ON SCREEN
  interpreter: true, // the CORE's switch: off, there is no box, balloon or chat
  // TASK-180, fatia 3/3: the assist's own two knobs — whether Jev is asked at
  // all once the matcher gives up (`assist`), and what a non-`refuse` tier
  // does once Jev has answered (`assist_mode`, `"cautious"` born default). The
  // second field keeps the server's own spelling (`FieldSpec.max_length`'s own
  // precedent) rather than a camelCase this file would have to translate.
  assist: true,
  assist_mode: "cautious",
  // SE A CREDENCIAL DO JEV ESTÁ CONFIGURADA (um `secret` de escopo `jev`). Sem
  // ela o Jev não é consultado, e o chat diz "Jev não configurado".
  jev_ready: false,
  risk: { threshold: 0.5, marks: [] } as Risk, // the ruler's numbers
  // WHAT THE FOLDER IS, VERSIONING-WISE (§4, item 30), already written out in
  // every language: a sentence when AT does not version the folder, and `null`
  // when it does — there is nothing to warn about, and a band with no words is
  // no band.
  versioning: null as Labels | null,
});

export function applyState(state: Partial<typeof store>): void {
  if (state.lang) store.lang = state.lang;
  store.origin = state.origin || "";
  store.labels = (state.labels as Record<string, Labels>) || {};
  store.theme = (state.theme as string | null) ?? null;
  store.themes = state.themes || [];
  store.tables = (state.tables as Kind[]) || [];
  store.types = (state.types as Record<string, string>) || {};
  // The switch is BORN ON and the server is the one that says so: an answer that
  // does not carry it leaves the interpreter where it was.
  if (typeof state.interpreter === "boolean") store.interpreter = state.interpreter;
  if (typeof state.assist === "boolean") store.assist = state.assist;
  if (typeof state.assist_mode === "string") store.assist_mode = state.assist_mode;
  if (typeof state.jev_ready === "boolean") store.jev_ready = state.jev_ready;
  if (state.risk) store.risk = state.risk as Risk;
  store.versioning = (state.versioning as Labels | null) ?? null;
}

// The display name of a thing in the active language.
export function label(labels: Labels | null | undefined): string {
  return (labels && (labels[store.lang] || labels.en_US)) || "";
}

// One of the page's own words. The page invents none: they come from the
// catalog, and the server hands over every language at once.
export function word(key: string): string {
  return label(store.labels[key]);
}

// The display name of a TABLE — the server names every table, and the page
// invents none.
export function kindLabel(key: string): string {
  const table = store.tables.find(kind => kind.key === key);
  return (table && table.label) || key;
}

// The table a view names, or null. A view is a table's key, so this is the
// lookup every page that has to know "does this table exist" asks.
export function tableOf(key: string): Kind | null {
  return store.tables.find(kind => kind.key === key) || null;
}

export function setFields(schema: FieldSpec[]): void {
  store.fields = schema || [];
}

export function field(name: string): FieldSpec | null {
  return store.fields.find(spec => spec.name === name) || null;
}

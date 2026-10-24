// What a table's cell IS, read off the record and the column's spec — pure, and
// shared by the filter, the sort, the width and the template of TableView.
// No field name is known here: the vocabulary comes from the schema.

import { computed, type ComputedRef } from "vue";
import { plainText } from "./markdown";
import type { FieldSpec, RecordField, RecordRow } from "./record";

// A CELL IS CUT AT THE TABLE'S CEILING, never at a number of this file's own: a
// field that declares `max_length` PROMISES the value fits. `CELL_LIMIT` is what
// is left for the fields that promised nothing.
export const CELL_LIMIT = 200;

export const value = (rec: RecordRow, name: string): RecordField =>
  rec.fields.find(field => field.name === name) || { name, type: null, value: "", raw: null, refs: [] };

export const cell = (rec: RecordRow, name: string): string =>
  name === "id" ? String(rec.id ?? "") : value(rec, name).value || "";

// A DATE SORTS BY WHAT IS STORED, never by what is shown: the locale writes
// `22/09/2026`, and that text sorts by the day of the month. The stored value is
// ISO, which sorts the way time does — so the display is free to be a display.
export const sortCell = (rec: RecordRow, name: string): string => {
  const field = value(rec, name);
  if (field.type === "day" || field.type === "instant") {
    return field.raw == null ? "" : String(field.raw);
  }
  return cell(rec, name);
};

export const by = (a: string, b: string): number =>
  String(a).localeCompare(String(b), undefined, { numeric: true, sensitivity: "base" });

export function useCells(fields: ComputedRef<FieldSpec[]>) {
  const byName = computed<Record<string, FieldSpec>>(() =>
    Object.fromEntries(fields.value.map(field => [field.name, field])),
  );
  const ALL = computed(() => fields.value.map(field => field.name));

  const limitOf = (name: string): number => byName.value[name]?.max_length || CELL_LIMIT;

  // WHICH MEMBER OF A CLOSED LIST the row carries, when the column declares one —
  // the marker the theme dresses a cell by (`data-value`, base.css), the same
  // idiom the file tree already uses for a row's bucket. The page says WHICH
  // value it is and never what it should look like: a column of prose carries
  // nothing here, and a vocabulary a theme does not know keeps its plain text.
  const enumOf = (rec: RecordRow, name: string): string | undefined => {
    const spec = byName.value[name];
    if (!spec || !spec.enum || !Object.keys(spec.enum).length) return undefined;
    const raw = value(rec, name).raw;
    return raw === null || raw === undefined || raw === "" ? undefined : String(raw);
  };

  function shownText(name: string, rec: RecordRow): string {
    if (name === "id") return String(cell(rec, name));
    const field = value(rec, name);
    // A markdown field is measured on the text the CELL shows — the notation taken
    // out —, exactly as `FieldValue` draws it.
    let text = field.type === "markdown" ? plainText(field.value) : field.value || "";
    const limit = limitOf(name);
    if (text.length > limit) text = text.slice(0, limit) + "…";
    // References read by TITLE in the table — that is what the cell shows.
    const refs = (field.refs || [])
      .map(ref => ({ ...ref, shown: ref.shown || String(ref.id), at: text.indexOf(ref.shown || String(ref.id)) }))
      .filter(ref => ref.at >= 0)
      .sort((a, b) => a.at - b.at);
    let out = "";
    let at = 0;
    for (const ref of refs) {
      if (ref.at < at) continue;
      out += text.slice(at, ref.at) + (ref.title || ref.id);
      at = ref.at + ref.shown.length;
    }
    return out + text.slice(at);
  }

  return { byName, ALL, limitOf, enumOf, shownText };
}

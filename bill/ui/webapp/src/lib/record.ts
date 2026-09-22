// record — the shapes the server hands over, in ONE place.
//
// The page draws what the server decided; these are the decisions it reads. A
// field arrives with its VALUE already written in the active language (`value`)
// and with what is stored (`raw`), so a cell shows one and a write sends the
// other — and neither the page nor the surface behind it ever renders a value a
// second time.

import type { FieldSpec, Labels } from "./store";

export interface RecordRef {
  key: string;
  id: number;
  title: string;
  shown?: string;
}

export interface RecordField {
  name: string;
  type: string | null;
  value: string;
  raw: unknown;
  refs: RecordRef[];
}

export interface RecordRow {
  id: number;
  shown_id: string;
  title: string;
  fields: RecordField[];
}

export interface TablePayload {
  key: string;
  name: string;
  filter: unknown;
  fields: FieldSpec[];
  // The fields a listing carries, in the order the table declares them. What is
  // not here steps aside into the pill — it is the table's rule, not the page's.
  columns: string[];
  records: RecordRow[];
}

export type { FieldSpec, Labels };

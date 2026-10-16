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
  // WHAT THE ROW HAS TO BE TOLD, over what its fields already say (item 11):
  // a `role` carries the names it declares that the catalogue does not have —
  // §4's saying, which is what gets read — and an `actor` carries whether a
  // credential is stored, because the value itself never travels.
  unknown?: string[];
  has_credential?: boolean;
}

export interface DeclarableAction {
  action: string;
  label: string;
  requires_id: boolean;
  fields: FieldSpec[];
}

export interface DeclarableTable {
  key: string;
  name: string;
  actions: DeclarableAction[];
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
  // What the ENGINE says this actor may do to a row of this table — never
  // invented by the page (TASK-120). Row-independent: the ceiling is the
  // role's, over the table, so one list answers for every record.
  actions: string[];
  // The `declare` panel's own picker (relógio, fatia 3/3) — present only on
  // the `job` table's payload, because it is the only one with a `declare`
  // act to offer: every table's own writes this actor may reach directly,
  // with the fields a scheduled `create`/`edit` would take.
  declarable?: DeclarableTable[];
}

export type { FieldSpec, Labels };

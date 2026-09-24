// order — the order of the panel's lists.
//
// ALPHABETICAL, in the language the page is drawn in. What a person does with a
// list of tables is LOOK ONE UP, and for that the name is the index — a declared
// order you have to learn is a worse index than the one everybody already knows.
//
// `numeric` keeps `TASK-2` before `TASK-10` (a plain string sort puts the 10
// first, which reads as a defect), and `base` compares case- and
// accent-insensitively while still sorting `Árvore` among the A's.

import { store } from "./store";

export function byName(a: string, b: string): number {
  const lang = (store.lang || "en_US").replace("_", "-");
  return String(a).localeCompare(String(b), lang, { numeric: true, sensitivity: "base" });
}

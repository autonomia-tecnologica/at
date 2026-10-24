// Each column's filter: the SET OF VALUES it accepts, and what is left out is the
// preference (`at.filters`, per table.field). Used by TableView.

import { ref, computed, type ComputedRef } from "vue";
import { FILTERS_KEY, loadPrefs, savePrefs } from "./prefs";
import { openPop, closePop, isPopOpen } from "./pop";
import { cell, by } from "./tableCells";
import FilterPop from "../components/pops/FilterPop.vue";
import type { FieldSpec, RecordRow } from "./record";

export function useFilters(
  props: { entity: string; records: RecordRow[] },
  fields: ComputedRef<FieldSpec[]>,
) {
  const filterPrefs = loadPrefs(FILTERS_KEY);
  const prefName = (name: string): string => props.entity + "." + name;

  const valuesOf = (name: string): string[] =>
    [...new Set(props.records.map(rec => cell(rec, name)))].sort(by);

  const filters = ref<Record<string, Set<string> | undefined>>({});
  for (const spec of fields.value) {
    if (!spec.filterable) continue;
    const values = valuesOf(spec.name);
    const off = ((filterPrefs[prefName(spec.name)] as string[]) || []).filter(value => values.includes(value));
    if (off.length) filters.value[spec.name] = new Set(values.filter(value => !off.includes(value)));
  }

  const keep = (rec: RecordRow): boolean =>
    Object.entries(filters.value).every(
      ([name, accepted]) => !accepted || accepted.has(cell(rec, name)),
    );

  const visible = computed(() => props.records.filter(keep));

  // Hiding a column DROPS its filter: a filter nobody can see goes on hiding rows
  // with no visible reason.
  function dropFilter(name: string): void {
    delete filters.value[name];
    delete filterPrefs[prefName(name)];
    savePrefs(FILTERS_KEY, filterPrefs);
  }

  // The filter panel holds no reference to the table: whoever applies it is HERE.
  const pendingFilter = ref<{ name: string; values: string[] } | null>(null);

  function applyFilter(next: Set<string>): void {
    const pending = pendingFilter.value;
    if (!pending) return;
    const { name, values } = pending;
    const all = next.size === values.length;
    if (all) delete filters.value[name];
    else filters.value[name] = next;
    const off = all ? [] : values.filter(value => !next.has(value));
    if (off.length) filterPrefs[prefName(name)] = off;
    else delete filterPrefs[prefName(name)];
    savePrefs(FILTERS_KEY, filterPrefs);
  }

  function toggleFilter(ev: Event, name: string): void {
    if (isPopOpen("filter:" + name)) {
      closePop();
      return;
    }
    const values = valuesOf(name);
    pendingFilter.value = { name, values };
    openPop("filter:" + name, FilterPop,
            { values, accepted: filters.value[name] || null, onApply: applyFilter },
            { anchor: ev.currentTarget as HTMLElement });
  }

  return { filters, visible, dropFilter, toggleFilter };
}

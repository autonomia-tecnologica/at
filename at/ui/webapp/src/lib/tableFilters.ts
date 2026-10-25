// Each column's filter: the SET OF VALUES it accepts, and what is left out is the
// preference (`at.filters`, per table.field). Used by TableView and TaskBoard.
//
// A column of DAYS (`type: day`) filters by INTERVAL instead — from a day, until a
// day, either end open — and the preference is the pair itself, in the same
// `at.filters` under the same `table.field` key. Filters combine AND between
// columns, OR among the values of one.

import { ref, computed, type ComputedRef } from "vue";
import { FILTERS_KEY, loadPrefs, savePrefs } from "./prefs";
import { openPop, closePop, isPopOpen } from "./pop";
import { cell, by, value } from "./tableCells";
import FilterPop from "../components/pops/FilterPop.vue";
import RangePop from "../components/pops/RangePop.vue";
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

  const isDay = (name: string): boolean => fields.value.find(f => f.name === name)?.type === "day";

  type Range = { from: string; until: string };
  const ranges = ref<Record<string, Range | undefined>>({});
  for (const spec of fields.value) {
    if (!spec.filterable || spec.type !== "day") continue;
    const saved = filterPrefs[prefName(spec.name)] as Partial<Range> | undefined;
    if (saved && !Array.isArray(saved) && (saved.from || saved.until)) {
      ranges.value[spec.name] = { from: String(saved.from || ""), until: String(saved.until || "") };
    }
  }

  // A DAY IS COMPARED BY WHAT IS STORED (ISO sorts the way time does); a row with
  // no day cannot be inside an interval that has an end, so it steps aside.
  const inRange = (rec: RecordRow, name: string, range: Range): boolean => {
    const raw = value(rec, name).raw;
    if (raw === null || raw === undefined || raw === "") return false;
    const day = String(raw).slice(0, 10);
    return (!range.from || day >= range.from) && (!range.until || day <= range.until);
  };

  const keep = (rec: RecordRow): boolean =>
    Object.entries(filters.value).every(
      ([name, accepted]) => !accepted || accepted.has(cell(rec, name)),
    ) && Object.entries(ranges.value).every(
      ([name, range]) => !range || inRange(rec, name, range),
    );

  const isOn = (name: string): boolean => !!filters.value[name] || !!ranges.value[name];

  const visible = computed(() => props.records.filter(keep));

  // Hiding a column DROPS its filter: a filter nobody can see goes on hiding rows
  // with no visible reason.
  function dropFilter(name: string): void {
    delete filters.value[name];
    delete ranges.value[name];
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

  function applyRange(name: string, next: Range): void {
    if (next.from || next.until) {
      ranges.value[name] = next;
      filterPrefs[prefName(name)] = next;
    } else {
      delete ranges.value[name];
      delete filterPrefs[prefName(name)];
    }
    savePrefs(FILTERS_KEY, filterPrefs);
  }

  function toggleFilter(ev: Event, name: string): void {
    if (isPopOpen("filter:" + name)) {
      closePop();
      return;
    }
    if (isDay(name)) {
      const range = ranges.value[name];
      openPop("filter:" + name, RangePop,
              { from: range?.from || "", until: range?.until || "",
                onApply: (next: Range) => applyRange(name, next) },
              { anchor: ev.currentTarget as HTMLElement });
      return;
    }
    const values = valuesOf(name);
    pendingFilter.value = { name, values };
    openPop("filter:" + name, FilterPop,
            { values, accepted: filters.value[name] || null, onApply: applyFilter },
            { anchor: ev.currentTarget as HTMLElement });
  }

  return { filters, isOn, visible, dropFilter, toggleFilter };
}

// The table's sort: one column, one direction. Used by TableView.

import { ref, computed, type ComputedRef } from "vue";
import { sortCell } from "./tableCells";
import type { RecordRow } from "./record";

export function useSort(visible: ComputedRef<RecordRow[]>) {
  const sort = ref<{ name: string; dir: number } | null>(null);

  const ordered = computed(() => {
    if (!sort.value) return visible.value;
    const { name, dir } = sort.value;
    return visible.value
      .slice()
      .sort((a, b) => dir * sortCell(a, name).localeCompare(sortCell(b, name), undefined,
                                                             { numeric: true, sensitivity: "base" }));
  });

  function toggleSort(name: string): void {
    sort.value = sort.value && sort.value.name === name
      ? { name, dir: -sort.value.dir }
      : { name, dir: 1 };
  }

  return { sort, ordered, toggleSort };
}

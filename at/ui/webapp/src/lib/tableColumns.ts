// The order of the columns and which are HIDDEN: the person's preference
// (`at.columns`, per VIEW) — or, on a `rule` view, the table's own declaration,
// which is never read from nor written to the preference. Also the narrow screen
// set and the drag-and-drop that reorders. Used by TableView.

import { ref, computed, type ComputedRef } from "vue";
import { COLUMNS_KEY, loadPrefs, savePrefs } from "./prefs";
import { narrow } from "./breakpoint";
import type { FieldSpec } from "./record";

export function useColumns(
  props: { rule: boolean; defaults: string[] | null },
  fields: ComputedRef<FieldSpec[]>,
  ALL: ComputedRef<string[]>,
  columnKey: ComputedRef<string>,
  // Called when a column is hidden: its sort and its filter go with it.
  onHide: (name: string) => void,
) {
  const columnPrefs = loadPrefs(COLUMNS_KEY);
  const viewPrefs = columnPrefs[columnKey.value] || (columnPrefs[columnKey.value] = {});
  const saveColumns = (): void => savePrefs(COLUMNS_KEY, columnPrefs);

  const primary = computed(() => fields.value.find(field => field.primary)?.name);

  function initialOrder(): string[] {
    // The rule views keep the table's order: there is no preference to read.
    const saved = !props.rule && Array.isArray(viewPrefs.order) ? (viewPrefs.order as string[]) : [];
    const preferred = saved.length
      ? saved
      : ["id", ...(primary.value ? [primary.value] : []),
         ...ALL.value.filter(name => name !== "id" && name !== primary.value)];
    const known = [...preferred.filter(name => ALL.value.includes(name)),
                   ...ALL.value.filter(name => !preferred.includes(name))];
    return ["id", ...known.filter(name => name !== "id")]; // the key column first
  }

  const order = ref<string[]>(initialOrder());

  // WHAT THE TABLE PUTS ASIDE ON A VIEW: a field that declares `hide: ["project"]`
  // steps aside on the pages that are the same shape — and nowhere else. The table
  // NAMES the views; the page reads the declaration and invents nothing.
  const declared = computed(() =>
    fields.value.filter(field => (field.hide || []).includes(columnKey.value)).map(field => field.name),
  );

  // What is hidden is the PERSON's list; a view that DECLARES a smaller set to
  // begin with seeds it ONCE — from then on the list is the person's own.
  const seeded = props.rule
    ? [...declared.value]
    : Array.isArray(viewPrefs.hidden)
      ? (viewPrefs.hidden as string[])
      : [
          ...declared.value,
          ...(props.defaults
            ? ALL.value.filter(name => name !== "id" && !props.defaults!.includes(name))
            : []),
        ];
  const hidden = ref<Set<string>>(new Set(seeded.filter(name => name !== "id" && ALL.value.includes(name))));

  // --- the narrow screen -------------------------------------------------------
  // Below the band, the columns the table declared it cannot do without are what
  // stays: a twenty-column table on a phone is 6% of it on screen.
  const narrowShown = ref<Set<string>>(
    new Set(Array.isArray(viewPrefs.narrow) ? (viewPrefs.narrow as string[]) : []),
  );
  const priority = computed(() => new Set(fields.value.filter(field => field.narrow).map(field => field.name)));

  function saveNarrow(): void {
    if (narrowShown.value.size) viewPrefs.narrow = [...narrowShown.value];
    else delete viewPrefs.narrow;
    saveColumns();
  }

  const narrowHidden = computed(() => {
    if (!narrow.value) return new Set<string>();
    const keep = new Set([...priority.value, "id"]);
    return new Set(order.value.filter(name => !keep.has(name) && !narrowShown.value.has(name)));
  });

  // What the table ACTUALLY hides — the person's set plus the narrow one. It is
  // what the count, the pill and the columns panel read, so nothing on screen
  // disagrees with what is drawn.
  const hiddenNow = computed(() => new Set([...hidden.value, ...narrowHidden.value]));
  const shown = computed(() => order.value.filter(name => !hiddenNow.value.has(name)));

  function setHidden(name: string, hide: boolean): void {
    if (name === "id") return; // the key column is never hidden
    // THE RULE VIEW HAS NOTHING TO WRITE, and writing it would be the lie: the page
    // would take a list nothing reads, and a reload would throw it away in silence.
    if (props.rule) return;
    // A NEW Set on every change: it is its identity the `computed` reads.
    const next = new Set(hidden.value);
    if (hide) {
      next.add(name);
      onHide(name);
      if (narrowShown.value.delete(name)) saveNarrow();
    } else {
      next.delete(name);
      if (narrow.value && !priority.value.has(name) && !narrowShown.value.has(name)) {
        narrowShown.value.add(name);
        saveNarrow();
      }
    }
    hidden.value = next;
    if (hidden.value.size) viewPrefs.hidden = order.value.filter(name => hidden.value.has(name));
    else delete viewPrefs.hidden;
    saveColumns();
  }

  // --- drag and drop -----------------------------------------------------------
  const dragName = ref<string | null>(null);
  const dropMark = ref<{ name: string; after: boolean } | null>(null);

  function dropColumn(target: string, after: boolean): void {
    if (props.rule) return; // the order is the table's here, as the set is
    const moved = dragName.value;
    if (!moved || moved === target) return;
    dragName.value = null;
    dropMark.value = null;
    const next = order.value.filter(name => name !== moved);
    if (target === "id") next.splice(1, 0, moved);
    else {
      const at = next.indexOf(target);
      next.splice(after ? at + 1 : at, 0, moved);
    }
    order.value = next;
    viewPrefs.order = next;
    saveColumns();
  }

  const isPast = (ev: DragEvent, th: HTMLElement): boolean =>
    ev.clientX > th.getBoundingClientRect().left + th.offsetWidth / 2;

  function onDragStart(ev: DragEvent, name: string): void {
    dragName.value = name;
    if (ev.dataTransfer) {
      ev.dataTransfer.effectAllowed = "move";
      ev.dataTransfer.setData("text/plain", name);
    }
  }
  function onDragEnd(): void {
    dragName.value = null;
    dropMark.value = null;
  }
  function onDragOver(ev: DragEvent, name: string): void {
    if (!dragName.value || dragName.value === name) return;
    ev.preventDefault();
    if (ev.dataTransfer) ev.dataTransfer.dropEffect = "move";
    dropMark.value = { name, after: isPast(ev, ev.currentTarget as HTMLElement) };
  }
  function onDrop(ev: DragEvent, name: string): void {
    ev.preventDefault();
    dropColumn(name, isPast(ev, ev.currentTarget as HTMLElement));
  }

  return { order, hidden, hiddenNow, shown, setHidden, dropMark,
           onDragStart, onDragEnd, onDragOver, onDrop };
}


<script setup lang="ts">
// TableView — one table's records, as a table, with the filter each column
// carries. The biggest piece of AT's UI.
//
// What it does NOT decide: any vocabulary. The columns (with names, types,
// references and flags) come from the table's own schema, the records from the
// API, and every word from the catalog. No field name is known here.
//
// What it DOES decide, and what matters to preserve:
// · the ORDER of the columns and which are HIDDEN are the person's preference
//   (`at.columns`, per VIEW), so they outlive the reload — and a column the
//   store gains LATER lands at the end;
// · each column's filter is the SET OF VALUES it accepts, and what is left out is
//   the preference (`at.filters`, per table.field);
// · each column's width is MEASURED on the content and on the theme's font,
//   never guessed — and measured over EVERY record, so filtering does not change
//   the table's shape.

import { ref, computed, watch, watchEffect, onMounted, nextTick } from "vue";
import { store, label, word } from "../lib/store";
import { COLUMNS_KEY, FILTERS_KEY, loadPrefs, savePrefs } from "../lib/prefs";
import { openPop, closePop, isPopOpen } from "../lib/pop";
import { openContextMenu, vContextMenu, type MenuItem } from "../lib/menu";
import { leave, markPage, setLiveCount } from "../lib/views";
import { narrow } from "../lib/breakpoint";
import { plainText, rendererReady, ensureRenderer } from "../lib/markdown";
import FieldValue from "./FieldValue.vue";
import FilterPop from "./pops/FilterPop.vue";
import ColumnsPop from "./pops/ColumnsPop.vue";
import type { FieldSpec, RecordField, RecordRef, RecordRow } from "../lib/record";

const props = withDefaults(
  defineProps<{
    entity: string;          // the table (the write and the filter name it)
    records: RecordRow[];
    schema?: FieldSpec[];
    viewKey?: string | null; // the key of the column preferences
    page?: string | null;    // what a reload returns to (`at.select`)
    // THE COLUMNS ARE THE VIEW'S RULE, OR THE PERSON'S PREFERENCE.
    // A TABLE is the person's: order, what is hidden and what comes back are
    // `at.columns`, per view, and they survive the reload. The PROJECTS pages
    // are not that — there the columns ARE the rule, declared by the table
    // (`hide: ["project", "orphans"]`), because those columns are not a taste: on
    // a project's page every row carries the same project and the same absence,
    // and four columns saying it say nothing. Where this is true the saved
    // preference is NOT read and nothing is written: a rule the person can
    // silently overwrite stops being a rule.
    rule?: boolean;
    defaults?: string[] | null; // columns shown before the person hides any
    // What the ENGINE says this actor may do to a row of this table
    // (TASK-120, fatia 1) — the context menu's own content, and never this
    // component's invention. Row-independent: one list for the whole table.
    actions?: string[];
  }>(),
  { schema: () => [], viewKey: null, page: null, rule: false, defaults: null,
    actions: () => [] },
);

const emit = defineEmits<{
  count: [shown: number, hidden: number];
  ref: [ref: RecordRef];
}>();

// A CELL IS CUT AT THE TABLE'S CEILING, never at a number of this file's own: a
// field that declares `max_length` PROMISES the value fits. `CELL_LIMIT` is what
// is left for the fields that promised nothing.
const CELL_LIMIT = 200;

const fields = computed<FieldSpec[]>(() => props.schema || []);
const byName = computed<Record<string, FieldSpec>>(() =>
  Object.fromEntries(fields.value.map(field => [field.name, field])),
);
const ALL = computed(() => fields.value.map(field => field.name));

const limitOf = (name: string): number => byName.value[name]?.max_length || CELL_LIMIT;

const columnKey = computed(() => props.viewKey || props.entity);
const page = computed(() => props.page || props.entity);

const value = (rec: RecordRow, name: string): RecordField =>
  rec.fields.find(field => field.name === name) || { name, type: null, value: "", raw: null, refs: [] };

const cell = (rec: RecordRow, name: string): string =>
  name === "id" ? String(rec.id ?? "") : value(rec, name).value || "";

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

// A DATE SORTS BY WHAT IS STORED, never by what is shown: the locale writes
// `22/09/2026`, and that text sorts by the day of the month. The stored value is
// ISO, which sorts the way time does — so the display is free to be a display.
const sortCell = (rec: RecordRow, name: string): string => {
  const field = value(rec, name);
  if (field.type === "day" || field.type === "instant") {
    return field.raw == null ? "" : String(field.raw);
  }
  return cell(rec, name);
};

const by = (a: string, b: string): number =>
  String(a).localeCompare(String(b), undefined, { numeric: true, sensitivity: "base" });

// --- the order and what is hidden (preference, per VIEW) ----------------------
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

// --- the narrow screen ---------------------------------------------------------
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

// --- each column's filter -----------------------------------------------------
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

const sort = ref<{ name: string; dir: number } | null>(null);
const dragName = ref<string | null>(null);
const dropMark = ref<{ name: string; after: boolean } | null>(null);

const ordered = computed(() => {
  if (!sort.value) return visible.value;
  const { name, dir } = sort.value;
  return visible.value
    .slice()
    .sort((a, b) => dir * sortCell(a, name).localeCompare(sortCell(b, name), undefined,
                                                           { numeric: true, sensitivity: "base" }));
});

watchEffect(() => {
  emit("count", visible.value.length, props.records.length - visible.value.length);
  // And the same number goes to the PANEL, which is where the person looks to
  // know how much is in a table.
  setLiveCount(page.value, visible.value.length);
});

function toggleSort(name: string): void {
  sort.value = sort.value && sort.value.name === name
    ? { name, dir: -sort.value.dir }
    : { name, dir: 1 };
}

// Hiding a column DROPS its filter and its sort: a filter nobody can see goes on
// hiding rows with no visible reason.
function setHidden(name: string, hide: boolean): void {
  if (name === "id") return; // the key column is never hidden
  // THE RULE VIEW HAS NOTHING TO WRITE, and writing it would be the lie: the page
  // would take a list nothing reads, and a reload would throw it away in silence.
  if (props.rule) return;
  // A NEW Set on every change: it is its identity the `computed` reads.
  const next = new Set(hidden.value);
  if (hide) {
    next.add(name);
    if (sort.value && sort.value.name === name) sort.value = null;
    delete filters.value[name];
    delete filterPrefs[prefName(name)];
    savePrefs(FILTERS_KEY, filterPrefs);
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

// --- the panels ---------------------------------------------------------------
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

function openColumns(anchor: HTMLElement | null): void {
  // No panel where there is nothing to choose: the columns are the rule, and a
  // panel of checkboxes that undo themselves would be a door painted on a wall.
  if (props.rule) return;
  openPop("columns:" + columnKey.value, ColumnsPop,
          { order: order.value, hidden: hiddenNow.value, fields: fields.value,
            onToggle: setHidden },
          { anchor });
}

// THE HEADER'S RIGHT CLICK, THROUGH THE ONE DOOR (TASK-120, fatia 1): a menu
// opens at the pointer, and its one item calls the SAME `openColumns` the
// header always called — the anchor is captured HERE, at open time, and not
// read off the menu item's own click later.
function openHeaderMenu(ev: MouseEvent): void {
  if (props.rule) return;
  const anchor = ev.currentTarget as HTMLElement;
  openContextMenu(ev, [{ label: word("columns"), action: () => openColumns(anchor) }]);
}

// A ROW'S RIGHT CLICK (and the context-menu key, Shift+F10, and a touch
// long-press — `v-context-menu` either way): what it offers is exactly what
// the engine said was legal (`props.actions`), and nothing this component
// invents.
function openRowMenu(ev: MouseEvent, rec: RecordRow): void {
  const items: MenuItem[] = [];
  if (props.actions.includes("edit")) {
    items.push({ label: word("edit"), action: () => openRecord(rec) });
  }
  openContextMenu(ev, items);
}

// A closure PER ROW, made in script and not in the template: the directive's
// handler type takes only an event, and `rec` is what tells rows apart.
function rowMenuHandler(rec: RecordRow): (ev: MouseEvent) => void {
  return ev => openRowMenu(ev, rec);
}

// --- each column's width: MEASURED, never guessed -----------------------------
const probeEl = ref<HTMLSpanElement | null>(null);
const widths = ref<number[]>([]);

function widthOf(text: string): number {
  const node = probeEl.value;
  if (!node) return 0;
  node.textContent = text;
  return node.getBoundingClientRect().width;
}

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

// A hidden span measures the text IN THE ACTIVE FONT: the theme styles it
// (`.probe`), so the measurement follows the theme like everything else.
function measure(): void {
  const css = getComputedStyle(document.documentElement);
  const chPx = widthOf("0".repeat(50)) / 50 || 0;
  const measurePx = (parseFloat(css.getPropertyValue("--measure")) || 66) * chPx;
  const padPx = 2 * (parseFloat(css.getPropertyValue("--cell-pad")) || 0);

  // `flexible` marks the column the reading measure CAPPED — the one holding a
  // long text. It is the one that gives up room on a narrow screen.
  function column(name: string): { px: number; flexible: boolean } {
    const spec = byName.value[name];
    let need = widthOf(label(spec?.labels) || name);
    if (spec?.refs?.length) need += chPx;
    if (spec?.filterable) need += 2 * chPx;
    if (sort.value && sort.value.name === name) need += chPx;
    let longest = "";
    for (const rec of props.records) {
      const text = shownText(name, rec);
      if (text.length > longest.length) longest = text;
    }
    need = Math.max(need, widthOf(longest));
    return { px: Math.min(need, measurePx) + padPx + 1, flexible: need > measurePx };
  }

  const entries = shown.value.map(column);
  const out = entries.map(entry => entry.px);

  // THE TABLE FITS THE ROOM IT IS HANDED: the columns the MEASURE capped give up
  // the excess between them, down to a floor where the text wraps instead of
  // vanishing. The short columns keep what their content needs.
  {
    const body = document.getElementById("body");
    const pagePad = 2 * (parseFloat(css.getPropertyValue("--page-pad-x")) || 20);
    const panelW = (body?.clientWidth || window.innerWidth) - (narrow.value ? 0 : pagePad);
    const floor = 5 * chPx + padPx + 1; // where the text wraps instead of vanishing
    let total = out.reduce((a, b) => a + b, 0);
    // 1) The READING columns give up first: they have room to spare.
    for (const i of entries.map((entry, i) => (entry.flexible ? i : -1)).filter(i => i >= 0)) {
      if (total <= panelW) break;
      const give = Math.min(out[i] - floor, total - panelW);
      if (give > 0) {
        out[i] -= give;
        total -= give;
      }
    }
    // 2) And if even that is not enough, the columns with the MOST ROOM give up
    // first — by slack, and never by position. Walking the columns left to right
    // is what the first version did, and it took everything from whoever came
    // first: the id and the title were squeezed to nothing while the widest
    // column kept every pixel it had asked for. "The ones with room to spare" is
    // not a position; it is how much is left over the floor.
    const bySlack = entries.map((_, i) => i).sort((a, b) => (out[b] - out[a]));
    for (const i of bySlack) {
      if (total <= panelW) break;
      const give = Math.min(out[i] - floor, total - panelW);
      if (give > 0) {
        out[i] -= give;
        total -= give;
      }
    }
  }

  widths.value = out;
}

watch(
  [order, hidden, hiddenNow, sort, () => props.records, () => store.themes, narrow, rendererReady],
  () => nextTick(measure),
);

onMounted(async () => {
  nextTick(measure);
  // A markdown column is drawn as the text its notation CARRIES, and taking the
  // notation out is the parser's job — so the renderer is asked for here, ONCE.
  if (fields.value.some(field => field.type === "markdown")) await ensureRenderer();
});

function openRecord(rec: RecordRow): void {
  leave(); // the table is where this record is being read from
  markPage(page.value, rec.id);
}
</script>

<template>
  <div v-if="!records.length" class="empty">{{ word("no_records") }}</div>
  <template v-else>
    <!-- THE COUNT OF THE COLUMNS THAT STEPPED ASIDE IS NOT A COLUMN: it is a MARK
         PINNED TO THE CORNER, drawn over the box instead of inside it, so the grid
         keeps exactly the columns the grid has. And it is OUTSIDE THE TABLE, ABOVE
         IT — under the grid a "+3" reads as "+3 ROWS", and the count is about the
         COLUMNS. -->
    <p v-if="hiddenNow.size" class="hidden-count">
      <!-- On a view where the columns are the person's it opens the panel; on a
           RULE view it is the sentence alone, because a control that undoes
           itself is worse than none. -->
      <button v-if="!rule" type="button" :title="word('columns')" :aria-label="word('columns')"
              @click.stop="openColumns($event.currentTarget as HTMLElement)"
              >+{{ hiddenNow.size }} {{ word("hidden") }}</button>
      <span v-else>+{{ hiddenNow.size }} {{ word("hidden") }}</span>
    </p>
    <table>
      <colgroup>
        <col v-for="(w, i) in widths" :key="i" :style="{ width: w + 'px' }">
      </colgroup>
      <thead>
        <tr>
          <th v-for="name in shown" :key="name" class="sortable"
              :title="(byName[name]?.refs || []).length
                ? word('refers') + ' ' + (byName[name].refs || []).map(r => label(r.labels)).join(', ')
                : undefined"
              :draggable="!rule && name !== 'id'"
              :class="{ 'drop-before': dropMark && dropMark.name === name && !dropMark.after,
                        'drop-after': dropMark && dropMark.name === name && dropMark.after }"
              @click="toggleSort(name)"
              v-context-menu="openHeaderMenu"
              @dragstart="onDragStart($event, name)"
              @dragend="onDragEnd"
              @dragover="onDragOver($event, name)"
              @dragleave="dropMark = null"
              @drop="onDrop($event, name)">
            <span>{{ label(byName[name]?.labels) || name }}</span>
            <span v-if="(byName[name]?.refs || []).length" class="to">→</span>
            <span v-if="sort && sort.name === name" class="arrow">{{ sort.dir > 0 ? " ▲" : " ▼" }}</span>
            <button v-if="byName[name]?.filterable" type="button" class="fbtn"
                    :class="{ on: !!filters[name] }"
                    :title="word('filter')" :aria-label="word('filter')"
                    @click.stop="toggleFilter($event, name)"></button>
          </th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="rec in ordered" :key="rec.id" :title="rec.title || ''" tabindex="0"
            @click="openRecord(rec)"
            v-context-menu="rowMenuHandler(rec)">
          <template v-for="name in shown" :key="name">
            <!-- `data-label` is the column's header, carried by the CELL: on a
                 narrow screen the header row is gone and each cell becomes a line
                 of a card, so the cell has to say what it is (base.css, 640). -->
            <td v-if="name === 'id'" class="id"
                :data-label="label(byName[name]?.labels) || name">{{ cell(rec, name) }}</td>
            <td v-else :data-label="label(byName[name]?.labels) || name"
                :data-value="enumOf(rec, name)"
                :title="String(value(rec, name).value || '').length > limitOf(name)
                  ? String(value(rec, name).value) : undefined">
              <!-- The `.v` is the cell's VALUE as ONE thing, and it is what a
                   theme dresses when the column declares a closed list — the
                   mark `data-value` sits on the cell and the drawing on this. -->
              <span class="v"><FieldValue :field="value(rec, name)" :limit="limitOf(name)" by-title
                          @ref="emit('ref', $event)" /></span>
            </td>
          </template>
        </tr>
      </tbody>
    </table>
    <span ref="probeEl" class="probe"></span>
  </template>
</template>

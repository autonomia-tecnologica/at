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

import { computed, watchEffect } from "vue";
import { label, word } from "../lib/store";
import { vContextMenu } from "../lib/menu";
import { setLiveCount } from "../lib/views";
import { useCells, value, cell } from "../lib/tableCells";
import { useFilters } from "../lib/tableFilters";
import { useSort } from "../lib/tableSort";
import { useColumns } from "../lib/tableColumns";
import { useWidths } from "../lib/tableWidths";
import { useMenus } from "../lib/tableMenus";
import { useCellEdit } from "../lib/tableEdit";
import FieldValue from "./FieldValue.vue";
import EmptyState from "./EmptyState.vue";
import type { DeclarableTable, FieldSpec, RecordRef, RecordRow } from "../lib/record";

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
    // O PAINEL DE DECLARAR (relógio, fatia 3/3): o que há para agendar,
    // presente só no payload da tabela `job` — nas demais `actions` nunca
    // traz `declare`, e o menu nem lê este prop.
    declarable?: DeclarableTable[];
    // O MODO DA TABELA (TASK-175): "tables" é a seção Tabelas, que edita como
    // planilha — clicar numa célula edita ali mesmo. Sem isto (as telas de
    // Configurações, `ActorView`/`RoleView`/`PeopleView`), o clique na linha
    // continua abrindo o registro inteiro, como sempre foi.
    section?: "tables" | "tasks" | null;
  }>(),
  { schema: () => [], viewKey: null, page: null, rule: false, defaults: null,
    actions: () => [], declarable: () => [], section: null },
);

const emit = defineEmits<{
  count: [shown: number, hidden: number];
  ref: [ref: RecordRef];
}>();

const fields = computed<FieldSpec[]>(() => props.schema || []);
const { byName, ALL, limitOf, enumOf, shownText } = useCells(fields);

const columnKey = computed(() => props.viewKey || props.entity);
const page = computed(() => props.page || props.entity);

const { isOn, visible, dropFilter, toggleFilter } = useFilters(props, fields);
const { sort, ordered, toggleSort } = useSort(visible);

// Hiding a column DROPS its filter and its sort: a filter nobody can see goes on
// hiding rows with no visible reason.
const { order, hidden, hiddenNow, shown, setHidden, dropMark,
        onDragStart, onDragEnd, onDragOver, onDrop } =
  useColumns(props, fields, ALL, columnKey, name => {
    if (sort.value && sort.value.name === name) sort.value = null;
    dropFilter(name);
  });

watchEffect(() => {
  emit("count", visible.value.length, props.records.length - visible.value.length);
  // And the same number goes to the PANEL, which is where the person looks to
  // know how much is in a table.
  setLiveCount(page.value, visible.value.length);
});

const { openColumns, openHeaderMenu, openEmptyMenu, rowMenuHandler, onRowClick } =
  useMenus(props, fields, columnKey, order, hiddenNow, setHidden);

const { probeEl, widths } = useWidths(props, fields, byName, shown, sort, shownText,
                                      [order, hidden, hiddenNow]);

const { editValue, editInputEl, isEditing, cellEditable, onCellClick, commitEdit, cancelEdit } =
  useCellEdit(props, byName);
</script>

<template>
  <EmptyState v-if="!records.length" :title="word('no_records')" v-context-menu="openEmptyMenu" />
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
      <button v-if="!rule" type="button" class="btn btn-sm btn-ghost" :title="word('columns')" :aria-label="word('columns')"
              @click.stop="openColumns($event.currentTarget as HTMLElement)"
              >+{{ hiddenNow.size }} {{ word("hidden") }}</button>
      <span v-else>+{{ hiddenNow.size }} {{ word("hidden") }}</span>
    </p>
    <!-- THE GRID WEARS `.grid` (2026-10-05): the product's table block in
         `base.css` — the card, the sticky uppercase header, the mobile
         `data-label` stacking — is THIS table's and no other's. A markdown
         table (a `.md` file, a chat answer) is a table too, and it must NOT
         wear the product's dress; scoping the block to `.grid` is what keeps
         the two apart. -->
    <table class="grid" :class="{ 'cells-edit': section === 'tables' }">
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
                        'drop-after': dropMark && dropMark.name === name && dropMark.after,
                        'id-col': name === 'id' }"
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
                    :class="{ on: isOn(name) }"
                    :title="word('filter')" :aria-label="word('filter')"
                    @click.stop="toggleFilter($event, name)"></button>
          </th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="rec in ordered" :key="rec.id" :title="rec.title || ''" tabindex="0"
            @click="onRowClick($event, rec)"
            v-context-menu="rowMenuHandler(rec)">
          <template v-for="name in shown" :key="name">
            <!-- `data-label` is the column's header, carried by the CELL: on a
                 narrow screen the header row is gone and each cell becomes a line
                 of a card, so the cell has to say what it is (base.css, 640). -->
            <td v-if="name === 'id'" class="id"
                :data-label="label(byName[name]?.labels) || name">{{ cell(rec, name) }}</td>
            <td v-else :data-label="label(byName[name]?.labels) || name"
                :data-value="enumOf(rec, name)"
                :class="{ editable: cellEditable(name), editing: isEditing(rec, name) }"
                :title="String(value(rec, name).value || '').length > limitOf(name)
                  ? String(value(rec, name).value) : undefined"
                @click="onCellClick($event, rec, name)">
              <!-- A CÉLULA EDITA A SI MESMA (TASK-175, seção Tabelas): o input
                   substitui a leitura só NESTA célula, enquanto `editing` a
                   aponta — Enter/blur grava, Esc cancela. -->
              <input v-if="isEditing(rec, name)" ref="editInputEl" v-model="editValue"
                     @click.stop
                     @keydown.enter="commitEdit(rec, name)"
                     @keydown.esc.stop="cancelEdit"
                     @blur="commitEdit(rec, name)">
              <!-- The `.v` is the cell's VALUE as ONE thing, and it is what a
                   theme dresses when the column declares a closed list — the
                   mark `data-value` sits on the cell and the drawing on this. -->
              <span v-else class="v"><FieldValue :field="value(rec, name)" :limit="limitOf(name)" by-title
                          @ref="emit('ref', $event)" /></span>
            </td>
          </template>
        </tr>
      </tbody>
    </table>
    <span ref="probeEl" class="probe"></span>
  </template>
</template>

<script setup lang="ts">
// TaskBoard — the tasks of a table, as a BOARD: one column per status, and a
// card is moved between them by dragging it — the same write the pick already
// does (`PickPop.vue`), through the same door (`action: "edit"`).
//
// THE COLUMNS ARE THE TABLE'S OWN VOCABULARY, in the order it declares them
// (`fields.status.enum`) — never a list written here, the same rule
// `TasksView.vue` already keeps for its counts.
//
// A CARD OPENS THE RECORD AS A FLOATING PANEL (TASK-173), over the board
// itself — the same door a task row in `TableView.vue` now opens through —
// so the board never leaves the screen for it.
//
// O VALOR É O CONTROLE (B-54, fatia 3): o título, a prioridade, o prazo, o
// projeto e as tags editam NO CARD, pelo `FieldEditor` — o mesmo editor da
// grade e do painel, e o tipo DECLARADO escolhe o controle. O status continua
// só pelo arrasto entre as colunas, e o `desc` (prosa) continua no painel.

import { computed, ref } from "vue";
import { label, word } from "../lib/store";
import { post } from "../lib/api";
import { showError, poke } from "../lib/views";
import { openPop } from "../lib/pop";
import { openContextMenu, vContextMenu, type MenuItem } from "../lib/menu";
import { ask } from "../lib/confirm";
import { toast } from "../lib/toast";
import { OFFLINE_TABLE, offlineState, writeTask } from "../lib/offline";
import { useFilters } from "../lib/tableFilters";
import FieldEditor from "./FieldEditor.vue";
import EmptyState from "./EmptyState.vue";
import RecordPop from "./pops/RecordPop.vue";
import ClosePop from "./pops/ClosePop.vue";
import type { FieldSpec, RecordField, RecordRef, RecordRow } from "../lib/record";

const props = withDefaults(
  defineProps<{
    entity: string;
    records: RecordRow[];
    schema: FieldSpec[];
    page: string;
    // Whether a card shows which project it belongs to. A project's OWN board
    // hides it — every card there already lives inside that page — the same
    // reason the table declares `hide: ["project", "orphans"]` for the column.
    showProject?: boolean;
    // Whether the quick-add ("nova tarefa") input is offered. A project's OWN
    // board does NOT: `addCard` below writes no `project`, so a card born
    // there would land as an orphan while the page it was born on says
    // otherwise — the input stays only where that mismatch cannot happen.
    allowCreate?: boolean;
    // O QUE O ENGINE DIZ QUE ESTE ATOR ALCANÇA NESTA TABELA (`_table_actions`):
    // o painel do registro que o card abre recebe a lista, e sem `edit` nele
    // nasce só de leitura (`RecordView`).
    actions?: string[];
  }>(),
  { showProject: true, allowCreate: true, actions: () => [] },
);

const emit = defineEmits<{ ref: [ref: RecordRef] }>();

const specOf = (name: string): FieldSpec | undefined => props.schema.find(f => f.name === name);

function fieldOf(rec: RecordRow, name: string): RecordField | null {
  return rec.fields.find(f => f.name === name) || null;
}

function rawOf(rec: RecordRow, name: string): unknown {
  return fieldOf(rec, name)?.raw ?? null;
}

// THE COLUMNS, in the STATUS field's own declared order — a status the table
// gains is a column this board gains, untouched.
const statuses = computed(() => {
  const spec = specOf("status");
  return Object.entries(spec?.enum || {}).map(([key, labels]) => ({ key, labels }));
});

// THE FILTERS ARE THE TABLE'S (`useFilters`): the same ones `TableView` draws on
// the column heads, the same preference (`at.filters`, per table.field) — what
// is left out in one is left out in the other. A column of days filters by
// interval. The PROJECT is not offered: the projects tree is the door for it,
// and the other filters add to the tree's cut. `id` is a number, not a cut.
const schemaFields = computed<FieldSpec[]>(() => props.schema || []);
const { isOn, visible, toggleFilter } = useFilters(props, schemaFields);
const filterable = computed(() =>
  schemaFields.value.filter(f => f.filterable && f.name !== "project" && f.name !== "id"));

const grouped = computed(() => {
  const out: Record<string, RecordRow[]> = {};
  for (const status of statuses.value) out[status.key] = [];
  for (const rec of visible.value) {
    const status = String(rawOf(rec, "status") ?? "");
    (out[status] ||= []).push(rec);
  }
  return out;
});

// O PAR QUE O `FieldEditor` DESENHA: a declaração e o valor daquela linha.
// Cada campo que o card edita é o que a DECLARAÇÃO nomeia — o card não inventa
// tipo nem nome, e o `FieldEditor` decide o controle pelo `spec.type`.
interface CardPart {
  field: RecordField;
  spec: FieldSpec;
}

function partOf(rec: RecordRow, name: string): CardPart | null {
  const spec = specOf(name);
  const field = fieldOf(rec, name);
  return spec && field ? { field, spec } : null;
}

// O TÍTULO É O CAMPO `text` (o `primary` da tabela); o card antigo lia
// `rec.title`, que é o mesmo valor já escrito. Sem o campo, o que resta é o
// título que a linha trouxe, e só para ler.
const titlePart = (rec: RecordRow): CardPart | null => partOf(rec, "text");
const priorityPart = (rec: RecordRow): CardPart | null => partOf(rec, "priority");
const tagsPart = (rec: RecordRow): CardPart | null => partOf(rec, "tags");

const priorityValue = (rec: RecordRow): string | null => {
  const raw = rawOf(rec, "priority");
  return raw === null || raw === undefined || raw === "" ? null : String(raw);
};

const projectPart = (rec: RecordRow): CardPart | null =>
  props.showProject ? partOf(rec, "project") : null;
const deadlinePart = (rec: RecordRow): CardPart | null => partOf(rec, "deadline");

// UM CAMPO VAZIO AINDA É O CONTROLE QUANDO HÁ PERMISSÃO DE ESCRITA: o "—" abre
// o `date` ou o seletor. Sem permissão, o campo vazio não vira ruído no card.
const canEdit = computed(() => props.actions.includes("edit"));
const hasValue = (part: CardPart | null): boolean => {
  if (!part) return false;
  const raw = part.field.raw;
  return raw !== null && raw !== undefined && raw !== "";
};
const shows = (part: CardPart | null): boolean => !!part && (hasValue(part) || canEdit.value);

// A CARD OPENS AS A FLOATING PANEL (TASK-173), over the board itself, instead
// of swapping the whole page for it — the board is tasks and only tasks, so
// every card here takes this door.
function openCard(rec: RecordRow): void {
  openPop("record:" + props.entity + ":" + rec.id, RecordPop,
          { entity: props.entity, page: props.page, id: rec.id, records: () => props.records,
            actions: props.actions },
          { attrs: { class: "record-pop" } });
}

// O MENU DO CARD: "abrir registro" é leitura e está sempre; fechar e apagar
// só quando o MOTOR disse que este ator pode (`actions`) — espelha o menu da
// linha em `lib/tableMenus.ts`. "Editar" não mora mais aqui: o valor do card é
// o controle. O `v-context-menu` já para a propagação, então o menu do projeto
// (que `ProjectView` prende no corpo da página) não abre por baixo.
function cardMenuHandler(rec: RecordRow): (ev: MouseEvent) => void {
  return ev => {
    const point = { x: ev.clientX, y: ev.clientY };
    const items: MenuItem[] = [
      { label: word("open_record"), action: () => openCard(rec) },
    ];
    if (props.actions.includes("cancel")) {
      items.push({ label: word("close"), action: () => openClose(rec, point) });
    }
    if (props.actions.includes("delete")) {
      items.push({ label: word("delete"), action: () => deleteTask(rec) });
    }
    openContextMenu(ev, items);
  };
}

function openClose(rec: RecordRow, point: { x: number; y: number }): void {
  openPop("close:" + props.entity + ":" + rec.id, ClosePop,
          { entity: props.entity, id: rec.id, title: rec.title || String(rec.id) },
          { point });
}

async function deleteTask(rec: RecordRow): Promise<void> {
  const name = rec.title || String(rec.id);
  if (!(await ask(word("delete_confirm").replace("{name}", name)))) return;
  try {
    await post("/api/table/" + encodeURIComponent(props.entity), { action: "delete", id: rec.id });
    poke();
  } catch (err) {
    toast((err as Error).message);
  }
}

// --- dragging one card between columns ------------------------------------
const draggingId = ref<number | null>(null);
const overColumn = ref<string | null>(null);

function onDragStart(rec: RecordRow, ev: DragEvent): void {
  draggingId.value = rec.id;
  if (ev.dataTransfer) {
    ev.dataTransfer.effectAllowed = "move";
    ev.dataTransfer.setData("text/plain", String(rec.id));
  }
}

function onDragEnd(): void {
  draggingId.value = null;
  overColumn.value = null;
}

async function onDrop(status: string, ev: DragEvent): Promise<void> {
  ev.preventDefault();
  overColumn.value = null;
  const id = draggingId.value;
  draggingId.value = null;
  if (id === null) return;
  const rec = props.records.find(r => r.id === id);
  if (!rec || rawOf(rec, "status") === status) return;
  try {
    // TASKS TAKE THE FILA'S DOOR offline (TASK-162) — the same door
    // `PickPop.vue` takes for the very same field, and for the same reason:
    // a request that never got an ANSWER is queued instead of refused, and
    // the card is moved on screen in place of a redraw that would fail the
    // same way the request did.
    if (props.entity === OFFLINE_TABLE) {
      const { queued } = await writeTask("edit", { status }, id);
      if (queued) {
        const field = fieldOf(rec, "status");
        if (field) field.raw = status;
        return;
      }
      poke();
      return;
    }
    await post("/api/table/" + encodeURIComponent(props.entity), {
      action: "edit",
      id,
      set: { status },
    });
    poke();
  } catch (err) {
    showError(err as Error);
  }
}

// --- adding a card, straight from the board --------------------------------
// THE BOARD IS WHERE A CARD IS MOVED, and until now nowhere was a card BORN —
// no view of the product wrote `action: "create"` for a task (TASK-121 and
// TASK-137, still `a-refinar`, are where that gesture will live for every
// table). TASK-162's own pronto-quando needs one path that works offline, and
// this is the narrowest: a title, Enter, and the first column the table's own
// order names — the fila's `create` (fatia 1) already knows what to do with
// it, offline or not.
const draft = ref("");

function draftField(name: string, raw: string): RecordField {
  const spec = specOf(name);
  return { name, type: spec?.type ?? null, value: label(spec?.enum?.[raw]) || raw, raw, refs: [] };
}

async function addCard(): Promise<void> {
  const text = draft.value.trim();
  if (!text || props.entity !== OFFLINE_TABLE) return;
  const status = statuses.value[0]?.key;
  draft.value = "";
  try {
    const { queued } = await writeTask("create", status ? { text, status } : { text });
    if (queued) {
      // NEGATIVE AND UNIQUE: the one mark this file uses for "not yet a row
      // the server knows" — real ids are allocated from 1 up, so a card born
      // here can never collide with one born there. Not draggable (below)
      // until the fila (`lib/offline.ts`) turns it into a real id.
      const fields = [draftField("text", text)];
      if (status) fields.push(draftField("status", status));
      props.records.push({ id: -Date.now(), shown_id: "…", title: text, fields });
      return;
    }
    poke();
  } catch (err) {
    showError(err as Error);
  }
}
</script>

<template>
  <form v-if="entity === OFFLINE_TABLE && allowCreate" class="board-add" @submit.prevent="addCard">
    <input v-model="draft" type="text" :placeholder="word('new_task')" :aria-label="word('new_task')">
  </form>
  <div v-if="filterable.length" class="board-filters">
    <button v-for="f in filterable" :key="f.name" type="button" class="btn btn-sm btn-ghost"
            :class="{ on: isOn(f.name) }" :title="word('filter')"
            @click.stop="toggleFilter($event, f.name)">{{ label(f.labels) || f.name }}</button>
  </div>
  <div class="board">
    <div v-for="status in statuses" :key="status.key" class="board-col"
         :data-state="status.key" :class="{ over: overColumn === status.key }"
         @dragover.prevent="overColumn = status.key" @dragleave="overColumn = null"
         @drop="onDrop(status.key, $event)">
      <div class="board-col-head">
        <span>{{ label(status.labels) }}</span>
        <span class="n">{{ (grouped[status.key] || []).length }}</span>
      </div>
      <div class="board-col-body">
        <!-- O CARD É UM CONTAINER, e não um `<button>`: os editores também são
             controles, e botão não se aninha em botão. O corpo abre o registro;
             o título, a prioridade, o prazo, o projeto e as tags editam no
             lugar — cada editor para o clique antes de ele chegar aqui. -->
        <div v-for="rec in grouped[status.key] || []" :key="rec.id"
             class="task-card" role="button" tabindex="0"
             :draggable="rec.id > 0" :class="{ dragging: draggingId === rec.id }"
             v-context-menu="cardMenuHandler(rec)"
             @touchstart.stop
             @dragstart="rec.id > 0 && onDragStart(rec, $event)" @dragend="onDragEnd"
             @click.stop="openCard(rec)"
             @keydown.enter.self.stop.prevent="openCard(rec)"
             @keydown.space.self.stop.prevent="openCard(rec)">
          <div class="task-card-text">
            <FieldEditor v-if="titlePart(rec)" :field="titlePart(rec)!.field"
                         :spec="titlePart(rec)!.spec" :entity="entity" :record="rec"
                         :can-edit="actions.includes('edit')" />
            <span v-else>{{ rec.title }}</span>
          </div>
          <div v-if="shows(priorityPart(rec)) || shows(projectPart(rec))" class="task-card-meta">
            <div v-if="shows(priorityPart(rec))"
                 :class="{ chip: hasValue(priorityPart(rec)) }"
                 :data-value="priorityValue(rec) || undefined">
              <FieldEditor :field="priorityPart(rec)!.field" :spec="priorityPart(rec)!.spec"
                           :entity="entity" :record="rec"
                           :can-edit="actions.includes('edit')" />
            </div>
            <FieldEditor v-if="shows(projectPart(rec))" :field="projectPart(rec)!.field"
                         :spec="projectPart(rec)!.spec" :entity="entity" :record="rec"
                         :can-edit="actions.includes('edit')" @ref="emit('ref', $event)" />
          </div>
          <div v-if="shows(deadlinePart(rec))" class="task-card-deadline">
            <FieldEditor :field="deadlinePart(rec)!.field" :spec="deadlinePart(rec)!.spec"
                         :entity="entity" :record="rec"
                         :can-edit="actions.includes('edit')" />
          </div>
          <!-- AS TAGS APARECEM MESMO VAZIAS: é o "+" delas que adiciona. -->
          <div v-if="tagsPart(rec)" class="task-card-tags">
            <FieldEditor :field="tagsPart(rec)!.field" :spec="tagsPart(rec)!.spec"
                         :entity="entity" :record="rec"
                         :can-edit="actions.includes('edit')" />
          </div>
        </div>
        <EmptyState v-if="!(grouped[status.key] || []).length" icon="note" :title="word('no_records')" />
      </div>
    </div>
  </div>
</template>

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

import { computed, ref } from "vue";
import { label, word } from "../lib/store";
import { post } from "../lib/api";
import { showError, poke } from "../lib/views";
import { openPop } from "../lib/pop";
import { OFFLINE_TABLE, offlineState, writeTask } from "../lib/offline";
import FieldValue from "./FieldValue.vue";
import RecordPop from "./pops/RecordPop.vue";
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
  }>(),
  { showProject: true, allowCreate: true },
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

const grouped = computed(() => {
  const out: Record<string, RecordRow[]> = {};
  for (const status of statuses.value) out[status.key] = [];
  for (const rec of props.records) {
    const status = String(rawOf(rec, "status") ?? "");
    (out[status] ||= []).push(rec);
  }
  return out;
});

const priorityValue = (rec: RecordRow): string | null => {
  const raw = rawOf(rec, "priority");
  return raw === null || raw === undefined || raw === "" ? null : String(raw);
};

const priorityLabel = (rec: RecordRow): string => {
  const value = priorityValue(rec);
  const spec = specOf("priority");
  return (value && spec && label(spec.enum[value])) || value || "";
};

const projectField = (rec: RecordRow): RecordField | null => {
  if (!props.showProject) return null;
  const field = fieldOf(rec, "project");
  return field && field.raw !== null && field.raw !== undefined ? field : null;
};

const deadlineText = (rec: RecordRow): string => {
  const field = fieldOf(rec, "deadline");
  return field && field.raw !== null && field.raw !== undefined ? field.value : "";
};

// A CARD OPENS AS A FLOATING PANEL (TASK-173), over the board itself, instead
// of swapping the whole page for it — the board is tasks and only tasks, so
// every card here takes this door.
function openCard(rec: RecordRow): void {
  openPop("record:" + props.entity + ":" + rec.id, RecordPop,
          { entity: props.entity, page: props.page, id: rec.id, records: () => props.records },
          { attrs: { class: "record-pop" } });
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
        <button v-for="rec in grouped[status.key] || []" :key="rec.id" type="button"
                class="task-card" :draggable="rec.id > 0" :class="{ dragging: draggingId === rec.id }"
                @dragstart="rec.id > 0 && onDragStart(rec, $event)" @dragend="onDragEnd"
                @click="openCard(rec)">
          <span class="task-card-text">{{ rec.title }}</span>
          <span v-if="priorityValue(rec) || projectField(rec)" class="task-card-meta">
            <span v-if="priorityValue(rec)" class="chip" :data-value="priorityValue(rec)"
                  >{{ priorityLabel(rec) }}</span>
            <FieldValue v-if="projectField(rec)" :field="projectField(rec)!" by-title
                        @ref="emit('ref', $event)" />
          </span>
          <span v-if="deadlineText(rec)" class="task-card-deadline">{{ deadlineText(rec) }}</span>
        </button>
        <p v-if="!(grouped[status.key] || []).length" class="empty">{{ word("no_records") }}</p>
      </div>
    </div>
  </div>
</template>

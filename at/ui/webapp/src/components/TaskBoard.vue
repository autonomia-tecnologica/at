<script setup lang="ts">
// TaskBoard — the tasks of a table, as a BOARD: one column per status, and a
// card is moved between them by dragging it — the same write the pick already
// does (`PickPop.vue`), through the same door (`action: "edit"`).
//
// THE COLUMNS ARE THE TABLE'S OWN VOCABULARY, in the order it declares them
// (`fields.status.enum`) — never a list written here, the same rule
// `TasksView.vue` already keeps for its counts.
//
// A CARD OPENS THE RECORD, the same gesture a table's row already is
// (`TableView.vue`'s `openRecord`): the board leaves no record of its own, and
// the step back lands where the card was.

import { computed, ref } from "vue";
import { label, word } from "../lib/store";
import { post } from "../lib/api";
import { leave, markPage, showError, poke } from "../lib/views";
import FieldValue from "./FieldValue.vue";
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
  }>(),
  { showProject: true },
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

function openCard(rec: RecordRow): void {
  leave();
  markPage(props.page, rec.id);
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
</script>

<template>
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
                class="task-card" draggable="true" :class="{ dragging: draggingId === rec.id }"
                @dragstart="onDragStart(rec, $event)" @dragend="onDragEnd"
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

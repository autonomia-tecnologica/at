<script setup lang="ts">
// FieldValue — ONE value, cut into what it holds. Every piece is either plain
// text or a REFERENCE, and both readers of the cut come from here: the cell it
// becomes and the single string a column is MEASURED by — so what is measured is
// exactly what is shown.
//
// `limit` is the table's: a cell shows at most that much, and the open record
// passes no limit — the whole value is always there to read.

import { computed } from "vue";
import { plainText } from "../lib/markdown";
import type { RecordField } from "../lib/record";

const props = withDefaults(
  defineProps<{
    field: RecordField;
    limit?: number;
    byTitle?: boolean;
  }>(),
  { limit: 0, byTitle: false },
);

const emit = defineEmits<{ ref: [ref: { key: string; id: number; title: string }] }>();

// What the cell READS: a markdown field is shown as the text its notation
// carries — the cell is a glimpse, not the page where the prose is drawn.
const isProse = computed(() => props.field.type === "markdown");

const text = computed(() =>
  isProse.value ? plainText(props.field.value) : props.field.value || "",
);

// Only http(s) becomes a link — anything else stays text (a `javascript:` value
// never reaches an href).
const isUrl = computed(() => props.field.type === "url" && /^https?:\/\//i.test(text.value));

const pieces = computed(() => {
  let body = text.value;
  if (props.limit && body.length > props.limit) body = body.slice(0, props.limit) + "…";
  const refs = (props.field.refs || [])
    .map(ref => ({ ...ref, shown: ref.shown || String(ref.id), at: body.indexOf(ref.shown || String(ref.id)) }))
    .filter(ref => ref.at >= 0)
    .sort((a, b) => a.at - b.at);
  const out: ({ text: string } | { ref: (typeof refs)[number] })[] = [];
  let at = 0;
  for (const ref of refs) {
    if (ref.at < at) continue;
    if (ref.at > at) out.push({ text: body.slice(at, ref.at) });
    out.push({ ref });
    at = ref.at + ref.shown.length;
  }
  if (at < body.length) out.push({ text: body.slice(at) });
  return out;
});

// A reference the cut left out is no longer in the text, so it does not become a
// link here: the slice is the cell's whole truth.
function linkText(ref: { id: number; title: string }): string {
  return (props.byTitle ? ref.title : null) || String(ref.id);
}

function isRef(piece: unknown): piece is { ref: { key: string; id: number; title: string } } {
  return !!(piece as { ref?: unknown }).ref;
}
</script>

<template>
  <a v-if="isUrl" class="url" :href="text" target="_blank" rel="noopener noreferrer"
     @click.stop>{{ text }}</a>
  <template v-else-if="!text">—</template>
  <template v-else>
    <template v-for="(piece, i) in pieces" :key="i">
      <a v-if="isRef(piece)" class="ref" href="#" :title="piece.ref.title || ''"
         @click.prevent.stop="emit('ref', piece.ref)">{{ linkText(piece.ref) }}</a>
      <template v-else>{{ (piece as { text: string }).text }}</template>
    </template>
  </template>
</template>

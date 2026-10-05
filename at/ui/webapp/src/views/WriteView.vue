<script setup lang="ts">
// WriteView — the file, writing, and NOTHING else on the page (2026-10-05).
//
// IT IS PURE EDITING, AND THE PAGE IS THE FIELD. `App.vue` renders this alone
// when the view is `write:` (`views.ts`) — no panel, no header, no trail, and
// no card: a white surface, the text, and a THIN STATUS LINE at the foot. The
// one screen a person opens to write from a phone, on the road, is not a place
// for a box drawn around the file.
//
// IT OWNS ITS OWN READ. The same door `FileView.vue` reads (`/api/file`), not
// a hand-off from it: a bookmark, a link sent to a phone, or a browser's own
// "open in new tab" all have to work with nothing else open already.
//
// MARKDOWN IS SOURCE, HIGHLIGHTED: no preview, no toolbar — the syntax itself
// wears colour through a mirror layer UNDER the field, the field's own text
// made transparent over it, so what is seen is the mirror's coloured spans and
// what is TYPED is still a plain `<textarea>` — the caret, the selection, the
// undo stack, all the browser's own.
import { ref, computed, onMounted, onBeforeUnmount } from "vue";
import { api } from "../lib/api";
import { word } from "../lib/store";
import { useWriting, writingState } from "../lib/writing";
import { highlightMarkdown } from "../lib/mdHighlight";

interface FilePayload {
  path: string;
  bucket: string;
  writable: boolean;
  rev: string;
  text: string | null;
  reason: string | null;
}

const props = defineProps<{ path: string }>();

const payload = ref<FilePayload | null>(null);
const error = ref("");
const draft = ref("");
const el = ref<HTMLTextAreaElement | null>(null);
const writer = useWriting(() => props.path);

// THE SAME FACT THE READ SIDE ALREADY TRUSTS: `bucket === "text"` is what
// `FileView.vue`/`ProseField.vue` already read as "this is prose" — a second
// rule here, from the extension, could answer differently from the one the
// folder already walks.
const isProse = computed(() => payload.value?.bucket === "text");
const highlighted = computed(() => highlightMarkdown(draft.value));

// WHAT THE STATUS LINE SAYS. The state is the writer's own two facts
// (`writingState`): the failure outranks everything, an edit not yet on the
// disk or a write in flight is "saving", and at rest the disk and the page
// agree.
const stateWord = computed(() => {
  if (writingState.failed) return word("save_failed");
  if (writingState.dirty || writingState.saving) return word("saving");
  return word("saved");
});
const chars = computed(() => draft.value.length);
const words = computed(() => {
  const text = draft.value.trim();
  return text ? text.split(/\s+/).length : 0;
});

// The field GROWS with what is written — the textarea is `overflow: hidden`
// and its own height follows the content, so the page's scroller is the only
// one (`base.css`, `.write-page`).
function grow(): void {
  const node = el.value;
  if (!node) return;
  node.style.height = "auto";
  node.style.height = node.scrollHeight + "px";
}

function onInput(): void {
  writer.touch(draft.value);
  grow();
}

function flush(): void {
  void writer.flush();
}

async function load(): Promise<void> {
  try {
    const found = await api<FilePayload>("/api/file?path=" + encodeURIComponent(props.path));
    payload.value = found;
    error.value = "";
    if (found.text !== null) {
      draft.value = found.text;
      writer.set(found.text, found.rev);
    }
  } catch (err) {
    payload.value = null;
    error.value = (err as Error).message;
  }
}

onMounted(async () => {
  document.title = props.path;
  await load();
  grow();
  el.value?.focus();
  document.addEventListener("visibilitychange", flush);
});

onBeforeUnmount(() => {
  document.removeEventListener("visibilitychange", flush);
  flush();
  writer.leave();
});
</script>

<template>
  <div class="write-page">
    <pre v-if="error" class="text">{{ error }}</pre>
    <template v-else-if="payload">
      <pre v-if="!payload.writable || payload.text === null" class="text">{{ payload.reason || payload.path }}</pre>
      <template v-else>
        <!-- `md` AND NOT `prose`: `prose` is the CONTENT CARD (`base.css` gives
             it a background, corners and a shadow), and a card around the field
             is exactly the box this page must not draw. The modifier only says
             "make the field transparent over the mirror". -->
        <div class="write-page-stage" :class="{ md: isProse }">
          <div v-if="isProse" class="write-highlight" aria-hidden="true" v-html="highlighted"></div>
          <textarea ref="el" v-model="draft" class="write-page-field" spellcheck="false"
                    @input="onInput"></textarea>
        </div>
        <!-- THE THIN STATUS LINE: the save's state, and what is written. Nothing
             else — no button, no chrome. -->
        <footer class="write-status" :class="{ bad: writingState.failed }">
          <span class="state">{{ stateWord }}</span>
          <span class="n">{{ chars }} {{ word("chars") }}</span>
          <span class="n">{{ words }} {{ word("words") }}</span>
        </footer>
      </template>
    </template>
  </div>
</template>

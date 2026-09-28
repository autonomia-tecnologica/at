<script setup lang="ts">
// FileView — one file of the prose folder: read, and written in place when the
// server says it may be.
//
// The page owns NO rule of the write: whether the file may be written is the
// server's answer (`writable`), the revision is the server's, and what saves is
// `WriteField`. Here is only which of the three shapes the file wears.
//
// A markdown file is PROSE (`bucket` — the server's word, not the extension), any
// other text is text as it is, and a file that is not text says why instead.

import { ref, watch, onMounted, onBeforeUnmount, watchEffect } from "vue";
import { api } from "../lib/api";
import { word } from "../lib/store";
import { nav, setTrail } from "../lib/views";
import { writingState } from "../lib/writing";
import ProseField from "../components/ProseField.vue";
import WriteField from "../components/WriteField.vue";

interface FilePayload {
  path: string;
  bucket: string;
  kind: string;
  writable: boolean;
  rev: string;
  text: string | null;
  reason: string | null;
}

const props = defineProps<{ path: string }>();

const payload = ref<FilePayload | null>(null);
const mode = ref<"view" | "write">("view");
const error = ref("");

async function load(): Promise<void> {
  try {
    payload.value = await api<FilePayload>("/api/file?path=" + encodeURIComponent(props.path));
    error.value = "";
  } catch (err) {
    payload.value = null;
    error.value = (err as Error).message;
  }
}

// Re-read BEFORE entering and before leaving write: while writing, the payload's
// text and revision are the ones the field was opened with, and both are stale
// the moment a save lands.
async function toggleWrite(): Promise<void> {
  await load();
  mode.value = mode.value === "write" ? "view" : "write";
}

// Escape leaves writing. It is caught here rather than where the pops are closed,
// because the field has focus and the key is meant for it.
function onKey(ev: KeyboardEvent): void {
  if (ev.key !== "Escape" || mode.value !== "write") return;
  ev.preventDefault();
  mode.value = "view";
}

onMounted(() => {
  void load();
  document.addEventListener("keydown", onKey, true);
});

onBeforeUnmount(() => document.removeEventListener("keydown", onKey, true));

// THE PATH IS THE TRAIL: `Arquivos › Notas › uma nota.md`. Every folder it
// passes through is a step, which is what the path already says — and the
// section is the shell's to add (`App.vue`).
watchEffect(() => setTrail(...String(props.path).split("/")));

watch(() => props.path, () => {
  payload.value = null;
  mode.value = "view";
  void load();
});

// The disk changed: the page re-reads, unless somebody is writing in it.
watch(() => nav.tick, () => {
  if (mode.value === "view") void load();
});
</script>

<template>
  <div class="file-page">
    <div v-if="payload && payload.writable" class="page-actions">
      <button type="button" class="btn" @click="toggleWrite">
        {{ mode === "write" ? word("leave_write") : word("write") }}
      </button>
      <!-- THE LINE OF THE SAVE IS THE PAGE TALKING ABOUT ITSELF, and a save that
           did NOT land is not that — it is text that is not on the disk. That is
           why "Saved" clears itself and a failure does not. -->
      <span class="file-state" :class="{ bad: writingState.failed }">{{ writingState.status }}</span>
    </div>
    <pre v-if="!payload" class="text">{{ error }}</pre>
    <pre v-else-if="payload.text === null" class="text">{{ payload.reason }}</pre>
    <WriteField v-else-if="mode === 'write'" :path="payload.path" :text="payload.text"
                :rev="payload.rev" />
    <ProseField v-else-if="payload.bucket === 'text'" :text="payload.text" />
    <pre v-else class="text">{{ payload.text }}</pre>
  </div>
</template>

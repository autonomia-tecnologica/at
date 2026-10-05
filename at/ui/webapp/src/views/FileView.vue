<script setup lang="ts">
// FileView — one file of the prose folder, READ. Writing is no longer a mode
// of this page (2026-10-05): a click/tap on a writable text file opens its
// own tab (`WriteView.vue`), with the whole window to itself — this page
// stays what it always drew, the read.
//
// A markdown file is PROSE (`bucket` — the server's word, not the extension), any
// other text is text as it is, and a file that is not text says why instead.

import { ref, watch, onMounted, watchEffect } from "vue";
import { api } from "../lib/api";
import { nav, setTrail, addressOf, WRITE_PREFIX } from "../lib/views";
import ProseField from "../components/ProseField.vue";

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

// ONE CLICK, ANYWHERE ON THE FILE, OPENS THE WRITE TAB (2026-10-05): there is
// no button to find and no mode to leave — the whole read surface IS the
// door, for the one case there is anything behind it (a writable text file).
// A NEW TAB, not a mode swapped in here: `WriteView.vue` owns the whole
// window for exactly the reason a phone, mid-trip, is not the place to also
// keep the folder open.
function openWrite(): void {
  if (!payload.value || !payload.value.writable || payload.value.text === null) return;
  window.open(addressOf(WRITE_PREFIX + payload.value.path, null), "_blank");
}

onMounted(() => {
  void load();
});

// THE PATH IS THE TRAIL: `Arquivos › Notas › uma nota.md`. Every folder it
// passes through is a step, which is what the path already says — and the
// section is the shell's to add (`App.vue`).
watchEffect(() => setTrail(...String(props.path).split("/")));

watch(() => props.path, () => {
  payload.value = null;
  void load();
});

// The disk changed: the page re-reads — there is no mode to leave any more,
// writing happens in its own tab (`WriteView.vue`), never here.
watch(() => nav.tick, () => void load());
</script>

<template>
  <div class="file-page">
    <pre v-if="!payload" class="text">{{ error }}</pre>
    <!-- AN IMAGE IS VIEWED, NEVER EDITED (TASK-167) — the branch sits before
         the "not text" refusal because an image IS one of those (`text` is
         `null`, same as any other binary) and has to be told apart from a
         file this page truly cannot open at all. `src` never repeats the
         bytes already in `payload` (there are none): it names the SAME safe
         door every other read of the folder walks (`_get_file_bytes`,
         `prose.inside`), and the browser fetches it on its own. -->
    <img v-else-if="payload.kind === 'image'" class="file-image"
         :src="'/api/file/bytes?path=' + encodeURIComponent(payload.path)"
         :alt="payload.path">
    <pre v-else-if="payload.text === null" class="text">{{ payload.reason }}</pre>
    <!-- THE WHOLE SURFACE IS THE DOOR (2026-10-05): a writable text file opens
         its write tab on ONE click/tap anywhere on it — no button to find,
         no mode to leave. `.writable` is the only thing that changes the
         cursor; a file that cannot be written stays exactly as quiet as it
         always was. -->
    <ProseField v-else-if="payload.bucket === 'text'" :text="payload.text"
                :class="{ writable: payload.writable }" @click="openWrite" />
    <pre v-else class="text" :class="{ writable: payload.writable }" @click="openWrite">{{ payload.text }}</pre>
  </div>
</template>

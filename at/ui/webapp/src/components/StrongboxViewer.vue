<script setup lang="ts">
// StrongboxViewer — the clear, in a LAYER over the page (TASK-155, the reader).
//
// THE ONLY PLACE A SEALED FILE IS EVER DRAWN. It is not a page of its own and
// it takes no address: the link that opens it is one-time, so the state that
// matters — the minted address and the kind — lives in memory (`lib/strongbox`)
// for exactly as long as the overlay is up. A reload, a bookmark, a shared
// link: none of them can reopen the clear, and that is the design and not a
// gap.
//
// HOW IT DRAWS depends on the kind the server answered (`strongbox.look`):
// an IMAGE and a PDF are drawn BY THE BROWSER, straight from the one-time
// address (`<img>`, `<iframe>`) — the address is spent by that load. TEXT is
// read here with a `fetch`, because the server hands it as an attachment and
// the page is what turns those bytes into the text on screen; the read is
// strict UTF-8, which the server already guaranteed (`strongbox.look`), so what
// is shown is the file. Everything else has no viewer: it is offered for save.
//
// CTRL+S SAVES A COPY TO THE PERSON'S MACHINE, byte a byte: a FRESH one-time
// address is minted (`sealedLink`) and downloaded whole — never the bytes the
// page already holds, and never a re-encoding. The address on screen was spent
// when the file opened; minting another is how the clear is walked again.
import { ref, watch, onMounted, onBeforeUnmount } from "vue";
import { word } from "../lib/store";
import { viewer, closeSealed, sealedLink, type Sealed } from "../lib/strongbox";
import { isSaveGesture } from "../lib/download";
import { toast } from "../lib/toast";

const text = ref<string | null>(null);
const failed = ref("");

async function loadText(file: Sealed): Promise<void> {
  text.value = null;
  failed.value = "";
  if (file.kind !== "text") return;
  try {
    const response = await fetch(file.url, { headers: { Accept: "text/plain" } });
    if (!response.ok) throw new Error(`${response.status}`);
    const bytes = new Uint8Array(await response.arrayBuffer());
    // Strict UTF-8 is the server's promise (`strongbox.look`); the decoder's
    // own `allow` here is the page trusting that promise, never inventing one.
    text.value = new TextDecoder("utf-8").decode(bytes);
  } catch (err) {
    failed.value = (err as Error).message;
  }
}

async function saveCopy(file: Sealed | null): Promise<void> {
  if (!file) return;
  try {
    const url = await sealedLink(file.path);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = file.name;
    document.body.appendChild(anchor);
    anchor.click();
    anchor.remove();
  } catch (err) {
    toast(`${word("save_failed")} ${(err as Error).message}`);
  }
}

function onKeydown(event: KeyboardEvent): void {
  if (event.key === "Escape") {
    closeSealed();
    return;
  }
  if (!viewer.file) return;
  if (isSaveGesture(event)) {
    event.preventDefault();
    void saveCopy(viewer.file);
  }
}

// The read of the text runs once per file opened — `immediate` covers the one
// the overlay opens WITH, and every later file it is repointed at. Doing it here
// and not in `onMounted` matters: a second read would spend the one-time address
// twice, and the second would find nothing.
watch(() => viewer.file, file => {
  if (file) void loadText(file);
}, { immediate: true });

onMounted(() => document.addEventListener("keydown", onKeydown));
onBeforeUnmount(() => document.removeEventListener("keydown", onKeydown));
</script>

<template>
  <div v-if="viewer.file" class="strongbox-viewer" role="dialog" aria-modal="true">
    <header class="viewer-bar">
      <button type="button" class="leave" @click="closeSealed">{{ word("back") }}</button>
      <span class="viewer-name">{{ viewer.file.name }}</span>
      <button type="button" class="save" @click="saveCopy(viewer.file)">
        {{ word("save_local") }}
      </button>
    </header>
    <div class="viewer-body">
      <p v-if="failed" class="viewer-error">{{ failed }}</p>
      <pre v-else-if="viewer.file.kind === 'text'" class="viewer-text">{{ text ?? "" }}</pre>
      <img v-else-if="viewer.file.kind === 'image'" class="viewer-image"
           :src="viewer.file.url" :alt="viewer.file.name">
      <iframe v-else-if="viewer.file.kind === 'pdf'" class="viewer-pdf"
              :src="viewer.file.url" :title="viewer.file.name"></iframe>
      <div v-else class="viewer-none">
        <p>{{ word("cannot_show") }}</p>
      </div>
    </div>
  </div>
</template>

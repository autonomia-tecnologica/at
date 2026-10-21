<script setup lang="ts">
// FileView — one file of the prose folder, READ. Writing is no longer a mode
// of this page (2026-10-05): a click/tap on a writable text file opens its
// own tab (`WriteView.vue`), with the whole window to itself — this page
// stays what it always drew, the read.
//
// A markdown file is PROSE (`bucket` — the server's word, not the extension), any
// other text is text as it is, and a file that is not text says why instead.

import { ref, computed, watch, onMounted, onBeforeUnmount, watchEffect } from "vue";
import { api } from "../lib/api";
import { word } from "../lib/store";
import { nav, setTrail, open, leave, markPage, FILE_PREFIX, WRITE_PREFIX } from "../lib/views";
import { downloadFile, isSaveGesture } from "../lib/download";
import { dirOf, fileOf } from "../lib/relative";
import ProseField from "../components/ProseField.vue";

interface FilePayload {
  path: string;
  bucket: string;
  kind: string;
  writable: boolean;
  rev: string;
  text: string | null;
  reason: string | null;
  // WHAT TO DO WITH IT — the server's word, never a rule of extension invented
  // here: "text" opens as text, "image" opens inline, "tab" opens in a NEW TAB
  // (the browser draws the PDF and plays the video), "download" is a file the
  // page cannot show.
  open: "text" | "image" | "tab" | "download";
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

// ONE CLICK, ANYWHERE ON THE FILE, OPENS THE WRITE PAGE (2026-10-05): there is
// no button to find and no mode to leave — the whole read surface IS the door,
// for the one case there is anything behind it (a writable text file).
//
// IN THIS WINDOW, AND NOT A TAB OF ITS OWN (2026-10-05, a pedido). It opened in
// a new tab, and that is exactly what the COFRE's reader must not do: on a
// phone the app is a PWA with no tabs, so a `window.open` throws the person out
// to the system browser — the same reason the sealed file opens over the page.
// The write page draws with no shell and keeps its OWN voltar (`WriteView.vue`),
// so opening it here is a page change with a way back, not a trap.
function openWrite(): void {
  if (!payload.value || !payload.value.writable || payload.value.text === null) return;
  open(WRITE_PREFIX + payload.value.path, null);
}

// A PDF E UM VÍDEO ABREM EM NOVA ABA, e o navegador é quem os desenha: a
// porta de bytes (`/api/file/bytes`) é a mesma que o `<img>` usa, e a aba nova
// é a do BROWSER — nada de `<object>`/`<embed>` dentro da SPA, que trouxeram
// o documento para a origem do AT.
function openInTab(): void {
  if (!payload.value) return;
  window.open("/api/file/bytes?path=" + encodeURIComponent(payload.value.path),
              "_blank", "noopener");
}

// O DOWNLOAD de um arquivo que a página não abre: a mesma porta de bytes, e o
// que sai é o arquivo do disco — byte a byte, sem re-encodear.
function download(): void {
  downloadFile(payload.value?.path || props.path);
}

// A PASTA DO ARQUIVO, and the base against which a RELATIVE path in the
// markdown is resolved (`lib/relative.ts`): a `![](../imagens/x.webp)` in
// `Carro/TR4/nota.md` points at `Carro/TR4/imagens/x.webp` — the way a
// relative path points at anything, in any markdown.
const baseDir = computed(() => dirOf(payload.value?.path || props.path));

// A LINK É UM LINK, E NÃO UM CLIQUE NO CORPO. The whole surface is the door to
// the WRITE page — and a link inside it is the one thing that is NOT the door:
// a click on the text around it opens the editor, a click ON THE LINK follows
// the link.
//
// A FILE OF THE AT (`/file/<caminho>`) opens that file's READ, in THIS tab —
// the markdown a person wrote points at another file of the folder, and
// opening it in the editor would be opening the WRONG file.
function onProseClick(event: MouseEvent): void {
  const target = event.target as HTMLElement | null;
  const anchor = target?.closest?.("a");
  if (!anchor) {
    openWrite();
    return;
  }
  // The click stops here, so the surface's own door (the editor) does not
  // open under the link that was followed.
  event.stopPropagation();
  // A click that MEANS another tab — ctrl, cmd or shift — is the browser's
  // own, and this page does not take it away.
  if (event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
  const href = anchor.getAttribute("href") || "";
  // The address may carry a query and a fragment, and NEITHER is part of the
  // path the folder knows — the same reading the shell does of an address it
  // is handed (`App.vue`'s `pathParts`, which reads the path alone).
  const path = fileOf(href.split("#")[0].split("?")[0]);
  if (path === null) return; // a link to somewhere else: the browser follows it
  event.preventDefault();
  // The page the link was clicked on goes on the path FIRST: that is what
  // makes the step back land on the file the person was reading — the same
  // order a reference has (`views.ts`'s `openRef`).
  leave();
  markPage(FILE_PREFIX + path, null);
}

// CTRL+S SAVES THE OPEN FILE TO THE PERSON'S MACHINE, byte a byte — the same
// promise the write page makes (`lib/download.ts`): what leaves is the file on
// the disk, not a re-encoding of it.
function onKeydown(event: KeyboardEvent): void {
  if (!isSaveGesture(event)) return;
  event.preventDefault();
  downloadFile(props.path);
}

onMounted(() => {
  document.addEventListener("keydown", onKeydown);
  void load();
});

onBeforeUnmount(() => {
  document.removeEventListener("keydown", onKeydown);
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
    <!-- AN IMAGE IS VIEWED, NEVER EDITED (TASK-167) — and it opens INLINE, the
         way it always did. `src` never repeats the bytes already in `payload`
         (there are none): it names the SAME safe door every other read of the
         folder walks (`_get_file_bytes`, `prose.inside`), and the browser
         fetches it on its own. -->
    <img v-else-if="payload.open === 'image'" class="file-image"
         :src="'/api/file/bytes?path=' + encodeURIComponent(payload.path)"
         :alt="payload.path">
    <!-- UM PDF E UM VÍDEO ABREM EM NOVA ABA: o navegador desenha o PDF e toca
         o vídeo, e a SPA não os carrega dentro dela. A aba nova é a do
         BROWSER — a porta de bytes é a mesma que o `<img>` usa. -->
    <div v-else-if="payload.open === 'tab'" class="file-open">
      <b class="file-name">{{ payload.path }}</b>
      <button type="button" class="btn" @click="openInTab">{{ word("open_in_tab") }}</button>
    </div>
    <!-- O QUE A PÁGINA NÃO ABRE: o motivo (o limite, ou o formato que o
         navegador não toca) e o download — a mesma porta de bytes. -->
    <div v-else-if="payload.open === 'download'" class="file-open">
      <pre class="text">{{ payload.reason }}</pre>
      <button type="button" class="btn" @click="download">{{ word("download") }}</button>
    </div>
    <!-- THE WHOLE SURFACE IS THE DOOR (2026-10-05): a writable text file opens
         its write tab on ONE click/tap anywhere on it — no button to find,
         no mode to leave. `.writable` is the only thing that changes the
         cursor; a file that cannot be written stays exactly as quiet as it
         always was. A LINK is the exception, and it is the page's own
         (`onProseClick`): a link is followed, not written over. -->
    <ProseField v-else-if="payload.bucket === 'text'" :text="payload.text ?? ''"
                :base-dir="baseDir"
                :class="{ writable: payload.writable }" @click="onProseClick" />
    <pre v-else class="text" :class="{ writable: payload.writable }" @click="openWrite">{{ payload.text }}</pre>
  </div>
</template>

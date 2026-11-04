<script setup lang="ts">
// FILES OFFLINE — how much of the files THIS browser keeps, and when it keeps
// them (item 21). The choice is a preference of the browser (`prefs`), and it
// reaches the Service Worker by `postMessage`, which keeps it in its own cache:
// the SW answers the files offline, the page only draws the choice.
import { ref } from "vue";
import { word } from "../../lib/store";
import {
  FILES_OFFLINE_MODES,
  filesOfflineLimit,
  filesOfflinePrefs,
  saveFilesOffline,
} from "../../lib/prefs";
import type { FilesOffline, FilesOfflineMode } from "../../lib/prefs";

const current = filesOfflinePrefs();
const mode = ref<FilesOfflineMode>(current.mode);
const limit = ref<string>(String(current.limitMb));

// The page saves what it shows: an empty or invalid limit is written back as the
// default, so the box never disagrees with what is kept.
async function commit(): Promise<void> {
  const saved = saveFilesOffline({ mode: mode.value, limitMb: filesOfflineLimit(limit.value) });
  mode.value = saved.mode;
  limit.value = String(saved.limitMb);
  await tellWorker(saved);
}

// Without a worker the preference stays in `prefs` and nothing is kept offline
// anyway, so there is nothing to tell.
async function tellWorker(config: FilesOffline): Promise<void> {
  if (!("serviceWorker" in navigator)) return;
  try {
    const registration = await navigator.serviceWorker.ready;
    registration.active?.postMessage({ type: "at:files-config", ...config });
  } catch {
    // A worker that is not there is not an error for the page.
  }
}
</script>

<template>
  <section class="block">
    <h2>{{ word("files_offline") }}</h2>
    <div class="block-body">
      <p class="pop-note">{{ word("files_offline_hint") }}</p>
      <div class="radios" role="radiogroup" :aria-label="word('files_offline')">
        <label v-for="state in FILES_OFFLINE_MODES" :key="state" class="radio-row"
               :class="{ on: mode === state }">
          <input type="radio" class="radio" name="files-offline-mode" :value="state"
                 :checked="mode === state" @change="mode = state; commit()">
          <span>{{ word(`files_offline_${state}`) }}</span>
        </label>
      </div>
      <label class="radio-row">
        <span>{{ word("files_offline_limit") }}</span>
        <input type="number" class="input" min="1" step="1" inputmode="numeric"
               v-model="limit" @change="commit()">
        <span>{{ word("files_offline_limit_unit") }}</span>
      </label>
    </div>
  </section>
</template>

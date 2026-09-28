<script setup lang="ts">
// FilesView — THE FILES SECTION'S OWN SCREEN, and the section is the fold.
//
// It is the sibling of `TasksView.vue` and follows the same discipline: it
// INVENTS NOTHING. Every number is a count of what the server already lists for
// the section (`/api/tree`, the same listing the panel's tree is built from),
// cut a different way — by the BUCKET each file falls in, and by the top folder
// it sits under. A file the page was not handed is a file the page does not
// count.
//
// THE BUCKETS ARE THE PANEL'S OWN, and this page does not choose them: they are
// the four the file rows wear a mark for (`prose.bucket`, in `at/prose/listing.py`),
// in the order the panel draws them. The words come from the catalog, like every
// other word on screen.

import { ref, computed, watch, onMounted } from "vue";
import { api } from "../lib/api";
import { word } from "../lib/store";
import { nav, setTrail, showError, FILES_KEY } from "../lib/views";

interface Listing {
  root: string;
  files: { path: string; bucket: string }[];
}

const listing = ref<Listing | null>(null);

// The four the engine knows, in the panel's order — never a list written here.
const BUCKETS = ["text", "code", "data", "other"] as const;

const total = computed(() => listing.value?.files.length || 0);

function countOf(bucket: string): number {
  return (listing.value?.files || []).filter(file => file.bucket === bucket).length;
}

// THE FOLDERS OF THE TOP, each with how many files it holds — and the whole path
// counts: `Notas/Diário/x.md` is a file of `Notas`, because that is where a
// person would go looking for it. A file at the root has no folder and is
// counted under the empty name, which the page shows as the root itself.
const folders = computed(() => {
  const counts = new Map<string, number>();
  for (const file of listing.value?.files || []) {
    const parts = file.path.split("/");
    const head = parts.length > 1 ? parts[0] : "";
    counts.set(head, (counts.get(head) || 0) + 1);
  }
  return [...counts.entries()]
    .map(([name, count]) => ({ name, count }))
    .sort((a, b) => a.name.localeCompare(b.name, undefined, { sensitivity: "base" }));
});

async function load(): Promise<void> {
  try {
    listing.value = await api<Listing>("/api/tree");
    setTrail(word("files"));
  } catch (err) {
    listing.value = null;
    showError(err as Error);
  }
}

onMounted(load);
watch(() => nav.tick, load);
</script>

<template>
  <div v-if="listing" class="section">
    <!-- WHAT THE FOLDER HOLDS, by bucket. -->
    <div class="stats">
      <div v-for="bucket in BUCKETS" :key="bucket" class="stat" :data-bucket="bucket">
        <b>{{ countOf(bucket) }}</b>
        <span>{{ word("bucket_" + bucket) }}</span>
      </div>
    </div>

    <!-- THE SAME NUMBERS AS ONE BAR — the share each bucket has of the whole. -->
    <div class="bars" v-if="total">
      <span v-for="bucket in BUCKETS" :key="bucket" class="bar-part"
            :data-bucket="bucket" :style="{ flexGrow: countOf(bucket) }"
            :title="word('bucket_' + bucket) + ': ' + countOf(bucket)"></span>
    </div>

    <!-- WHERE THE FILES SIT. The rows are READ and not opened: a folder is not a
         page in this panel — the way into a file is the tree, and a row here
         that opened something would be a second door to the same room. -->
    <section class="cards">
      <h2>{{ word("files") }}</h2>
      <div v-for="folder in folders" :key="folder.name" class="row">
        <b>{{ folder.name || word("files") }}</b>
        <span class="n">{{ folder.count }}</span>
      </div>
      <p v-if="!total" class="empty">{{ word("no_records") }}</p>
    </section>
  </div>
</template>

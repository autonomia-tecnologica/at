<script setup lang="ts">
// CofreTree — the sidebar's own listing of `Cofre/` (TASK-156).
//
// FLAT, and on purpose: `FileTree` nests by folder because Arquivos is a
// place a person organizes; Cofre is a drop — what matters is THAT a file
// sealed, not where under it it happened to land — and a sealed file has no
// bucket to hang an icon on either. Each row is a NAME and nothing else: it
// is not a button and opens nothing, because there is no reader for a sealed
// file on this page yet (TASK-155).

import { ref, onMounted, watch } from "vue";
import { api } from "../lib/api";
import { word } from "../lib/store";
import { nav } from "../lib/views";

interface Listing {
  files: { path: string }[];
}

const files = ref<{ path: string }[]>([]);
const error = ref("");

async function load(): Promise<void> {
  try {
    const listing = await api<Listing>("/api/cofre");
    files.value = listing.files || [];
    error.value = "";
  } catch (err) {
    error.value = `${word("error")} ${(err as Error).message}`;
  }
}

onMounted(load);
watch(() => nav.tick, load);
</script>

<template>
  <div v-if="error" class="empty">{{ error }}</div>
  <div v-else-if="!files.length" class="empty">{{ word("no_records") }}</div>
  <div v-else v-for="file in files" :key="file.path" class="file entry">
    <span>{{ file.path }}</span>
  </div>
</template>

<script setup lang="ts">
// CofreView — THE COFRE SECTION'S OWN SCREEN, and the section is the fold
// (TASK-156, fatia 3/3).
//
// It is the sibling of `FilesView.vue`, and reads the SAME shape of listing
// (`/api/cofre`) the sidebar's `CofreTree` already draws from — cut a
// different way, as a count and a list, the way `FilesView` does for
// Arquivos.
//
// **There is no bucket here.** `FilesView` groups by what a file IS — text,
// code, data — and a sealed file answers that question with nothing: what
// selar hides is exactly its own shape, so this page shows a name and a
// count and stops there.

import { ref, computed, watch, onMounted } from "vue";
import { api } from "../lib/api";
import { word } from "../lib/store";
import { nav, setTrail, showError } from "../lib/views";

interface Listing {
  files: { path: string }[];
}

const listing = ref<Listing | null>(null);

const total = computed(() => listing.value?.files.length || 0);

async function load(): Promise<void> {
  try {
    listing.value = await api<Listing>("/api/cofre");
    setTrail(word("cofre"));
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
    <!-- THE ONE NUMBER THIS PAGE HAS: how many `.enc` the Cofre already holds. -->
    <div class="stats">
      <div class="stat">
        <b>{{ total }}</b>
        <span>{{ word("cofre") }}</span>
      </div>
    </div>

    <!-- THE NAMES. Not opened: a sealed file has no reader on this page yet
         (TASK-155), the same way a row of `FilesView` is read and not opened —
         the way into a file, when there is one, is never a card here. -->
    <section class="cards">
      <h2>{{ word("cofre") }}</h2>
      <div v-for="file in listing.files" :key="file.path" class="row">
        <b>{{ file.path }}</b>
      </div>
      <p v-if="!total" class="empty">{{ word("no_records") }}</p>
    </section>
  </div>
</template>

<script setup lang="ts">
// TablesView — THE TABLES SECTION'S OWN SCREEN, and the section is the fold.
//
// The sibling of `TasksView.vue` and `FilesView.vue`, with one difference that
// is the whole of this page: A ROW HERE IS A DOOR. A table IS a page of the
// panel (`/task`, `/audit`), so the list is the way in — the same list the
// panel's fold draws, with the count the server already sends for each table
// (`/api/state`), and nothing counted here.
//
// It invents no words either: the name of a table is the table's own name
// (`kindLabel`), and the two tables that have a screen of their own — the actor
// and the role — are not here, for the same reason they are not in the panel's
// fold: they live inside Settings (`Sidebar.vue`, `PEOPLE_TABLES`).

import { computed, watchEffect } from "vue";
import { store, word, kindLabel } from "../lib/store";
import { open, setTrail } from "../lib/views";
import { byName } from "../lib/order";

// The same two the panel keeps out of the fold, and for the same reason: a table
// that has a screen of its own is not a table to browse.
const PEOPLE_TABLES = ["actor", "role"];

const tables = computed(() =>
  [...store.tables]
    .filter(kind => !PEOPLE_TABLES.includes(kind.key))
    .sort((a, b) => byName(a.label, b.label)),
);

const rows = computed(() => tables.value.reduce((sum, kind) => sum + kind.count, 0));

// The page has nothing to fetch: the panel already carries every table and its
// count, and the trail follows the language like every other word on screen.
watchEffect(() => setTrail(word("tables")));

function openTable(key: string): void {
  open(key, null);
}
</script>

<template>
  <div class="section">
    <!-- WHAT THE FOLDER DECLARES, in two numbers: how many tables and how many
         rows they hold together. -->
    <div class="stats">
      <div class="stat">
        <b>{{ tables.length }}</b>
        <span>{{ word("tables") }}</span>
      </div>
      <div class="stat">
        <b>{{ rows }}</b>
        <span>{{ word("records") }}</span>
      </div>
    </div>

    <!-- AS TABELAS, uma a uma, e cada linha é a porta da sua página. -->
    <section class="cards">
      <h2>{{ word("tables") }}</h2>
      <button v-for="kind in tables" :key="kind.key" type="button" class="card"
              @click="openTable(kind.key)">
        <span class="card-top">
          <b>{{ kindLabel(kind.key) }}</b>
          <span class="n">{{ kind.count }}</span>
        </span>
      </button>
    </section>
  </div>
</template>

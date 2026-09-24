<script setup lang="ts">
// PeopleView — the panel's People entry: who may act, with which ceiling.
//
// It is the entry §5 declares, and it holds the two system tables of item 11
// TOGETHER: the actors (who, with which role, and which credential) and the
// roles (the set of permissions that caps them). What a row opens is its own
// SCREEN — the role's closed list, the actor's credential — and this page is the
// door to both, which is what keeps a person from hunting for a table name in the
// Tabelas fold.
//
// The page owns no rule: the tables are the ones the server declares, the words
// of the headings are the tables' own, and whoever does not carry `actor:list` is
// refused by the server, in the server's words.

import { ref, watch, onMounted } from "vue";
import { api } from "../lib/api";
import { kindLabel, word } from "../lib/store";
import { nav, openRef, setTitle, showError } from "../lib/views";
import TableView from "../components/TableView.vue";
import MachineMint from "../components/MachineMint.vue";
import RoleCreate from "../components/RoleCreate.vue";
import Foldable from "../components/Foldable.vue";
import type { TablePayload } from "../lib/record";

const people = ref<TablePayload | null>(null);
const roles = ref<TablePayload | null>(null);

async function load(): Promise<void> {
  try {
    people.value = await api<TablePayload>("/api/table/actor?all");
  } catch (err) {
    people.value = null;
    showError(err as Error);
  }
  try {
    roles.value = await api<TablePayload>("/api/table/role?all");
  } catch {
    // The same permission reads both, so this is the same refusal — and a screen
    // that drew half of itself and died would say less than the one that says it
    // once, where the band is.
    roles.value = null;
  }
}

onMounted(() => {
  setTitle(word("people"));
  void load();
});
watch(() => nav.tick, load);
</script>

<template>
  <div class="groups">
    <!-- THE ACTORS: the who, the role each one wears, and the credential a
         machine proves. The bands count nothing: two tables share the page and a
         single count in the header would belong to whichever spoke last. -->
    <div class="group">
      <Foldable id="people:actors" :label="kindLabel('actor')"
                head-class="group-head" box-class="group-body">
        <MachineMint v-if="people" :roles="roles ? roles.records : []" :fields="people.fields" />
        <TableView v-if="people" entity="actor" :records="people.records"
                   :schema="people.fields" :defaults="people.columns" page="actor"
                   @ref="openRef" />
      </Foldable>
    </div>

    <div class="group">
      <Foldable id="people:roles" :label="kindLabel('role')"
                head-class="group-head" box-class="group-body">
        <RoleCreate v-if="roles" :fields="roles.fields" />
        <TableView v-if="roles" entity="role" :records="roles.records"
                   :schema="roles.fields" :defaults="roles.columns" page="role"
                   @ref="openRef" />
      </Foldable>
    </div>
  </div>
</template>

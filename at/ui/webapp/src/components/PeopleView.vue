<script setup lang="ts">
// PeopleView — the actors and the roles: who may act, with which ceiling.
//
// It is embedded by `SettingsView.vue` now (§5, item 11): who may act is an
// adjustment of the folder, and not a table to browse — the same reason the
// theme and the language sit behind that door. It holds the two system tables
// TOGETHER: the actors (who, with which role, and which credential) and the
// roles (the set of permissions that caps them). What a row opens is its own
// SCREEN — the role's closed list, the actor's credential (`ActorView`,
// `RoleView`) — and this component is the door to both.
//
// It owns no title and no rule: the tables are the ones the server declares,
// the words of the headings are the tables' own, and whoever does not carry
// `actor:list` is refused by the server, in the server's words. It is a
// FRAGMENT (two `.group`s, no wrapper) so its host can drop it straight into
// its OWN `.groups` box without nesting one flex column inside another.

import { ref, watch, onMounted } from "vue";
import { api } from "../lib/api";
import { kindLabel } from "../lib/store";
import { nav, openRef, showError } from "../lib/views";
import TableView from "./TableView.vue";
import MachineMint from "./MachineMint.vue";
import RoleCreate from "./RoleCreate.vue";
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

onMounted(() => void load());
watch(() => nav.tick, load);
</script>

<template>
  <!-- AS DUAS SEÇÕES DA PESSOA: quem age e o que cada um pode. Elas não dobram
       (2026-09-28): são os dois assuntos da tela, e o que uma seção esconde a
       outra não mostra — quem veio mexer em papel quer ver o papel. -->
  <section class="block">
    <h2>{{ kindLabel('actor') }}</h2>
    <div class="block-body">
      <MachineMint v-if="people" :roles="roles ? roles.records : []" :fields="people.fields" />
      <TableView v-if="people" entity="actor" :records="people.records"
                 :schema="people.fields" :defaults="people.columns" page="actor"
                 :actions="people.actions" @ref="openRef" />
    </div>
  </section>

  <section class="block">
    <h2>{{ kindLabel('role') }}</h2>
    <div class="block-body">
      <RoleCreate v-if="roles" :fields="roles.fields" />
      <TableView v-if="roles" entity="role" :records="roles.records"
                 :schema="roles.fields" :defaults="roles.columns" page="role"
                 :actions="roles.actions" @ref="openRef" />
    </div>
  </section>
</template>

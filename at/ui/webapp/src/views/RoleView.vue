<script setup lang="ts">
// RoleView — the role screen: the SET a role is, and the saying §4 owes.
//
// A role is a row of the `role` table, and the table's own table (`KindView`)
// already lists them. What this page adds is what a listing cannot show:
//
// · the CLOSED LIST of the catalogue, drawn as checks — the permission is
//   `objeto:ação`, the objects and the actions are a closed list, and free text
//   here would be the RBAC misconfiguring in silence (§4). It is read from the
//   server (`GET /api/catalogue`) and written back through the table route the
//   `cli` already walks (`POST /api/table/role`, `action: edit`);
// · the permissions the role names that the catalogue DOES NOT HAVE — §4: "a
//   role naming a permission that does not exist does not bring AT down: it
//   warns, and the warning is what gets read". They are kept in the set, so
//   saving the role neither drops them in silence nor pretends they work;
// · and the CREATION of a role, which is the one other way a role moves.
//
// The page owns no rule: the labels are the catalogue's own words, the refusal a
// screen gets when it may not read roles comes from the server with the
// permission's name, and this page invents neither.

import { ref, computed, watch, onMounted } from "vue";
import { api, post } from "../lib/api";
import { label as worded, setFields, word } from "../lib/store";
import { back, markPage, nav, openRef, poke, setTrail, showError } from "../lib/views";
import TableView from "../components/TableView.vue";
import RoleCreate from "../components/RoleCreate.vue";
import type { RecordRow, TablePayload } from "../lib/record";

const ROLE = "role";

// One entry of the closed list, as the server hands it over: the machine name,
// the words for its object and its action, and the risk it declares.
interface CatalogueEntry {
  key: string;
  object: string;
  object_label: string;
  action: string;
  action_label: string;
  label: string;
  risk: number;
}

const payload = ref<TablePayload | null>(null);
const catalogue = ref<CatalogueEntry[]>([]);

// What the record is being EDITED into: the buffers hold the person's typing,
// and what is on the store is what the last read answered.
const chosen = ref<Set<string>>(new Set());
const name = ref("");
const desc = ref("");
const saving = ref(false);
const saved = ref<boolean | null>(null);

const record = computed(() => {
  const current = nav.current;
  if (!current || current.view !== ROLE || !current.id || !payload.value) return null;
  return payload.value.records.find(rec => rec.id === current.id) || null;
});

const unknown = computed(() => record.value?.unknown ?? []);

// The closed list, GROUPED BY OBJECT: the objects are what a person thinks in
// (`Tarefas`, `Papéis`), and forty checks in a row would be a wall with no doors.
const groups = computed(() => {
  const out: { object: string; label: string; entries: CatalogueEntry[] }[] = [];
  for (const entry of catalogue.value) {
    let group = out.find(candidate => candidate.object === entry.object);
    if (!group) {
      group = { object: entry.object, label: entry.object_label, entries: [] };
      out.push(group);
    }
    group.entries.push(entry);
  }
  return out;
});

const spec = (field: string) => payload.value?.fields.find(item => item.name === field) || null;
const fieldWord = (field: string) => worded(spec(field)?.labels);

function raw(rec: RecordRow, field: string): unknown {
  return rec.fields.find(item => item.name === field)?.raw;
}

// THE BUFFERS START FROM THE STORE, and only when the RECORD changes — the id is
// what a reload does not change, and reseeding on every read would erase what the
// person just saved (`saved` would blink out under the answer it belongs to).
function seed(): void {
  const rec = record.value;
  if (!rec) return;
  const held = raw(rec, "permissions");
  chosen.value = new Set(Array.isArray(held) ? held.map(String) : []);
  name.value = String(raw(rec, "name") ?? "");
  desc.value = String(raw(rec, "desc") ?? "");
  saved.value = null;
}

function toggle(key: string): void {
  const next = new Set(chosen.value);
  if (next.has(key)) next.delete(key);
  else next.add(key);
  chosen.value = next;
  saved.value = null;
}

async function load(): Promise<void> {
  try {
    const data = await api<TablePayload>("/api/table/" + ROLE + "?all");
    payload.value = data;
    setFields(data.fields);
  } catch (err) {
    payload.value = null;
    showError(err as Error);
  }
}

async function loadCatalogue(): Promise<void> {
  try {
    const answer = await api<{ permissions: CatalogueEntry[] }>("/api/catalogue");
    catalogue.value = answer.permissions;
  } catch (err) {
    // The catalogue is what the SCREEN needs and not what the folder owes: a
    // person who may read roles but not the list is refused, and the refusal is
    // the server's sentence. The listing still draws.
    catalogue.value = [];
    showError(err as Error);
  }
}

async function save(): Promise<void> {
  const rec = record.value;
  if (!rec) return;
  saving.value = true;
  try {
    await post("/api/table/" + ROLE, {
      action: "edit",
      id: rec.id,
      set: {
        name: name.value,
        desc: desc.value,
        // The field is a LIST (§4): the engine splits it on commas, and the
        // value on the wire is the string the `cli` would send.
        permissions: [...chosen.value].join(","),
      },
    });
    saved.value = true;
    poke();
  } catch (err) {
    saved.value = false;
    showError(err as Error);
  } finally {
    saving.value = false;
  }
}

function stepBack(): void {
  back(() => markPage(ROLE, null));
}

watch(() => record.value?.id, seed, { immediate: true });
watch(() => record.value?.title, title => { if (title) setTrail(title); }, { immediate: true });

onMounted(() => {
  void loadCatalogue();
  void load();
});
watch(() => nav.tick, load);
watch(() => nav.current?.view, view => {
  if (view === ROLE) {
    payload.value = null;
    void load();
  }
});
</script>

<template>
  <!-- THE RECORD IS THE SCREEN: a role is read and moved one at a time. -->
  <div v-if="record" class="record-page">
    <div class="page-actions">
      <button type="button" class="back" @click="stepBack">{{ word("back") }}</button>
      <span v-if="saved !== null" class="file-state" :class="{ bad: saved === false }">
        {{ word(saved ? "saved" : "save_failed") }}
      </span>
      <button type="button" class="btn" :disabled="saving" @click="save">
        {{ word("write") }}
      </button>
    </div>

    <div class="record-body">
      <div class="form">
        <label>
          <span>{{ fieldWord("name") }}</span>
          <input v-model="name" type="text" />
        </label>
        <label>
          <span>{{ fieldWord("desc") }}</span>
          <textarea v-model="desc"></textarea>
        </label>
      </div>

      <!-- THE CLOSED LIST. Each object is a block of its actions, and the check
           is the many-choice control: a role is a SET. -->
      <div class="form-block">
        <h2>{{ word("permission_pick") }}</h2>
        <div v-for="group in groups" :key="group.object" class="form-block">
          <h3>{{ group.label }}</h3>
          <div class="checks">
            <label v-for="entry in group.entries" :key="entry.key" class="check-row"
                   :class="{ on: chosen.has(entry.key) }">
              <input type="checkbox" class="check" :checked="chosen.has(entry.key)"
                     @change="toggle(entry.key)" />
              <span>{{ entry.action_label }}</span>
            </label>
          </div>
        </div>
      </div>

      <!-- THE SAYING (§4): the names the catalogue does not have. They stay in
           the set — saving keeps them unless the person unchecks them, and the
           warning is what says they grant nothing. -->
      <div v-if="unknown.length" class="form-block unknown">
        <h3>{{ word("unknown_permission") }}</h3>
        <p>{{ word("unknown_hint") }}</p>
        <div class="checks">
          <label v-for="key in unknown" :key="key" class="check-row"
                 :class="{ on: chosen.has(key) }">
            <input type="checkbox" class="check" :checked="chosen.has(key)"
                   @change="toggle(key)" />
            <span>{{ key }}</span>
          </label>
        </div>
      </div>
    </div>
  </div>

  <!-- THE TABLE, and the one other way a role MOVES: being born. -->
  <div v-else-if="payload">
    <RoleCreate :fields="payload.fields" />

    <TableView :entity="ROLE" :records="payload.records" :schema="payload.fields"
               :defaults="payload.columns" :page="ROLE" :actions="payload.actions"
               @ref="openRef" />
  </div>
</template>

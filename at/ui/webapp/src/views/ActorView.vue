<script setup lang="ts">
// ActorView — the actor screen, and the surface that MINTS and REVOKES a
// machine's credential.
//
// An actor is a row of the `actor` table, and the `actor` table's own table
// (`KindView`) already lists them; what this page adds is the one thing item 10
// left without a surface: an `agent` could only be born through the table door
// with the token TYPED (`at actor create`), and a token is not something a
// person types — it is something AT draws. Here it is drawn
// (`POST /api/agent`), shown ONCE, and taken away.
//
// The page owns no rule: the credential is the engine's (`tables._hashed` on the
// way in, a comparison on the way out), the actor's row is written through the
// table route the `cli` already walks, and a refusal comes from the server with
// its own words.

import { ref, computed, watch, onMounted } from "vue";
import { api, post } from "../lib/api";
import { label as worded, setFields, word } from "../lib/store";
import { back, markPage, nav, openRef, poke, setCount, setTitle, showError } from "../lib/views";
import TableView from "../components/TableView.vue";
import MachineMint from "../components/MachineMint.vue";
import type { RecordRow, TablePayload } from "../lib/record";

const ACTOR = "actor";
const ROLE = "role";

const payload = ref<TablePayload | null>(null);
const roles = ref<RecordRow[]>([]);

const name = ref("");
const roleNumber = ref<number | null>(null);
const token = ref("");
const saving = ref(false);
const saved = ref<boolean | null>(null);

const record = computed(() => {
  const current = nav.current;
  if (!current || current.view !== ACTOR || !current.id || !payload.value) return null;
  return payload.value.records.find(rec => rec.id === current.id) || null;
});

const spec = (field: string) => payload.value?.fields.find(item => item.name === field) || null;
const fieldWord = (field: string) => worded(spec(field)?.labels);

function raw(rec: RecordRow | null, field: string): unknown {
  return rec?.fields.find(item => item.name === field)?.raw;
}

function shown(rec: RecordRow | null, field: string): string {
  return rec?.fields.find(item => item.name === field)?.value ?? "";
}

const isMachine = computed(() => raw(record.value, "type") === "agent");
const typeWord = computed(() => shown(record.value, "type"));
const credentialWord = computed(() =>
  record.value?.has_credential ? shown(record.value, "credential") : word("credential_none"),
);
// WHO THE ACTOR WEARS. The options are the roles, and the role it wears is the
// NUMBER the row stores beside the title it resolves to — the page sends the
// number, which is what a reference is (§4).
const roleOptions = computed(() =>
  roles.value.map(role => ({ id: role.id, title: role.title })),
);

function seed(): void {
  const rec = record.value;
  if (!rec) return;
  const held = raw(rec, "role");
  name.value = String(raw(rec, "name") ?? "");
  roleNumber.value = typeof held === "number" ? held : null;
  saved.value = null;
}

async function load(): Promise<void> {
  try {
    const data = await api<TablePayload>("/api/table/" + ACTOR + "?all");
    payload.value = data;
    setFields(data.fields);
  } catch (err) {
    payload.value = null;
    showError(err as Error);
  }
}

async function loadRoles(): Promise<void> {
  try {
    roles.value = (await api<TablePayload>("/api/table/" + ROLE + "?all")).records;
  } catch {
    // A person who may read the actors and not the roles gets an empty list, and
    // the screen says WHICH ROLE the actor wears without offering to move it —
    // the listing still draws, and the permission that refused is the server's.
    roles.value = [];
  }
}

async function save(): Promise<void> {
  const rec = record.value;
  if (!rec) return;
  saving.value = true;
  try {
    const values: Record<string, string> = { name: name.value };
    if (roleNumber.value !== null) values.role = String(roleNumber.value);
    await post("/api/table/" + ACTOR, { action: "edit", id: rec.id, set: values });
    saved.value = true;
    poke();
  } catch (err) {
    saved.value = false;
    showError(err as Error);
  } finally {
    saving.value = false;
  }
}

// THE MACHINE CREDENTIAL GIVEN AGAIN: the machine that already exists — and
// whose token was lost, leaked, or is about to be pasted somewhere it should not
// be — keeps its name and its role, and the token it proves is replaced. A
// machine being BORN is the other half of the same door, and it belongs to the
// LISTING (`MachineMint`), where there is no row yet.
async function mint(): Promise<void> {
  const rec = record.value;
  if (!rec) return;
  try {
    const answer = await post<{ record: RecordRow; token: string }>("/api/agent", {
      action: "mint",
      id: rec.id,
    });
    token.value = answer.token;
    saved.value = null;
    poke();
  } catch (err) {
    showError(err as Error);
  }
}

async function revoke(): Promise<void> {
  const rec = record.value;
  if (!rec) return;
  try {
    await post("/api/agent", { action: "revoke", id: rec.id });
    token.value = "";
    poke();
  } catch (err) {
    showError(err as Error);
  }
}

function stepBack(): void {
  back(() => markPage(ACTOR, null));
}

watch(() => record.value?.id, seed, { immediate: true });
watch(() => record.value?.title, title => { if (title) setTitle(title); }, { immediate: true });

onMounted(() => {
  void loadRoles();
  void load();
});
watch(() => nav.tick, load);
watch(() => nav.current?.view, view => {
  if (view === ACTOR) {
    payload.value = null;
    void load();
  }
});
</script>

<template>
  <!-- THE RECORD: who the actor is, and the credential it proves. -->
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
        <label v-if="roleOptions.length">
          <span>{{ fieldWord("role") }}</span>
          <select v-model="roleNumber">
            <option v-for="role in roleOptions" :key="role.id" :value="role.id">
              {{ role.title }}
            </option>
          </select>
        </label>
        <div v-else class="form-block">
          <h3>{{ fieldWord("role") }}</h3>
          <p>{{ shown(record, "role") }}</p>
        </div>
      </div>

      <div class="form-block">
        <h3>{{ fieldWord("type") }}</h3>
        <p>{{ typeWord }}</p>
      </div>

      <!-- THE CREDENTIAL, which never leaves the row: what is drawn is the mask,
           and the boolean the server sends is what says whether one is held. -->
      <div class="form-block">
        <h2>{{ fieldWord("credential") }}</h2>
        <p>{{ credentialWord }}</p>
        <div v-if="isMachine" class="page-actions">
          <button type="button" class="btn" @click="mint">{{ word("mint") }}</button>
          <button v-if="record.has_credential" type="button" class="btn danger"
                  @click="revoke">{{ word("revoke") }}</button>
        </div>
      </div>

      <div v-if="token" class="form-block">
        <h3>{{ word("token_once") }}</h3>
        <pre class="text">{{ token }}</pre>
      </div>
    </div>
  </div>

  <!-- THE TABLE, and the surface that MINTS: a machine is born here. -->
  <div v-else-if="payload">
    <MachineMint :roles="roles" :fields="payload.fields" />

    <TableView :entity="ACTOR" :records="payload.records" :schema="payload.fields"
               :defaults="payload.columns" :page="ACTOR" @count="setCount" @ref="openRef" />
  </div>
</template>

<script setup lang="ts">
// ProjectView — the page a project opens.
//
// A project is a SCOPE of tasks, not a table of its own: the page shows the
// projects directly inside it and then the tasks of the WHOLE subtree, each row
// saying which subproject it came from. The page holds no data and no vocabulary
// — the tree, the counts and the rows all come from the API, which resolved the
// `parent` tree and the task links.
//
// It has no "back" of its own: what it has is the tree it lives in, and the
// parent's line is the way up.

import { ref, computed, watch, onMounted } from "vue";
import { api, post } from "../lib/api";
import { store, setFields, word } from "../lib/store";
import { nav, markPage, leave, open, openRef, setTrail, showError, poke } from "../lib/views";
import { openContextMenu, vContextMenu, type MenuItem } from "../lib/menu";
import { openPop } from "../lib/pop";
import { ask } from "../lib/confirm";
import { toast } from "../lib/toast";
import TaskBoard from "../components/TaskBoard.vue";
import EmptyState from "../components/EmptyState.vue";
import FieldEditor from "../components/FieldEditor.vue";
import RecordView from "../components/RecordView.vue";
import ClosePop from "../components/pops/ClosePop.vue";
import type { FieldSpec, RecordField, RecordRow } from "../lib/record";

interface Child {
  id: number;
  title: string;
  status: string;
  tasks: number;
}

interface ProjectPayload {
  id: number;
  title: string;
  status: string;
  parent: { id: number; title: string } | null;
  children: Child[];
  fields: FieldSpec[];
  records: RecordRow[];
  actions: string[];
  // The project's OWN fields and record — the pair `fields`/`records` above is
  // the TASKS the page draws, and this one is the project the page IS. It is
  // where the body of an item arrives: the `desc` the table declares
  // `markdown`, which is what a backlog item keeps its why and its decided in.
  // `actions` here is the ENGINE's own word on the project record itself
  // (TASK-137, fatia 7/7) — `_table_actions("project")` on the server, the
  // same door a table's row menu already asks, and never the tree's
  // `_project_actions` (create/edit only).
  project: { fields: FieldSpec[]; record: RecordRow; actions: string[] };
}

const props = defineProps<{ id: string }>();

const payload = ref<ProjectPayload | null>(null);

const page = computed(() => "project:" + props.id);

// A FATIA 4 DO B-54: a página edita os CINCO campos do próprio projeto no
// lugar, pelo `FieldEditor` — o mesmo editor da grade, das notas e das tarefas.
// O par que ele desenha é o da DECLARAÇÃO (`payload.project.fields`) com o
// valor da LINHA (`payload.project.record`), e o `spec.type` escolhe o
// controle. A entidade da escrita é a tabela que DECLARA o tipo `project`
// (`store.types.project`), nunca a palavra "project" escrita aqui.
interface ProjectPart {
  field: RecordField;
  spec: FieldSpec;
}

const entity = computed(() => store.types.project);

function partOf(name: string): ProjectPart | null {
  const project = payload.value?.project;
  if (!project) return null;
  const spec = project.fields.find(f => f.name === name);
  const field = project.record.fields.find(f => f.name === name);
  return spec && field ? { field, spec } : null;
}

const namePart = computed(() => partOf("name"));
const statusPart = computed(() => partOf("status"));
const priorityPart = computed(() => partOf("priority"));
const parentPart = computed(() => partOf("parent"));

// O QUE O ENGINE DIZ QUE ESTE ATOR ALCANÇA NO REGISTRO DO PROJETO: sem `edit`,
// cada `FieldEditor` nasce só de leitura.
const canEdit = computed(() => Boolean(payload.value?.project.actions.includes("edit")));

function rawOf(part: ProjectPart | null): string | null {
  const raw = part?.field.raw;
  return raw === null || raw === undefined || raw === "" ? null : String(raw);
}

const hasValue = (part: ProjectPart | null): boolean => rawOf(part) !== null;

// O CORPO DO ITEM: todo campo que a declaração do projeto marca `markdown`
// (hoje só o `desc`), onde um item guarda o seu porquê, o seu decidido e o seu
// aberto. Ele é desenhado como PROSA e clicado edita no lugar — o
// `FieldEditor` com `panel` lê pelo `ProseField` e abre a textarea que cresce.
const proseParts = computed<ProjectPart[]>(() => {
  const project = payload.value?.project;
  if (!project) return [];
  return project.fields
    .filter(spec => spec.type === "markdown")
    .map(spec => {
      const field = project.record.fields.find(f => f.name === spec.name);
      return field ? { field, spec } : null;
    })
    .filter((part): part is ProjectPart => part !== null);
});

// A página vazia é a que não tem TAREFA nem PROSA — o nome, o estado e a
// prioridade do projeto estão sempre no cabeçalho e não são "conteúdo".
const hasProse = computed(() => proseParts.value.some(part => Boolean(part.field.value)));

// THE BAND IS THE WAY IN: `Tarefas › WebApp`, and the section is the shell's
// to add (`App.vue`). The state, the priority and the counts it used to spell
// out here are all IN the page, where a person reads them with the rows they
// describe — a band that recites four values is a band that stops being a
// place.
function describe(): void {
  if (!payload.value) return;
  setTrail(payload.value.title);
}

const record = computed(() => {
  const current = nav.current;
  if (!current || current.view !== page.value || !current.id || !payload.value) return null;
  return payload.value.records.find(rec => rec.id === current.id) || null;
});

async function load(): Promise<void> {
  // The record that was open survives the page being reloaded.
  const wasOpen = nav.current ? nav.current.id : null;
  try {
    const data = await api<ProjectPayload>("/api/project/" + encodeURIComponent(props.id));
    payload.value = data;
    setFields(data.fields);
    markPage("project:" + data.id, wasOpen);
    describe();
  } catch (err) {
    // A project can have been CLOSED, and the preference outlives what it names:
    // the page falls to the first table, never to an error page.
    payload.value = null;
    if (store.tables.length) open(store.tables[0].key, null);
    else showError(err as Error);
  }
}

// Going down the tree is a NAVIGATION: the page left behind goes on the path,
// the same way a reference does.
function go(id: number): void {
  leave();
  markPage("project:" + id, null);
}

// THE PAGE'S OWN RIGHT CLICK (TASK-137, fatia 7/7): close and delete, the
// same two the row menu already offers a table (`TableView.vue`'s
// `openRowMenu`) — and never `edit`, because this page already IS the
// project's form. What shows is exactly what the engine allowed
// (`payload.project.actions`), nothing this page invents.
function openProjectMenu(ev: MouseEvent): void {
  if (!payload.value) return;
  const point = { x: ev.clientX, y: ev.clientY };
  const items: MenuItem[] = [];
  if (payload.value.project.actions.includes("cancel")) {
    items.push({ label: word("close"), action: () => openCloseProject(point) });
  }
  if (payload.value.project.actions.includes("delete")) {
    items.push({ label: word("delete"), action: () => deleteProject() });
  }
  openContextMenu(ev, items);
}

function openCloseProject(point: { x: number; y: number }): void {
  if (!payload.value) return;
  const rec = payload.value.project.record;
  openPop("close:" + entity.value + ":" + rec.id, ClosePop,
          { entity: entity.value, id: rec.id, title: rec.title || payload.value.title },
          { point });
}

async function deleteProject(): Promise<void> {
  if (!payload.value) return;
  const name = payload.value.title;
  if (!(await ask(word("delete_confirm").replace("{name}", name)))) return;
  try {
    await post("/api/table/" + encodeURIComponent(entity.value),
               { action: "delete", id: payload.value.project.record.id });
    poke();
  } catch (err) {
    toast((err as Error).message);
  }
}

onMounted(load);
watch(() => nav.tick, load);
watch(() => props.id, () => {
  payload.value = null;
  load();
});
</script>

<template>
  <RecordView v-if="record" :record="record" :total="payload?.records.length ?? 0"
              :page="page" :entity="store.types.task" @ref="openRef" />
  <!-- THE PAGE'S OWN RIGHT CLICK (TASK-137, fatia 7/7): anchored on the whole
       body, because the page has no header of its own to carry it on — the
       title lives in the shell's trail band, not here. The task card has its
       OWN menu now (B-54, fatia 3), and it stops the gesture before it gets
       here; a right click on the prose or the board's empty room still
       reaches this one, about the PROJECT itself. -->
  <div v-else-if="payload" v-context-menu="openProjectMenu">
    <!-- The parent's line is the way up, and it is the tree the page lives in —
         not a "back" the page keeps of its own. -->
    <div v-if="payload.parent" class="back" @click="go(payload.parent.id)">
      ← {{ payload.parent.id }}  ({{ payload.parent.title }})
    </div>
    <!-- O CABEÇALHO DO PROJETO (B-54, fatia 4): o nome é o `h1`, o estado, a
         prioridade e o pai são os chips, e o `desc` é a prosa — cada valor é o
         seu controle. O pai no chip EDITA a referência; a linha "voltar" acima
         NAVEGA para ele: são gestos diferentes. -->
    <div class="project-head">
      <h1 class="project-title">
        <FieldEditor v-if="namePart" :field="namePart.field" :spec="namePart.spec"
                     :entity="entity" :record="payload.project.record"
                     :can-edit="canEdit" @ref="openRef" />
        <template v-else>{{ payload.title }}</template>
      </h1>
      <div v-if="statusPart || priorityPart || parentPart" class="project-chips">
        <div v-if="statusPart" class="project-chip chip"
             :data-value="rawOf(statusPart) || undefined">
          <FieldEditor :field="statusPart.field" :spec="statusPart.spec"
                       :entity="entity" :record="payload.project.record" :can-edit="canEdit" />
        </div>
        <div v-if="priorityPart" class="project-chip chip"
             :data-value="rawOf(priorityPart) || undefined">
          <FieldEditor :field="priorityPart.field" :spec="priorityPart.spec"
                       :entity="entity" :record="payload.project.record" :can-edit="canEdit" />
        </div>
        <div v-if="parentPart" class="project-chip project-chip-parent"
             :class="{ 'is-empty': !hasValue(parentPart) }">
          <FieldEditor :field="parentPart.field" :spec="parentPart.spec"
                       :entity="entity" :record="payload.project.record"
                       :can-edit="canEdit" @ref="openRef" />
        </div>
      </div>
      <div v-for="part in proseParts" :key="part.spec.name" class="project-prose">
        <FieldEditor :field="part.field" :spec="part.spec" :entity="entity"
                     :record="payload.project.record" :can-edit="canEdit" panel
                     @ref="openRef" />
      </div>
    </div>
    <!-- THE BOARD BELOW IS THE TASKS' — the table the server said declares the
         TYPE `task`, never the word "task" read as a table's name. It hides
         the project chip a card would otherwise carry (`show-project`
         false): every card here already lives inside this project's own
         page, the same reason the table declares `hide: ["project"]` for the
         column a plain table would have drawn. A macro project's subprojects
         are the TREE's to show, not the task view's — the board here is
         tasks and only tasks, so the quick-add is off too: it writes no
         `project`, and a card born on this page landing as an orphan would
         be the page lying about where it put it. -->
    <EmptyState v-if="!payload.records.length && !hasProse" icon="folder"
                :title="word('empty_project_title')" :text="word('empty_project_text')">
      <button v-if="store.types.task" type="button" class="btn"
              @click="open(store.types.task, null)">{{ word("all_tasks") }}</button>
    </EmptyState>
    <TaskBoard v-else-if="store.types.task" :entity="store.types.task" :records="payload.records"
               :schema="payload.fields" :page="page" :show-project="false" :allow-create="false"
               :actions="payload.actions" @ref="openRef" />
  </div>
</template>

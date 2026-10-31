<script setup lang="ts">
// NotesView — A SEÇÃO DE NOTAS (TASK-198), e a seção é uma LINHA do painel.
//
// A TELA É A DE UMA TABELA — a `note` — lida pela PORTA GENÉRICA
// (`/api/table/note?all`), e não uma tela nova com porta nova: o que se cria,
// o que se abre, o que se edita e o que se apaga vai pelo MESMO caminho que
// qualquer linha de qualquer tabela percorre. A seção não inventa uma
// "tabela de notas": ela É a tabela `note`, mostrada do jeito que uma seção
// mostra.
//
// O QUE A PÁGINA NÃO SABE: o nome do campo que carrega o texto da nota, e o
// nome do campo que carrega as tags. A DECLARAÇÃO é que os nomeia
// (`fields[].primary`, `fields[].type`), e a página lê a que o servidor mandou
// — como toda página deste produto lê o que a porta entrega.
//
// O QUE ELA FAZ (B-54, fatia 2): lista as notas, EDITA O TEXTO E AS TAGS NO
// LUGAR pelo `FieldEditor` (o valor é o controle, e a escrita é a de
// `lib/fieldWrite`), abre o registro pelo corpo do card e pelo menu, e apaga
// pelo menu — o que o MOTOR disser que este ator pode (`payload.actions`), e
// nunca um ato inventado aqui.

import { ref, computed, watch, onMounted } from "vue";
import { api, post } from "../lib/api";
import { label, word, setFields } from "../lib/store";
import { nav, setTrail, showError, pageReadsOnItsOwn, pageLoaded, poke, NOTES_KEY } from "../lib/views";
import { openPop } from "../lib/pop";
import { openContextMenu, type MenuItem } from "../lib/menu";
import { ask } from "../lib/confirm";
import { toast } from "../lib/toast";
import EmptyState from "../components/EmptyState.vue";
import CreatePop from "../components/pops/CreatePop.vue";
import RecordPop from "../components/pops/RecordPop.vue";
import FieldEditor from "../components/FieldEditor.vue";
import type { TablePayload, RecordRow, RecordField, FieldSpec } from "../lib/record";

// A TABELA QUE A SEÇÃO MOSTRA. O nome é o da tabela — a seção não tem nome de
// tabela próprio, ela É a `note`.
const TABLE = "note";

// THE PAGE READS FOR ITSELF, and the boot has to know (`views.ts`): the notes
// come from the server on mount, so without this the shell would reveal over
// an empty section and fill it a beat later.
pageReadsOnItsOwn();

const payload = ref<TablePayload | null>(null);

const fields = computed(() => payload.value?.fields || []);
const records = computed(() => payload.value?.records || []);
const actions = computed(() => payload.value?.actions || []);

// O CAMPO PRINCIPAL é o que a nota DIZ — a declaração o nomeia (`primary`),
// e a página não sabe o nome.
const primary = computed(() => fields.value.find(field => field.primary) || null);

// AS LISTAS — os campos que são lista (`type: "list"`): é o que ordena a
// nota, e a página também não sabe o nome delas.
const lists = computed(() => fields.value.filter(field => field.type === "list"));

function fieldOf(rec: RecordRow, name: string): RecordField | null {
  return rec.fields.find(field => field.name === name) || null;
}

// O PAR QUE O `FieldEditor` desenha: a DECLARAÇÃO (tipo, rótulo, enum) e o
// VALOR daquela linha. O campo pode não vir na linha; aí não há o que editar.
interface NotePart {
  field: RecordField;
  spec: FieldSpec;
}

function partOf(rec: RecordRow, spec: FieldSpec): NotePart | null {
  const field = fieldOf(rec, spec.name);
  return field ? { field, spec } : null;
}

// CADA LINHA, LIDA UMA VEZ: o campo principal e as listas que a declaração
// nomeia. O card não sabe nome de campo nenhum.
interface NoteRow {
  rec: RecordRow;
  main: NotePart | null;
  tags: NotePart[];
}

const noteRows = computed<NoteRow[]>(() => records.value.map(rec => ({
  rec,
  main: primary.value ? partOf(rec, primary.value) : null,
  tags: lists.value
    .map(spec => partOf(rec, spec))
    .filter((part): part is NotePart => part !== null),
})));

// A NOTA NASCE: o formulário genérico de criar, que já sabe fazer o que a
// seção precisa — um campo de prosa e um de lista.
function openCreate(ev: Event): void {
  openPop("create:" + TABLE, CreatePop,
          { entity: TABLE, schema: fields.value },
          { anchor: ev.currentTarget as HTMLElement });
}

// A NOTA ABRE: o registro, que é a leitura dela — a mesma janela flutuante
// que a de qualquer outra linha de qualquer outra tabela. O painel EDITA: o
// `actions` que o motor deu à página vai junto.
function openNote(rec: RecordRow): void {
  openPop("record:" + TABLE + ":" + rec.id, RecordPop,
          { entity: TABLE, page: NOTES_KEY, id: rec.id, records: () => records.value,
            actions: actions.value },
          { attrs: { class: "record-pop" } });
}

// A NOTA APAGA: a confirmação que a apagação deve, e a mesma porta.
async function remove(rec: RecordRow): Promise<void> {
  const name = rec.title || String(rec.id);
  if (!(await ask(word("delete_confirm").replace("{name}", name)))) return;
  try {
    await post("/api/table/" + encodeURIComponent(TABLE), { action: "delete", id: rec.id });
    poke();
  } catch (err) {
    toast((err as Error).message);
  }
}

// O MENU DA LINHA: abrir é leitura e está sempre lá; apagar só quando o MOTOR
// disse que este ator pode (`actions`). Editar não mora mais aqui — o valor do
// card é o controle.
function rowMenuHandler(rec: RecordRow): (ev: MouseEvent) => void {
  return ev => {
    const items: MenuItem[] = [
      { label: word("open_record"), action: () => openNote(rec) },
    ];
    if (actions.value.includes("delete")) {
      items.push({ label: word("delete"), action: () => remove(rec) });
    }
    openContextMenu(ev, items);
  };
}

async function load(): Promise<void> {
  try {
    const data = await api<TablePayload>("/api/table/" + encodeURIComponent(TABLE) + "?all");
    payload.value = data;
    setFields(data.fields);
    setTrail(word("notes"));
  } catch (err) {
    payload.value = null;
    showError(err as Error);
  } finally {
    pageLoaded();
  }
}

onMounted(load);
// A write (a create, a edição, a apagada) redesenha a MESMA página, no mesmo
// lugar.
watch(() => nav.tick, load);
</script>

<template>
  <div v-if="payload" class="section">
    <section class="cards">
      <h2>{{ word("notes") }}</h2>
      <!-- A NOTA NASCE pelo botão da própria seção — e só quando o MOTOR diz que
           este ator pode criar uma. -->
      <button v-if="actions.includes('create') && records.length" type="button" class="btn"
              @click.stop="openCreate">{{ word("new_note") }}</button>
      <!-- CADA NOTA É UM CARD QUE ABRE A SI MESMO: o corpo abre o registro (a
           leitura), e os valores — o texto e as tags — editam no lugar pelo
           `FieldEditor`, que para o clique antes de ele chegar aqui. O card é
           um container focável e não um `<button>`: os editores também são
           botões, e botão não se aninha em botão. O `.stop` é o que segura o
           clique no card — sem ele, o clique fora (o de fechar o painel, em
           `App.vue`) calaria a nota no mesmo tique em que ela abria. -->
      <div v-for="note in noteRows" :key="note.rec.id" class="card note-card"
           tabindex="0"
           v-context-menu="rowMenuHandler(note.rec)"
           @click.stop="openNote(note.rec)"
           @keydown.enter.self.stop.prevent="openNote(note.rec)"
           @keydown.space.self.stop.prevent="openNote(note.rec)">
        <div v-if="note.main" class="card-top">
          <FieldEditor :field="note.main.field" :spec="note.main.spec" :entity="TABLE"
                       :record="note.rec" :can-edit="actions.includes('edit')" />
        </div>
        <div v-for="part in note.tags" :key="part.spec.name" class="meta">
          {{ label(part.spec.labels) || part.spec.name }}:
          <FieldEditor :field="part.field" :spec="part.spec" :entity="TABLE"
                       :record="note.rec" :can-edit="actions.includes('edit')" />
        </div>
      </div>
      <EmptyState v-if="!records.length" icon="note"
                  :title="word('empty_notes_title')" :text="word('empty_notes_text')">
        <button v-if="actions.includes('create')" type="button" class="btn"
                @click.stop="openCreate">{{ word("new_note") }}</button>
      </EmptyState>
    </section>
  </div>
</template>

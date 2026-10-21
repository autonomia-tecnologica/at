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
// O QUE ELA FAZ: lista as notas (o texto sem a notação, que é o que uma
// célula mostra de um campo markdown), abre uma (o registro, que é a
// leitura), e pelo menu de contexto edita e apaga — o que o MOTOR disser que
// este ator pode (`payload.actions`), e nunca um ato inventado aqui.

import { ref, computed, watch, onMounted } from "vue";
import { api, post } from "../lib/api";
import { label, word, setFields } from "../lib/store";
import { nav, setTrail, showError, pageReadsOnItsOwn, pageLoaded, poke, NOTES_KEY } from "../lib/views";
import { openPop } from "../lib/pop";
import { openContextMenu, type MenuItem } from "../lib/menu";
import { plainText } from "../lib/markdown";
import { ask } from "../lib/confirm";
import { toast } from "../lib/toast";
import CreatePop from "../components/pops/CreatePop.vue";
import EditPop from "../components/pops/EditPop.vue";
import RecordPop from "../components/pops/RecordPop.vue";
import type { TablePayload, RecordRow, RecordField } from "../lib/record";

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

// O TEXTO DA NOTA: o campo principal, como a pessoa o lê. Um campo markdown é
// mostrado SEM a notação — é o que uma célula faz —, e a notação fica no
// registro aberto, que a desenha como prosa.
function textOf(rec: RecordRow): string {
  const name = primary.value?.name;
  const field = name ? fieldOf(rec, name) : null;
  const value = field ? field.value : rec.title;
  return primary.value?.type === "markdown" ? plainText(value) : value || "";
}

// AS TAGS: a lista como ela está GUARDADA (`raw`) — a célula mostra a lista
// junta por vírgula, e a junta não é a lista.
function tagsOf(rec: RecordRow, name: string): string {
  const raw = fieldOf(rec, name)?.raw;
  if (!Array.isArray(raw)) return "";
  return raw.map(item => String(item)).join(", ");
}

// A NOTA NASCE: o formulário genérico de criar, que já sabe fazer o que a
// seção precisa — um campo de prosa e um de lista.
function openCreate(ev: Event): void {
  openPop("create:" + TABLE, CreatePop,
          { entity: TABLE, schema: fields.value },
          { anchor: ev.currentTarget as HTMLElement });
}

// A NOTA ABRE: o registro, que é a leitura dela — a mesma janela flutuante
// que a de qualquer outra linha de qualquer outra tabela.
function openNote(rec: RecordRow): void {
  openPop("record:" + TABLE + ":" + rec.id, RecordPop,
          { entity: TABLE, page: NOTES_KEY, id: rec.id, records: () => records.value },
          { attrs: { class: "record-pop" } });
}

// A NOTA EDITA: o formulário genérico de editar, que é a porta que faltava
// para um campo que não é escolha (uma prosa, uma lista de tags).
function openEdit(rec: RecordRow, point: { x: number; y: number }): void {
  openPop("edit:" + TABLE + ":" + rec.id, EditPop,
          { entity: TABLE, id: rec.id, schema: fields.value, record: rec },
          { point });
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

// O MENU DA LINHA: o que o MOTOR disse que este ator pode (`actions`), e nada
// que ele não disse — como o menu de qualquer outra tabela.
function rowMenuHandler(rec: RecordRow): (ev: MouseEvent) => void {
  return ev => {
    const point = { x: ev.clientX, y: ev.clientY };
    const items: MenuItem[] = [];
    if (actions.value.includes("edit")) {
      items.push({ label: word("edit"), action: () => openEdit(rec, point) });
    }
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
      <button v-if="actions.includes('create')" type="button" class="btn"
              @click="openCreate">{{ word("new_note") }}</button>
      <!-- CADA NOTA É UMA LINHA QUE ABRE A SI MESMA: o registro é a leitura
           dela, e o menu de contexto é o que edita e apaga. O `.stop` é o que
           segura o clique na linha — sem ele, o clique fora (o de fechar o
           painel, em `App.vue`) calaria a nota no mesmo tique em que ela
           abria. -->
      <button v-for="rec in records" :key="rec.id" type="button" class="card"
              v-context-menu="rowMenuHandler(rec)" @click.stop="openNote(rec)">
        <span class="card-top">
          <b>{{ textOf(rec) }}</b>
        </span>
        <span v-for="field in lists" :key="field.name" class="meta">
          {{ label(field.labels) || field.name }}: {{ tagsOf(rec, field.name) }}
        </span>
      </button>
      <p v-if="!records.length" class="empty">{{ word("notes_none") }}</p>
    </section>
  </div>
</template>

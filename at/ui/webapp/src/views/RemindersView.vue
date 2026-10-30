<script setup lang="ts">
// RemindersView — A SEÇÃO DE LEMBRETES (TASK-164), e a seção é uma LINHA só.
//
// Duas metades. A de cima mostra o que VEM, em três seções que o SERVIDOR já
// separa pelo `kind` de cada item — **Vencidos**, **Para hoje**, **Em breve** —
// e a página não recalcula a recorrência: ela só agrupa pelo campo que chegou,
// porque a regra mora num lugar só (`/api/reminders` → `reminder.current`). É
// a instância corrente que separa um lembrete de uma tarefa — a tarefa tem
// prazo, o lembrete tem um PRÓXIMO.
//
// FECHAR É O MESMO ATO DA NOTIFICAÇÃO. O círculo de check à esquerda chama a
// MESMA rota que o push usa quando a pessoa fecha pelo aviso
// (`POST /api/reminders/close`), com a instância corrente que a linha mostra;
// fechar QUALQUER item da lista — inclusive o de amanhã — passa pela mesma
// porta única, e a instância nova é a que o servidor devolve.
//
// A metade de baixo é LEITURA: **o que JÁ TOCOU hoje**, o inbox do notificador
// (`/api/notifications`), os avisos que SAÍRAM. É onde se confere o que o push
// entregou quando o aviso não foi visto (o navegador fechado, o SO que engoliu).
//
// A página inventa palavra nenhuma (tudo vem do catálogo, pelo servidor) e não
// abre porta nenhuma para EDITAR: o caminho de edição do lembrete é a tabela, e
// uma linha aqui que editasse seria uma segunda porta para a mesma sala
// (`base.css`'s `.row`). O fechar é a exceção já decidida — é o ato da pessoa
// sobre a ocorrência, e é o mesmo da notificação.

import { ref, computed, watch, onMounted, onUnmounted } from "vue";
import { api, post } from "../lib/api";
import { store, word } from "../lib/store";
import { loadPrefs, savePrefs, REMINDER_DAYS_KEY } from "../lib/prefs";
import EmptyState from "../components/EmptyState.vue";
import PageActions from "../components/PageActions.vue";
import { nav, open, CHAT_KEY, NLU_UI_ENABLED, setTrail, showError, pageReadsOnItsOwn, pageLoaded, REMINDERS_KEY } from "../lib/views";

type Kind = "overdue" | "today" | "soon";

interface Reminder {
  id: number;
  text: string;
  freq: string;
  at: string[];
  status: string;
  active: boolean;
  next: string | null;
  kind: Kind;
}

interface Message {
  id: number;
  time: number;
  title: string;
  message: string;
}

// THE PAGE READS FOR ITSELF, and the boot has to know (`views.ts`): the two
// halves come from the server on mount, so without this the shell would reveal
// over an empty page and fill it a beat later.
pageReadsOnItsOwn();

// O HORIZONTE É PREFERÊNCIA DO NAVEGADOR (7/30/90): o valor guardado é lido uma
// vez, e um valor fora da faixa cai em 7 em vez de virar erro.
const DAYS = [7, 30, 90] as const;

function savedDays(): number {
  const raw = loadPrefs(REMINDER_DAYS_KEY).days;
  return DAYS.includes(raw) ? raw : 7;
}

const days = ref<number>(savedDays());
const hidden = ref(0);
const canClose = ref(false);
const reminders = ref<Reminder[]>([]);
const messages = ref<Message[]>([]);
const closing = ref<number | null>(null);
const ready = ref(false);

// AS TRÊS SEÇÕES, na ordem que o servidor já manda (vencidos, hoje, o que vem).
// Só aparece a que tem item — e a de "Em breve" também aparece quando o
// horizonte escondeu algum, para a linha do `+N` ter onde morar.
const groups = computed(() =>
  (["overdue", "today", "soon"] as const)
    .map(kind => ({
      kind,
      title: `reminders_${kind}`,
      items: reminders.value.filter(item => item.kind === kind),
    }))
    .filter(group => group.items.length || (group.kind === "soon" && hidden.value > 0))
);

// O QUE JÁ TOCOU HOJE — os avisos do DIA, e não os últimos de sempre: o inbox
// guarda os que saíram, e a metade pede os de hoje. O dia é o do NAVEGADOR, que
// é o dia de quem está lendo.
const fired = computed(() => {
  const today = new Date().toDateString();
  return messages.value.filter(msg => new Date(msg.time * 1000).toDateString() === today);
});

// A instância corrente como a pessoa lê. Em "Para hoje" basta a hora (`09:00`); em
// "Em breve" e em "Vencidos" o dia importa, porque a linha pode ser de outra
// data (`06/10 09:00`). Sem próximo (um pausado, um `once` vencido), o próprio
// estado, e não um disparo que `occurs` já recusa.
function nextText(reminder: Reminder): string {
  if (!reminder.next) return reminder.status;
  const [day, time] = reminder.next.split(" ");
  if (reminder.kind === "today") return time;
  const [, month, date] = day.split("-");
  return `${date}/${month} ${time}`;
}

function atText(reminder: Reminder): string {
  return (reminder.at || []).join(", ");
}

// A hora do aviso, no relógio de quem lê.
function clock(epoch: number): string {
  return new Date(epoch * 1000).toLocaleTimeString(undefined, {
    hour: "2-digit",
    minute: "2-digit",
  });
}

// A ESCOLHA DO HORIZONTE recarrega: quem decide o que cabe é o servidor, e a
// página só pede o `days` que a pessoa escolheu.
function setDays(value: number): void {
  if (value === days.value) return;
  days.value = value;
  savePrefs(REMINDER_DAYS_KEY, { days: value });
  void load();
}

// FECHAR: o MESMO ato da notificação, pela mesma rota. Nada de atualização
// otimista — a instância nova é a que o servidor devolve, e a lista recarrega.
async function close(reminder: Reminder): Promise<void> {
  if (!reminder.next || closing.value === reminder.id) return;
  closing.value = reminder.id;
  try {
    await post("/api/reminders/close", { id: reminder.id, instance: reminder.next });
    await load();
  } catch (err) {
    showError(err as Error);
  } finally {
    closing.value = null;
  }
}

async function load(): Promise<void> {
  try {
    const [coming, rang] = await Promise.all([
      api<{ reminders: Reminder[]; days: number; hidden: number; can_close: boolean }>(
        `/api/reminders?days=${days.value}`
      ),
      api<{ messages: Message[] }>("/api/notifications"),
    ]);
    reminders.value = coming.reminders;
    hidden.value = coming.hidden;
    canClose.value = coming.can_close;
    messages.value = rang.messages;
    ready.value = true;
    setTrail(word("reminders"));
  } catch (err) {
    showError(err as Error);
  } finally {
    pageLoaded();
  }
}

// O AVISO DO SERVICE WORKER: o push fecha pela notificação e manda
// `{type: "at:reminders"}` para as janelas abertas — a lista recarrega para a
// linha fechada sumir sem a pessoa recarregar a página.
function onWorkerMessage(event: MessageEvent): void {
  if (event.data && event.data.type === "at:reminders") void load();
}

onMounted(() => {
  void load();
  if ("serviceWorker" in navigator) {
    navigator.serviceWorker.addEventListener("message", onWorkerMessage);
  }
});

onUnmounted(() => {
  if ("serviceWorker" in navigator) {
    navigator.serviceWorker.removeEventListener("message", onWorkerMessage);
  }
});

watch(() => nav.tick, load);
</script>

<template>
  <div v-if="ready" class="section">
    <!-- O HORIZONTE: 7/30/90 dias, à frente da palavra, com o ativo marcado. -->
    <PageActions>
      <div class="reminder-range">
        <span class="label">{{ word("reminders_days") }}</span>
        <button v-for="option in DAYS" :key="option" type="button"
                class="btn btn-sm btn-quiet" :class="{ on: days === option }"
                :aria-pressed="days === option"
                @click="setDays(option)">{{ option }}</button>
      </div>
    </PageActions>

    <!-- O QUE VEM, separado pelo `kind` que o servidor manda. -->
    <template v-if="reminders.length || hidden">
      <section v-for="group in groups" :key="group.kind" class="cards">
        <h2 :class="{ 'reminder-overdue': group.kind === 'overdue' }">{{ word(group.title) }}</h2>
        <div v-for="reminder in group.items" :key="reminder.id" class="row reminder"
             :class="{ paused: !reminder.active, overdue: reminder.kind === 'overdue' }">
          <button v-if="canClose && reminder.next" type="button" class="reminder-done"
                  :aria-label="word('reminders_close')" :disabled="closing === reminder.id"
                  @click="close(reminder)"></button>
          <b>{{ reminder.text }}</b>
          <span class="meta">
            {{ reminder.freq }}<template v-if="atText(reminder)"> · {{ atText(reminder) }}</template>
          </span>
          <span class="n">{{ nextText(reminder) }}</span>
        </div>
        <p v-if="group.kind === 'soon' && hidden" class="reminder-beyond">
          +{{ hidden }} {{ word("reminders_beyond") }}
        </p>
      </section>
    </template>

    <!-- A PASTA SEM LEMBRETE NENHUM: o estado vazio, com o atalho do chat. -->
    <section v-else class="cards">
      <EmptyState icon="bell"
                  :title="word('empty_reminders_title')" :text="word('empty_reminders_text')">
        <button v-if="NLU_UI_ENABLED && store.interpreter" type="button" class="btn"
                @click="open(CHAT_KEY, null)">{{ word("chat") }}</button>
      </EmptyState>
    </section>

    <!-- O QUE JÁ TOCOU HOJE: os avisos que saíram, para conferir o que o push
         entregou quando o aviso não foi visto. -->
    <section class="cards">
      <h2>{{ word("reminders_rang") }}</h2>
      <div v-for="msg in fired" :key="msg.id" class="row reminder">
        <b>{{ msg.message }}</b>
        <span class="n">{{ clock(msg.time) }}</span>
      </div>
      <p v-if="!fired.length" class="empty">{{ word("reminders_quiet") }}</p>
    </section>
  </div>
</template>

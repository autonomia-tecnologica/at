<script setup lang="ts">
// RemindersView — A SEÇÃO DE LEMBRETES (TASK-164), e a seção é uma LINHA só.
//
// Duas metades, e as duas são LEITURA:
//
// · **o que VEM** — cada lembrete com o PRÓXIMO disparo CALCULADO. O cálculo é
//   do motor (`/api/reminders` → `reminder.upcoming`), e a página não repete a
//   recorrência: a regra mora num lugar só. É o próximo toque que separa um
//   lembrete de uma tarefa — a tarefa tem prazo, o lembrete tem um PRÓXIMO.
// · **o que JÁ TOCOU hoje** — o inbox do notificador (`/api/notifications`), os
//   avisos que SAÍRAM. É onde se confere o que o push entregou quando o aviso
//   não foi visto (o navegador fechado, o SO que engoliu).
//
// A página inventa palavra nenhuma (tudo vem do catálogo, pelo servidor) e não
// abre porta nenhuma: as linhas são para LER — o caminho de escrita do lembrete
// é a tabela, e uma linha aqui que editasse seria uma segunda porta para a
// mesma sala (`base.css`'s `.row`).

import { ref, computed, watch, onMounted } from "vue";
import { api } from "../lib/api";
import { word } from "../lib/store";
import { nav, setTrail, showError, pageReadsOnItsOwn, pageLoaded, REMINDERS_KEY } from "../lib/views";

interface Reminder {
  id: number;
  text: string;
  freq: string;
  at: string[];
  status: string;
  active: boolean;
  next: string | null;
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

const reminders = ref<Reminder[]>([]);
const messages = ref<Message[]>([]);
const ready = ref(false);

// O QUE JÁ TOCOU HOJE — os avisos do DIA, e não os últimos de sempre: o inbox
// guarda os que saíram, e a metade pede os de hoje. O dia é o do NAVEGADOR, que
// é o dia de quem está lendo.
const fired = computed(() => {
  const today = new Date().toDateString();
  return messages.value.filter(msg => new Date(msg.time * 1000).toDateString() === today);
});

// O PRÓXIMO toque como a pessoa lê (`06/10 09:00`), e — quando não há próximo
// (um pausado, um `once` vencido) — o próprio estado, e não um disparo que
// `occurs` já recusa.
function nextText(reminder: Reminder): string {
  if (!reminder.next) return reminder.status;
  const [day, time] = reminder.next.split(" ");
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

async function load(): Promise<void> {
  try {
    const [coming, rang] = await Promise.all([
      api<{ reminders: Reminder[] }>("/api/reminders"),
      api<{ messages: Message[] }>("/api/notifications"),
    ]);
    reminders.value = coming.reminders;
    messages.value = rang.messages;
    ready.value = true;
    setTrail(word("reminders"));
  } catch (err) {
    showError(err as Error);
  } finally {
    pageLoaded();
  }
}

onMounted(load);
watch(() => nav.tick, load);
</script>

<template>
  <div v-if="ready" class="section">
    <!-- O QUE VEM: cada lembrete com o seu próximo toque. -->
    <section class="cards">
      <h2>{{ word("reminders_coming") }}</h2>
      <div v-for="reminder in reminders" :key="reminder.id" class="row reminder"
           :class="{ paused: !reminder.active }">
        <b>{{ reminder.text }}</b>
        <span class="meta">
          {{ reminder.freq }}<template v-if="atText(reminder)"> · {{ atText(reminder) }}</template>
        </span>
        <span class="n">{{ nextText(reminder) }}</span>
      </div>
      <p v-if="!reminders.length" class="empty">{{ word("reminders_none") }}</p>
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

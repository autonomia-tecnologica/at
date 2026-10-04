<script setup lang="ts">
// SettingsView — the Settings page: what CONFIGURES the folder, and what
// configures the page.
//
// It writes no store at all for the PAGE half — the look and the box are kept in
// localStorage, never the data. The rest is reading: the language the whole
// interface is drawn in and where it came from, and the RULER of the demand
// filter, which draws what the product declares about risk. THE ONE THING HERE
// THAT DOES WRITE THE FOLDER is People (§5, item 11): who may act, with which
// ceiling, is an adjustment of the folder, and this door is where every other
// adjustment already lives.
//
// The page is made of GROUPS THAT FOLD — the SAME fold as the panel's folder, and
// what changes is the cloth: here the PAGE's (`--group-*`), there the PANEL's.
//
// THE THEME PICKER IS BACK (2026-09-28), and the day it came back is the day a
// SECOND look existed. It left on 2026-09-27 because a list of one is a caption
// and not a choice — and that was true: with Paper the only row, the control let
// a person leave the one look the product had. What changed is not the rule but
// the count: `at` is a design system of its own, walked through its own base
// (`base_css_path`), and whoever is comparing two looks needs the row that moves
// between them. The whole mechanism stayed ready under the removal — the
// registry, `chooseTheme`, the `.theme` rows — which is what this restores, and
// nothing more.
//
// IT SITS FIRST, because the side is the THEME's: a control that asks which of a
// theme's two faces to wear, placed above the list that picks the theme, asks
// the question backwards.

import { computed, ref, watchEffect } from "vue";
import { store, word } from "../lib/store";
import { post } from "../lib/api";
import { DARK_STATES, chooseDark, chooseTheme, darkState, themeState } from "../lib/theme";
import { motionOn, setMotion } from "../lib/motion";
import { byName } from "../lib/order";
import { setTrail } from "../lib/views";
// NOTIFICAÇÕES (Web Push): o botão pede a permissão do navegador e inscreve o
// PWA — sem ntfy, sem app à parte. `state()` diz o que a tela desenha.
import { enable as enablePush, state as pushNow } from "../lib/push";
import ActionsView from "../components/ActionsView.vue";
import Foldable from "../components/Foldable.vue";
import PeopleView from "../components/PeopleView.vue";
import RiskRuler from "../components/RiskRuler.vue";
import type { DarkState } from "../lib/theme";
import type { ThemeRow } from "../lib/store";

// TASK-180, fatia 3/3: o assist — o switch e o modo, os dois ajustes da pasta
// que `/api/assist` escreve. `busy` evita um segundo clique enquanto o
// primeiro ainda não voltou, e o que a tela mostra depois é o que o SERVIDOR
// respondeu (`store.assist`/`store.assist_mode`), nunca o que foi clicado.
const ASSIST_MODES = ["cautious", "automatic"] as const;
const assistBusy = ref(false);

async function toggleAssist(): Promise<void> {
  if (assistBusy.value) return;
  assistBusy.value = true;
  try {
    const data = await post<{ enabled: boolean; mode: string }>(
      "/api/assist", { enabled: !store.assist },
    );
    store.assist = data.enabled;
    store.assist_mode = data.mode;
  } finally {
    assistBusy.value = false;
  }
}

async function pickAssistMode(mode: (typeof ASSIST_MODES)[number]): Promise<void> {
  if (assistBusy.value || mode === store.assist_mode) return;
  assistBusy.value = true;
  try {
    const data = await post<{ enabled: boolean; mode: string }>(
      "/api/assist", { mode },
    );
    store.assist = data.enabled;
    store.assist_mode = data.mode;
  } finally {
    assistBusy.value = false;
  }
}

// AS ABAS, na ordem em que a tela se apresenta: o que a pasta é (o idioma), o
// que se vê, quem age nela e o que ela mede de risco.
const TABS = ["general", "appearance", "people", "risk", "actions"] as const;

const tab = ref<(typeof TABS)[number]>("general");
const motion = ref(motionOn());
const side = ref(darkState());

// O estado do push, o que a tela mostra: o navegador pergunta uma vez, e depois
// disso é a permissão que responde (`push.state`).
const pushState = ref(pushNow());

async function askPush(): Promise<void> {
  const ok = await enablePush();
  pushState.value = ok ? "on" : pushNow();
}

// A CREDENCIAL DO JEV: só a chave da API (TypeSafe). A Chave Principal NÃO é
// digitada aqui — ela é a da SUBIDA, guardada em memória pelo host, e é ela que
// sela a chave do Jev. A linha que nasce (`secret` de escopo `jev`) é o que faz
// o chat parar de dizer "Jev não configurado".
const jevKey = ref("");
const jevBusy = ref(false);
const jevError = ref("");

async function saveJev(): Promise<void> {
  if (jevBusy.value || !jevKey.value) return;
  jevBusy.value = true;
  jevError.value = "";
  try {
    await post("/api/jev", { key: jevKey.value });
    store.jev_ready = true;
    jevKey.value = "";
  } catch (err) {
    jevError.value = (err as Error).message;
  } finally {
    jevBusy.value = false;
  }
}

// The theme's description is PER SIDE: the same theme describes itself
// differently in light and dark, and what is read is the side being worn —
// `themeState.dark` is the signal that follows the swap, so changing sides
// needs no redraw.
const descOf = (row: ThemeRow): string =>
  row.desc ? (themeState.dark ? row.desc.dark : row.desc.light) || "" : "";

// THE THEMES IN ALPHABETICAL ORDER, by the name the page PRINTS. The registry
// declares them in the order they were born, which is a history and not an
// index — and what somebody does with a list of themes is look one up. It is the
// same rule the panel already follows for the tables (`order.ts`).
const themeList = computed(() => [...store.themes].sort((a, b) => byName(a.label, b.label)));

function pick(row: ThemeRow): void {
  chooseTheme(row.id);
}

const WORDS: Record<DarkState, string> = {
  system: "dark_system", light: "dark_light", dark: "dark_dark",
};

// SÓ UM TEMA COM OS DOIS LADOS TEM O QUE ESCOLHER (2026-10-04): os outros
// ficaram com o lado que já vestiam por padrão (`gothic`/`console`/`hotel`
// escuro, os quatro que restam claro) e não têm mais o arquivo do lado que
// perderam — `row.sides` é o que o SERVIDOR leu do disco, nunca um palpite
// desta tela. Sem os dois lados, não há radiogroup: não existe ajuste a
// mostrar por um tema que não carrega escolha nenhuma.
const sideStates = computed<readonly DarkState[]>(() => {
  const row = store.themes.find(r => r.id === themeState.id);
  return row && row.sides.length > 1 ? DARK_STATES : [];
});

function toggleMotion(): void {
  motion.value = setMotion(!motion.value);
}

function pickSide(state: DarkState): void {
  side.value = state;
  chooseDark(state);
}

watchEffect(() => setTrail(word("settings")));
</script>

<template>
  <!-- AS ABAS SÃO OS GRUPOS, e cada parte é uma seção. A tela configura a pasta
       inteira — o idioma, o que se vê, quem age e o que é risco —, e agrupar
       isso em dobras fazia a pessoa ABRIR para descobrir o que havia dentro; o
       que uma aba guarda não é surpresa, é a outra metade da mesma tela. -->
  <div class="page">
    <div class="tabs" role="tablist">
      <button v-for="name in TABS" :key="name" type="button" role="tab"
              class="tab" :class="{ on: tab === name }"
              :aria-selected="tab === name" @click="tab = name">{{ word(name) }}</button>
    </div>

    <div class="panel">
      <section v-if="tab === 'general'" class="block">
        <h2>{{ word("language") }}</h2>
        <div class="block-body">
          {{ store.lang }}<template v-if="store.origin"> ({{ store.origin }})</template>
        </div>
      </section>

      <!-- O ASSIST (TASK-180, fatia 3/3): o switch, e o modo só quando ligado
           — um modo escolhido com o assist desligado não teria o que fazer. -->
      <section v-if="tab === 'general'" class="block">
        <h2>{{ word("assist") }}</h2>
        <div class="block-body">
          <p class="pop-note">{{ word("assist_hint") }}</p>
          <button type="button" class="switch" role="switch"
                  :aria-label="word('assist')" :class="{ on: store.assist }"
                  :aria-checked="store.assist" :disabled="assistBusy"
                  @click="toggleAssist"></button>
          <div v-if="store.assist" class="radios" role="radiogroup" :aria-label="word('assist_mode')">
            <label v-for="mode in ASSIST_MODES" :key="mode" class="radio-row"
                   :class="{ on: store.assist_mode === mode }">
              <input type="radio" class="radio" name="assist-mode" :value="mode"
                     :checked="store.assist_mode === mode" :disabled="assistBusy"
                     @change="pickAssistMode(mode)">
              <span>{{ word(`assist_${mode}`) }}</span>
            </label>
          </div>
        </div>
      </section>

      <!-- NOTIFICAÇÕES (Web Push): o botão PEDE a permissão do navegador e
           inscreve o PWA — sem ntfy, sem app à parte. Um navegador que não sabe
           fazer push não mostra o bloco. -->
      <section v-if="tab === 'general' && pushState !== 'unsupported'" class="block">
        <h2>{{ word("notifications") }}</h2>
        <div class="block-body">
          <p class="pop-note">{{ word("notifications_hint") }}</p>
          <button type="button" class="btn"
                  :disabled="pushState === 'on' || pushState === 'denied'"
                  @click="askPush">
            {{ pushState === "on" ? word("notifications_on") : word("notifications_off") }}
          </button>
        </div>
      </section>

      <!-- A CREDENCIAL DO JEV: a chave da API e a Chave Principal que a sela.
           É ajuste da pasta (o `secret` de escopo `jev`), e sem ela o chat diz
           "Jev não configurado". -->
      <section v-if="tab === 'general'" class="block">
        <h2>{{ word("jev") }}</h2>
        <div class="block-body">
          <p class="pop-note">{{ word("jev_hint") }}</p>
          <div class="jev-form">
            <input v-model="jevKey" type="password" autocomplete="off"
                   class="jev-input" :placeholder="word('jev_key')"
                   :aria-label="word('jev_key')">
            <button type="button" class="btn"
                    :disabled="jevBusy || !jevKey" @click="saveJev">
              {{ word("jev_save") }}
            </button>
          </div>
          <p v-if="jevError" class="pop-note">{{ jevError }}</p>
          <p v-else-if="store.jev_ready" class="pop-note">{{ word("jev_saved") }}</p>
        </div>
      </section>

      <!-- OS TEMAS: the whole list, which is what a person comparing two looks
           came here for. -->
      <section v-if="tab === 'appearance'" class="block">
        <h2>{{ word("themes") }}</h2>
        <div class="block-body">
          <div class="settings">
            <button v-for="row in themeList" :key="row.id" type="button" class="theme"
                    :class="{ on: themeState.id === row.id }"
                    :aria-pressed="themeState.id === row.id"
                    @click="pick(row)">
              <b>{{ row.label }}</b>
              <span class="key">{{ row.id }}</span>
              <span v-if="descOf(row)" class="desc">{{ descOf(row) }}</span>
            </button>
          </div>
        </div>
      </section>

      <section v-if="tab === 'appearance' && sideStates.length" class="block">
        <h2>{{ word("dark_mode") }}</h2>
        <div class="block-body">
          <div class="radios" role="radiogroup" :aria-label="word('dark_mode')">
            <label v-for="state in sideStates" :key="state" class="radio-row"
                   :class="{ on: side === state }">
              <input type="radio" class="radio" name="dark-side" :value="state"
                     :checked="side === state" @change="pickSide(state)">
              <span>{{ word(WORDS[state]) }}</span>
            </label>
          </div>
        </div>
      </section>

      <section v-if="tab === 'appearance'" class="block">
        <h2>{{ word("motion") }}</h2>
        <div class="block-body">
          <button type="button" class="switch" role="switch"
                  :aria-label="word('motion')" :class="{ on: motion }"
                  :aria-checked="motion" @click="toggleMotion"></button>
        </div>
      </section>

      <!-- PESSOAS (§5, item 11): quem pode agir, com qual teto. É ajuste da
           pasta, e o componente traz as DUAS seções dele (atores e papéis). -->
      <PeopleView v-if="tab === 'people'" />

      <!-- O RISCO — a escala do filtro de demanda, desenhada a partir do que o
           produto declara. É leitura e não escolha. -->
      <section v-if="tab === 'risk'" class="block">
        <h2>{{ word("risk") }}</h2>
        <div class="block-body">
          <RiskRuler />
        </div>
      </section>

      <!-- A ÁRVORE DE ACTIONS (TASK-189, fatia 4/4): o catálogo inteiro, por
           verbo — leitura, nunca um botão que executa. -->
      <section v-if="tab === 'actions'" class="block">
        <h2>{{ word("actions") }}</h2>
        <div class="block-body">
          <ActionsView />
        </div>
      </section>
    </div>
  </div>
</template>

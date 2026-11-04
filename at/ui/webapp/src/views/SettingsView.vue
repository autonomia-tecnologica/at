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

import { ref, watchEffect } from "vue";
import { store, word } from "../lib/store";
import { setTrail } from "../lib/views";
import ActionsView from "../components/ActionsView.vue";
import PeopleView from "../components/PeopleView.vue";
import RiskRuler from "../components/RiskRuler.vue";
import AssistSection from "../components/settings/AssistSection.vue";
import DarkSideSection from "../components/settings/DarkSideSection.vue";
import DensitySection from "../components/settings/DensitySection.vue";
import FilesOfflineSection from "../components/settings/FilesOfflineSection.vue";
import JevSection from "../components/settings/JevSection.vue";
import MotionSection from "../components/settings/MotionSection.vue";
import PushSection from "../components/settings/PushSection.vue";
import ThemesSection from "../components/settings/ThemesSection.vue";

// AS ABAS, na ordem em que a tela se apresenta: o que a pasta é (o idioma), o
// que se vê, quem age nela e o que ela mede de risco.
const TABS = ["general", "appearance", "people", "risk", "actions"] as const;

const tab = ref<(typeof TABS)[number]>("general");

watchEffect(() => setTrail(word("settings")));
</script>

<template>
  <!-- AS ABAS SÃO OS GRUPOS, e cada parte é uma seção. A tela configura a pasta
       inteira — o idioma, o que se vê, quem age e o que é risco —, e agrupar
       isso em dobras fazia a pessoa ABRIR para descobrir o que havia dentro; o
       que uma aba guarda não é surpresa, é a outra metade da mesma tela. -->
  <div class="settings-page">
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

      <!-- O ASSIST (TASK-180, fatia 3/3), as NOTIFICAÇÕES (Web Push) e a
           CREDENCIAL DO JEV: cada ajuste da pasta é uma seção em `settings/`. -->
      <template v-if="tab === 'general'">
        <AssistSection />
        <PushSection />
        <FilesOfflineSection />
        <JevSection />
      </template>

      <!-- Aparência: os temas, o lado, a densidade e o movimento. -->
      <template v-if="tab === 'appearance'">
        <ThemesSection />
        <DarkSideSection />
        <DensitySection />
        <MotionSection />
      </template>

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

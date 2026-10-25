<script setup lang="ts">
// DesignView — the specimen: every token and component of the system on one page,
// on whichever theme and side is worn. Internal: it has an address (`/design`)
// and NO row in the panel; it exists so the system is reviewed here, not screen by screen.

import { h, ref, watchEffect } from "vue";
import { setTrail } from "../lib/views";
import { store, word } from "../lib/store";
import { openPop } from "../lib/pop";
import { ask } from "../lib/confirm";
import { toast } from "../lib/toast";
import { DARK_STATES, chooseDark, chooseTheme, darkState, themeState } from "../lib/theme";
import type { DarkState } from "../lib/theme";
import { DENSITIES, density, setDensity } from "../lib/density";
import type { Density } from "../lib/density";
import EmptyState from "../components/EmptyState.vue";

watchEffect(() => setTrail("Design"));

const side = ref<DarkState>(darkState());
const dense = ref<Density>(density());

function pickSide(state: DarkState): void { side.value = state; chooseDark(state); }
function pickDensity(state: Density): void { dense.value = state; setDensity(state); }

const TEXT_ROLES: [string, string][] = [
  ["--text-primary", "ds_primary"], ["--text-secondary", "ds_secondary"], ["--text-tertiary", "ds_tertiary"],
];
const TYPE_SCALE: [string, string, number][] = [
  ["--type-display", "ds_display", 28], ["--type-page", "ds_page", 20], ["--type-title", "ds_title", 16],
  ["--type-body-lg", "ds_body_large", 16], ["--type-body", "ds_body", 14], ["--type-body-sm", "ds_body_small", 13],
  ["--type-caption", "ds_caption", 12],
];
const STEPS = [50, 100, 200, 300, 400, 500, 600, 700, 800];
const SURFACES = ["--surface-canvas", "--surface-card", "--surface-raised", "--surface-sunken", "--border-subtle", "--border-default"];
const STATES = ["success", "warning", "danger", "info"];
const CHIPS = ["todo", "doing", "done", "cancelled", "low", "high", "critical"];
const SPACES = ["1", "2", "3", "4", "6", "8", "12", "16"];

const sample = { render: () => h("div", { class: "opt" }, word("ds_pop_text")) };

function showPop(event: MouseEvent): void {
  openPop("design-pop", sample, {}, { anchor: event.currentTarget as HTMLElement });
}
async function showDialog(): Promise<void> {
  toast((await ask(word("ds_ask"))) ? word("ds_yes") : word("ds_no"));
}
</script>

<template>
  <div class="design">
    <section>
      <h2>{{ word("ds_theme") }}</h2>
      <div class="row">
        <button v-for="row in store.themes" :key="row.id" type="button" class="btn btn-sm" :class="themeState.id === row.id ? '' : 'btn-quiet'" :aria-pressed="themeState.id === row.id" @click="chooseTheme(row.id)">{{ row.label }}</button>
        <button v-for="state in DARK_STATES" :key="state" type="button" class="btn btn-sm"
                :class="side === state ? '' : 'btn-quiet'" @click="pickSide(state)">{{ state }}</button>
        <button v-for="state in DENSITIES" :key="state" type="button" class="btn btn-sm"
                :class="dense === state ? '' : 'btn-quiet'" @click="pickDensity(state)">{{ state }}</button>
      </div>
    </section>

    <section>
      <h2>{{ word("ds_text_roles") }}</h2>
      <p v-for="[token, name] in TEXT_ROLES" :key="token" :style="{ color: `var(${token})`, margin: 0 }">
        {{ word(name) }} <code>{{ token }}</code> — {{ word("ds_fox") }}
      </p>
    </section>

    <section>
      <h2>{{ word("ds_type_scale") }}</h2>
      <p v-for="[token, name, px] in TYPE_SCALE" :key="token" :style="{ fontSize: `var(${token})`, margin: 0 }">
        {{ word(name) }} {{ px }} <code>{{ token }}</code>
      </p>
    </section>

    <section>
      <h2>{{ word("ds_colour") }}</h2>
      <div class="row">
        <span v-for="step in STEPS" :key="step" class="swatch" :style="{ background: `var(--accent-${step})` }"
              :title="`--accent-${step}`">{{ step }}</span>
      </div>
      <div class="row">
        <span v-for="token in SURFACES" :key="token" class="swatch ink" :style="{ background: `var(${token})` }"
              :title="token">{{ token.slice(2) }}</span>
      </div>
      <div class="row">
        <template v-for="kind in STATES" :key="kind">
          <span class="swatch" :style="{ background: `var(--${kind})` }" :title="`--${kind}`"></span>
          <span class="swatch ink" :style="{ background: `var(--${kind}-soft)`, color: `var(--${kind}-text)` }"
                :title="`--${kind}-soft / --${kind}-text`">{{ kind }}</span>
        </template>
      </div>
      <div class="row">
        <span v-for="n in SPACES" :key="n" class="bar" :style="{ width: `var(--space-${n})` }"
              :title="`--space-${n}`"></span>
      </div>
    </section>

    <section>
      <h2>{{ word("ds_buttons") }}</h2>
      <div class="row">
        <button type="button" class="btn btn-sm">{{ word("ds_small") }}</button>
        <button type="button" class="btn">{{ word("ds_medium") }}</button>
        <button type="button" class="btn btn-lg">{{ word("ds_large") }}</button>
        <button type="button" class="btn btn-quiet">{{ word("ds_quiet") }}</button>
        <button type="button" class="btn btn-ghost">{{ word("ds_ghost") }}</button>
        <button type="button" class="btn danger">{{ word("ds_danger") }}</button>
        <button type="button" class="btn" disabled>{{ word("ds_disabled") }}</button>
      </div>
    </section>

    <section>
      <h2>{{ word("ds_inputs") }}</h2>
      <div class="form">
        <label><span>{{ word("ds_text") }}</span><input type="text" :value="word('ds_value')"></label>
        <label><span>{{ word("ds_select") }}</span><select><option>1</option><option>2</option></select></label>
        <label><span>{{ word("ds_textarea") }}</span><textarea :value="word('ds_lines')"></textarea></label>
        <label><span>{{ word("ds_disabled") }}</span><input type="text" :value="word('ds_locked')" disabled></label>
      </div>
      <div class="radios">
        <label class="check-row"><input type="checkbox" class="check" checked><span>{{ word("ds_checked") }}</span></label>
        <label class="check-row"><input type="checkbox" class="check"><span>{{ word("ds_unchecked") }}</span></label>
        <label class="radio-row"><input type="radio" class="radio" name="d" checked><span>{{ word("ds_radio_on") }}</span></label>
        <label class="radio-row"><input type="radio" class="radio" name="d"><span>{{ word("ds_radio_off") }}</span></label>
      </div>
    </section>

    <section>
      <h2>{{ word("ds_chips") }}</h2>
      <div class="row"><span v-for="value in CHIPS" :key="value" class="chip" :data-value="value">{{ value }}</span></div>
    </section>

    <section>
      <h2>{{ word("ds_cards_table") }}</h2>
      <div class="cards">
        <div class="card"><span class="card-top"><b>{{ word("ds_a_card") }}</b><span class="n">12</span></span></div>
      </div>
      <table class="grid">
        <thead><tr><th>Id</th><th>{{ word("ds_title") }}</th><th>{{ word("ds_status") }}</th></tr></thead>
        <tbody>
          <tr v-for="(value, i) in CHIPS.slice(0, 3)" :key="value">
            <td class="id" data-label="Id">{{ i + 1 }}</td>
            <td data-label="Title">{{ word("ds_a_row") }}</td>
            <td :data-value="value" data-label="Status"><span class="v">{{ value }}</span></td>
          </tr>
        </tbody>
      </table>
    </section>

    <section>
      <h2>{{ word("ds_overlays") }}</h2>
      <div class="row">
        <button type="button" class="btn btn-quiet" @click="showPop($event)">{{ word("ds_popover") }}</button>
        <button type="button" class="btn btn-quiet" @click="showDialog">{{ word("ds_dialog") }}</button>
        <button type="button" class="btn btn-quiet" @click="toast(word('ds_toast_text'))">{{ word("ds_toast") }}</button>
      </div>
    </section>

    <section>
      <h2>{{ word("ds_empty") }}</h2>
      <EmptyState :title="word('ds_nothing')" :text="word('ds_nothing_text')" icon="note">
        <button type="button" class="btn">{{ word("ds_action") }}</button>
      </EmptyState>
    </section>
  </div>
</template>

<style scoped>
.design section { display: flex; flex-direction: column; gap: var(--space-3); }
.design h2 { margin: 0; font-size: var(--type-title); }
.row { display: flex; flex-wrap: wrap; align-items: center; gap: var(--space-2); }
.swatch {
  min-width: 56px; height: 40px; padding: 0 var(--space-2); display: inline-flex; align-items: center;
  border: 1px solid var(--border-subtle); border-radius: var(--r-sm);
  font-size: var(--type-caption); color: var(--text-secondary);
}
.swatch.ink { height: auto; min-height: 40px; }
.bar { height: 12px; background: var(--accent); border-radius: var(--r-sm); }
</style>

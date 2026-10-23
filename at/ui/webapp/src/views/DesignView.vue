<script setup lang="ts">
// DesignView — the specimen: every token and component of the system on one page,
// on whichever theme and side is worn. Internal: it has an address (`/design`)
// and NO row in the panel; it exists so the system is reviewed here, not screen by screen.

import { h, ref, watchEffect } from "vue";
import { setTrail } from "../lib/views";
import { store } from "../lib/store";
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

const TEXT_ROLES = [
  ["--text-primary", "primary"], ["--text-secondary", "secondary"], ["--text-tertiary", "tertiary"],
];
const TYPE_SCALE = [
  ["--type-display", "Display 28"], ["--type-page", "Page 20"], ["--type-title", "Title 16"],
  ["--type-body-lg", "Body large 16"], ["--type-body", "Body 14"], ["--type-body-sm", "Body small 13"],
  ["--type-caption", "Caption 12"],
];
const STEPS = [50, 100, 200, 300, 400, 500, 600, 700, 800];
const SURFACES = ["--surface-0", "--surface-1", "--surface-2", "--border-soft", "--border-strong"];
const STATES = ["success", "warning", "danger", "info"];
const CHIPS = ["todo", "doing", "done", "cancelled", "low", "high", "critical"];
const SPACES = ["1", "2", "3", "4", "6", "8", "12", "16"];

const sample = { render: () => h("div", { class: "opt" }, "A popover is a floating panel") };

function showPop(event: MouseEvent): void {
  openPop("design-pop", sample, {}, { anchor: event.currentTarget as HTMLElement });
}
async function showDialog(): Promise<void> {
  toast((await ask("Is this the dialog?")) ? "Answered yes" : "Answered no");
}
</script>

<template>
  <div class="page design">
    <section>
      <h2>Theme, side and density</h2>
      <div class="row">
        <button v-for="row in store.themes" :key="row.id" type="button" class="btn btn-sm" :class="themeState.id === row.id ? '' : 'btn-quiet'" :aria-pressed="themeState.id === row.id" @click="chooseTheme(row.id)">{{ row.label }}</button>
        <button v-for="state in DARK_STATES" :key="state" type="button" class="btn btn-sm"
                :class="side === state ? '' : 'btn-quiet'" @click="pickSide(state)">{{ state }}</button>
        <button v-for="state in DENSITIES" :key="state" type="button" class="btn btn-sm"
                :class="dense === state ? '' : 'btn-quiet'" @click="pickDensity(state)">{{ state }}</button>
      </div>
    </section>

    <section>
      <h2>Text roles</h2>
      <p v-for="[token, name] in TEXT_ROLES" :key="token" :style="{ color: `var(${token})`, margin: 0 }">
        {{ name }} <code>{{ token }}</code> — the quick brown fox jumps over the lazy dog
      </p>
    </section>

    <section>
      <h2>Type scale</h2>
      <p v-for="[token, name] in TYPE_SCALE" :key="token" :style="{ fontSize: `var(${token})`, margin: 0 }">
        {{ name }} <code>{{ token }}</code>
      </p>
    </section>

    <section>
      <h2>Colour</h2>
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
      <h2>Buttons</h2>
      <div class="row">
        <button type="button" class="btn btn-sm">Small</button>
        <button type="button" class="btn">Medium</button>
        <button type="button" class="btn btn-lg">Large</button>
        <button type="button" class="btn btn-quiet">Quiet</button>
        <button type="button" class="btn btn-ghost">Ghost</button>
        <button type="button" class="btn danger">Danger</button>
        <button type="button" class="btn" disabled>Disabled</button>
      </div>
    </section>

    <section>
      <h2>Inputs</h2>
      <div class="form">
        <label><span>Text</span><input type="text" value="A value"></label>
        <label><span>Select</span><select><option>One</option><option>Two</option></select></label>
        <label><span>Textarea</span><textarea>Some lines</textarea></label>
        <label><span>Disabled</span><input type="text" value="Locked" disabled></label>
      </div>
      <div class="radios">
        <label class="check-row"><input type="checkbox" class="check" checked><span>Checked</span></label>
        <label class="check-row"><input type="checkbox" class="check"><span>Unchecked</span></label>
        <label class="radio-row"><input type="radio" class="radio" name="d" checked><span>Radio on</span></label>
        <label class="radio-row"><input type="radio" class="radio" name="d"><span>Radio off</span></label>
      </div>
    </section>

    <section>
      <h2>State chips</h2>
      <div class="row"><span v-for="value in CHIPS" :key="value" class="chip" :data-value="value">{{ value }}</span></div>
    </section>

    <section>
      <h2>Cards and table</h2>
      <div class="cards">
        <div class="card"><span class="card-top"><b>A card</b><span class="n">12</span></span></div>
      </div>
      <table class="grid">
        <thead><tr><th>Id</th><th>Title</th><th>Status</th></tr></thead>
        <tbody>
          <tr v-for="(value, i) in CHIPS.slice(0, 3)" :key="value">
            <td class="id" data-label="Id">{{ i + 1 }}</td>
            <td data-label="Title">A row of the table</td>
            <td :data-value="value" data-label="Status"><span class="v">{{ value }}</span></td>
          </tr>
        </tbody>
      </table>
    </section>

    <section>
      <h2>Popover, dialog, toast</h2>
      <div class="row">
        <button type="button" class="btn btn-quiet" @click="showPop($event)">Popover</button>
        <button type="button" class="btn btn-quiet" @click="showDialog">Dialog</button>
        <button type="button" class="btn btn-quiet" @click="toast('A toast, five seconds')">Toast</button>
      </div>
    </section>

    <section>
      <h2>Empty state</h2>
      <EmptyState title="Nothing here yet" text="An empty room says what it is and what to do next." icon="note">
        <button type="button" class="btn">The action</button>
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
  border: 1px solid var(--border-soft); border-radius: var(--r-sm);
  font-size: var(--type-caption); color: var(--text-secondary);
}
.swatch.ink { height: auto; min-height: 40px; }
.bar { height: 12px; background: var(--accent); border-radius: var(--r-sm); }
</style>

<script setup lang="ts">
// ClosePop — the row's own closing (TASK-122, fatia 3/7): the engine's
// `cancel`, asked from the row menu instead of a plain yes/no — the reason is
// the closing's own argument (`tables.cancel`), and a table that requires one
// (`reason_required`) answers `error.reason_required` verbatim, shown here the
// same way `CreatePop` shows a refusal.
import { ref } from "vue";
import { word } from "../../lib/store";
import { post } from "../../lib/api";
import { closePop } from "../../lib/pop";
import { poke } from "../../lib/views";

const props = defineProps<{
  entity: string;
  id: number;
  title: string;
}>();

const reason = ref("");
const refusal = ref("");

async function submit(): Promise<void> {
  refusal.value = "";
  try {
    await post("/api/table/" + encodeURIComponent(props.entity), {
      action: "cancel",
      id: props.id,
      set: reason.value ? { reason: reason.value } : {},
    });
    closePop();
    poke();
  } catch (err) {
    refusal.value = (err as Error).message;
  }
}
</script>

<template>
  <form class="form" @submit.prevent="submit">
    <p v-if="refusal" class="refused">{{ refusal }}</p>
    <p>{{ word("close_confirm").replace("{name}", title) }}</p>
    <label>
      <span>{{ word("close_reason") }}</span>
      <textarea v-model="reason"></textarea>
    </label>
    <div class="dialog-actions">
      <button type="submit" class="btn">{{ word("close") }}</button>
    </div>
  </form>
</template>

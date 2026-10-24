// A CÉLULA EDITA A SI MESMA (TASK-175, seção Tabelas). SÓ NA SEÇÃO TABELAS, e só
// o campo que o catálogo marcou `editable`: o clique na linha parou de abrir o
// registro ali, e é a célula que toma o gesto. Um ENUM continua pelo `PickPop` de
// sempre — só a ÂNCORA muda, da célula em vez de um botão do registro —; o resto
// é texto editado no lugar. Used by TableView.

import { ref, watch, nextTick, type ComputedRef } from "vue";
import { openPop } from "./pop";
import { poke } from "./views";
import { post } from "./api";
import { toast } from "./toast";
import { value } from "./tableCells";
import PickPop from "../components/pops/PickPop.vue";
import type { FieldSpec, RecordRow } from "./record";

export function useCellEdit(
  props: { entity: string; section: "tables" | "tasks" | null },
  byName: ComputedRef<Record<string, FieldSpec>>,
) {
  const editing = ref<{ id: number; name: string } | null>(null);
  const editValue = ref("");
  const editInputEl = ref<HTMLInputElement | null>(null);

  function isEditing(rec: RecordRow, name: string): boolean {
    return !!editing.value && editing.value.id === rec.id && editing.value.name === name;
  }

  function cellEditable(name: string): boolean {
    return props.section === "tables" && !!byName.value[name]?.editable;
  }

  function onCellClick(ev: MouseEvent, rec: RecordRow, name: string): void {
    // SÓ QUEM EDITA PARA O CLIQUE: fora disso ele SOBE até a linha — é de lá
    // que `/task` (seção Tarefas) abre o popup da TASK-173, e parar aqui
    // SEMPRE teria calado esse clique também, não só o da célula editável.
    if (!cellEditable(name) || isEditing(rec, name)) return;
    ev.stopPropagation(); // a célula toma o gesto; a linha não abre nada atrás dela
    const spec = byName.value[name];
    if (spec?.enum && Object.keys(spec.enum).length) {
      openPop("cell-pick:" + props.entity + ":" + rec.id + ":" + name, PickPop,
              { field: value(rec, name), spec, entity: props.entity, record: rec },
              { anchor: ev.currentTarget as HTMLElement });
      return;
    }
    editing.value = { id: rec.id, name };
    editValue.value = value(rec, name).value || "";
  }

  watch(editing, async next => {
    if (!next) return;
    await nextTick();
    editInputEl.value?.focus();
    editInputEl.value?.select();
  });

  async function commitEdit(rec: RecordRow, name: string): Promise<void> {
    if (!isEditing(rec, name)) return;
    const next = editValue.value;
    editing.value = null;
    if (next === (value(rec, name).value || "")) return; // nada mudou, nada para escrever
    try {
      await post("/api/table/" + encodeURIComponent(props.entity), {
        action: "edit",
        id: rec.id,
        set: { [name]: next },
      });
      poke();
    } catch (err) {
      toast((err as Error).message);
    }
  }

  function cancelEdit(): void {
    editing.value = null;
  }

  return { editValue, editInputEl, isEditing, cellEditable, onCellClick, commitEdit, cancelEdit };
}

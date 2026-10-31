// A GRADE DA SEÇÃO TABELAS EDITA A SI MESMA (B-54), e só ela: fora da seção
// `tables` o clique na linha continua abrindo o registro, como sempre foi.
//
// O que este arquivo decide é só QUEM pode editar: o servidor disse
// (`actions` traz `edit`) e o tipo declarado permite (`editableField`). O
// editor em si é `FieldEditor.vue`, e a escrita é `lib/fieldWrite`; nenhum
// nome de campo é conhecido aqui.

import { computed, type ComputedRef } from "vue";
import { editableField } from "./fieldWrite";
import type { FieldSpec } from "./record";

export function useCellEdit(
  props: { section: "tables" | "tasks" | null; actions: string[] },
  byName: ComputedRef<Record<string, FieldSpec>>,
) {
  // SEM PERMISSÃO, TUDO É LEITURA: a edição direta só existe quando o engine
  // diz que este ator alcança `edit` nesta tabela.
  const canEdit = computed(() => props.section === "tables" && props.actions.includes("edit"));

  function cellEditable(name: string): boolean {
    const spec = byName.value[name];
    return !!spec && canEdit.value && editableField(spec);
  }

  return { canEdit, cellEditable };
}

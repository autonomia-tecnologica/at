// O catálogo — a leitura de `/api/catalogue` que RoleView (o picker do papel) e
// ActionsView (a árvore de Actions, TASK-189 fatia 4/4) compartilham. Uma
// leitura só, e um agrupamento genérico só: o que muda entre as duas telas é a
// CHAVE que agrupa (objeto, lá; verbo, aqui), nunca o catálogo em si.

import { api } from "./api";

export interface Modifier {
  name: string;
  label: string;
  kind: string;
}

// Uma entrada do catálogo, como o servidor a entrega — a palavra, as partes
// (objeto/ação) e, desde a fatia 4/4, os modificadores que o ato aceita e as
// portas (`reach`) que o alcançam.
export interface CatalogueEntry {
  key: string;
  object: string;
  object_label: string;
  action: string;
  action_label: string;
  label: string;
  risk: number;
  modifiers: Modifier[];
  reach: string[];
  orphan: boolean;
}

export interface CatalogueGroup {
  key: string;
  label: string;
  entries: CatalogueEntry[];
}

export async function fetchCatalogue(): Promise<CatalogueEntry[]> {
  const answer = await api<{ permissions: CatalogueEntry[] }>("/api/catalogue");
  return answer.permissions;
}

// Agrupa a lista fechada por qualquer eixo dela — o objeto (RoleView) ou o
// verbo (ActionsView) —, na ordem em que o catálogo já veio. Nenhuma das duas
// telas ordena nada: a ordem é a do servidor.
export function groupCatalogue(
  entries: CatalogueEntry[],
  keyOf: (entry: CatalogueEntry) => string,
  labelOf: (entry: CatalogueEntry) => string,
): CatalogueGroup[] {
  const out: CatalogueGroup[] = [];
  for (const entry of entries) {
    const key = keyOf(entry);
    let group = out.find(candidate => candidate.key === key);
    if (!group) {
      group = { key, label: labelOf(entry), entries: [] };
      out.push(group);
    }
    group.entries.push(entry);
  }
  return out;
}

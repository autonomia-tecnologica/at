// The panels and the context menus of a table: what the header, the empty table
// and a row offer — exactly what the engine said was legal (`props.actions`),
// and nothing TableView invents. Used by TableView.

import { computed, type ComputedRef } from "vue";
import { store, word } from "./store";
import { openPop } from "./pop";
import { openContextMenu, type MenuItem } from "./menu";
import { leave, markPage, poke } from "./views";
import { ask } from "./confirm";
import { post } from "./api";
import { toast } from "./toast";
import ColumnsPop from "../components/pops/ColumnsPop.vue";
import CreatePop from "../components/pops/CreatePop.vue";
import ClosePop from "../components/pops/ClosePop.vue";
import DeclarePop from "../components/pops/DeclarePop.vue";
import RecordPop from "../components/pops/RecordPop.vue";
import type { DeclarableTable, FieldSpec, RecordRow } from "./record";

type At = { anchor?: HTMLElement | null; point?: { x: number; y: number } };

export function useMenus(
  props: {
    entity: string;
    records: RecordRow[];
    page: string | null;
    rule: boolean;
    actions: string[];
    declarable: DeclarableTable[];
    section: "tables" | "tasks" | null;
  },
  fields: ComputedRef<FieldSpec[]>,
  columnKey: ComputedRef<string>,
  order: { value: string[] },
  hiddenNow: ComputedRef<Set<string>>,
  setHidden: (name: string, hide: boolean) => void,
) {
  const page = computed(() => props.page || props.entity);

  function openColumns(anchor: HTMLElement | null): void {
    // No panel where there is nothing to choose: the columns are the rule, and a
    // panel of checkboxes that undo themselves would be a door painted on a wall.
    if (props.rule) return;
    openPop("columns:" + columnKey.value, ColumnsPop,
            { order: order.value, hidden: hiddenNow.value, fields: fields.value,
              onToggle: setHidden },
            { anchor });
  }

  // A RULE VIEW HAS AN IMPLICIT FIELD ITS FORM CANNOT KNOW (the project a task
  // lives under, `hide: ["project", "orphans"]`): creating there would write an
  // orphan silently, the same mismatch `TaskBoard.vue`'s own quick-add avoids by
  // staying out of it. So `create`, like `columns`, stays off a rule view.
  function openCreate(at: At): void {
    openPop("create:" + props.entity, CreatePop, { entity: props.entity, schema: fields.value }, at);
  }

  // O PAINEL DE DECLARAR (relógio, fatia 3/3) — ao lado de `openCreate` e pelo
  // mesmo motivo: `declare` só chega em `props.actions` para a tabela `job`
  // (`_table_actions`), e é `props.declarable` que traz o que há para agendar.
  function openDeclare(at: At): void {
    openPop("declare:" + props.entity, DeclarePop, { declarable: props.declarable }, at);
  }

  // THE HEADER'S RIGHT CLICK, THROUGH THE ONE DOOR (TASK-120, fatia 1): a menu
  // opens at the pointer, with "columns" and — when the engine says this actor
  // may (TASK-121) — "create" beside it. The anchor is captured HERE, at open
  // time, and not read off the menu item's own click later.
  function openHeaderMenu(ev: MouseEvent): void {
    if (props.rule) return;
    const anchor = ev.currentTarget as HTMLElement;
    const items: MenuItem[] = [{ label: word("columns"), action: () => openColumns(anchor) }];
    if (props.actions.includes("create")) {
      items.push({ label: word("create"), action: () => openCreate({ anchor }) });
    }
    if (props.actions.includes("declare")) {
      items.push({ label: word("declare"), action: () => openDeclare({ anchor }) });
    }
    openContextMenu(ev, items);
  }

  // THE EMPTY TABLE'S RIGHT CLICK (TASK-137, fatia 6/7): there is no header and
  // no row to anchor on, so `create` opens AT THE POINTER — the same `point` a
  // row's close/delete already uses. The rule view's `create` is already
  // refused above (`openHeaderMenu`'s early return); here there is no row menu
  // to refuse it from, so the check is this function's own.
  function openEmptyMenu(ev: MouseEvent): void {
    if (props.rule) return;
    const point = { x: ev.clientX, y: ev.clientY };
    const items: MenuItem[] = [];
    if (props.actions.includes("create")) {
      items.push({ label: word("create"), action: () => openCreate({ point }) });
    }
    if (props.actions.includes("declare")) {
      items.push({ label: word("declare"), action: () => openDeclare({ point }) });
    }
    if (items.length) openContextMenu(ev, items);
  }

  // A ROW'S RIGHT CLICK (and the context-menu key, Shift+F10, and a touch
  // long-press — `v-context-menu` either way): what it offers is exactly what
  // the engine said was legal (`props.actions`), and nothing this component
  // invents.
  //
  // `cancel` and `delete` (TASK-122, fatia 3/7) join `edit` here, each with the
  // confirmation it owes BEFORE the write reaches the server: a closing asks
  // for the reason in its own panel (`ClosePop`, since a table may require
  // one), a deletion asks the plain yes/no (`lib/confirm`) because it takes
  // nothing else — and a refusal either one meets (the engine's own words, a
  // line a reference still names) is shown as the server worded it, in a
  // toast, never a stack trace.
  function openRowMenu(ev: MouseEvent, rec: RecordRow): void {
    const point = { x: ev.clientX, y: ev.clientY };
    const items: MenuItem[] = [];
    // NA SEÇÃO TABELAS "ABRIR REGISTRO" É LEITURA, e não edição: aparece
    // SEMPRE, mesmo sem `edit` nos `actions` — o painel que ele abre já recebe
    // a lista e nasce só de leitura quando a escrita não é permitida. Nas
    // demais superfícies o "Editar" continua com o portão e o rótulo de hoje.
    if (props.section === "tables") {
      items.push({ label: word("open_record"), action: () => openRecord(rec) });
    } else if (props.actions.includes("edit")) {
      items.push({ label: word("edit"), action: () => openRecord(rec) });
    }
    if (props.actions.includes("cancel")) {
      items.push({ label: word("close"), action: () => openClose(rec, point) });
    }
    if (props.actions.includes("delete")) {
      items.push({ label: word("delete"), action: () => deleteRow(rec) });
    }
    // O RELÓGIO, FATIA 3/3: `disable` É O JOB's OWN ACT, do mesmo jeito
    // `cancel`/`delete` já são — row-independent, como todo este menu (o
    // DOCSTRING de `_table_actions` é a regra): tentar desligar um job que já
    // não está `scheduled` chega ao mesmo lugar que cancelar um já cancelado
    // chega hoje, um toast com a recusa do motor.
    if (props.actions.includes("disable")) {
      items.push({ label: word("disable"), action: () => disableRow(rec) });
    }
    openContextMenu(ev, items);
  }

  function openClose(rec: RecordRow, point: { x: number; y: number }): void {
    openPop("close:" + props.entity + ":" + rec.id, ClosePop,
            { entity: props.entity, id: rec.id, title: rec.title || String(rec.id) },
            { point });
  }

  async function deleteRow(rec: RecordRow): Promise<void> {
    const name = rec.title || String(rec.id);
    if (!(await ask(word("delete_confirm").replace("{name}", name)))) return;
    try {
      await post("/api/table/" + encodeURIComponent(props.entity), { action: "delete", id: rec.id });
      poke();
    } catch (err) {
      toast((err as Error).message);
    }
  }

  // `disable` NÃO ANDA POR `/api/table` (relógio, fatia 3/3): é um ato PRÓPRIO
  // do `job` (`jobs.ACTS`), e a porta é a sua, `/api/job` — a mesma distinção
  // que já vale no servidor (`_post_job`, nunca `_post_table`).
  async function disableRow(rec: RecordRow): Promise<void> {
    const name = rec.title || String(rec.id);
    if (!(await ask(word("disable_confirm").replace("{name}", name)))) return;
    try {
      await post("/api/job", { action: "disable", id: rec.id });
      poke();
    } catch (err) {
      toast((err as Error).message);
    }
  }

  // A closure PER ROW, made in script and not in the template: the directive's
  // handler type takes only an event, and `rec` is what tells rows apart.
  function rowMenuHandler(rec: RecordRow): (ev: MouseEvent) => void {
    return ev => openRowMenu(ev, rec);
  }

  // A TASK OPENS AS A FLOATING PANEL (TASK-173), over this very table, instead
  // of swapping the whole page for it — the person asked for this in the TASKS
  // part, and every other table keeps the page swap it always had.
  //
  // A SEÇÃO TABELAS NÃO TEM MAIS "abrir o registro" NO CLIQUE (TASK-175, fatia
  // planilha): a célula edita a si mesma, e o registro inteiro — quando
  // precisar, um campo de prosa longo — é o menu de contexto que abre, pela
  // MESMA porta flutuante que a TASK-173 deu à tarefa, agora para QUALQUER
  // tabela vista em modo planilha.
  function openRecord(rec: RecordRow): void {
    if (props.section === "tables" || props.entity === store.types.task) {
      openPop("record:" + props.entity + ":" + rec.id, RecordPop,
              { entity: props.entity, page: page.value, id: rec.id,
                records: () => props.records, actions: props.actions },
              { attrs: { class: "record-pop" } });
      return;
    }
    leave(); // the table is where this record is being read from
    markPage(page.value, rec.id);
  }

  // A LINHA, QUANDO AINDA ABRE ALGO (TASK-175): fora da seção Tabelas, um clique
  // na linha segue abrindo o registro — mas o mesmo clique BORBULHA até o
  // listener global de `App.vue` (`document.addEventListener("click", () =>
  // closePop())`), que fecharia o painel flutuante no MESMO tique em que ele
  // acabou de abrir (achado ao testar esta fatia: a TASK-173 já carregava essa
  // falha, por não ter `.stop` nenhum aqui). Parar aqui é o mesmo remédio que o
  // botão de filtro do cabeçalho já tinha.
  function onRowClick(ev: MouseEvent, rec: RecordRow): void {
    if (props.section === "tables") return;
    ev.stopPropagation();
    openRecord(rec);
  }

  return { openColumns, openHeaderMenu, openEmptyMenu, rowMenuHandler, onRowClick };
}

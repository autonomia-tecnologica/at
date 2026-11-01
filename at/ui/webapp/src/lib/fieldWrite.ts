// fieldWrite — UMA escrita de campo, e o desfazer de UM passo (B-54).
//
// A regra que mora aqui e em nenhum componente: QUAIS campos uma superfície
// edita e COMO o valor sai. O tipo é o declarado (`FieldSpec`, que o servidor
// monta do schema), nunca um nome de campo — `id`, os três tipos que o motor
// não entrega (`instant`, `hashed`, `sealed`) e o que o motor escreve
// (`managed`: `append`/`tracks`/`touch`) são leitura. Uma referência de mais de
// uma tabela não ganha seletor inventado: fica leitura.
//
// A ESCRITA É A DO SERVIDOR: toda alteração caminha por `POST /api/table/<t>`
// `{action:"edit", id, set:{...}}` — e `task` caminha pela fila (`writeTask`),
// como `PickPop`/`TaskBoard` já fazem. Nenhuma regra de validação é reescrita
// no cliente; em erro, o toast mostra a palavra do servidor e o valor lido
// permanece.
//
// O DESFAZER É DE UM PASSO: cada escrita bem-sucedida guarda o `raw` ANTERIOR
// e substitui o desfazer da escrita anterior. Quem o oferece é o toast "Salvo".

import { post } from "./api";
import { label, word } from "./store";
import { poke } from "./views";
import { OFFLINE_TABLE, writeTask } from "./offline";
import { toast, type ToastAction } from "./toast";
import type { FieldSpec, RecordRow } from "./record";

// Os tipos que o motor não entrega à página, e o `id` que é do store.
const READ_ONLY_TYPES = ["instant", "hashed", "sealed"];

export type FieldKind = "text" | "markdown" | "day" | "enum" | "list" | "ref";

export function editableField(spec: FieldSpec): boolean {
  if (spec.name === "id") return false;
  if (spec.managed) return false;
  if (READ_ONLY_TYPES.includes(spec.type || "")) return false;
  // Uma referência que aponta para mais de uma tabela não tem seletor: ela
  // continua leitura, e nada é inventado para adivinhar qual tabela buscar.
  if ((spec.refs || []).length > 1) return false;
  return true;
}

export function fieldKind(spec: FieldSpec): FieldKind {
  if (spec.enum && Object.keys(spec.enum).length) return "enum";
  if (spec.type === "list") return "list";
  if (spec.type === "day") return "day";
  if (spec.type === "markdown") return "markdown";
  if ((spec.refs || []).length === 1) return "ref";
  return "text";
}

interface Step {
  entity: string;
  record: RecordRow;
  spec: FieldSpec;
  raw: unknown; // o valor que a escrita vai regravar no desfazer
}

// O DESFAZER DE UM PASSO, só. A próxima escrita o substitui.
let lastStep: Step | null = null;

function currentRaw(record: RecordRow, name: string): unknown {
  const field = record.fields.find(f => f.name === name);
  return field ? field.raw : null;
}

// A ponta de leitura de uma escrita otimista (a fila): o campo passa a mostrar
// o que foi escrito sem uma releitura que ainda não pode acontecer.
function patch(record: RecordRow, spec: FieldSpec, raw: unknown): void {
  const field = record.fields.find(f => f.name === spec.name);
  if (!field) return;
  field.raw = raw;
  if (raw === null || raw === undefined) field.value = "";
  else if (spec.enum) field.value = label(spec.enum[String(raw)]) || String(raw);
  else if (Array.isArray(raw)) field.value = raw.map(item => String(item)).join(", ");
  else field.value = String(raw);
}

// O MOTOR LÊ UMA LISTA COMO O TEXTO SEPARADO POR VÍRGULA (`tables_types`):
// o array que a tela mostra não é o que viaja. A vírgula continua sendo do
// armazenamento — a tela mostra chips e nunca a expõe.
function wireValue(spec: FieldSpec, raw: unknown): unknown {
  if (spec.type === "list" && Array.isArray(raw)) {
    return raw.map(item => String(item)).join(",");
  }
  return raw;
}

async function send(entity: string, id: number, spec: FieldSpec, raw: unknown): Promise<boolean> {
  const value = wireValue(spec, raw);
  if (entity === OFFLINE_TABLE) {
    const { queued } = await writeTask("edit", { [spec.name]: value }, id);
    return queued;
  }
  await post("/api/table/" + encodeURIComponent(entity), {
    action: "edit",
    id,
    set: { [spec.name]: value },
  });
  return false;
}

// A escrita de um campo, com o desfazer da escrita ANTERIOR trocado por esta.
// Devolve se gravou.
export async function saveField(
  entity: string,
  record: RecordRow,
  spec: FieldSpec,
  raw: unknown,
): Promise<boolean> {
  const previous = currentRaw(record, spec.name);
  let queued = false;
  try {
    queued = await send(entity, record.id, spec, raw);
  } catch (err) {
    // O VALOR LIDO PERMANECE: quem chamou não mexeu no estado local, e o toast
    // diz a recusa com as palavras do servidor.
    toast((err as Error).message);
    return false;
  }
  if (queued) patch(record, spec, raw);
  else poke();
  lastStep = { entity, record, spec, raw: previous };
  const action: ToastAction = { label: word("undo"), run: () => { void undo(); } };
  toast(word("saved"), action);
  return true;
}

// O desfazer regrava o valor ANTERIOR e recarrega. Ele não nasce com desfazer
// próprio: um passo só, como decidido.
async function undo(): Promise<void> {
  const step = lastStep;
  if (!step) return;
  lastStep = null;
  try {
    const queued = await send(step.entity, step.record.id, step.spec, step.raw);
    if (queued) patch(step.record, step.spec, step.raw);
    else poke();
    toast(word("saved"));
  } catch (err) {
    toast((err as Error).message);
  }
}

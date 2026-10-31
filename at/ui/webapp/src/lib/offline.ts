// offline — the write queue a browser keeps when there is no network at all
// (TASK-162, fatia 2/2). The Service Worker (`assets/js/sw.js`) is the shell's
// mouth for READS; this file is the page's own hand for WRITES, because a
// Service Worker that faked a POST would be a write the fila never saw, and a
// fila the page cannot read (`pending`, below) would not be VISIBLE — which
// the pronto-quando demands.
//
// THE SCOPE IS TASKS, and only Tasks (TASK-162, Ressalvas): the same
// narrowing `at.core.offline.TABLE` carries on the server. A caller with
// another table's write reaches `post` directly and takes whatever the
// network gives it, offline included — this file has nothing to say about it.
//
// THE MOTOR THAT DECIDES A CONFLICT IS THE SERVER'S (`at.core.offline`, fatia
// 1, walked from `POST /api/offline/sync`): this file never resolves a
// conflict itself, it only gets an edit there — with the instant it was
// made — and back.

import { reactive } from "vue";
import { post, whenNetwork } from "./api";
import { poke } from "./views";

const DB_NAME = "at-offline";
const DB_VERSION = 1;
const QUEUE_STORE = "queue";

// The one table this whole file knows about (`at.core.offline.TABLE`, fatia
// 1's own narrowing) — a call site compares its entity against this constant
// instead of writing the bare word "task" a second place it could drift from.
export const OFFLINE_TABLE = "task";

// O QUE A FILA GUARDA É JSON: um campo de dia é texto, um de referência é o
// número e uma lista é um array — o motor lê cada um pelo tipo declarado.
export type WriteValues = Record<string, unknown>;

export interface QueueEntry {
  local_id: string;
  action: "create" | "edit";
  values: WriteValues;
  edited_at: string;
  id?: number;
}

interface Resolution {
  local_id: string | null;
  id: number | string | null;
  applied: boolean;
  record: unknown;
}

// WHAT THE SHELL DRAWS WITH. `online` starts at `navigator.onLine`, but that
// is the ADAPTER's word, not the SERVER's: a Wi-Fi up with a VPN/Tailscale
// down is still "online" to the browser, and the only proof otherwise is a
// request that never got an answer (`api.ts`'s `whenNetwork`, fed by every
// `api`/`post` call). `pending` is the fila's own length, so a banner reading
// it needs no IndexedDB call of its own — this module is the one place that
// counts.
export const offlineState = reactive({
  online: navigator.onLine,
  pending: 0,
});

function openDb(): Promise<IDBDatabase> {
  return new Promise((resolve, reject) => {
    const req = indexedDB.open(DB_NAME, DB_VERSION);
    req.onupgradeneeded = () => {
      req.result.createObjectStore(QUEUE_STORE, { keyPath: "local_id" });
    };
    req.onsuccess = () => resolve(req.result);
    req.onerror = () => reject(req.error);
  });
}

async function withStore<T>(
  mode: IDBTransactionMode, run: (store: IDBObjectStore) => IDBRequest<T>,
): Promise<T> {
  const db = await openDb();
  try {
    return await new Promise<T>((resolve, reject) => {
      const store = db.transaction(QUEUE_STORE, mode).objectStore(QUEUE_STORE);
      const request = run(store);
      request.onsuccess = () => resolve(request.result);
      request.onerror = () => reject(request.error);
    });
  } finally {
    db.close();
  }
}

function allEntries(): Promise<QueueEntry[]> {
  return withStore("readonly", store => store.getAll());
}

async function countPending(): Promise<void> {
  offlineState.pending = (await allEntries()).length;
}

// THE WRITE. Tried through the SAME door every other write of the page walks
// (`post`, `/api/table/task`) — offline is not a second API, it is what
// happens when the first one never arrives. Only `err.network` — a request
// that never got an ANSWER (`api.ts`'s `offTheAir`) — falls to the fila; a
// refusal (a 400, a 403) is the server's own word and offline has nothing to
// add to it, so it is re-thrown for the caller to show as it always does.
export async function writeTask(
  action: "create" | "edit", values: WriteValues, id?: number,
): Promise<{ queued: boolean }> {
  try {
    await post("/api/table/task", { action, id, set: values });
    return { queued: false };
  } catch (err) {
    if (!(err as { network?: boolean }).network) throw err;
  }
  const entry: QueueEntry = {
    local_id: crypto.randomUUID(), action, values,
    edited_at: new Date().toISOString(), id,
  };
  await withStore("readwrite", store => store.put(entry));
  await countPending();
  return { queued: true };
}

let syncing = false;

// THE RECONCILIATION. One round trip, the whole fila at once, walked in the
// order it was written (`at.core.offline.reconcile` needs that order to
// follow a `create` a later `edit` in the SAME batch points back to). Every
// entry the server answers for is removed, WHETHER IT WON OR LOST — a losing
// entry was already decided (last-write-wins, TASK-162 "o risco é aceito"),
// and keeping it queued would retry a fight that is already over.
export async function sync(): Promise<void> {
  if (syncing || !navigator.onLine) return;
  const entries = await allEntries();
  if (!entries.length) return;
  syncing = true;
  try {
    const answer = await post<{ resolutions: Resolution[] }>(
      "/api/offline/sync", { entries },
    );
    await withStore("readwrite", store => {
      for (const res of answer.resolutions) if (res.local_id) store.delete(res.local_id);
      return store.count();
    });
    // WHATEVER THE SERVER DECIDED IS THE TRUTH NOW — an entry that lost was
    // still applied OPTIMISTICALLY on screen (the call sites patch a field in
    // place, `TaskBoard.vue`, `PickPop.vue`), and only a fresh read corrects a
    // screen that guessed wrong. Cheap and exact: `poke` is the same redraw a
    // write online already causes.
    if (answer.resolutions.length) poke();
  } catch {
    // Sem rede de verdade (ou o servidor fora do ar): a fila fica como está,
    // e a próxima reconexão tenta de novo — não há o que fazer aqui.
  } finally {
    syncing = false;
    await countPending();
  }
}

window.addEventListener("online", () => {
  offlineState.online = true;
  void sync();
});
window.addEventListener("offline", () => {
  offlineState.online = false;
});

// A REQUISIÇÃO É QUEM SABE DE VERDADE. O adaptador pode dizer "online" com a
// Tailscale fora do ar; o que muda o aviso aqui é o que `api`/`post` de fato
// conseguiram, ou não, trocar com o servidor.
whenNetwork(ok => {
  offlineState.online = ok;
  if (ok) void sync();
});

void countPending();
if (navigator.onLine) void sync();

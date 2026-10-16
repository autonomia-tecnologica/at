// session — who is in, and the door that says so.
//
// THE SERVER OWNS THE ANSWER. `/api/session` is the one public answer of the
// API, and it says two things the page cannot work out by itself: whether this
// folder asks anybody to enter at all (`auth`), and who is past the entrance
// (`actor`). The page keeps none of it as a rule — it draws what it is handed,
// the same way it draws the tables.
//
// THREE STATES, NOT TWO. `ready` is false until the server has answered, and
// until then the page draws NOTHING. A boolean that started at "not signed in"
// would paint the entrance on every reload and take it away a moment later —
// exactly the flash `js/boot.js` exists to avoid, one screen earlier.

import { computed, reactive } from "vue";
import { api, post } from "./api";
import { store, type Labels } from "./store";

// The actor who is in — the name only. What the page draws of a person is the
// name; the role, the ceiling and every screen that moves them are item 11's.
export interface Actor {
  name: string;
}

// What `/api/session` answers. The names are the server's (`entry_payload`) and
// a name that drifts between the two sides is INVISIBLE — the page reads
// `undefined` and the entrance comes out without a word in it.
export interface Entry {
  auth: boolean;
  first: boolean;
  folder: boolean;
  actor: Actor | null;
  lang: string;
  labels: Record<string, Labels>;
}

export const session = reactive({
  ready: false, // has the server answered yet?
  auth: false, // does this folder ask anybody to enter?
  // A PRIMEIRA SUBIDA (TASK-176, fatia 3/3): a pasta sem administrador nenhum.
  // Não é "não estou dentro" — é "não há com quem entrar ainda", e a tela que
  // responde a isso é a que CRIA o primeiro, e não a que pede a credencial de
  // alguém que não existe.
  first: false,
  // A PASTA QUE AINDA NÃO EXISTE (TASK-169, fatia 2/3): um passo ANTES da
  // primeira subida — sem pasta não há admin, não há tabela, não há nada. O
  // modo local é o único que chega aqui sem ter perguntado nada antes (ele
  // não pede terminal), e a tela que responde é a que CONFIRMA a pasta.
  folder: false,
  actor: null as Actor | null,
});

// Whether the shell may be drawn. A folder that asks nothing draws it always —
// §3: with no authentication configured, AT listens on loopback and asks
// nothing, and an entrance there would be a door nobody could open. A folder
// that asks draws it once somebody is past the door.
//
// **E a primeira subida NÃO desenha a casca, mesmo quando não pergunta nada.**
// Ela é o caso em que `auth` é falso e ainda assim não há sessão a abrir: sem
// administrador nenhum não há tabela a mostrar, e a casca desenhada ali seria
// uma tela de trabalho vazia no lugar do formulário que a preenche.
export const signedIn = computed(
  () =>
    session.ready &&
    !session.folder &&
    !session.first &&
    (!session.auth || session.actor !== null),
);

// The answer of the door, wherever it came from: the first load, or the moment
// after a credential was proved.
export function applyEntry(entry: Entry): void {
  session.auth = entry.auth === true;
  session.first = entry.first === true;
  session.folder = entry.folder === true;
  session.actor = entry.actor || null;
  if (entry.lang) store.lang = entry.lang;
  // The words enter the SAME store every other screen reads, and in the same
  // shape (`{key: {lang: word}}`): the entrance draws with `word()` like
  // everything else, and invents none of them.
  if (entry.labels) store.labels = entry.labels;
  session.ready = true;
}

// The question. It is asked before the state, because the state is refused to
// whoever is not in.
export async function enter(): Promise<void> {
  applyEntry(await api<Entry>("/api/session"));
}

// The credential, proved. The refusal comes back as the SERVER's sentence —
// `post` throws what the answer carried — and the page prints it as it stands.
export async function signIn(name: string, credential: string): Promise<void> {
  await post("/api/session", { name, credential });
  await enter();
}

// A PRIMEIRA SUBIDA: o nome e a Chave Principal, e a porta que os transforma no
// primeiro administrador (TASK-176, fatia 3/3; `/api/first`, acima do portão
// como a entrada). As duas leituras vão juntas porque a Chave não se recupera —
// é a mesma regra do terminal, e quem a recusa é o servidor, com a string do
// `at-cli admin`.
//
// `enter()` no fim, e não um `applyEntry` daqui: quem acabou de criar o
// administrador entra com ele, e o servidor já abriu a sessão na resposta — o
// `Set-Cookie` veio nela. A pergunta seguinte é o mesmo caminho de sempre.
export async function firstRun(
  name: string,
  credential: string,
  again: string,
): Promise<void> {
  await post("/api/first", { name, credential, again });
  await enter();
}

// A PASTA (TASK-169, fatia 2/3): confirmando, o servidor cria o Working
// Folder e `enter()` lê o que vem depois — `first` ou já a casca, a mesma
// estrada que já existia. Recusando, não há nada mais a perguntar: o
// servidor marca a recusa (é o que fecha a janela do outro lado) e esta tela
// não chama `enter()` de novo — não há pasta para a próxima pergunta ler.
export async function confirmFolder(confirm: boolean): Promise<void> {
  await post("/api/folder", { confirm });
  if (confirm) await enter();
}

// THE SESSION IS GONE. A 401 under a running page means the server was
// restarted under it, and what it costs is the entrance back — never a page
// full of "401 Unauthorized". `api.ts` calls this through `whenRefused`.
export function lost(): void {
  session.actor = null;
}

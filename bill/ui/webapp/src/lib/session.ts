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
  actor: Actor | null;
  lang: string;
  labels: Record<string, Labels>;
}

export const session = reactive({
  ready: false, // has the server answered yet?
  auth: false, // does this folder ask anybody to enter?
  actor: null as Actor | null,
});

// Whether the shell may be drawn. A folder that asks nothing draws it always —
// §3: with no authentication configured, Bill listens on loopback and asks
// nothing, and an entrance there would be a door nobody could open. A folder
// that asks draws it once somebody is past the door.
export const signedIn = computed(
  () => session.ready && (!session.auth || session.actor !== null),
);

// The answer of the door, wherever it came from: the first load, or the moment
// after a credential was proved.
export function applyEntry(entry: Entry): void {
  session.auth = entry.auth === true;
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

// THE SESSION IS GONE. A 401 under a running page means the server was
// restarted under it, and what it costs is the entrance back — never a page
// full of "401 Unauthorized". `api.ts` calls this through `whenRefused`.
export function lost(): void {
  session.actor = null;
}

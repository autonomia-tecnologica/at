// chat — the conversation, which the chat and the balloon SHARE (TASK-183).
//
// It KEEPS what was said — the sentence, the proposal it became, the answer, and
// the question when the sentence was ambiguous — so that a person can come back
// to it, from either shape: two lists of the same conversation would be two
// truths the moment a person asked something in one and opened the other next.
//
// It lives HERE and not inside either view or component because both come and
// go well before a conversation ends: a view is unmounted the moment another
// one opens, and the balloon's own window closes back into a bubble on a click
// — keeping the list in either would keep it only as long as that one shape
// stayed on screen.
//
// It PERSISTS, in the browser's own storage: a conversation a reload forgot
// would be a history in name only. `SEND` is the one door either shape walks to
// ask something — it is what tells a CHATBOT action (clearing the history
// itself) apart from a SENTENCE the engine reads, before either one leaves the
// browser; the engine never sees the first kind, and `ask()` (`lib/ask.ts`) is
// never asked to make sense of it.

import { reactive } from "vue";
import { ask, type Turn } from "./ask";
import { word } from "./store";

const KEY = "at.chat.turns";

function loaded(): Turn[] {
  try {
    const raw = localStorage.getItem(KEY);
    const parsed = raw ? JSON.parse(raw) : [];
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

export const chatState = reactive({ turns: loaded() as Turn[] });

// THE TURN A YES OR A NO WOULD ANSWER, and THE SENTENCE A BARE VERB LEFT
// OPEN — never a field ON a turn, and never written back into one: a turn,
// once remembered, is NEVER CHANGED again (the person's own rule — every
// message is part of the record, the same way a line in `audit` is). This is
// bookkeeping ABOUT the record, kept beside it, and a reload starts it fresh
// from whatever the LAST turn already says — never from a flag some earlier
// turn was made to carry.
let open: Turn | null = lastOf(chatState.turns, turn => !!turn.confirm);
let openVerb: string | null = lastOf(chatState.turns, turn => !!turn.awaiting)?.sentence ?? null;

function lastOf(turns: Turn[], matches: (turn: Turn) => boolean): Turn | null {
  const last = turns[turns.length - 1];
  return last && matches(last) ? last : null;
}

function persist(): void {
  try {
    localStorage.setItem(KEY, JSON.stringify(chatState.turns));
  } catch {
    // A browser that refuses storage (private mode, quota) still gets the
    // conversation for as long as the tab stays open — losing persistence is
    // not losing the chat already on screen.
  }
}

// The one who writes is whoever ASKED: the view hands the turn back so the
// conversation keeps the order things happened in. APPENDED, always — nothing
// this module ever hands back here is a turn already in `chatState.turns`.
export function remember(turn: Turn): void {
  if (!turn.at) turn.at = new Date().toISOString();
  chatState.turns.push(turn);
  open = turn.confirm ? turn : null;
  openVerb = turn.awaiting ? turn.sentence : null;
  persist();
}

export function forget(): void {
  chatState.turns.splice(0, chatState.turns.length);
  open = null;
  openVerb = null;
  persist();
}

// THE CHATBOT'S OWN ACTIONS, never the engine's: a sentence this matches is
// answered HERE, with no request leaving the browser — the same reason `nlu`
// never sees a password typed at the wrong field (§3, a wall the sentence never
// reaches). Tolerant of accent, case and the small grammar a person actually
// types, the way the engine's own matcher is — but this vocabulary is the
// chat's, not a table's, so it stays here and not in `at/nlu`.
const CLEAR_VERBS = ["limpar", "limpa", "apagar", "apaga", "zerar", "zera", "clear"];
const CLEAR_NOUNS = ["chat", "sessao", "conversa", "historico", "session", "conversation", "history"];
const CLEAR_SKIP = new Set(["o", "a", "os", "as", "esse", "essa", "este", "esta", "meu", "minha", "the", "this", "my"]);

function folded(text: string): string {
  return text.normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase();
}

function isClear(text: string): boolean {
  const words = folded(text).trim().replace(/[.!?]+$/, "").split(/\s+/).filter(Boolean);
  if (!words.length) return false;
  const [verb, ...rest] = words;
  if (!CLEAR_VERBS.includes(verb)) return false;
  // A VERB WITH NO OBJECT NAMES THE CHAT: the one thing a person asking a chat
  // to "limpar" could mean is the chat itself — the object is the box they are
  // typing into, not a guess over what else "limpar" could ever name.
  if (!rest.length) return true;
  const noun = rest.filter(w => !CLEAR_SKIP.has(w)).pop();
  return !!noun && CLEAR_NOUNS.some(candidate => noun === candidate || noun === candidate + "s");
}

function refusal(sentence: string, message: string): Turn {
  return {
    sentence, kind: "refused", proposal: null, text: message,
    assist: false, confirm: null, table: null,
  };
}

// A CAUTIOUS QUESTION'S YES AND NO — a chat is typed answers, never clicked
// ones (the person's own words): the pending turn is resolved by the NEXT
// thing typed, read against this small, tolerant vocabulary, before that text
// ever has a chance of being asked to the engine as a sentence of its own.
const YES_WORDS = ["sim", "s", "yes", "y", "ok", "okay", "certo", "isso", "exato", "confirma", "confirmo", "pode"];
const NO_WORDS = ["nao", "n", "no", "negativo", "cancela", "cancelar", "errado", "deny"];

function folds(text: string): string {
  return folded(text).trim().replace(/[.!?]+$/, "");
}

// "Sim" and "não" are their OWN new turns, said the way anything else typed
// into the box is — `remember` is the only way either reaches the log, and it
// only ever APPENDS. What a "sim" asks the engine is the REWRITTEN sentence
// the open question already carried; what the person is shown having SAID is
// "sim" itself, never that rewritten sentence standing in for it.
async function confirmOpen(said: string, rewritten: string): Promise<void> {
  try {
    const result = await ask(rewritten, undefined, true);
    remember({ ...result, sentence: said });
  } catch (err) {
    remember(refusal(said, (err as Error).message));
  }
}

function denyOpen(said: string): void {
  remember({
    sentence: said, kind: "refused", proposal: null, text: word("assist_denied"),
    assist: false, confirm: null, table: null,
  });
}

// THE ONE DOOR a sentence walks, from either shape of the box: a yes or a no
// for a question still open is read HERE and never reaches the engine; a
// chatbot action (clearing the history itself) is read the same way; anything
// else is `ask()`'s, same as before. `mainKey`/`confirmed` are a retry and the
// REWRITTEN sentence a "sim" already resolved on its own — never typed by a
// person — so neither is checked against an open question or `isClear`.
export async function send(
  sentence: string, mainKey?: string, confirmed?: boolean,
): Promise<void> {
  const text = sentence.trim();
  if (!text) return;
  if (!mainKey && !confirmed && open) {
    const said = folds(text);
    if (YES_WORDS.includes(said)) {
      await confirmOpen(text, open.confirm as string);
      return;
    }
    if (NO_WORDS.includes(said)) {
      denyOpen(text);
      return;
    }
    // Neither a yes nor a no: the open question stays exactly as it was,
    // read and never answered, and what was just typed is asked as its OWN
    // sentence — the same thing a person who changed the subject means. The
    // next `remember` (below, or `isClear`'s own) is what retires `open`.
  }
  if (!mainKey && !confirmed && isClear(text)) {
    forget();
    remember({
      sentence: text, kind: "answer", proposal: null, text: word("chat_cleared"),
      assist: false, confirm: null, table: null,
    });
    return;
  }
  // A BARE VERB LEFT OPEN — "listar", alone — is completed by whatever is
  // typed next: "tarefas" on its own names nothing (there is no verb in it),
  // but read AS THE OBJECT of the verb still open, it is "listar tarefas".
  // One try, shown as it comes back — success or its own refusal — and
  // `remember` (below) is what retires `openVerb` either way.
  if (!mainKey && !confirmed && openVerb) {
    try {
      const result = await ask(`${openVerb} ${text}`, undefined, false);
      remember({ ...result, sentence: text });
    } catch (err) {
      remember(refusal(text, (err as Error).message));
    }
    return;
  }
  try {
    remember(await ask(text, mainKey, confirmed));
  } catch (err) {
    remember(refusal(text, (err as Error).message));
  }
}

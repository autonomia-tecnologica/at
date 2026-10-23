// ask — the interpreter's door, from the page's side: one sentence, and whatever
// the engine said about it.
//
// The page owns NO rule here: the sentence goes to the server, which walks the
// same road the `cli` walks (`nlu.propose` for the reading and the table engine
// for the writing), and what comes back is what a person reads — the proposal in
// the engine's words, the answer after it, the question when the sentence was
// ambiguous, or the reason when it was not read at all. The page writes none of
// those sentences; it puts them where they are read.
//
// The two shapes of the box (the chat and the balloon) call this one door, which
// is what makes them ask the same thing and show the same thing.

import { post } from "./api";
import { poke } from "./views";

// `intent` is conversation (a greeting, thanks, help): a line the chat SAYS, not
// an error and not an answer to a record.
export type Kind = "answer" | "question" | "refused" | "intent";

// ONE ROW as a card — the table's main fields, already written out in the
// active language, and the id that makes the card a door to the record's page.
// It is the shape the server hands over (`at.ui.ask.card`), not the full record
// (`RecordRow`): there is no editor here, and no field the table does not
// declare as its `columns`.
export interface RecordCardField {
  name: string;
  label: string;
  value: string;
}

export interface RecordCard {
  table: string;   // the table the row IS — the key a link opens it by
  entity: string;  // its display name, for the card's own heading
  id: number;
  shown_id: string; // `TASK-3`, the way the engine names it
  title: string;
  fields: RecordCardField[];
}

export interface Turn {
  sentence: string; // what was asked
  kind: Kind; // which of the three came back
  proposal: string | null; // the proposal, in the engine's words — when there was one
  text: string; // the answer, the question, or the refusal
  // TASK-180, fatia 3/3: whether the assist could still answer THIS refusal for
  // a Main Key typed now — `false` for every `answer` and `question`, and for a
  // `refused` the retry already tried or the role may not spend.
  assist: boolean;
  // TASK-183: the rewritten sentence a "Confirmar" resubmits, when this turn is
  // the assist's own CONFIRM question — `null` for every `answer` and for the
  // grammar's ordinary ambiguity questions, which have none to offer.
  confirm: string | null;
  // A `list`'s own header and rows — `null` for every other answer, and for a
  // `list` that found nothing, and for a `list` that filled `bullets` (below)
  // instead. When it carries something the turn draws an actual table instead
  // of `text`'s ASCII, which keeps the same words.
  table: { header: string[]; rows: string[][] } | null;
  // A `list`'s OTHER shape — one line per row, its title and nothing beside
  // it — the default a sentence with no "tabela"/"table" in it gets (the
  // person's own convention, 03/10/2026). Mutually exclusive with `table`.
  // Optional/absent (not just `null`) on a turn this module builds itself
  // (a chatbot action, a refusal with no server round trip).
  bullets?: string[] | null;
  // The action a bare verb named with nothing to act on ("listar", alone) —
  // `null` for every answer that is not that one refusal. `lib/chat.ts` reads
  // it to complete the sentence from whatever is typed next, the way "sim"
  // completes an open CONFIRM question.
  awaiting?: string | null;
  // THE OBJECT the answer was about, as a CARD (20/10/2026): `create`, `edit`,
  // `cancel`, `delete` and `view` answer with the row they touched, so the
  // conversation can show it whole instead of only naming it. `null` for a
  // `list` (its own `table`/`bullets` are the shape) and for every question
  // and refusal. The server composes it (`at.ui.ask.card`) — the page draws
  // the fields it was handed and invents none.
  record?: RecordCard | null;
  // WHAT A CONVERSATION SAYS BEFORE THE CARD — "Achei TASK-1 para você. É
  // este:" — also composed by the server, for the same reason every other
  // sentence here is (§3). `null` whenever `record` is.
  lead?: string | null;
  // For kind "intent": which intent and subintent produced `text`.
  intent?: string | null;
  subintent?: string | null;
  // When this turn was ADDED to the conversation, stamped by `chat.ts`'s
  // `remember` and read nowhere else — the engine answers no clock here, and a
  // chat that showed none would be the one place a person cannot tell two
  // turns apart. Optional here because `remember` is what fills it; nothing
  // that BUILDS a turn needs to know the time it is kept at.
  at?: string;
}

export async function ask(
  sentence: string, mainKey?: string, confirmed?: boolean,
): Promise<Turn> {
  const body: { text: string; main_key?: string; confirmed?: boolean } = { text: sentence };
  // Sent once, with THIS request, and kept nowhere on the page: a retry types
  // it again, the same way `at-cli assist` reads it fresh every time.
  if (mainKey) body.main_key = mainKey;
  // A frase canônica que o "Confirmar" reenvia: com a marca, o servidor a lê
  // SÓ com o matcher — o Jev não é re-consultado, e o confirm não entra em loop.
  if (confirmed) body.confirmed = true;
  const data = await post<
    {
      kind: Kind; proposal: string | null; text: string; assist?: boolean;
      confirm?: string | null; table?: { header: string[]; rows: string[][] } | null;
      bullets?: string[] | null; awaiting?: string | null;
      record?: RecordCard | null; lead?: string | null;
      intent?: string | null; subintent?: string | null;
    }
  >("/api/ask", body);
  // A proposal may have WRITTEN: the same page is redrawn where it stands, exactly
  // as the pick of a field does. A question and a refusal wrote nothing, and
  // redrawing for them would be work nobody asked for.
  if (data.kind === "answer") poke();
  return {
    sentence, kind: data.kind, proposal: data.proposal ?? null, text: data.text,
    assist: !!data.assist, confirm: data.confirm ?? null, table: data.table ?? null,
    bullets: data.bullets ?? null, awaiting: data.awaiting ?? null,
    record: data.record ?? null, lead: data.lead ?? null,
    intent: data.intent ?? null, subintent: data.subintent ?? null,
  };
}

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

export type Kind = "answer" | "question" | "refused";

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
}

export async function ask(sentence: string, mainKey?: string): Promise<Turn> {
  const body: { text: string; main_key?: string } = { text: sentence };
  // Sent once, with THIS request, and kept nowhere on the page: a retry types
  // it again, the same way `at-cli assist` reads it fresh every time.
  if (mainKey) body.main_key = mainKey;
  const data = await post<
    {
      kind: Kind; proposal: string | null; text: string; assist?: boolean;
      confirm?: string | null;
    }
  >("/api/ask", body);
  // A proposal may have WRITTEN: the same page is redrawn where it stands, exactly
  // as the pick of a field does. A question and a refusal wrote nothing, and
  // redrawing for them would be work nobody asked for.
  if (data.kind === "answer") poke();
  return {
    sentence, kind: data.kind, proposal: data.proposal ?? null, text: data.text,
    assist: !!data.assist, confirm: data.confirm ?? null,
  };
}

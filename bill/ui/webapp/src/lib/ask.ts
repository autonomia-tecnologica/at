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
}

export async function ask(sentence: string): Promise<Turn> {
  const data = await post<{ kind: Kind; proposal: string | null; text: string }>(
    "/api/ask", { text: sentence },
  );
  // A proposal may have WRITTEN: the same page is redrawn where it stands, exactly
  // as the pick of a field does. A question and a refusal wrote nothing, and
  // redrawing for them would be work nobody asked for.
  if (data.kind === "answer") poke();
  return { sentence, kind: data.kind, proposal: data.proposal ?? null, text: data.text };
}

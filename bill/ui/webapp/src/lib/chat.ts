// chat — the conversation, which is what the chat has and the balloon does not.
//
// The balloon carries the EFFECT of one sentence and forgets the last one; the
// chat KEEPS what was said — the sentence, the proposal it became, the answer,
// and the question when the sentence was ambiguous — so that a person can come
// back to it.
//
// It lives HERE and not inside the view because a view is unmounted the moment
// another one opens: keeping it in the component would keep it exactly until the
// person looked at something else. What a reload does to it is forget it — a
// conversation is neither the store's data nor a preference of the browser, and
// the page has no third place to put it. What the ADDRESS guarantees is the view:
// a reload lands back in the chat.

import { reactive } from "vue";
import type { Turn } from "./ask";

export const chatState = reactive({ turns: [] as Turn[] });

// The one who writes is whoever ASKED: the view hands the turn back so the
// conversation keeps the order things happened in.
export function remember(turn: Turn): void {
  chatState.turns.push(turn);
}

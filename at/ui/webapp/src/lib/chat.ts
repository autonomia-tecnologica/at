// chat — the conversation, which the chat and the balloon now SHARE (TASK-183).
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
// stayed on screen. What a reload does to it is forget it — a conversation is
// neither the store's data nor a preference of the browser, and the page has no
// third place to put it. What the ADDRESS guarantees is the view: a reload
// lands back in the chat, with the same history the balloon would have shown.

import { reactive } from "vue";
import type { Turn } from "./ask";

export const chatState = reactive({ turns: [] as Turn[] });

// The one who writes is whoever ASKED: the view hands the turn back so the
// conversation keeps the order things happened in.
export function remember(turn: Turn): void {
  chatState.turns.push(turn);
}

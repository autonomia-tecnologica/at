"""The `nlu` layer: a sentence becomes one proposal, and nothing else (§4).

It is a **resource, not a surface**: the WebApp and the `cli` reach it, the actor
is the person and the via is `nlu`. Inside it, the glossary's three names hold —
`nlu` is this layer, the **interpreter** is whoever works in it, and the
**vocabulary** is the dictionary it consults per language. The vocabulary is data
and lands in slice 5; the grammar, which is code and lives one module per
language, is what exists here.

What the layer answers is a **reading**: a value, a residue, a question, or a
refusal (§4, and the item's own rule — what does not resolve is residue, never a
guess). It does not write, does not decide and has no ceiling of its own.

Two doors open into it, and they are the two halves of the language: `resolve`
reads a date, a time or a number in the active language's grammar, and
`canonical` names the machine word a person's word means, however it was typed.
"""

from bill.nlu.interpreter import KINDS, resolve
from bill.nlu.normalizer import canonical
from bill.nlu.reading import Reading, Question, Refused, Residue, Value

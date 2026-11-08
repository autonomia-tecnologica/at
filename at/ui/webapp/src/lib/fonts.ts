// fonts — the seven self-hosted faces, and the one promise that says they are
// all actually IN, pixels and all.
//
// `base.css` already marks every one of them `font-display: block` — the
// browser holds the glyph invisible instead of painting it in a fallback and
// swapping later — but `block` is a promise PER FACE, and the seven faces are
// SEVEN SEPARATE FILES (`vendor/manifest.json`): a plain cell and a status pill
// often wear DIFFERENT WEIGHTS of the same family, and nothing says they
// finish downloading together. A reload that reveals once the data is ready
// can still show a table whose badges read fine and whose plain text is
// blank for a beat longer — the same flash the boot gate exists to kill, one
// layer lower, and font-display alone does not reach it.
//
// So the boot ASKS for every face BY NAME, with the Font Loading API, and
// waits on the answer — `document.fonts.load` triggers the same fetch a cell
// using that weight would, and resolves once it has actually landed. Asking
// for a weight the active theme never wears costs a few KB of a file already
// pinned and served from this origin; asking for only SOME of them would mean
// knowing which theme is about to paint before the gate that decides it has
// even run.
const FACES: ReadonlyArray<readonly [string, number]> = [
  ["Nunito Sans", 400],
  ["Nunito Sans", 600],
  ["Nunito Sans", 700],
  ["Nunito Sans", 800],
  ["UnifrakturMaguntia", 400],
  ["Silkscreen", 400],
  ["Silkscreen", 700],
];

export function ensureFonts(): Promise<void> {
  if (!("fonts" in document)) return Promise.resolve();
  return Promise.all(
    FACES.map(([family, weight]) =>
      document.fonts.load(`${weight} 16px "${family}"`).catch(() => undefined),
    ),
  ).then(() => undefined);
}

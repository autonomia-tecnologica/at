// boot — the step BEFORE the first paint, and the only classic script here.
//
// The theme is a preference of THIS browser, and the page wears it by pointing
// the `link` at an id — and at a SIDE (`&dark`), because "which theme" and "which
// side of it" are two choices. But the page is served fresh on every request: on
// a reload the `link` arrives as the server's default (`/theme.css`) and the
// choices only enter when the module graph runs — AFTER the first paint. So the
// page paints one theme and swaps to another: the flash on Ctrl-R.
//
// This file is a CLASSIC script, and that is the whole point of it: a
// `type="module"` is always deferred, so it runs after the document is parsed —
// too late for the paint. A classic script BLOCKS the parser, and that is the
// only thing that runs early enough. It is the ONE exception the rule carries,
// and it carries NO behaviour: it reads the
// choices, moves the `link` and stops. Everything the page DOES is still the
// module graph under `js/`.
//
// The keys, the three states and the URL shape are the ones `theme.js` owns, and
// the key and the class are the ones `motion.js` owns — nothing here may drift
// from them (a test keeps each pair in agreement). An id that names no theme is
// NOT an error: the server answers an id it does not know with the default,
// which is the same theme `theme.js` resolves.
try {
  const params = [];
  const saved = JSON.parse(localStorage.getItem("at.theme"));
  const id = saved && typeof saved.id === "string" ? saved.id : "";
  if (id) params.push("theme=" + encodeURIComponent(id));
  // THE SIDE: four states, and the factory one is the SYSTEM. The question asked
  // here is the same one `theme.js` will ask after the paint — the choice is a
  // single one, read twice, and that is why the key, the states and the name of
  // the key in the URL cannot diverge between the two.
  const side = JSON.parse(localStorage.getItem("at.dark"));
  const raw = side && typeof side.state === "string" ? side.state : "";
  // A state that is NONE of the four counts as "system" — exactly as in
  // `theme.js`, and that is why the list shows up here. A spoiled value cannot
  // make the boot answer one thing and the page another: between the two lives the
  // flash, which is precisely what this file exists to avoid.
  const state = ["system", "theme", "light", "dark"].includes(raw) ? raw : "system";
  // `theme` IS ANSWERED FROM THE CACHE, and it is the only state this file cannot
  // work out by itself: which side a theme wears is declared in the registry, the
  // registry arrives with the API — after the paint. So `theme.js` writes the
  // answer down when it knows it (`side` beside the state) and this reads it.
  // WITH NO CACHED ANSWER the system answers, which is the state this file would
  // have fallen back to anyway.
  const dark = state === "dark" ||
    (state === "theme" && side && side.side === "dark") ||
    (state === "system" && matchMedia("(prefers-color-scheme: dark)").matches);
  if (dark) params.push("dark");
  if (params.length) {
    document.getElementById("theme").setAttribute(
      "href", "/theme.css?" + params.join("&"));
  }
  // The collapsed PANEL enters through the SAME door: the rail is what the page
  // wears, and it has to be on before the paint — otherwise the sidebar shows up
  // whole and collapses later, which is the usual flash. The key and the classes
  // are `nav.js`'s, and the ruler holds the pair. With no saved choice no class is
  // set on purpose: the empty hands the decision back to the width (base.css §5).
  const nav = JSON.parse(localStorage.getItem("at.nav"));
  if (nav && nav.state === "rail") {
    document.documentElement.classList.add("nav-rail");
  } else if (nav && nav.state === "open") {
    document.documentElement.classList.add("nav-open");
  }
  // MOTION enters through the same door and the same reason: the choice decides
  // what the page WEARS, so it has to be on before the page is painted. The class
  // is the one `base.css` reads; the name is `motion.js`'s.
  const motion = JSON.parse(localStorage.getItem("at.motion"));
  if (motion && motion.on === false) {
    document.documentElement.classList.add("no-motion");
  }
} catch (error) {
  // No localStorage (or one that refuses): the `link` stays as it arrived and
  // the server's default answers — never an error, only the default theme. And
  // the movement stays ON, which is the default too.
}

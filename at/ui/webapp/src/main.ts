// main — the entry point of the Vue app: it registers the pages that are not a
// table's table, and mounts the shell.
//
// The app is served by the SAME server as the AT, and that is what lets it wear
// the look without defining any: `/theme.css`, `/base.css` and `/js/boot.js` are
// of the same origin. `boot.js` has already run before this line — it is classic
// and lives in the `head` —, so the theme is already applied when the app mounts.

import { createApp } from "vue";
import App from "./App.vue";
import "./styles/app.css";
import { registerView, registerType } from "./lib/views";
import SettingsView from "./views/SettingsView.vue";
import ChatView from "./views/ChatView.vue";
import ProjectView from "./views/ProjectView.vue";
import OrphansView from "./views/OrphansView.vue";
import FileView from "./views/FileView.vue";
import ActorView from "./views/ActorView.vue";
import RoleView from "./views/RoleView.vue";

// The pages that are a SINGLE key (no rest): the chat, Settings and the "no
// project". The chat has an address like every other view, which is what makes a
// reload land back in the conversation.
registerView("chat", ChatView);
registerView("settings", SettingsView);
registerView("orphans", OrphansView);
// PEOPLE IS NOT A VIEW OF ITS OWN ANY MORE (2026-09-27): the actors and the
// roles, together, are a SECTION of Configurações now (`SettingsView.vue`
// embeds `PeopleView.vue` directly) — who may act is an adjustment of the
// folder, and this is the same door that already holds the theme and the
// language. Each row still opens its own screen (`/actor/3`, `/role/2`),
// through the two registrations below.
// THE TWO SYSTEM TABLES THAT ARE MORE THAN A TABLE (item 11). A role is a SET,
// and the closed list it is written against is drawn as checks; an actor that is
// a machine carries a credential AT MINTS. Both keep the table's own address —
// `/actor`, `/actor/3` — because the page is the SAME view with a record open,
// and the frame is what says which (`nav.current.id`).
registerView("actor", ActorView);
registerView("role", RoleView);
// The ones that name a RECORD: the rest of the key is the id or the path.
registerView("project:", ProjectView, "id");
registerView("file:", FileView, "path");

// And a table that declares the TYPE `project` is a PAGE, not a record in a
// table: it is through this map that a reference to a project opens the project.
registerType("project", "project:");

createApp(App).mount("#app");

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
// THE FILA, wired in from the module that owns it (TASK-162, fatia 2/2) — its
// own `online` listener and its first `sync()` attempt fire the moment this
// file runs, which is the earliest a queued edit from a past session can
// leave.
import "./lib/offline";
// A ESCUTA DO VIGIA (TASK-128, fatia 2/3) — abre a conexão `/api/events` e
// poka a página a cada aviso; o mesmo motivo do `offline` acima, o quanto
// antes este arquivo roda é o quanto antes uma escrita de fora da aba chega.
import "./lib/events";
// A INSCRIÇÃO NO PUSH (Web Push) — a notificação do PWA, que substituiu o ntfy.
import { register as registerPush } from "./lib/push";
import { registerView, registerType, TASKS_KEY, FILES_KEY, TABLES_KEY, TABLES_TASK_KEY, REMINDERS_KEY, NOTES_KEY, BOARD_KEY, WRITE_PREFIX } from "./lib/views";
import TasksView from "./views/TasksView.vue";
import FilesView from "./views/FilesView.vue";
import TablesView from "./views/TablesView.vue";
import RemindersView from "./views/RemindersView.vue";
import NotesView from "./views/NotesView.vue";
import BoardView from "./views/BoardView.vue";
import SettingsView from "./views/SettingsView.vue";
import ChatView from "./views/ChatView.vue";
import ProjectView from "./views/ProjectView.vue";
import OrphansView from "./views/OrphansView.vue";
import FileView from "./views/FileView.vue";
import WriteView from "./views/WriteView.vue";
import ActorView from "./views/ActorView.vue";
import RoleView from "./views/RoleView.vue";
import TablesTaskView from "./views/TablesTaskView.vue";

// The pages that are a SINGLE key (no rest): the section screens, the chat,
// Settings and the "no project". The chat has an address like every other view,
// which is what makes a reload land back in the conversation.
//
// THE SECTION SCREEN REGISTERS LIKE THE OTHERS, which is the point of the
// registry: it is a page with an address (`/tasks`), a row in the panel and a
// step back like any other, and nothing in the shell had to learn that it
// exists. Its key is the fold's own id, so a section's address is the section's
// name — and FILES, when it has a screen, is one line here.
registerView(TASKS_KEY, TasksView);
// THE OTHER TWO SECTIONS, one line each — which is the whole point of the key
// being the fold's id.
registerView(FILES_KEY, FilesView);
// O COFRE NÃO TEM TELA PRÓPRIA (2026-10-05): a seção era uma página só com a
// mesma árvore do painel, e "sem necessidade de existir". O que ele oferece —
// o leitor de um arquivo selado — abre por cima de QUALQUER tela
// (`StrongboxViewer`), então a seção é só a dobra que cresce no painel.
registerView(TABLES_KEY, TablesView);
// A SEGUNDA PORTA DA TABELA `task` (TASK-175): endereço próprio
// (`/tables/task`), que o card da seção Tabelas abre em vez de `/task` — é
// essa diferença de endereço que diz ao `KindView` que aqui o modo é
// planilha, e não o popup que `/task` continua abrindo pela árvore.
registerView(TABLES_TASK_KEY, TablesTaskView);
// A SEÇÃO DE LEMBRETES (TASK-164): a chave é o nome dela, e o endereço é
// `/reminders`. A seção é uma LINHA no painel e não uma dobra, mas a tela é
// dela — o registro não sabe a diferença, e é isso que o registro é para.
registerView(REMINDERS_KEY, RemindersView);
// A SEÇÃO DE NOTAS (TASK-198): a chave é o nome dela, e o endereço é `/notes`.
// A tela é a da tabela `note` — a seção não abre uma porta nova, ela mostra a
// porta que já existe.
registerView(NOTES_KEY, NotesView);
// THE BOARD: not a section's own fold, but the door right after ORPHANS in the
// same tree (`Sidebar.vue`) — a view like any other, with an address of its
// own (`/board`).
registerView(BOARD_KEY, BoardView);
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
// THE WRITE TAB (2026-10-05): the same REST-of-the-key shape as `file:`'s own
// (a path, not an id) — `App.vue` draws it alone, with no shell around it.
registerView(WRITE_PREFIX, WriteView, "path");

// And a table that declares the TYPE `project` is a PAGE, not a record in a
// table: it is through this map that a reference to a project opens the project.
registerType("project", "project:");

createApp(App).mount("#app");

// THE SHELL'S OFFLINE MOUTH (TASK-162, fatia 2/2). Registered from the root
// (`/sw.js`, not `/js/sw.js`) so its scope is the whole origin — the document
// included — and not just the one folder its file happens to sit in
// (`assets/js/sw.js`'s own comment says why). A browser with no Service
// Worker at all (an old one, a locked-down one) is simply a browser this file
// changes nothing for: every read and write still reaches the network the way
// it always did.
if ("serviceWorker" in navigator) {
  navigator.serviceWorker.register("/sw.js");
  // A inscrição no push, REAFIRMADA aqui quando a permissão já foi dada numa
  // visita anterior. Uma permissão que ainda não existe NÃO é pedida no load:
  // a pergunta do navegador exige um gesto, e quem o tem é o botão das
  // Configurações (`SettingsView.vue`).
  registerPush();
}

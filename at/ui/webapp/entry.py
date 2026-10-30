"""What the page is told before and after the entrance: the word lists and the
payloads built from them (`entry_payload`, `state_payload`, `catalogue_payload`),
plus the two small request helpers that shape an answer (`_worded`) and a
`declare` body (`_declare_args`).

Moved out of `app.py` (B-6) without a change of behaviour. Nothing here knows the
`Handler` or the server: every function reads the engine and the catalog and
returns a dict. `app.py` imports the names back.
"""

from __future__ import annotations

from at import __version__, i18n, nlu
from at.core import (
    actions_audit,
    actors,
    assist,
    boot,
    paths,
    permissions,
    risk,
    tables,
    versioning,
)
from at.data import schema
from at.ui.webapp import session
from at.ui.webapp.look import active_theme, theme_label, theme_rows, theme_sides

# The entrance's own words (§3, Forms local). They are a list of their own
# because they travel in a payload of their own: the page that draws the
# entrance has no session to read `/api/state` with.
SESSION_WORDS = (
    "session_hint", "session_name", "session_credential", "session_enter",
    "session_refused", "session_needed",
    # A PRIMEIRA SUBIDA é a outra tela que a entrada desenha (TASK-176, fatia
    # 3/3), e ela é irmã da entrada e não da casca: quem chega numa pasta sem
    # administrador vê o formulário que o cria, e o vê ANTES de ter sessão —
    # então as palavras que ele desenha têm de viajar com a entrada, e o
    # `create` do botão é uma delas (o mesmo que a tela de criar papel usa).
    "first_hint", "create",
)

# And what the entrance is handed: its words, plus the two the shell already
# uses. `brand` is the card's heading — the name of the thing being entered is
# the heading a person expects over a door, and it is written once for the whole
# product. `error` is there because the entrance can fail too: a request that
# never arrived is said in the page's own language, and a word missing on the
# FIRST screen AT ever shows would be the one nobody could miss.
ENTRY_WORDS = ("brand", "error", *SESSION_WORDS)

# The words the PAGE reads. They come from the catalog like everything else —
# the page writes none of its own (§3) — and they travel in every language, so
# switching the language costs no request.
#
# The entrance's words are among them, and that is not duplication: a session
# that dies under a running page brings the entrance back (the page's own 401
# hook), and a `/api/state` that replaced the labels without them would draw a
# second entrance with no words in it.
PAGE_WORDS = (
    # The BRAND was missing from this list, and the defect was invisible because
    # the one screen that draws it did not exist yet: the entrance's heading is
    # the brand, and the second entrance — the one a dead session brings back —
    # came out with an empty one. The panel's `#brand` was drawing nothing all
    # along.
    "brand", "brand_name",
    "tasks", "files", "strongbox", "tables", "settings", "general", "appearance", "language",
    "dark_mode", "dark_system", "dark_light", "dark_dark",
    "motion", "density", "density_comfortable", "density_compact",
    "empty_orphans_title", "empty_orphans_text", "empty_project_title", "empty_project_text",
    "empty_reminders_title", "empty_reminders_text", "empty_notes_title", "empty_notes_text",
    "themes", "no_project", "all_tasks", "board", "new_task", "new_project", "delete_project",
    # A ÁRVORE DE PROJETOS, O CRUD (TASK-135): o subprojeto que `new_project`
    # não nomeia, o verbo genérico de renomear, o rótulo do campo de nome do
    # formulário inline, e a opção "sem pai" do seletor de mover.
    "new_subproject", "rename", "name", "no_parent",
    # A TELA DE LEMBRETES (TASK-164): a seção, as três faixas do que vem
    # (vencidos, hoje, em breve), o horizonte e o que ele esconde, o fechar de
    # uma linha, as duas metades, e o que uma pasta sem lembrete e um dia sem
    # aviso dizem.
    "reminders", "reminders_coming", "reminders_overdue", "reminders_today",
    "reminders_soon", "reminders_beyond", "reminders_days", "reminders_close",
    "reminders_rang", "reminders_none", "reminders_quiet",
    # A SEÇÃO DE NOTAS (TASK-198): a seção, o botão que nasce uma nota, e o que
    # uma pasta sem nota diz. E o "salvar" do formulário que edita uma linha —
    # a porta que faltava para um campo que não é escolha (TASK-198).
    "notes", "new_note", "notes_none", "save",
    # A BUSCA GLOBAL (B-21): o overlay aberto por `/`.
    "search", "search_placeholder", "search_none_title", "search_none_text",
    "search_start", "search_name", "search_line",
    "move_to_project", "records", "hidden", "no_records", "error", "filter",
    # O INTERVALO DE DATA do filtro (B-37): as duas pontas, "de" e "até".
    "date_from", "date_until",
    # THE SPECIMEN (`/design`): its own sentences, in both languages.
    "ds_theme", "ds_text_roles", "ds_type_scale", "ds_colour", "ds_buttons", "ds_inputs", "ds_chips",
    "ds_cards_table", "ds_overlays", "ds_empty", "ds_small", "ds_medium", "ds_large", "ds_quiet", "ds_ghost",
    "ds_danger", "ds_disabled", "ds_popover", "ds_dialog", "ds_toast", "ds_text", "ds_select", "ds_textarea",
    "ds_value", "ds_locked", "ds_lines", "ds_checked", "ds_unchecked", "ds_radio_on", "ds_radio_off",
    "ds_a_card", "ds_a_row", "ds_title", "ds_status", "ds_pop_text", "ds_ask", "ds_yes", "ds_no",
    "ds_toast_text", "ds_nothing", "ds_nothing_text", "ds_action", "ds_fox", "ds_primary", "ds_secondary",
    "ds_tertiary", "ds_display", "ds_page", "ds_body_large", "ds_body", "ds_body_small", "ds_caption",
    # THE FILA'S BADGE (TASK-162, fatia 2/2): whether this browser is online,
    # and how many edits are still waiting to leave it.
    "offline", "queued",
    # THE FILE TREE'S FIRST CONTEXT MENU (TASK-165, fatia 4/4): the two
    # actions and the toast that follows one.
    "convert_pdf", "convert_docx", "convert_toast",
    # THE FILE TREE'S OWN CRUD (TASK-120, fatia 5/7): create, over the two
    # shapes `Arquivos/` holds. `rename`/`delete`/`name`/`delete_confirm` are
    # already above, shared with the project tree and the table row.
    "new_file", "new_folder",
    # O navegador de Arquivos: o rótulo da contagem, a pasta vazia e o "subir".
    "items", "folder_empty", "folder_up",
    "columns", "refers", "panel", "collapse_menu", "expand_menu",
    # The context menu's own items (TASK-120, fatia 1): what the row's menu
    # offers when the engine says `edit` is legal.
    "edit",
    # TASK-122, fatia 3/7: the row menu's other two — a closing and a deletion,
    # each with the confirmation it owes before either reaches the server.
    "close", "close_confirm", "close_reason", "delete", "delete_confirm",
    # O RELÓGIO, FATIA 3/3: os dois atos próprios do `job` que o menu de
    # contexto passa a oferecer — declarar um job novo e desligar um que já
    # está `scheduled` — e as palavras do painel de declarar.
    "disable", "disable_confirm", "declare", "declare_table", "declare_act",
    "declare_when", "declare_id",
    "back", "confirm_cancel", "confirm_ok", "write", "saving",
    "saved", "save_failed", "chars", "words", "spell_none", "language_name", "language_flag",
    "ft_text", "ft_markdown", "ft_python", "ft_json", "ft_yaml", "ft_shell",
    "ft_dockerfile", "ft_binary", "ft_other",
    "bucket_code", "bucket_text", "bucket_data", "bucket_image", "bucket_other",
    # The interpreter's box, the switch that hides the balloon, and the ruler of
    # the demand filter (§4).
    "chat", "ask", "ask_hint", "proposal", "interpreter", "balloon", "balloon_close",
    "chat_cleared", "chat_thinking",
    # A ABERTURA DO CHAT E OS SEUS EXEMPLOS (20/10/2026): o que a conversa diz
    # quando ainda não há conversa, e as quatro frases que mostram o que ela
    # entende — clicáveis, porque um exemplo que se digita não ensina ninguém a
    # digitar. As frases moram no catálogo pelo motivo de sempre: a página
    # escreve nenhuma delas (§3), e cada idioma exemplifica no seu.
    "chat_hello", "chat_example",
    "chat_ex1", "chat_ex2", "chat_ex3", "chat_ex4",
    "risk", "risk_runs", "risk_waits", "risk_threshold", "risk_none",
    # The assist's own Control Panel section, and its one retry (TASK-180,
    # fatia 3/3): the switch, and the inline form a refusal offers when a Main
    # Key could still turn it into an answer.
    "assist", "assist_hint",
    "assist_key", "assist_retry",
    # The CONFIRM tier's own words (TASK-183): what a question offers instead
    # of the sentence it used to ask to be retyped.
    "assist_confirm", "assist_deny", "assist_denied",
    # NOTIFICAÇÕES (Web Push): o bloco das Configurações que pede a permissão
    # do navegador e inscreve o PWA — sem ntfy.
    "notifications", "notifications_hint", "notifications_on", "notifications_off",
    # A CREDENCIAL DO JEV, em Configurações, e o aviso do chat quando falta.
    "jev", "jev_hint", "jev_key", "jev_save", "jev_saved", "jev_not_configured",
    # The screens that move a role and a machine's credential — the two system
    # tables whose records are more than a form (§4, item 11).
    "people", "create", "new_role", "new_machine", "mint", "revoke", "token_once",
    "permission_pick", "unknown_permission", "unknown_hint", "credential_none",
    # A árvore de Actions (TASK-189, fatia 4/4): verbo → entidades → modificadores,
    # com a marca de quais portas alcançam cada ação do catálogo.
    "actions", "actions_hint", "modifier_flag", "modifier_argument",
    "reach_cli", "reach_web", "reach_llm", "reach_orphan", "reach_none_known",
    # O LEITOR DO COFRE (TASK-155): a confirmação antes de abrir, o botão de
    # salvar uma cópia, e o que se diz de um arquivo que não tem visualizador.
    "open_confirm", "save_local", "cannot_show",
    # A LEITURA DE UM ARQUIVO QUE A PÁGINA NÃO ABRE: o que abre em nova aba (o
    # PDF e o vídeo que o navegador desenha) e o download do que não abre.
    "open_in_tab", "download",
    # The entrance's, because the entrance comes back when a session dies under
    # a running page (the 401 hook) — and it would come back wordless.
    *SESSION_WORDS,
)


# As palavras do `at-cli admin` que a PRIMEIRA SUBIDA em página desenha
# (TASK-176, fatia 3/3). Elas vêm do MESMO bloco do catálogo (`admin.json`) e
# nunca de uma segunda cópia: o que a pessoa lê no formulário e o que ela leria
# no terminal são uma string só, e uma das duas não pode envelhecer sozinha —
# "as mesmas strings que a fatia 2/3 já pôs no `at-cli admin`". Elas viajam com
# o próprio nome (`admin.name`) porque o bloco é outro: o formulário pede
# `admin.name`, e não um `webapp.*` que repetisse a frase.
FIRST_WORDS = ("name", "credential", "credential.again", "credential.twice",
               "error.short")


def _first_words() -> dict:
    """As palavras da primeira subida, na forma que uma ETIQUETA tem.

    **A pontuação é do PROMPT e não da palavra.** `admin.name` é "Nome do
    administrador: " — dois-pontos e espaço, que é como um prompt de terminal
    termina e como um formulário não escreve: a etiqueta já pede a resposta por
    estar onde está, e o sinal solto vira ruído. O que sai aqui é só isso, e a
    frase é a MESMA de `at-cli admin`; trocar a pontuação é o preço de a mesma
    string servir aos dois suportes, e é menor do que o de manter duas frases
    que possam divergir.
    """
    found = {}
    for key in FIRST_WORDS:
        name = f"admin.{key}"
        rendered = {}
        for lang, text in i18n.labels(name).items():
            # O PISO É DO MOTOR, e viaja já escrito: `admin.error.short` diz o
            # número, e quem o decide é `actors.MIN_CREDENTIAL` — que é o do
            # Cofre. Uma página que o soubesse teria a segunda cópia da regra.
            if key == "error.short":
                text = text.format(min=actors.MIN_CREDENTIAL)
            rendered[lang] = text.rstrip(": ")
        found[name] = rendered
    return found


# As palavras da CONFIRMAÇÃO DA PASTA (TASK-169, fatia 2/3) — o mesmo bloco
# `boot` que o terminal já lê (`ensure_working_folder`), e não uma segunda
# frase: quem chega no modo local sem pasta nenhuma lê a MESMA pergunta, só
# que na tela. `first_run.confirm` fica de fora — é "[s/N]", o prompt do
# terminal, e a tela pergunta com dois botões (`confirm_ok`/`confirm_cancel`,
# que já existem, da casa).
FOLDER_WORDS = ("first_run.notice", "first_run.cancelled")


def _folder_words() -> dict:
    """As palavras da pasta, com o CAMINHO já embutido — a mesma substituição
    que `_first_words` já faz pelo piso do Cofre, aqui pelo caminho que
    `ensure_working_folder` imprimiria no terminal."""
    folder = str(paths.working_folder())
    found = {}
    for key in FOLDER_WORDS:
        name = f"boot.{key}"
        rendered = {}
        for lang, text in i18n.labels(name).items():
            if key == "first_run.notice":
                text = text.format(folder=folder)
            rendered[lang] = text
        found[name] = rendered
    return found


def entry_payload(open_session: session.Session | None, asks: bool = True) -> dict:
    """Who is in, and the words the entrance needs before anybody is.

    It is the ONE public answer of the API, and it carries no table and no
    count: a page that described the folder to whoever can reach the port would
    be the folder read by whoever can reach the port. What it says is whether
    there is an entrance at all (`auth`) and, when there is one, who is past it.

    `auth` is not a detail: a folder with no row carrying a credential has
    nothing to prove, and an entrance drawn there would be a door that never
    opens — nobody could type anything that wins. The page tells "nobody is in"
    from "nobody can enter" by this boolean, and only one of the two draws a
    form.

    **`asks` is the OTHER reason a server has no entrance**, and it comes from
    the caller and not from here: a run from the source tree does not draw one
    (`server.asks`, `run`). The page reads the same `false` for both, which is
    the point — what it must not do is draw a form, and why the form is not
    there is not a thing the form could say.

    `version` rides along for a reader that is not the page: `at-cli webapp`,
    landing on a port another AT already holds, asks THIS route to find out
    which one — it stays the ONE public answer instead of a second route, and
    the page itself has no use for the field and reads past it.

    **`first` is the OTHER screen this answer draws** (TASK-176, fatia 3/3): a
    folder with no administrator at all has no entrance either — nobody could
    prove anything against it — and what the page draws in the entrance's place
    is the form that CREATES the first one (`/api/first`). The question is
    `admins()` and not `can_expose()`: a folder whose only actor is a machine's
    `agent` still has no administrator, and that is exactly the condition
    `at-cli admin` refuses by (`admin.exists`) — one rule, one answer, whether
    the word is typed at a terminal or in this form.

    A run that asks NOBODY has no first run to draw (`asks`), for the same
    reason it has no entrance: there is no door, so there is nothing to open.
    """
    return {
        "auth": asks and actors.can_expose(),
        "first": asks and not actors.admins(),
        # **A PASTA É ANTES DE TUDO ISSO** (TASK-169, fatia 2/3), e por isso
        # NÃO depende de `asks`: o modo local não pergunta quem entra, mas
        # ainda pergunta SE HÁ ONDE entrar — sem pasta não há admin, não há
        # tabela, não há nada para o resto deste payload descrever. O gate do
        # terminal é `boot.is_configured()`, e é o mesmo aqui.
        "folder": not boot.is_configured(),
        "actor": {"name": open_session.name} if open_session else None,
        "lang": i18n.active_code(),
        "version": __version__,
        # The WHOLE language each word, like `/api/state` hands them: the page
        # picks by the language on screen and the server keeps owning the words.
        # The `admin.*` block rides beside them, and it is the same store the
        # entrance reads (`_first_words`). `_folder_words` is its sibling, for
        # the question one step before it.
        "labels": {
            **{key: i18n.labels(f"webapp.{key}") for key in ENTRY_WORDS},
            **_first_words(),
            **_folder_words(),
        },
    }


def state_payload() -> dict:
    row = active_theme(None)
    # The folder's versioning, when there is something to say about it (§4, item
    # 30). It travels written out in every language, like the themes' own
    # description: the page draws the sentence the server hands it, and a folder
    # AT versions hands NOTHING — the band has no words because there is nothing
    # wrong to name.
    unversioned = versioning.phrase()
    return {
        "lang": i18n.active_code(),
        "origin": i18n.active_origin(),
        "labels": {key: i18n.labels(f"webapp.{key}") for key in PAGE_WORDS},
        # WHETHER THE INTERPRETER IS ON is the CORE's switch (`nlu.enabled`), and
        # the page reads it to know what to draw: off, there is no box, no balloon
        # and no chat — the whole function is gone, and nothing else is.
        "interpreter": nlu.enabled(),
        # THE ASSIST'S OWN SWITCH (TASK-180, fatia 3/3): whether Jev is asked
        # at all, once the matcher gives up. The Control Panel draws it from
        # here and writes it back through `/api/assist`.
        "assist": assist.enabled(),
        # SE A CREDENCIAL DO JEV ESTÁ CONFIGURADA: sem ela o Jev não é
        # consultado, e a página diz "Jev não configurado" no chat em vez de
        # fingir que leu.
        "jev_ready": assist.configured(),
        # THE RULER'S NUMBERS. The threshold is the one the demand filter honours
        # (§4); the marks are one per catalogue entry, each carrying the number
        # the demand is measured at — the catalogue's, adjusted by what this
        # folder wrote (`risk.marks`). The page draws what it is handed and
        # invents no number, so the mark and the engine say the same thing.
        "risk": {"threshold": risk.threshold(), "marks": risk.marks()},
        # `None` is the answer for a folder under versioning, and it is not the
        # same as absent: the page tells "nothing to say" from "not here yet"
        # exactly the way it does with a session.
        "versioning": i18n.labels(unversioned) if unversioned else None,
        "theme": row.get("id") if row else None,
        "themes": [
            {"id": theme.get("id"), "label": theme_label(theme),
             "sides": theme_sides(str(theme.get("id"))),
             # The theme describes ITSELF, one description per side: the page
             # shows the one being worn, and follows the swap without asking.
             "desc": theme.get("desc") if isinstance(theme.get("desc"), dict) else None,
             # Almost always absent: the shared `base.css` needs no name of its
             # own. A theme that walks its OWN door (`base_css_path`) says so
             # here, and `theme.ts` reads it to swap the second link.
             "base": theme.get("base") if isinstance(theme.get("base"), str) else None}
            for theme in theme_rows()
        ],
        "tables": [
            {"key": declared.get("id"),
             "label": tables.table_name(str(declared.get("id")), many=True),
             "type": declared.get("type"),
             "count": len(tables.rows(str(declared.get("id"))))}
            for declared in schema.declared()
        ],
        # A DECLARED type → the table that declares it. A reference to something
        # is followed through here, so a page asks for the TYPE and never guesses
        # a table by its name.
        "types": {
            str(declared["type"]): str(declared["id"])
            for declared in schema.declared()
            if isinstance(declared.get("type"), str)
        },
    }


def catalogue_payload() -> dict:
    """The closed list, as the screen that moves a role reads it — and, for the
    Actions tree (TASK-189, fatia 4/4), the same list carrying what the role
    picker never needed: the modifiers each act accepts and the interfaces that
    reach it.

    One entry per permission — the machine name, the label a person reads, the
    description of what the act does and the risk it declares — and never a
    guess: whatever the catalogue does not name is not here, which is exactly
    what makes the screen able to say that a role names something that does not
    exist. The order is the catalogue's, so the picker draws the list it was
    handed and sorts nothing.

    **`description` travels with the entry** so the Actions tree writes the
    sentence a person reads in place of the machine name; it comes from the same
    catalog read as the labels (`permissions.description`), and an empty string
    is the screen's word to hide the line.

    **`modifiers` and `reach` are read off the SAME declarations the fatias
    before this one wrote** (`permissions.modifiers`, `actions_audit.reach`), and
    not a second count: a page that drew its own would be the catalogue's
    second home. `orphan` is `actions_audit.orphans()`'s verdict, by key — the
    named exceptions (`NO_INTERFACE_YET`) answer `False` with an empty `reach`,
    which is a gap already decided, and never the one `orphan` flags.
    """
    reached = actions_audit.reach()
    orphaned = frozenset(actions_audit.orphans())
    entries = []
    for name in permissions.all_permissions():
        obj, _, action = name.partition(":")
        entries.append(
            {
                "key": name,
                # The PARTS as well as the whole: the screen groups the closed
                # list by object, and splitting the label here would be the page
                # parsing a sentence the catalogue already knows how to cut.
                "object": obj,
                "object_label": permissions.object_label(obj),
                "action": action,
                "action_label": permissions.action_label(action),
                "label": permissions.label(name),
                "description": permissions.description(name),
                "risk": permissions.risk(name),
                "modifiers": [
                    {"name": modifier.name, "label": i18n.tr(modifier.key), "kind": modifier.kind}
                    for modifier in permissions.modifiers(name)
                ],
                "reach": sorted(reached.get(name, frozenset())),
                "orphan": name in orphaned,
            }
        )
    return {"permissions": entries}


def _worded(answer: dict) -> dict:
    """The engine answers with CATALOG KEYS; the wire carries the words.

    A refusal is read by a person, and the page prints what it is handed — so the
    translation happens here, where the catalog is, and never in the page (§3).
    """
    key = answer.get("error")
    if isinstance(key, str) and key.startswith(("prose.", "webapp.")):
        return {**answer, "error": i18n.tr(key)}
    return answer


def _declare_args(payload: dict) -> list[str] | None:
    """The body of a `declare` POST, spelled the way `ask._declared` already
    parses an argument list — the ONE parser, read by the `cli` and by this
    route alike, and never a second one invented here (relógio, fatia 3/3).

    `--when` first, then the table and the act being scheduled, then the
    act's own row id when it needs one (`edit`/`cancel`/`delete`), then a
    `--set` pair per value the chosen act's fields carry. `_pulled`/`_sets`
    read a flag wherever it sits, so the order here is a choice and not a
    requirement — this is simply the one `_declared`'s own docstring reads.
    """
    table = payload.get("table")
    act = payload.get("act")
    when = payload.get("when")
    if not isinstance(table, str) or not isinstance(act, str) or not isinstance(when, str):
        return None
    args = [table, act]
    row_id = payload.get("id")
    if row_id is not None and str(row_id).strip():
        args.append(str(row_id))
    args += ["--when", when]
    values = payload.get("set")
    if isinstance(values, dict):
        for name, value in values.items():
            args += ["--set", f"{name}={value}"]
    return args

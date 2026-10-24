"""The declarations of the permission catalogue: names, NARROWED, EXTRA and the word map.

Corte de `at.core.permissions` (a fachada); ver o docstring de lá.
"""

from __future__ import annotations

from at.core import reminder, tables

# The key a declaration narrows itself with, and the whole of what it may say:
# the permission `object:permission` the table answers, and the engine actions
# that reach it. A table that declares none answers the engine's six
# (`tables.ACTIONS`) under their own names — `task:list`, `task:edit`. A table
# that declares one answers exactly what it names and nothing else: `secret`
# answers `read` and `edit`, so its listing is `secret:read` and its write is
# `secret:edit`, and the two actions the table does not answer — a closing and a
# deletion — are not permissions it has.
#
# The actions are held to `tables.ACTIONS` both ways, and that is the point of
# reading them here: a name the ENGINE does not have is not a permission that
# exists (§4), and an action the declaration forgot is one the table does not
# answer any more.
DECLARED = "permissions"

# The name of the settings OBJECT. It is not a table — the word names what
# `setting:read` and `setting:edit` are about — and it is here, once, because
# the catalogue, the tree and the risk all spell it.
SETTING = "setting"

# The name of the `job` object — the table the demand that could not run becomes
# (item 15's fourth slice). It is here for the reason `SETTING` is: the schema,
# the tree, the risk and the door all spell it, and a second spelling would be
# the one that drifts.
JOB = "job"

# The name of the `secret` object — the table that carries what AT USES, sealed
# (§4, item 14). It is here for the reason `JOB` is: the schema, the catalogue
# and the dispatch all spell it, and a second spelling would be the one that
# drifts.
SECRET = "secret"

# The act that is the SECRET's OWN — `at-cli secret scan` (item 51). It is not
# one of the engine's six: the word reads the FOLDER and rewrites no row of any
# table, so it is not a `create`, an `edit` nor a `cancel`, and it is declared in
# `NARROWED` and nowhere else, exactly as the `job`'s own three acts are.
SCAN = "scan"

# The SECRET's second own act — `at-cli secret install_hooks`: the varredura
# becomes the `pre-commit`/`pre-push` of a repository's own `.git/hooks/`
# (`core.hooks`). It writes two files and reads nothing of any table, so it is
# an act of its own exactly the way `SCAN` is, and not one of the engine's six.
INSTALL_HOOKS = "install_hooks"

# The name of the `reminder` object, and the act that is its OWN — `at-cli
# reminder due` (item 29's first slice). `REMINDER` is read off the table
# module and not spelled a second time here, because the two constants this
# object needs (`REMINDER`, `DUE`) already live where the recurrence they name
# is decided. `DUE` reads the store and rewrites no row, so it is not one of the
# engine's six either, for the reason `SCAN` is not.
REMINDER = reminder.REMINDER
DUE = reminder.DUE

# The objects whose acts are THEIR OWN, narrowed here in the same shape a table
# writes in its own declaration — permission → the actions it answers.
#
# The settings are an object that is not a table: `list` and `view` are the one
# read, `edit` is the one write, and the three are the words the `cli` offers
# under `setting`.
#
# **The `job` is a table, and it narrows itself here all the same**, because its
# acts are not the engine's six. §4 fixes the closed list of objects and actions,
# and the engine's six are a row's: `run` performs the act the job holds,
# `approve` releases it and `refuse` ends it — none of the three rewrites a field
# of the row, and none of them is a `create`, an `edit` or a `cancel`. A
# declaration cannot name them, because `narrowed` holds a table's own
# declaration to the engine's list and drops what the engine does not have; so
# they are declared HERE, once, and read by the same door every other narrowing
# is — so the help, the route, the dispatch and the role cannot disagree about
# what the object answers: a second mapping beside this one would be the second
# home this module refuses.
#
# **A table that keeps its declaration AND has an act of its own writes both**,
# and `secret` is the case (item 51): its declaration narrows it to the engine's
# `read` and `edit`, and the ONE act the engine does not have — its `scan` — is
# named here. The two are COMPOSED and not one-or-the-other (`narrowed`), which
# is what lets a table that answers two of the six keep reading its declaration
# and still declare the seventh act under its own word.
NARROWED: dict[str, dict[str, tuple[str, ...]]] = {
    SETTING: {"read": ("list", "view"), "edit": ("edit",)},
    JOB: {
        "read": ("list", "view"),
        "run": ("run",),
        "approve": ("approve",),
        "refuse": ("refuse",),
        # Item 24's fatia 2/3: `declare` writes the row born `scheduled` — a
        # write like `run`'s, and not the person's word over a demand that
        # already waited, which is what the two above are. `disable` IS that
        # word, over a round instead of a demand, so it is priced and guarded
        # beside `approve`/`refuse` and not beside `declare`.
        "declare": ("declare",),
        "disable": ("disable",),
    },
    # `secret scan` reads the folder and reports what it found — it writes no
    # row, so it is a read on §4's scale and it is nobody's approval but the
    # administrator's. `secret install_hooks` WRITES — two files, in a
    # repository's own `.git/hooks/` — so it sits beside `scan` as the
    # object's second own act, and a closing and a deletion stay the two
    # permissions the table does not have.
    SECRET: {SCAN: (SCAN,), INSTALL_HOOKS: (INSTALL_HOOKS,)},
    # `reminder` keeps every one of the engine's six under its own name — the
    # table does not narrow itself, so this is the identity a table with no
    # declaration of its own already answers with — and adds `due`, the one act
    # the engine does not have. Read off `tables.ACTIONS` rather than spelled
    # out here, so a sixth action the engine grows is a sixth permission this
    # object already answers for, and not a silent gap.
    REMINDER: {**{action: (action,) for action in tables.ACTIONS}, DUE: (DUE,)},
}

# The objects that are not a table, and the actions each one accepts. §4 names
# the settings with all the letters; the other two are what the WebApp's routes
# reach and no table answers for — `prose` is the layer that manages every file
# that is not structured data, and `nlu` is the interpreter's door, which
# proposes and never writes. They are named here because there is no other place
# where they exist.
#
# **The last three are reached by NO route yet, and they are declared all the
# same.** §4 lists them among the objects — "the settings, the services, the
# plugins and the interpreter's vocabulary" — and the screens that move them
# (items 13, 15 and 16) are what will demand them. Declaring them here is not
# anticipation: the catalogue is the CLOSED list a role is written against, and a
# role that names `service:edit` today names a permission that EXISTS that
# nothing has yet been refused for — which is a different thing, and the
# difference is the whole of `is_known`. Leaving them out would have the screens
# arrive into a catalogue that has to grow under a live role.
EXTRA: dict[str, tuple[str, ...]] = {
    SETTING: ("read", "edit"),
    "prose": ("read", "edit"),
    "nlu": ("ask",),
    "service": ("read", "edit"),
    "plugin": ("read", "edit"),
    "vocabulary": ("read", "edit"),
    # TASK-180: o assist (`at.core.assist`) é o ato de perguntar ao Jev o que
    # a frase significa — uma chamada a um serviço externo, e por isso um ato
    # próprio, com o risco já declarado para `ask` (`RISK_BY_ACTION`) em vez de
    # um número inventado aqui: a dúvida sobre gíria não é maior nem menor do
    # que a do `nlu:ask` que já estava reservado para a porta do interpretador.
    "assist": ("ask",),
    # TASK-156: a seção lê a lista dos `.enc` — nada aqui edita nada, porque o
    # que entra em `Cofre/` sela sozinho (o vigia, TASK-154), e não por um
    # gesto da página. O objeto é `strongbox` e não `cofre`: o nome do código
    # é inglês como todo o resto desta lista, e uma migração (vinte e cinco)
    # renomeia o que já estava escrito em papéis existentes.
    "strongbox": ("read",),
    # TASK-176, fatia 3/3: o WebApp lê o TÓPICO do notificador por dentro e é
    # disso que esta entrada é o teto — `notifier:read` é a rota que consome o
    # tópico, e nada mais. **O `read` é o ato inteiro dela**, e o objeto é o
    # serviço e não a marca: o dia em que outro servir o papel, a permissão não
    # se muda. O que publica no tópico não está aqui porque não é uma rota —
    # quem publica é o relógio (`at.core.notifier.publish`), e ele não pede
    # licença a esta lista para falar com o serviço que o próprio ambiente subiu.
    "notifier": ("read",),
    # TASK-186, fatia 1/4: as palavras não-tabela que `tree.WORDS` já expõe e
    # que o catálogo, até aqui, ficava em silêncio sobre (o motor de Actions
    # centralizado). `webapp` e `backup` são objeto+verbo de fato — a página
    # sobe (`run`) e a cópia se faz ou se restaura (`make`, `restore`) —, e
    # `cli` é o terceiro: os verbos SOLTOS, sem objeto próprio, que ainda assim
    # mudam a pasta — `admin` nasce o primeiro administrador, `lang` escolhe o
    # idioma, `convert` escreve em `Convertidos/`. `help`, `version`,
    # `license`, `install` e `uninstall` ficam de fora: são a própria
    # interface, não um ato sobre a pasta, e `at/tests/test_permissions.py`
    # escreve o porquê de cada um.
    "webapp": ("run",),
    "backup": ("make", "restore"),
    "cli": ("admin", "lang", "convert"),
    # TASK-186, fatia 3/4: `help` É um objeto e um verbo (a pessoa, ao decidir
    # esta fatia) — ao contrário de `admin`/`lang`/`convert`, que são verbos
    # SOLTOS sem objeto próprio e por isso compartilham `cli`, `help` tem os
    # dois: o objeto é a própria ajuda, e `show` é o único ato que ela
    # responde. Deixa de ser um dos cinco nomes de `NAMED_EXCEPTIONS`
    # (`test_permissions.py`) — `version`, `license`, `install` e `uninstall`
    # continuam de fora, sem decisão nova sobre eles.
    "help": ("show",),
}


# Every other non-table word, mapped to the permission(s) it carries — the
# proof `at/tests/test_permissions.py` walks, and the data the audit
# (`at.core.actions_audit`, fatia 3/4) reads for the CLI side of the words
# that are not a table: a second mapping of the same words would be the
# second home the catalogue already refuses elsewhere (`permissions.py`'s own
# docstring). Most words ARE their own object (`webapp:run`,
# `backup:make`/`backup:restore`) — the clear object+verb cases. `admin`,
# `lang` and `convert` are verbs left SOLTOS, with no object of their own, so
# the three share one, `cli`. `assist` and `setting` were catalogued already
# (`EXTRA`, before fatia 1/4). `help` joined in fatia 3/4: it IS an object
# and a verb (the person's own call, unlike the three SOLTOS above), so it
# gets its own — `help:show`.
WORD_PERMISSIONS: dict[str, tuple[str, ...]] = {
    "webapp": ("webapp:run",),
    "backup": ("backup:make", "backup:restore"),
    "convert": ("cli:convert",),
    "admin": ("cli:admin",),
    "lang": ("cli:lang",),
    "assist": ("assist:ask",),
    SETTING: ("setting:read", "setting:edit"),
    "help": ("help:show",),
}

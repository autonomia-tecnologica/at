"""The routes that reach the interpreter and the machine credentials: `_post_ask`
(one sentence through the door), `_post_jev`, `_post_assist`, `_post_agent`,
`_post_job` and `_post_convert`.

Moved out of `app.py` (B-6) without a change of behaviour. `AiRoutes` is a
mixin (no `__init__`) the `Handler` inherits: it reads `_body`, `_json`, `_may`,
`_legal` and `_actor` from the `Handler`. This module does not import `app` at
the top.
"""

from __future__ import annotations

from typing import cast

from at import convert, i18n
from at.core import actors, assist, audit, files, jobs, permissions, tables
from at.prose import listing as prose
from at.prose import payload as shape
from at.ui import ask as door
from at.ui.webapp import keys
from at.ui.webapp.entry import _declare_args
from at.ui.webapp.routes_base import RouteBase


class AiRoutes(RouteBase):
    def _post_convert(self) -> None:
        """`{path, to}` → a DOCX or PDF landed in `Convertidos/` (TASK-165,
        fatia 4/4). The same door and the same refusals `_get_file` already
        answers with — a path outside `Arquivos/` or a file that is not text
        is refused by `prose` itself, never a second rule invented here.
        """
        payload = self._body()
        if payload is None:
            return
        rel, to = payload.get("path"), payload.get("to")
        if not isinstance(rel, str) or to not in convert.FORMATS:
            self._json({"error": "bad request"}, 400)
            return
        info = prose.read(rel)
        if info is None:
            self._json({"error": i18n.tr("prose.not_served")}, 404)
            return
        # A conversion is of TEXT — a PDF, an image or a video opens in the page
        # (`open`), and none of them is a markdown to convert.
        if info.get("open") != "text":
            self._json({"error": i18n.tr(str(info.get("reason") or "prose.not_supported"))}, 400)
            return
        where = prose.inside(rel)
        assert where is not None  # `prose.read` above already served this path
        try:
            target = convert.convert(where, to)
        except files.ReadOnly as error:
            self._json({"error": f"read-only: {error.where}"}, 403)
            return
        self._json({"path": target.name})

    def _post_ask(self) -> None:
        """One sentence through the interpreter's door: the proposal, and then.

        The door is `at.ui.ask`, which the `cli` reads too — the page walks the
        same road (`nlu.propose` for the reading, the table engine for the
        writing) and gains no rule of its own. What travels back is what a person
        reads: the proposal in the engine's words, the answer after it, the
        question when the sentence was ambiguous, or the reason when it was not
        read at all. A refusal is an ANSWER here and not a failure of the request:
        it is a sentence the conversation keeps, and the page prints it as it
        stands.

        **`main_key` is the one thing this route adds past fatia 1/2** (TASK-180,
        fatia 3/3): the real path through the assist, from the ONE place that can
        type a Main Key without it ever landing in a file or a log — the person's
        own browser, for the one request that carries it. It is never cached here
        and never on the page: a retry sends it again, exactly the way `at-cli
        assist` reads it fresh every time.

        **Asking Jev is its own ceiling, separate from `nlu:ask`'s** (already
        asked at the dispatch above): a role may read the deterministic box
        without being free to spend a call to an external service, so a key that
        arrived without `assist:ask` is dropped here — the sentence gets the
        same answer it would have gotten with no key at all, and never a 403 over
        a field the request did not have to send.
        """
        payload = self._body()
        if payload is None:
            return
        sentence = payload.get("text")
        if not isinstance(sentence, str) or not sentence.strip():
            self._json({"error": "bad request"}, 400)
            return
        raw_key = payload.get("main_key")
        main_key = raw_key if isinstance(raw_key, str) and raw_key else None
        if main_key is not None and not self._legal("assist:ask"):
            main_key = None
        # A Chave Principal da SUBIDA, guardada em memória no `boot` (§4): o
        # pedido não precisa trazê-la de novo a cada mensagem.
        if main_key is None:
            main_key = keys.main_key()
        # The ACTOR comes along: the door owns the ceiling (§5, "o que ela pode
        # propor é o que ela já pode fazer"), and it is the same door the balloon,
        # the chat and `at-cli ask` read — so the refusal lands on every surface at
        # once and none of them keeps a ceiling of its own. `None` is a folder
        # asking nobody, and there the door answers as it always did.
        result = door.ask(sentence, actor=self._actor(), main_key=main_key,
                          confirmed=bool(payload.get("confirmed")))
        self._json({
            "kind": result.kind,
            "proposal": result.proposal,
            "text": result.text,
            # Whether the assist could still answer THIS refusal for a Main Key
            # typed now — `False` once one already travelled (nothing left to
            # retry) and for an actor the role does not let spend the call at
            # all, so the browser never offers a retry that can only be denied.
            "assist": result.assist and self._legal("assist:ask"),
            # The rewritten sentence a "Confirmar" resubmits (TASK-183) — `None`
            # for every answer and every ordinary ambiguity question. It needs
            # no ceiling of its own: `door.ask` only fills it once the assist
            # has already run, which only happened because the Main Key that
            # reached it already cleared `assist:ask` above.
            "confirm": result.confirm,
            # A `list`'s own header and cells, so the chat draws an actual
            # table instead of parsing `text`'s ASCII back apart — `None` for
            # every other answer, and for a `list` that found nothing.
            "table": {"header": result.table[0], "rows": result.table[1]}
            if result.table is not None else None,
            # A `list`'s own bullets — the default shape, one line per row —
            # mutually exclusive with `table` (above): a sentence that said
            # "tabela" fills one, every other `list` fills the other.
            "bullets": result.bullets,
            # The action a bare verb named ("listar", alone) — `null` for
            # every answer that is not that one refusal — so the chat can
            # complete it from whatever is typed next instead of asking the
            # person to repeat themselves with the object already in hand.
            "awaiting": result.awaiting,
            # THE CARD and THE SENTENCE AROUND IT (20/10/2026) — the object the
            # answer was about, the way a person reads it, and what a
            # conversation says before showing it. Both are composed by the
            # door and only PLACED here: the page invents neither (§3). `None`
            # for a `list` (its own `table`/`bullets` are the shape) and for
            # every question and refusal.
            "record": result.record,
            "lead": result.lead,
            # O desfecho `intent` (conversa): qual intenção e subintenção
            # produziram `text`. `null` em todo outro desfecho.
            "intent": result.intent,
            "subintent": result.subintent,
        })

    def _post_jev(self) -> None:
        """Configura a credencial do Jev — o `secret` de escopo `jev` (§4).

        O corpo traz a chave do Jev e a Chave Principal: a segunda é o que SELA
        a primeira (`assist.configure`), e não é guardada em lugar nenhum. A
        rota não abre nada e não chama o Jev — só escreve a linha; a página
        passa a ver `jev_ready` no estado.
        """
        payload = self._body()
        if payload is None:
            return
        value = payload.get("key")
        if not (isinstance(value, str) and value.strip()):
            self._json({"error": i18n.tr("webapp.jev_missing")}, 400)
            return
        # A Chave Principal é a da SUBIDA, em memória (`keys.main_key`) — a
        # pessoa NÃO a digita de novo aqui: ela já foi digitada quando o AT
        # subiu, e é a mesma que sela o valor (§4).
        main_key = keys.main_key()
        if not main_key:
            self._json({"error": i18n.tr("webapp.jev_no_main_key")}, 409)
            return
        if not assist.configure(value.strip(), main_key):
            self._json({"error": i18n.tr("webapp.jev_bad_key")}, 400)
            return
        self._json({"ok": True, "jev_ready": True})

    def _post_assist(self) -> None:
        """The assist's own two knobs, from the Control Panel (TASK-180, fatia
        3/3): the switch and the mode, each an adjustment of the folder (§4)
        and not a datum of the page, so each is written through `door.setting`
        — the same line and the same version a `setting edit` at a terminal
        already leaves, and not a second road into `settings.json`.

        Either field alone is a legal request — the switch flips without
        touching the mode, and the mode changes without touching the switch —
        so the two are read and written independently, and the answer is the
        pair as the folder now holds it, read back rather than echoed, the
        same reason `door.setting` itself answers from the file and not from
        what was typed.
        """
        payload = self._body()
        if payload is None:
            return
        on = payload.get("enabled")
        wanted_mode = payload.get("mode")
        actor = self._actor()
        if isinstance(on, bool):
            code, answer = door.setting(
                "edit", [assist.SWITCH, "true" if on else "false"],
                actor=actor, via=audit.WEBAPP,
            )
            if code != door.OK:
                self._json({"error": answer}, 400)
                return
        if isinstance(wanted_mode, str):
            if wanted_mode not in (assist.CAUTIOUS, assist.AUTOMATIC):
                self._json({"error": f"unknown mode: {wanted_mode}"}, 400)
                return
            code, answer = door.setting(
                "edit", [assist.MODE, wanted_mode], actor=actor, via=audit.WEBAPP,
            )
            if code != door.OK:
                self._json({"error": answer}, 400)
                return
        self._json({"enabled": assist.enabled(), "mode": assist.mode()})

    def _post_agent(self) -> None:
        """The machine credential's door: mint it, give it again, take it away.

        It is the surface item 10 left without one, and it is a route of its own
        for the reason the credential is a thing of its own: an `agent` could only
        be born through the table door with the token TYPED, and a token is not
        something a person types — it is something AT draws and hands over once.

        The permission is the ACTION's, asked here because the action travels in
        the body: minting a new machine is the `actor` CREATE and re-issuing or
        revoking one is the `actor` EDIT. The three are one door because they are
        one subject — the machine's credential — and the vocabulary a person reads
        is the screen's, not the wire's.
        """
        payload = self._body()
        if payload is None:
            return
        action = payload.get("action")
        number = payload.get("id")
        if action == "mint":
            # A machine being BORN is a create; one being given a new token is an
            # edit. Two acts under one word, and the row is what tells them apart.
            if number is None:
                if not self._may("actor:create"):
                    return
                try:
                    row, token = actors.mint_agent(cast(str, payload.get("name")), payload.get("role"))
                except (actors.MachineError, tables.TableError) as refused:
                    self._json({"error": str(refused)}, 400)
                    return
            else:
                if not self._may("actor:edit"):
                    return
                try:
                    row, token = actors.reissue_agent(number)
                except (actors.MachineError, tables.TableError) as refused:
                    self._json({"error": str(refused)}, 400)
                    return
            self._json({"record": shape.record("actor", row), "token": token})
            return
        if action == "revoke":
            if not self._may("actor:edit"):
                return
            try:
                row = actors.revoke_agent(number)
            except (actors.MachineError, tables.TableError) as refused:
                self._json({"error": str(refused)}, 400)
                return
            self._json({"record": shape.record("actor", row)})
            return
        self._json({"error": f"unknown action: {action}"}, 400)

    def _post_job(self) -> None:
        """One act on a `job` — the page's own door to `at.ui.ask.job`
        (relógio, fatia 3/3), beside `_post_table` and never through it.

        `declare` and `disable` (and `run`/`approve`/`refuse`, read the same
        way for whichever fatia wires a button to them) are the object's OWN
        acts (`jobs.ACTS`, `jobs.DECLARE`) — none of them rewrites a field of
        a row through `tables.edit`, so none of them walks `door.run`, and
        `door.job` is the one door that already knows how to run each, write
        its line and version it, exactly as the `cli` does.
        """
        payload = self._body()
        if payload is None:
            return
        action = payload.get("action")
        if action != jobs.DECLARE and action not in jobs.ACTS:
            self._json({"error": f"unknown action: {action}"}, 400)
            return
        # The permission is read off the catalogue like every other write's,
        # and never composed: `job` narrows `declare` and `disable` to their
        # own names (`permissions.NARROWED`), so this is the same door
        # `_post_table` already asks.
        needed = permissions.needed(jobs.JOB, action)
        actor = self._actor()
        if not self._may(
            needed,
            owing=lambda: door.denied(
                jobs.JOB,
                action,
                actor=actor,
                via=audit.WEBAPP,
                reason=audit.DENIED,
                saying=i18n.tr(
                    "permission.denied", permission=permissions.label(needed)
                ),
            ),
        ):
            return
        if action == jobs.DECLARE:
            args = _declare_args(payload)
            if args is None:
                self._json({"error": "bad arguments"}, 400)
                return
        else:
            args = [str(payload.get("id"))]
        try:
            code, answer = door.job(action, args, actor=actor, via=audit.WEBAPP)
        except tables.TableError as error:
            self._json({"error": str(error)}, 400)
            return
        except files.ReadOnly as error:
            self._json({"error": f"read-only: {error.where}"}, 403)
            return
        if code != door.OK:
            self._json({"error": answer}, 400)
            return
        self._json({"answer": answer})

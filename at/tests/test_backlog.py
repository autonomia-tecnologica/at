"""O backlog como dado: a ordem, as fatias e o corpo do item.

Um item de backlog não é uma tabela nova (§4): é um PROJETO, sub-projeto do
projeto do produto, e uma fatia é uma TAREFA dentro dele. O que este arquivo
prova é o que o produto tinha de ganhar para a árvore que ele já declara
carregar a fila — "the direction; macro or micro by the parent tree — the task
is the movement".

São três lacunas, e cada classe é uma:

- **a ordem** — o projeto passa a declarar por que campo a exibição se ordena
  (`sort`), e a fila responde "qual é o próximo" pelo vocabulário que a tarefa
  já tinha;
- **as fatias** — `project view` mostra o que está dentro do item, e `task list
  --project <id>` estreita a listagem ao escopo da página dele;
- **o corpo** — o `desc` do projeto é onde um item guarda o porquê, o decidido
  e o que ficou aberto, e é ele que a página do item carrega.

Toda prova roda numa pasta descartável com `AT_ROOT`, e nenhuma toca a Pasta de
Trabalho de ninguém.
"""

from __future__ import annotations

import io
import json
import os
import re
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

from at import i18n
from at.core import boot, projects, tables
from at.data import schema, store
from at.ui.cli import main


class BacklogCase(unittest.TestCase):
    """Uma pasta própria, e itens montados como o produto os monta."""

    def setUp(self):
        self.scratch = tempfile.TemporaryDirectory()
        self.root = Path(self.scratch.name)
        self.env = mock.patch.dict(
            os.environ, {"AT_ROOT": str(self.root), "AT_LANG": "pt_BR"}
        )
        self.env.start()
        i18n.reset()
        schema.reset()
        with redirect_stdout(io.StringIO()):
            boot.create_working_folder()

    def tearDown(self):
        self.env.stop()
        i18n.reset()
        schema.reset()
        store.reset()
        self.scratch.cleanup()

    def make(self, table: str, **values: object) -> dict:
        return tables.create(table, {name: str(value) for name, value in values.items()})

    def column(self, table: str, field: str, *args: str) -> list[str]:
        """One column of the listing as the `cli` PRINTS it.

        The columns are padded and separated by two spaces, so the line is cut
        on the runs of two or more — and the position read is the one the
        HEADER names, which is the very word `tables.label` gives.
        """
        code, said = self.words(table, "list", *args)
        self.assertEqual(code, 0, said)
        lines = [re.split(r"\s{2,}", line.rstrip()) for line in said.splitlines()]
        at = lines[0].index(tables.label(table, field))
        return [line[at] for line in lines[1:]]

    def words(self, *args: str) -> tuple[int, str]:
        output = io.StringIO()
        with redirect_stdout(output):
            code = main(list(args))
        return code, output.getvalue()


class TheDeclaration(BacklogCase):
    """O que a declaração do produto passou a dizer — e o produto SHIPS isto."""

    def test_the_project_declares_the_field_the_queue_is_ordered_by(self):
        declared = schema.bundled()["project"]
        self.assertEqual(declared["sort"], {"by": "priority", "direction": "desc", "then": "id"})
        priority = declared["fields"]["priority"]
        self.assertEqual(priority["default"], "medium")
        self.assertEqual(
            list(priority["enum"]),
            ["low", "medium", "high", "critical"],
        )

    def test_the_project_declares_the_step_between_decided_and_started(self):
        status = schema.bundled()["project"]["fields"]["status"]
        self.assertIn("planned", status["enum"])
        # A listing that did not carry it would hide every item that is decided
        # and not started — which is the whole of a backlog.
        self.assertIn("planned", status["show"])

    def test_the_project_listing_carries_the_priority_it_is_ordered_by(self):
        self.assertIn("priority", schema.bundled()["project"]["columns"])

    def test_the_task_listing_carries_the_project_it_belongs_to(self):
        self.assertIn("project", schema.bundled()["task"]["columns"])

    def test_the_two_languages_write_the_new_words(self):
        block = json.loads(
            (Path(__file__).resolve().parents[1] / "i18n" / "blocks" / "table.project.json")
            .read_text(encoding="utf-8")
        )
        for language in i18n.SUPPORTED:
            with self.subTest(language=language):
                self.assertTrue(block[language]["field.priority"])
                self.assertTrue(block[language]["field.status.planned"])


class TheOrder(BacklogCase):
    """A fila: o maior primeiro, o mais antigo entre os iguais."""

    def setUp(self):
        super().setUp()
        self.make("project", name="raiz", priority="critical", status="planned")
        self.make("project", name="terceiro", parent=1, priority="medium")
        self.make("project", name="primeiro", parent=1, priority="critical")
        self.make("project", name="segundo", parent=1, priority="high")
        self.make("project", name="quarto", parent=1, priority="critical")

    def test_the_listing_answers_the_highest_priority_first(self):
        self.assertEqual(self.column("project", "name"),
                         ["raiz", "primeiro", "quarto", "segundo", "terceiro"])

    def test_two_of_the_same_priority_keep_the_order_they_arrived_in(self):
        # `primeiro` was written before `quarto`, and the tie does not reorder
        # them: the `then` of the declaration is the id, ascending.
        listed = self.column("project", "name")
        self.assertEqual(listed.index("quarto") - listed.index("primeiro"), 1)

    def test_the_page_lists_the_subprojects_in_the_same_order(self):
        children = [child["title"] for child in projects.page(1)["children"]]
        self.assertEqual(children, ["primeiro", "quarto", "segundo", "terceiro"])

    def test_the_order_is_the_declared_one_and_not_a_rule_of_the_cli(self):
        # The engine is what orders: the same read the page and the `cli` make.
        listed = [row["name"] for row in tables.rows("project")]
        self.assertEqual(listed, self.column("project", "name"))

    def test_the_priority_is_a_column_the_listing_reads(self):
        self.assertEqual(self.column("project", "priority"),
                         ["Crítica", "Crítica", "Crítica", "Alta", "Média"])

    def test_a_row_that_predates_the_field_reads_as_the_declared_default(self):
        # A folder restored from a backup, or a store a hand edited: the row has
        # no `priority`, and it lands where a `medium` would — with the rows that
        # arrived before it.
        where = store.path("project")
        rows = [json.loads(line) for line in where.read_text(encoding="utf-8").splitlines()]
        rows.append({"id": 99, "name": "antigo", "status": "idea"})
        where.write_text(
            "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows),
            encoding="utf-8",
        )
        self.assertEqual(
            self.column("project", "name"),
            ["raiz", "primeiro", "quarto", "segundo", "terceiro", "antigo"],
        )

    def test_a_table_that_declares_no_order_keeps_the_order_of_the_file(self):
        for text in ("café", "chá", "água"):
            self.make("task", text=text)
        self.assertEqual(self.column("task", "text"), ["café", "chá", "água"])


class TheSlices(BacklogCase):
    """As fatias de um item — a pergunta que a `cli` não sabia fazer."""

    def setUp(self):
        super().setUp()
        self.make("project", name="AT", priority="critical", status="planned")
        self.make("project", name="item", parent=1, priority="high", status="planned")
        self.make("project", name="sub", parent=2, priority="medium", status="planned")
        self.make("task", text="fatia do item", project=2)
        self.make("task", text="fatia do sub", project=3)
        self.make("task", text="de outro", project=1)
        self.make("task", text="órfã")

    def test_the_view_of_an_item_lists_the_slices_inside_it(self):
        code, said = self.words("project", "view", "2")
        self.assertEqual(code, 0)
        self.assertIn("fatia do item", said)
        self.assertIn("fatia do sub", said)
        self.assertNotIn("de outro", said)
        self.assertNotIn("órfã", said)

    def test_the_filter_takes_the_whole_subtree_of_the_item(self):
        code, said = self.words("task", "list", "--project", "2")
        self.assertEqual(code, 0)
        self.assertIn("fatia do item", said)
        self.assertIn("fatia do sub", said)

    def test_the_filter_also_takes_what_the_listing_hides_when_all_is_asked(self):
        self.make("task", text="fatia feita", project=2, status="done")
        _, hidden = self.words("task", "list", "--project", "2")
        _, shown = self.words("task", "list", "--project", "2", "--all")
        self.assertNotIn("fatia feita", hidden)
        self.assertIn("fatia feita", shown)

    def test_a_project_nobody_has_is_refused_like_a_row_nobody_has(self):
        code, said = self.words("task", "list", "--project", "99")
        self.assertEqual(code, 1)
        self.assertIn("99", said)

    def test_a_table_that_claims_no_project_is_not_filtered_by_one(self):
        code, _ = self.words("project", "list", "--project", "1")
        self.assertEqual(code, 2)

    def test_the_listing_says_which_item_each_task_belongs_to(self):
        self.assertEqual(
            self.column("task", "project"),
            ["item", "sub", "AT", "—"],
        )


if __name__ == "__main__":
    unittest.main()

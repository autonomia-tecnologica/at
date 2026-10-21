"""O CAMINHO RELATIVO do markdown: o que o texto escreve, virado nas portas.

Este é o módulo `at/ui/webapp/src/lib/relative.ts` — o que resolve um `![](...)`
ou um `[...](...)` RELATIVO ao arquivo que o escreve, e o que vira a porta dos
BYTES (`/api/file/bytes?path=`) ou o ENDEREÇO de um arquivo no AT
(`/file/<caminho>`).

A régua é o MÓDULO, e não a página: a porta é a do SERVIDOR (`prose.inside`,
que recusa o mesmo `..`), e o que este módulo decide é para onde o nome aponta.
Uma vez resolvido, o resto é o servidor.

**A suíte é PYTHON, e não depende de node.** O módulo é TypeScript, e o node o
lê com `--experimental-strip-types` — mas só quando o node está na máquina. Onde
não está, a régua de verdade é a de baixo: o arquivo declara o que a página
precisa que ele declare, e o resto fica para quem tem node. Não se inventa uma
dependência que a suíte não tem.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import unittest

from at.ui.webapp import app as webapp

# The module itself, where the page reads it.
MODULE = webapp.HERE / "src" / "lib" / "relative.ts"

# The node that reads a TypeScript file with the types taken off — the way this
# machine reads it today.
NODE = shutil.which("node")


def ask(expression: str) -> object:
    """What the module answers, asked through the node.

    The module is imported by its OWN path, so the answer is the module's and
    not a copy of it: `import("<path>")` is what the page does, in the browser,
    and what this does, in the shell.

    The expression is JavaScript, with the module under the name `m` — the same
    name the page's own import binds.
    """
    done = subprocess.run(
        [NODE, "--experimental-strip-types", "-e",
         f'import({json.dumps(str(MODULE))}).then(m => console.log(JSON.stringify({expression})))'],
        capture_output=True,
        text=True,
        timeout=60,
    )
    if done.returncode != 0:
        raise AssertionError(f"node falhou: {done.stderr.strip()}")
    return json.loads(done.stdout.strip())


class TheModule(unittest.TestCase):
    """What the page needs the module to hold — and it holds it by NAME."""

    @classmethod
    def setUpClass(cls):
        cls.text = MODULE.read_text(encoding="utf-8")

    def test_the_module_is_there(self):
        self.assertTrue(MODULE.is_file(), MODULE)

    def test_it_declares_everything_the_page_asks_of_it(self):
        for name in ("resolve", "rewriteSrc", "rewriteHref",
                     "fileDoor", "bytesDoor", "fileOf", "dirOf"):
            self.assertIn(f"export function {name}", self.text, name)

    def test_the_doors_are_the_ones_the_server_answers(self):
        # A porta dos BYTES é a mesma que a página já usa para uma imagem
        # (`download.ts`, `FileView.vue`) — e a que o SERVIDOR atende
        # (`_get_file_bytes`).
        self.assertIn('"/api/file/bytes?path="', self.text)
        # O ENDEREÇO de um arquivo é o que o shell sabe abrir: a view `file:`
        # (`views.ts`'s `FILE_PREFIX`), com o caminho depois do prefixo.
        self.assertIn('FILE_DOOR = "/file/"', self.text)


@unittest.skipUnless(NODE, "sem node na máquina: a régua do módulo fica por quem o tem")
class TheResolution(unittest.TestCase):
    """O QUE UM NOME APONTA — a régua de verdade, com o node na máquina."""

    def test_a_relative_path_resolves_against_the_folder_of_the_file(self):
        self.assertEqual(
            ask('m.resolve("Vida pessoal/Carro/TR4/secoes", "../imagens/x.webp")'),
            {"path": "Vida pessoal/Carro/TR4/imagens/x.webp", "query": "", "fragment": ""},
        )

    def test_a_path_that_leaves_the_folder_points_to_nothing(self):
        # `../../../` a partir de `a/b` sai da base: não vira caminho nenhum, e
        # o servidor nem chega a ser perguntado.
        self.assertIsNone(ask('m.resolve("a/b", "../../../c.md")'))
        self.assertIsNone(ask('m.resolve("a/b", "%2Fetc%2Fpasswd")'))

    def test_a_fragment_and_a_query_are_kept(self):
        self.assertEqual(
            ask('m.resolve("a/b", "c.md#sec")'),
            {"path": "a/b/c.md", "query": "", "fragment": "#sec"},
        )
        self.assertEqual(
            ask('m.resolve("a/b", "c.md?q=1#sec")'),
            {"path": "a/b/c.md", "query": "?q=1", "fragment": "#sec"},
        )

    def test_the_dot_and_the_dotdot_inside_resolve(self):
        self.assertEqual(
            ask('m.resolve("a/b", "sub/../c.md")'),
            {"path": "a/b/c.md", "query": "", "fragment": ""},
        )
        self.assertEqual(
            ask('m.resolve("a/b", "./c.md")'),
            {"path": "a/b/c.md", "query": "", "fragment": ""},
        )

    def test_an_image_becomes_the_bytes_door(self):
        self.assertEqual(
            ask('m.rewriteSrc("../imagens/x.webp", "a/b")'),
            {"kind": "set", "value": "/api/file/bytes?path=a%2Fimagens%2Fx.webp"},
        )

    def test_a_link_becomes_the_address_of_a_file(self):
        self.assertEqual(
            ask('m.rewriteHref("secoes/motor.md", "Vida pessoal/Carro/TR4")'),
            {"kind": "set", "value": "/file/Vida%20pessoal/Carro/TR4/secoes/motor.md"},
        )

    def test_a_link_to_elsewhere_is_left_alone(self):
        # `https:` e uma âncora não são nossos: o atributo fica como está.
        self.assertEqual(ask('m.rewriteHref("https://x.com/a", "a/b")'), {"kind": "keep"})
        self.assertEqual(ask('m.rewriteHref("#ancora", "a/b")'), {"kind": "keep"})

    def test_the_address_reads_back_as_the_path(self):
        self.assertEqual(
            ask('m.fileOf(m.fileDoor("Vida pessoal/Carro/TR4/motor.md"))'),
            "Vida pessoal/Carro/TR4/motor.md",
        )
        self.assertEqual(ask('m.fileOf("/file/ok.md")'), "ok.md")

    def test_an_address_that_names_no_file_is_not_a_path(self):
        # A MESMA REGUA DO SERVIDOR (`prose.inside`): um caminho vazio, um
        # absoluto e um `..` — mesmo escondido atrás de um `%2F` — não são
        # caminho nenhum, e o `fileOf` não pode prometer o que o `inside` recusa.
        for address in ("/file/", "/file/%2F", "/file/a%2F..%2Fb", "/file/../b.md"):
            self.assertIsNone(ask(f'm.fileOf({json.dumps(address)})'), address)

    def test_the_folder_of_a_path_is_its_base(self):
        self.assertEqual(ask('m.dirOf("a/b/c.md")'), "a/b")
        self.assertEqual(ask('m.dirOf("c.md")'), "")


if __name__ == "__main__":
    unittest.main()

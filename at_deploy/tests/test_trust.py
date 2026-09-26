"""A CA do AT no cofre que o navegador lê: o NSS por perfil, e o `certutil`.

O §7a entrega a CA pelo NOME (`cert.at.local`), e isso resolve o aparelho que não
lê o disco desta máquina. O navegador DESTA máquina é outro problema, e é o que
esta suíte prova: o Firefox não lê o cofre do sistema — tem o NSS dele, um por
perfil —, e o Chromium lê o `~/.pki/nssdb`. Quem escreve nos dois é o `certutil`,
e o que se prova aqui é o que o AT MANDA a ele: o banco de cada cofre, o apelido,
a confiança e o certificado, que são onde as decisões desta palavra ficam
legíveis.

**Nada aqui toca a máquina de quem roda a suíte.** O `run` do `certutil` é um
seam, e o `home()` também: um teste que escrevesse no NSS de verdade instalaria
uma CA na máquina da pessoa, que é exatamente o que nenhum teste pode fazer. Um
`certutil` falso guarda quais cofres TÊM a CA, para que a instalação e a remoção
sejam provadas como atos que se completam — o que `-A` põe, `-L` acha e `-D`
tira.

As três frases que a suíte existe para fixar: **o cofre que o navegador desta
máquina lê é o que a palavra cobre** (e o do sistema fica de fora, sem elevação);
**sem o `certutil` ela diz as duas saídas e não instala nada**; e **um cofre que
só cresce é um cofre que ninguém audita**, então a mesma palavra desinstala.
"""

from __future__ import annotations

import io
import os
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from at import i18n
from at.core import boot
from at_deploy import environment as env
from at_deploy import tree, trust
from at_deploy.cli import CA_WORDS, OK, REFUSED, USAGE, main

# Every sentence the word says, in either language: the two acts and what each
# one prints on the way out. A key the catalog does not have answers with the KEY
# itself, which is why this list exists — a message added to `trust.py`,
# `deploy.json` or `cli.py` without a line here is a message nobody checks.
SAID = (
    "deploy.ca.about", "deploy.ca.install.about", "deploy.ca.uninstall.about",
    "deploy.ca.ask", "deploy.ca.unknown",
    "services.ca.no_certutil", "services.ca.by_hand", "services.ca.no_authority",
    "services.ca.no_store", "services.ca.installed", "services.ca.removed",
    "services.ca.absent", "services.ca.failed",
)


class FakeCertutil:
    """O `certutil`, sem executar nada — o seam `trust.run`.

    Ele modela o BANCO e não a chamada: guarda quais cofres TÊM a CA, para que
    `-L`, `-A` e `-D` respondam como o programa responde — e é isso que faz a
    remoção ser provada contra o que a instalação pôs, e não contra uma lista de
    argumentos que alguém escreveu à mão.

    `fails` recusa uma OPERAÇÃO inteira (o `-A` de todo cofre, o `-D` de todo
    mundo); `refuse` recusa um COFRE, e é o que encena o caso que importa: um
    banco que recusou sem levar os outros com ele.
    """

    def __init__(self, fails: tuple[str, ...] = (),
                 refuse: tuple[str, ...] = (),
                 held: tuple[str, ...] = ()) -> None:
        self.calls: list[list[str]] = []
        self.fails = fails
        self.refuse = refuse
        # O que já estava no cofre antes desta rodada: é o que deixa uma remoção
        # ser encenada sobre o que uma instalação anterior pôs.
        self.held: set[str] = set(held)

    def run(self, args) -> SimpleNamespace:
        call = [str(part) for part in args]
        self.calls.append(call)
        store = call[call.index("-d") + 1]
        broken = store in self.refuse or any(word in call for word in self.fails)
        if "-L" in call:
            return self._answer(0 if store in self.held else 1)
        if "-A" in call:
            if broken:
                return self._answer(1)
            self.held.add(store)
            return self._answer(0)
        if "-D" in call:
            if broken or store not in self.held:
                return self._answer(1)
            self.held.discard(store)
            return self._answer(0)
        return self._answer(1)

    @staticmethod
    def _answer(code: int) -> SimpleNamespace:
        return SimpleNamespace(returncode=code, stdout="", stderr="")

    def argv(self) -> list[list[str]]:
        return self.calls

    def asked(self, verb: str) -> list[list[str]]:
        return [call for call in self.calls if verb in call]

    def stores(self, verb: str) -> list[str]:
        """O banco de cada chamada daquele verbo, em ordem."""
        return [call[call.index("-d") + 1] for call in self.asked(verb)]


class FolderCase(unittest.TestCase):
    """Uma Pasta de Trabalho e um LAR de mentira: o que o AT lê, e nada da máquina."""

    def setUp(self):
        self.scratch = tempfile.TemporaryDirectory()
        self.root = Path(self.scratch.name)
        self.lar = tempfile.TemporaryDirectory()
        self.env = mock.patch.dict(
            os.environ, {"AT_ROOT": str(self.root), "AT_LANG": "pt_BR"}
        )
        self.env.start()
        i18n.reset()
        # O lar de quem navega é de mentira pelo mesmo motivo que o `run` é: o
        # verdadeiro tem os perfis de quem roda a suíte, e um teste que
        # escrevesse neles instalaria uma CA na máquina dela.
        self.whose = mock.patch.object(trust, "home",
                                       lambda: Path(self.lar.name))
        self.whose.start()
        self.addCleanup(self.whose.stop)
        # E a CA existe na pasta, porque sem ela não há o que pôr no cofre — o
        # caminho dos testes que a querem ausente é `authority(False)`.
        with redirect_stdout(io.StringIO()):
            boot.create_working_folder()
        self.authority()

    def tearDown(self):
        self.env.stop()
        i18n.reset()
        self.scratch.cleanup()
        self.lar.cleanup()

    def authority(self, present: bool = True) -> Path:
        """O `root.crt` que a borda emitiu, dentro do storage do Caddy."""
        where = env.authority_file()
        if present:
            where.parent.mkdir(parents=True, exist_ok=True)
            where.write_text("-----BEGIN CERTIFICATE-----\n")
        elif where.exists():
            where.unlink()
        return where

    def profile(self, name: str, database: bool = True) -> Path:
        """Um perfil do Firefox: a pasta, e o banco NSS dentro dela."""
        where = trust.firefox_home() / name
        where.mkdir(parents=True, exist_ok=True)
        if database:
            (where / trust.DB).write_text("")
        return where

    def chromium(self, database: bool = True) -> Path:
        where = trust.chromium_home()
        where.mkdir(parents=True, exist_ok=True)
        if database:
            (where / trust.DB).write_text("")
        return where

    def certutil(self, present: bool = True, **kw) -> FakeCertutil:
        fake = FakeCertutil(**kw)
        for patch in (
            mock.patch.object(trust, "run", fake.run),
            mock.patch.object(trust, "found",
                              lambda: "/usr/bin/certutil" if present else None),
        ):
            patch.start()
            self.addCleanup(patch.stop)
        return fake

    def quiet(self, call, *args, **kw):
        output = io.StringIO()
        with redirect_stdout(output):
            result = call(*args, **kw)
        return result, output.getvalue()


# --------------------------------------------------------------- os atos ---

class TheStores(FolderCase):
    """Onde a CA entra: um banco por perfil do Firefox, e o `~/.pki/nssdb`."""

    def test_the_default_covers_every_store_this_machine_has(self):
        # O alvo vazio é o PADRÃO: "a CA ao alcance" quer dizer os dois bancos
        # que a pessoa tem, e é isso que a palavra faz sem ninguém nomear nada.
        default, release = self.profile("abc.default"), self.profile("xyz.default-release")
        chromium = self.chromium()
        fake = self.certutil()

        outcome, text = self.quiet(trust.install)

        self.assertEqual(outcome, trust.INSTALLED)
        self.assertEqual(sorted(fake.stores("-A")),
                         sorted(f"sql:{store}" for store in (default, release, chromium)))
        self.assertIn(str(default), text)
        self.assertIn(str(release), text)
        self.assertIn(str(chromium), text)

    def test_every_profile_of_firefox_is_its_own_store(self):
        # É a medida que faz esta palavra existir: uma CA posta no cofre do
        # sistema não chega ao Firefox, porque cada perfil tem o banco dele.
        first, second = self.profile("um.default"), self.profile("dois.default")
        self.certutil()
        self.quiet(trust.install, [trust.FIREFOX])
        self.assertEqual(trust.firefox_stores(), tuple(sorted((first, second))))

    def test_a_profile_without_the_database_is_not_a_store(self):
        # Uma pasta que o navegador nunca abriu não é um cofre: tratá-la como
        # cofre seria anunciar uma instalação que ninguém lê.
        real = self.profile("real.default")
        self.profile("vazio.default", database=False)
        fake = self.certutil()

        outcome, _ = self.quiet(trust.install, [trust.FIREFOX])

        self.assertEqual(outcome, trust.INSTALLED)
        self.assertEqual(fake.stores("-A"), [f"sql:{real}"])

    def test_naming_the_target_narrows_the_act(self):
        profile, chromium = self.profile("abc.default"), self.chromium()
        fake = self.certutil()

        self.quiet(trust.install, [trust.FIREFOX])
        self.assertEqual(fake.stores("-A"), [f"sql:{profile}"])

        fake2 = self.certutil()
        self.quiet(trust.install, [trust.CHROMIUM])
        self.assertEqual(fake2.stores("-A"), [f"sql:{chromium}"])

    def test_the_cofre_of_the_system_is_not_covered(self):
        # §3 pede o MAIS ESTREITO que funciona, e o mais estreito aqui é não
        # pedir elevação nenhuma: os dois bancos são arquivos da própria pessoa.
        # O cofre do sistema seria a segunda entrada da lista fechada do §3, e o
        # Firefox não o lê de todo modo — o NSS dele é por perfil.
        self.profile("abc.default")
        self.chromium()
        fake = self.certutil()
        self.quiet(trust.install)
        for call in fake.argv():
            self.assertTrue(call[call.index("-d") + 1].startswith("sql:"))
            self.assertNotIn("/etc", " ".join(call))
            self.assertNotIn("sudo", " ".join(call))

    def test_the_seat_of_the_ca_is_the_file_the_edge_serves(self):
        # O certificado que entra no cofre é o MESMO que a borda serve por
        # `cert.at.local` e que o celular importa — o `root.crt` do storage do
        # Caddy, dentro da pasta que o backup cobre.
        self.profile("abc.default")
        fake = self.certutil()

        self.quiet(trust.install)

        added = fake.asked("-A")[0]
        self.assertEqual(added[added.index("-i") + 1], str(env.authority_file()))
        self.assertEqual(
            env.authority_file(),
            env.state(env.CADDY) / env.CADDY_STORAGE
            / "pki" / "authorities" / "local" / "root.crt",
        )

    def test_the_nickname_and_the_trust_are_what_the_store_reads(self):
        # O apelido é o que a pessoa lê na lista de certificados e o que a
        # remoção procura; a confiança é `C` no SSL — "confie nesta CA para
        # identificar sites" —, e o resto fica em branco.
        self.chromium()
        fake = self.certutil()
        self.quiet(trust.install)
        added = fake.asked("-A")[0]
        self.assertEqual(added[added.index("-n") + 1], trust.NICKNAME)
        self.assertEqual(added[added.index("-t") + 1], trust.TRUST)
        self.assertEqual(trust.TRUST, "C,,")

    def test_installing_again_is_the_same_act(self):
        # O apelido é limpo antes de escrever, e é isso que faz o mesmo comando
        # ser o mesmo comando: uma autoridade que nasceu de novo tem outro
        # certificado, e um apelido já lá faria o `-A` recusar — deixando o
        # cofre confiando numa chave que ninguém mais tem.
        chromium = self.chromium()
        fake = self.certutil()
        self.quiet(trust.install)
        outcome, _ = self.quiet(trust.install)
        self.assertEqual(outcome, trust.INSTALLED)
        self.assertEqual(fake.held, {f"sql:{chromium}"})
        self.assertGreaterEqual(len(fake.asked("-D")), 2)
        self.assertEqual(len(fake.asked("-A")), 2)


class TheWayBack(FolderCase):
    """A remoção — um cofre que só cresce é um cofre que ninguém audita."""

    def test_the_ca_is_removed_by_the_same_name_it_was_put(self):
        profile, chromium = self.profile("abc.default"), self.chromium()
        fake = self.certutil()
        self.quiet(trust.install)

        outcome, text = self.quiet(trust.uninstall)

        self.assertEqual(outcome, trust.REMOVED)
        self.assertEqual(fake.held, set())
        # O `-D` aparece duas vezes por cofre e por duas razões diferentes: a
        # limpeza que a INSTALAÇÃO faz antes de escrever, e a remoção. O que a
        # remoção prova é o conjunto — todo cofre que tinha a CA ficou sem ela.
        self.assertEqual(sorted(set(fake.stores("-D"))),
                         sorted(f"sql:{store}" for store in (profile, chromium)))
        self.assertIn(str(profile), text)

    def test_a_store_that_never_had_the_ca_is_said_and_not_counted_as_removal(self):
        # As duas terminam com o cofre sem a CA, e só uma delas é uma remoção:
        # a frase diz qual foi qual, e o ato fecha nas duas.
        self.chromium()
        self.certutil()
        outcome, text = self.quiet(trust.uninstall)
        self.assertEqual(outcome, trust.REMOVED)
        self.assertIn(i18n.tr("services.ca.absent", target=trust.CHROMIUM,
                              where=trust.chromium_home()), text)

    def test_the_removal_narrows_with_the_target_too(self):
        self.profile("abc.default")
        self.chromium()
        self.certutil()
        self.quiet(trust.install)
        fake = self.certutil(held=(f"sql:{trust.chromium_home()}",))
        self.quiet(trust.uninstall, [trust.CHROMIUM])
        self.assertEqual(fake.stores("-D"), [f"sql:{trust.chromium_home()}"])


class TheTwoWaysOut(FolderCase):
    """Sem `certutil`, e sem a CA: as duas saídas, e nada instalado."""

    def test_a_machine_without_certutil_is_told_the_two_ways_out(self):
        # A mesma forma do Podman: o AT não instala NADA por conta própria, diz
        # como a pessoa instala, e diz a outra estrada — aqui, a mão, com a CA
        # que o §7a já entrega pelo nome.
        self.profile("abc.default")
        self.chromium()
        fake = self.certutil(present=False)

        outcome, text = self.quiet(trust.install)

        self.assertEqual(outcome, trust.NO_CERTUTIL)
        self.assertEqual(fake.calls, [])
        self.assertIn(i18n.tr("services.ca.no_certutil"), text)
        self.assertIn(str(trust.delivery()), text)
        self.assertIn(str(env.authority_file()), text)
        # A estrada da mão é o NOME que a fatia 1 pôs de pé, e não o laço.
        self.assertEqual(trust.delivery(), f"https://{env.cert_host()}")

    def test_the_ways_out_come_before_the_stores_are_looked_for(self):
        # Numa máquina sem o programa, "não há cofre" mandaria a pessoa procurar
        # no lugar errado: o que falta é o `certutil`.
        self.certutil(present=False)
        _, text = self.quiet(trust.install)
        self.assertNotIn(i18n.tr("services.ca.no_store", targets="firefox, chromium",
                                 firefox=trust.firefox_home(),
                                 chromium=trust.chromium_home()), text)

    def test_a_ca_that_does_not_exist_yet_is_said_before_anything_else(self):
        # A palavra é sobre o certificado que a borda emitiu: numa pasta onde
        # ele ainda não nasceu, o que falta é subir o ambiente.
        self.authority(False)
        self.profile("abc.default")
        fake = self.certutil()
        outcome, text = self.quiet(trust.install)
        self.assertEqual(outcome, trust.NO_AUTHORITY)
        self.assertEqual(fake.calls, [])
        self.assertIn(str(env.authority_file()), text)

    def test_a_removal_does_not_need_the_certificate_to_exist(self):
        # Tirar não depende do que se pôs: o apelido é o que a remoção procura, e
        # uma CA que a pasta perdeu continua saindo do cofre.
        self.chromium()
        self.authority(False)
        self.certutil()
        outcome, _ = self.quiet(trust.uninstall)
        self.assertEqual(outcome, trust.REMOVED)

    def test_no_store_at_all_is_said_with_the_paths_that_were_looked_for(self):
        fake = self.certutil()
        outcome, text = self.quiet(trust.install)
        self.assertEqual(outcome, trust.NO_STORE)
        self.assertEqual(fake.calls, [])
        self.assertIn(str(trust.firefox_home()), text)
        self.assertIn(str(trust.chromium_home()), text)
        # E o Chromium com a pasta mas sem o banco também não é cofre.
        self.chromium(database=False)
        outcome, _ = self.quiet(trust.install)
        self.assertEqual(outcome, trust.NO_STORE)


class TheStoreThatRefused(FolderCase):
    """Um cofre que recusou não é a palavra tendo fechado."""

    def test_one_store_refusing_leaves_the_others_where_they_landed(self):
        # Desfazer o que deu certo seria inventar uma transação que ninguém
        # pediu; o que a palavra deve é DIZER qual cofre recusou, e o código de
        # saída diz que alguma coisa não fechou.
        first, second = self.profile("um.default"), self.profile("dois.default")
        fake = self.certutil(refuse=(f"sql:{second}",))

        outcome, text = self.quiet(trust.install)

        self.assertEqual(outcome, trust.FAILED)
        self.assertIn(f"sql:{first}", fake.held)
        self.assertNotIn(f"sql:{second}", fake.held)
        self.assertIn(i18n.tr("services.ca.installed", target=trust.FIREFOX,
                              where=first), text)
        self.assertIn(i18n.tr("services.ca.failed", target=trust.FIREFOX,
                              where=second), text)

    def test_a_removal_that_refuses_is_the_same_refusal(self):
        self.chromium()
        self.certutil()
        self.quiet(trust.install)
        fake = self.certutil(fails=("-D",),
                             held=(f"sql:{trust.chromium_home()}",))
        outcome, text = self.quiet(trust.uninstall)
        self.assertEqual(outcome, trust.FAILED)
        self.assertIn(i18n.tr("services.ca.failed", target=trust.CHROMIUM,
                              where=trust.chromium_home()), text)


# ---------------------------------------------------------------- a porta ---

class TheDoor(FolderCase):
    """A palavra, alcançada como a pessoa a alcança."""

    def test_the_tree_offers_the_two_acts_and_the_cli_reads_them_from_there(self):
        # §5: uma palavra que despacha é uma palavra que a ajuda oferece. Os atos
        # são os filhos de `ca`; os alvos são argumento, como o nome de
        # `services credential <nome>`.
        node = tree.find("ca")
        self.assertIsNotNone(node)
        assert node is not None
        self.assertEqual([child.name for child in node.children], list(CA_WORDS))
        self.assertEqual(CA_WORDS, trust.ACTS)

    def test_the_word_takes_a_store_and_puts_the_ca_in_it(self):
        chromium = self.chromium()
        fake = self.certutil()
        code, text = self.quiet(main, ["ca", "install", "chromium"])
        self.assertEqual(code, OK)
        self.assertIn(f"sql:{chromium}", fake.held)
        self.assertIn(i18n.tr("services.ca.installed", target=trust.CHROMIUM,
                              where=chromium), text)

    def test_the_word_takes_a_named_removal_too(self):
        self.chromium()
        fake = self.certutil()
        self.quiet(main, ["ca", "install"])
        code, _ = self.quiet(main, ["ca", "uninstall", "chromium"])
        self.assertEqual(code, OK)
        self.assertEqual(fake.held, set())

    def test_the_word_with_no_act_says_the_two_acts_and_the_targets(self):
        code, text = self.quiet(main, ["ca"])
        self.assertEqual(code, USAGE)
        self.assertIn(i18n.tr("deploy.ca.ask", targets=", ".join(trust.TARGETS)),
                      text)

    def test_a_target_nobody_has_is_a_usage_error_naming_the_vocabulary(self):
        code, text = self.quiet(main, ["ca", "install", "sistema"])
        self.assertEqual(code, USAGE)
        self.assertIn(i18n.tr("deploy.ca.unknown", name="sistema",
                              targets=", ".join(trust.TARGETS)), text)

    def test_an_act_the_tree_does_not_offer_is_rejected(self):
        for words in (["ca", "run"], ["ca", "instalar"]):
            with self.subTest(words=words):
                code, _ = self.quiet(main, words)
                self.assertEqual(code, USAGE)

    def test_the_word_refuses_when_the_store_did_not_take_the_ca(self):
        self.chromium()
        self.certutil(refuse=(f"sql:{trust.chromium_home()}",))
        code, _ = self.quiet(main, ["ca", "install"])
        self.assertEqual(code, REFUSED)

    def test_a_machine_without_certutil_is_a_refusal_at_the_door(self):
        self.chromium()
        self.certutil(present=False)
        code, text = self.quiet(main, ["ca", "install"])
        self.assertEqual(code, REFUSED)
        self.assertIn(i18n.tr("services.ca.no_certutil"), text)

    def test_the_help_offers_the_word_and_its_acts(self):
        code, text = self.quiet(main, ["help"])
        self.assertEqual(code, OK)
        self.assertIn("ca", text)
        self.assertIn("install, uninstall", text)


class TheWords(unittest.TestCase):
    """Toda frase da palavra, nas duas línguas."""

    def test_every_sentence_of_the_word_is_written_in_both_languages(self):
        for key in SAID:
            for code in i18n.SUPPORTED:
                with self.subTest(key=key, language=code):
                    self.assertNotEqual(
                        i18n.text(key, code), key,
                        f"{key} is not written in {code}: the screen would show the key",
                    )

    def test_the_two_ways_out_name_the_road_the_ca_is_already_delivered_on(self):
        # A segunda saída é a CA que a fatia 1 pôs ao alcance: sem ela a frase
        # mandaria a pessoa procurar um arquivo sem dizer onde.
        for code in i18n.SUPPORTED:
            text = i18n.text("services.ca.by_hand", code)
            for placeholder in ("{url}", "{where}"):
                with self.subTest(placeholder=placeholder, language=code):
                    self.assertIn(placeholder, text)

    def test_the_no_store_sentence_says_where_the_two_places_are(self):
        for code in i18n.SUPPORTED:
            text = i18n.text("services.ca.no_store", code)
            for placeholder in ("{targets}", "{firefox}", "{chromium}"):
                with self.subTest(placeholder=placeholder, language=code):
                    self.assertIn(placeholder, text)


if __name__ == "__main__":
    unittest.main()

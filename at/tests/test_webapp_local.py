"""O modo local: `at-cli` sem palavra (TASK-169, fatia 1/3).

`run` sorteia a porta, abre o navegador e espera uma das duas mortes —
e é por isso que toda classe aqui INJETA o `opener`: nenhum teste desta
suíte abre um navegador de verdade, nem espera minutos por um timeout real.
"""

from __future__ import annotations

import io
import json
import os
import re
import socket
import tempfile
import threading
import unittest
import urllib.request
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

from at import i18n
from at.core import boot, settings
from at.ui.webapp import local


class _FakeProcess:
    """O filho que a janela com moldura seria — e o `.wait()` que `run` chama."""

    def __init__(self) -> None:
        self.waited = False
        self.terminated = False

    def wait(self) -> None:
        self.waited = True

    def terminate(self) -> None:
        self.terminated = True


class TheRun(unittest.TestCase):
    def setUp(self) -> None:
        self.scratch = tempfile.TemporaryDirectory()
        self.env = mock.patch.dict(
            os.environ, {"AT_ROOT": self.scratch.name, "AT_LANG": "pt_BR"},
        )
        self.env.start()
        i18n.reset()
        with redirect_stdout(io.StringIO()):
            boot.create_working_folder()

    def tearDown(self) -> None:
        self.env.stop()
        i18n.reset()
        self.scratch.cleanup()

    def _port_of(self, output: str) -> int:
        found = re.search(r"http://127\.0\.0\.1:(\d+)/\?k=", output)
        assert found, output
        return int(found.group(1))

    def test_the_framed_window_closing_is_the_death(self) -> None:
        process = _FakeProcess()
        profile = tempfile.mkdtemp()
        output = io.StringIO()
        with redirect_stdout(output):
            code = local.run(opener=lambda url: (process, profile))
        self.assertEqual(code, 0)
        self.assertTrue(process.waited)
        # The profile was a throwaway for THIS window, and it does not
        # outlive it.
        self.assertFalse(Path(profile).exists())
        # And the port it served on answers nobody anymore.
        port = self._port_of(output.getvalue())
        with self.assertRaises(OSError):
            socket.create_connection(("127.0.0.1", port), timeout=1).close()

    def test_idle_with_no_tab_open_is_the_other_death(self) -> None:
        output = io.StringIO()
        with redirect_stdout(output):
            code = local.run(opener=lambda url: None, idle_timeout=0.05, poll=0.01)
        self.assertEqual(code, 0)

    def test_the_url_handed_to_the_opener_carries_the_token(self) -> None:
        process = _FakeProcess()
        profile = tempfile.mkdtemp()
        captured: dict = {}

        def opener(url: str):
            captured["url"] = url
            return process, profile

        with redirect_stdout(io.StringIO()):
            local.run(opener=opener)
        self.assertIn("?k=", captured["url"])
        self.assertTrue(captured["url"].startswith("http://127.0.0.1:"))


class TheRunWithoutAFolder(unittest.TestCase):
    """O modo local sobe MESMO SEM pasta nenhuma (TASK-169, fatia 2/3): quem
    pergunta é a própria tela, pela porta `/api/folder` — sem
    `boot.create_working_folder()` nenhum no `setUp`, de propósito.
    """

    def setUp(self) -> None:
        self.scratch = tempfile.TemporaryDirectory()
        self.env = mock.patch.dict(
            os.environ, {"AT_ROOT": self.scratch.name, "AT_LANG": "pt_BR"},
        )
        self.env.start()
        i18n.reset()

    def tearDown(self) -> None:
        self.env.stop()
        i18n.reset()
        self.scratch.cleanup()

    def _confirm(self, url: str, confirm: bool) -> None:
        # O TOKEN de uso único (fatia 1/3) guarda toda rota deste modo,
        # `/api/folder` incluída — a query carrega o `?k=` que a própria
        # tela usaria. `url` é `http://host:porta/?k=...`, e o `/` antes do
        # `?` é exatamente onde `api/folder` entra no lugar do vazio.
        root, _, query = url.partition("?")
        body = json.dumps({"confirm": confirm}).encode("utf-8")
        request = urllib.request.Request(
            f"{root}api/folder?{query}", data=body,
            method="POST", headers={"Content-Type": "application/json"},
        )
        urllib.request.urlopen(request).close()

    def test_confirming_through_the_page_creates_the_folder(self) -> None:
        process = _FakeProcess()
        profile = tempfile.mkdtemp()

        def opener(url: str):
            self._confirm(url, True)
            return process, profile

        with redirect_stdout(io.StringIO()):
            code = local.run(opener=opener)
        self.assertEqual(code, 0)
        self.assertTrue(settings.exists())

    def test_refusing_through_the_page_ends_the_framed_window(self) -> None:
        process = _FakeProcess()
        profile = tempfile.mkdtemp()

        def opener(url: str):
            self._confirm(url, False)
            return process, profile

        with redirect_stdout(io.StringIO()):
            code = local.run(opener=opener)
        self.assertEqual(code, 0)
        self.assertFalse(settings.exists())
        self.assertTrue(process.terminated)


class TheIdleWatch(unittest.TestCase):
    """`_idle_watch` alone: no server, no process, just the broadcaster's own
    count of open tabs."""

    class _Events:
        def __init__(self, count: int) -> None:
            self.count = count

        def __len__(self) -> int:
            return self.count

    class _Server:
        def __init__(self, count: int) -> None:
            self.events = TheIdleWatch._Events(count)

    def test_a_refused_folder_ends_the_watch_too(self) -> None:
        # A terceira morte (TASK-169, fatia 2/3): sem moldura não há processo
        # para fechar, e é esta rodada que confere a recusa.
        server = self._Server(0)
        server.folder_cancelled = threading.Event()
        server.folder_cancelled.set()
        ticks = {"n": 0}

        def pause(seconds: float) -> None:
            ticks["n"] += 1

        local._idle_watch(server, timeout=10, pause=pause, poll=0.01)
        self.assertEqual(ticks["n"], 1)

    def test_a_fake_server_with_no_such_field_is_untouched(self) -> None:
        # Os testes acima, que já existiam, não carregam `folder_cancelled` —
        # e a conferência tem de deixá-los exatamente como estavam.
        server = self._Server(1)
        ticks = {"n": 0}

        def pause(seconds: float) -> None:
            ticks["n"] += 1
            if ticks["n"] >= 2:
                server.events.count = 0

        local._idle_watch(server, timeout=0.02, pause=pause, poll=0.01)
        self.assertGreaterEqual(ticks["n"], 2)

    def test_it_returns_once_the_quiet_outlasts_the_timeout(self) -> None:
        server = self._Server(0)
        ticks = {"n": 0}

        clock = {"now": 0.0}

        def pause(seconds: float) -> None:
            ticks["n"] += 1
            clock["now"] += seconds  # relógio falso: o tempo passa sem dormir

        with mock.patch.object(local.time, "monotonic", lambda: clock["now"]):
            local._idle_watch(server, timeout=0.02, pause=pause, poll=0.01)
        self.assertGreaterEqual(ticks["n"], 2)

    def test_a_tab_reopening_resets_the_quiet_clock(self) -> None:
        server = self._Server(0)
        calls = {"n": 0}

        clock = {"now": 0.0}

        def pause(seconds: float) -> None:
            calls["n"] += 1
            clock["now"] += seconds  # relógio falso: o tempo passa sem dormir
            # A aba volta a abrir bem no meio da espera — o relógio da
            # ociosidade zera, e o retorno custa mais voltas do que as
            # mínimas para `timeout`.
            server.events.count = 1 if calls["n"] == 2 else 0

        with mock.patch.object(local.time, "monotonic", lambda: clock["now"]):
            local._idle_watch(server, timeout=0.02, pause=pause, poll=0.01)
        self.assertGreater(calls["n"], 2)


class TheCancelWatch(unittest.TestCase):
    """`_end_on_cancel`: a recusa da pasta fecha a janela com moldura
    (TASK-169, fatia 2/3) — a mesma morte que o X dela já era."""

    class _Server:
        def __init__(self) -> None:
            self.folder_cancelled = threading.Event()

    class _Process:
        def __init__(self) -> None:
            self.terminated = False

        def terminate(self) -> None:
            self.terminated = True

    def test_the_event_already_set_terminates_at_once(self) -> None:
        server, process = self._Server(), self._Process()
        server.folder_cancelled.set()
        local._end_on_cancel(server, process)
        self.assertTrue(process.terminated)

    def test_a_folder_confirmed_never_wakes_this_thread(self) -> None:
        # Sem marcar o evento, `_end_on_cancel` fica dormindo — é o que a
        # thread daemon de `run` faz na vida inteira de uma pasta confirmada.
        server, process = self._Server(), self._Process()
        watcher = threading.Thread(
            target=local._end_on_cancel, args=(server, process), daemon=True
        )
        watcher.start()
        watcher.join(timeout=0.05)
        self.assertFalse(process.terminated)
        self.assertTrue(watcher.is_alive())


class TheChromiumDetection(unittest.TestCase):
    """Como o binário descobre se há um navegador Chromium-like — a decisão
    desta fatia (`local._chromium_executable`)."""

    def test_none_found_answers_none(self) -> None:
        with mock.patch.object(local.shutil, "which", return_value=None), \
             mock.patch("os.path.isfile", return_value=False):
            self.assertIsNone(local._chromium_executable())

    def test_a_name_on_the_path_is_found(self) -> None:
        with mock.patch.object(local.shutil, "which",
                                side_effect=lambda name: "/usr/bin/chromium" if name == "chromium" else None):
            self.assertEqual(local._chromium_executable(), "/usr/bin/chromium")


class TheOpenBrowser(unittest.TestCase):
    def test_with_a_chromium_it_opens_framed_with_its_own_profile(self) -> None:
        with mock.patch.object(local, "_chromium_executable", return_value="/usr/bin/chromium"), \
             mock.patch.object(local.subprocess, "Popen") as popen, \
             mock.patch.object(local.tempfile, "mkdtemp", return_value="/tmp/at-local-x"):
            opened = local.open_browser("http://127.0.0.1:1/?k=abc")
        self.assertIsNotNone(opened)
        process, profile = opened
        self.assertIs(process, popen.return_value)
        self.assertEqual(profile, "/tmp/at-local-x")
        args = popen.call_args[0][0]
        self.assertEqual(args[0], "/usr/bin/chromium")
        self.assertIn("--app=http://127.0.0.1:1/?k=abc", args)
        self.assertIn("--user-data-dir=/tmp/at-local-x", args)

    def test_with_no_chromium_it_falls_back_to_the_default_browser(self) -> None:
        with mock.patch.object(local, "_chromium_executable", return_value=None), \
             mock.patch.object(local.webbrowser, "open") as opened_default:
            opened = local.open_browser("http://127.0.0.1:1/?k=abc")
        self.assertIsNone(opened)
        opened_default.assert_called_once_with("http://127.0.0.1:1/?k=abc")

    def test_a_chromium_that_fails_to_spawn_falls_back_too(self) -> None:
        with mock.patch.object(local, "_chromium_executable", return_value="/usr/bin/chromium"), \
             mock.patch.object(local.subprocess, "Popen", side_effect=OSError), \
             mock.patch.object(local.tempfile, "mkdtemp", return_value=tempfile.mkdtemp()), \
             mock.patch.object(local.webbrowser, "open") as opened_default:
            opened = local.open_browser("http://127.0.0.1:1/?k=abc")
        self.assertIsNone(opened)
        opened_default.assert_called_once_with("http://127.0.0.1:1/?k=abc")

"""`polish_text`: capital letter, plus case/accent fixes from the spelling-checker."""

import unittest
from unittest import mock

from at.core import spelling
from at.nlu import polish
from at.tests import test_matcher


def finding(text, word, *suggestions, nth=0):
    offset = -1
    for _ in range(nth + 1):
        offset = text.index(word, offset + 1)
    return spelling.Finding(offset, len(word), "R", tuple(suggestions))


def polished(text, findings):
    with mock.patch.object(spelling, "check", return_value=findings):
        return polish.polish_text("task", "text", text, "pt_BR")


class PolishTest(test_matcher.MatcherCase):
    def test_accent_is_applied(self):
        text = "nao falar com fulano"
        self.assertEqual(polished(text, [finding(text, "nao", "não")]), "Não falar com fulano")

    def test_several_suggestions_are_ignored(self):
        text = "falar com ele ate amanha"
        found = [finding(text, "ate", "até", "ata")]
        self.assertEqual(polished(text, found), "Falar com ele ate amanha")

    def test_a_suggestion_that_changes_the_word_is_ignored(self):
        text = "limpar carro"
        self.assertEqual(polished(text, [finding(text, "carro", "carrão")]), "Limpar carro")
        self.assertEqual(polished(text, [finding(text, "carro", "carros")]), "Limpar carro")

    def test_unavailable_keeps_the_capital_only(self):
        self.assertEqual(polished("nao falar com fulano", None), "Nao falar com fulano")

    def test_a_failing_service_never_raises(self):
        with mock.patch.object(spelling, "check", side_effect=RuntimeError("x")):
            self.assertEqual(polish.polish_text("task", "text", "nao", "pt_BR"), "Nao")

    def test_acronyms_and_names_are_kept(self):
        text = "limpar TR4 e Joao"
        found = [finding(text, "TR4", "tr4"), finding(text, "Joao", "João")]
        self.assertEqual(polished(text, found), "Limpar TR4 e Joao")

    def test_a_lowercase_name_is_not_capitalised_midsentence(self):
        text = "falar com fulano"
        self.assertEqual(polished(text, [finding(text, "fulano", "Fulano")]), "Falar com fulano")

    def test_non_prose_is_untouched(self):
        with mock.patch.object(spelling, "check", side_effect=AssertionError):
            self.assertEqual(polish.polish_text("task", "project", "nao"), "nao")

    def test_the_chat_sentence_gets_the_accent(self):
        sentence = "escrever nota nao falar com fulano"
        with mock.patch.object(spelling, "check", side_effect=lambda t, lang: [finding(t, "Nao", "Não")]):
            proposal = self.propose(sentence)
        self.assertEqual(proposal.values["text"], "Não falar com fulano")
        with mock.patch.object(spelling, "check", return_value=None):
            self.assertEqual(self.propose(sentence).values["text"], "Nao falar com fulano")


if __name__ == "__main__":
    unittest.main()

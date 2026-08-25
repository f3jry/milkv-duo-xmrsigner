from __future__ import annotations
from unittest import TestCase

from test.xmrsigner.wordlist import words
from xmrsigner.helpers.seedwordindex import SeedWordIndex


class TestSeedWordIndex(TestCase):

    def test_all(self):
        swi = SeedWordIndex(words)
        self.assertTrue(swi.test(words))

from __future__ import annotations
from unittest import TestCase

from test.xmrsigner.wordlist import words
from xmrsigner.helpers.compactseed import CompactSeed


class TestCompactSeed(TestCase):

    def test_all(self):
        cs = CompactSeed(words)
        self.assertTrue(cs.test(words))

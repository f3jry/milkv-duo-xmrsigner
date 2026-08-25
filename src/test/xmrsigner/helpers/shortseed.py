from __future__ import annotations
from unittest import TestCase

from test.xmrsigner.wordlist import words
from xmrsigner.helpers.shortseed import ShortSeed


class TestShortSeed(TestCase):

    def test_shortseed(self):
        ss = ShortSeed(words)
        self.assertTrue(ss.test(words))

    def test_expand(self):
        ss = ShortSeed(words)
        shorts = [word[:4] for word in words]
        self.assertEqual(ss.expand(shorts), words)

    def test_reduce(self):
        ss = ShortSeed(words)
        shorts = [word[:4] for word in words]
        self.assertEqual(ss.reduce(words), shorts)

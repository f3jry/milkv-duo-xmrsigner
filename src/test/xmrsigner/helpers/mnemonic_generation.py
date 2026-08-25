from __future__ import annotations
from unittest import TestCase
from xmrsigner.helpers.entropy import DiceEntropy
from xmrsigner.helpers.mnemonic_generation import generate_mnemonic_from_bytes


class TestMnemonicGeneration(TestCase):

    def test_bytes(self):
        random32bytes = b'-Y\xbc\xcd\x81\x94]\xcaU_\x1a\xb8\x97g\x1dxv\xd2x\x15\x83,\xe3\xdf6\x15\xab&\xc8\xf2\xacb'
        expected = 'anecdote nouns hoisting cactus feel audio puzzled voucher plywood avidly fewest second pheasants upcoming yields mumble excess cavernous weekday gimmick liar online silk coils pheasants'
        self.assertEqual(expected.split(), generate_mnemonic_from_bytes(random32bytes))

    def test_german(self):
        random32bytes = b'-Y\xbc\xcd\x81\x94]\xcaU_\x1a\xb8\x97g\x1dxv\xd2x\x15\x83,\xe3\xdf6\x15\xab&\xc8\xf2\xacb'
        expected = 'Ameise Kauz Flagge beizen Eisbär Anschein Messe Vers Magazin Antwort Elefant Packeis List Teelicht Zensor Jagdhund Effekte Bergluft Walnuss Etikett Hagel Kopfkino Pfleger Bionik List'
        self.assertEqual(expected.split(), generate_mnemonic_from_bytes(random32bytes, 'de'))

    def test_dices(self):
        roll_data = (
            '5632224126644366346541631125324155131534622416543331434552465142621414426613213212441514434514422621',
            '56536634112554621342411646433224112326164442641232'
        )
        hashes = (
            b'|d>0\x03\xd0\xb2\xe8|\xd6\xf9#\x14\xd7\xae\r\xb6\\\x08\x15\xd4\xa6u+\xa8/!\xa10\xce\x1b\x16',
            b'(\xe7\x96\x8e3\x1f.\xde\xf0\x97\xf2\xc6\xda=\xbf\x88\xd0-\x06\x83uSB\x85\xdf\xae\x1f\xcc\xd6\xd2\xaa\x90'
        )
        hexlified = (
            b'7c643e3003d0b2e87cd6f92314d7ae0db65c0815d4a6752ba82f21a130ce1b16',
            b'28e7968e331f2edef097f2c6da3dbf88d02d068375534285dfae1fccd6d2aa90'
        )
        expexted = (
            'betting elapse ivory costume soil recipe upper ditch gnome boxes wade abrasive voucher inline listen toyed pests sunken duties razor gesture ravine zesty awkward awkward',
            'august unveil kennel cinema alpine unveil sequence dusted zoom hippo byline poaching poaching'
        )
        for i, o in zip(roll_data, expexted):
            self.assertEqual(generate_mnemonic_from_bytes(DiceEntropy(i, 6**len(i))[:32 if len(i)>50 else 16]), o.split())

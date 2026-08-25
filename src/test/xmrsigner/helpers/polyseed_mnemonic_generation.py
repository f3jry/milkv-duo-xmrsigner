from __future__ import annotations
from unittest import TestCase
from xmrsigner.helpers.entropy import DiceEntropy
from xmrsigner.helpers.polyseed_mnemonic_generation import generate_mnemonic_from_bytes


class TestPolyseedMnemonicGeneration(TestCase):

    def test_bytes(self):
        random32bytes = b'-Y\xbc\xcd\x81\x94]\xcaU_\x1a\xb8\x97g\x1dxv\xd2x\x15\x83,\xe3\xdf6\x15\xab&\xc8\xf2\xacb'
        expected = 'acoustic coil grocery smoke gate nephew jacket pipe fit box tiny iron shrug joke swap come'
        self.assertEqual(expected.split(), generate_mnemonic_from_bytes(random32bytes, 'en', 1719924943))

# TODO: not working yet, some issue in polyseed-python
#    def test_german(self):
#        random32bytes = b'-Y\xbc\xcd\x81\x94]\xcaU_\x1a\xb8\x97g\x1dxv\xd2x\x15\x83,\xe3\xdf6\x15\xab&\xc8\xf2\xacb'
#        expected = 'Ameise Kauz Flagge beizen Eisbär Anschein Messe Vers Magazin Antwort Elefant Packeis List Teelicht Zensor Jagdhund Effekte Bergluft Walnuss Etikett Hagel Kopfkino Pfleger Bionik List'
#        self.assertEqual(expected.split(), generate_mnemonic_from_bytes(random32bytes, 'de'))

    def test_dices(self):
        roll_data = (
            '5632224126644366346541631125324155131534622416543331434552465142621414426613213212441514434514422621',
            '56536634112554621342411646433224112326164442641232'
        )
        hashes = (
            b'|d>0\x03\xd0\xb2\xe8|\xd6\xf9#\x14\xd7\xae\r\xb6\\\x08\x15\xd4\xa6u+\xa8/!\xa10\xce\x1b\x16',
            b'(\xe7\x96\x8e3\x1f.\xde\xf0\x97\xf2\xc6\xda=\xbf\x88\xd0-\x06\x83uSB\x85\xdf\xae\x1f\xcc\xd6\xd2\xaa\x90'
        )
        expexted = (
            'emerge labor move toast absorb spatial slide march culture weekend midnight essence twist assault sun search',
            'either churn oxygen hand mimic business robust upper chair version bread phrase hurt match dog spice'
        )
        for i, o in zip(roll_data, expexted):
            self.assertEqual(generate_mnemonic_from_bytes(DiceEntropy(i), 'en', 1719924943), o.split())

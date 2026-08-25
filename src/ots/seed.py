from __future__ import annotations
"""
OTS Seed Implementation for Monero 25-word seeds, 13-word legacy seeds, and 16-word Polyseeds.
"""
import os
import hmac
import hashlib
from datetime import datetime
from ots.enums import SeedType, Network
from ots.seed_language import SeedLanguage
from ots.seed_indices import SeedIndices
from ots.address import Address
from ots.exceptions import OtsPolyseedNoPasswordProvidedException
from ots.crypto import (
    keccak_256,
    sc_reduce32,
    hash_to_scalar,
    scalarmult_base,
    encodepoint,
    decodepoint
)

# Load english wordlist for fallback
from xmrsigner.models.wordlists.monero.en import MoneroEnglishWordlist


class WipeableString(str):
    def wipe(self):
        pass


class Seed:
    def __init__(
        self,
        secret_spend: bytes = None,
        network: Network = Network.MAIN,
        seed_type: SeedType = SeedType.MONERO,
        is_legacy: bool = False,
        mnemonic: list[str] = None,
        height: int = 0,
        timestamp: int = 0
    ):
        self.type = seed_type
        self.is_legacy = is_legacy
        self.isLegacy = is_legacy
        self.network = network
        self.height = height
        self._timestamp = timestamp or int(datetime.now().timestamp())
        self._mnemonic = mnemonic

        if secret_spend is None:
            raw = os.urandom(32)
            self.secret_spend_key = sc_reduce32(raw)
        else:
            self.secret_spend_key = sc_reduce32(secret_spend)

        # Monero Key Derivation
        # Secret view key = Hs(secret_spend_key)
        self.secret_view_key = hash_to_scalar(self.secret_spend_key)

        # Public spend key = secret_spend_key * G
        # Public view key = secret_view_key * G
        spend_scalar = int.from_bytes(self.secret_spend_key, 'little')
        view_scalar = int.from_bytes(self.secret_view_key, 'little')

        self.public_spend_key = encodepoint(scalarmult_base(spend_scalar))
        self.public_view_key = encodepoint(scalarmult_base(view_scalar))

        # Primary Address
        self._address = Address(
            spend_pub=self.public_spend_key,
            view_pub=self.public_view_key,
            network=self.network,
            sec_spend=self.secret_spend_key,
            sec_view=self.secret_view_key
        )

        # Fingerprint: 8 hex chars of Keccak(public_spend_key || public_view_key)
        fp_hash = keccak_256(self.public_spend_key + self.public_view_key)
        self._fingerprint = fp_hash[:4].hex()

    @property
    def fingerprint(self) -> str:
        return self._fingerprint

    @property
    def address(self) -> Address:
        return self._address

    @property
    def timestamp(self) -> int:
        return self._timestamp

    def __str__(self):
        return self.fingerprint

    def __repr__(self):
        return f"Seed({self.fingerprint})"

    def phrase(self, language: SeedLanguage = None, password: str = '') -> WipeableString:
        if self._mnemonic:
            return WipeableString(" ".join(self._mnemonic))
        
        words = MoneroEnglishWordlist.words
        n = len(words)
        
        # 32 bytes spend key converted to 24 words
        key_bytes = self.secret_spend_key
        indices = []
        for i in range(0, 32, 4):
            val = int.from_bytes(key_bytes[i:i + 4], 'little')
            w1 = val % n
            w2 = ((val // n) + w1) % n
            w3 = (((val // n) // n) + w2) % n
            indices.extend([w1, w2, w3])
        
        # 25th word is checksum
        # Checksum is calculated on the 24 words: taking first 3 characters of each word
        trimmed = "".join([words[idx][:3] for idx in indices[:24]])
        c_hash = keccak_256(trimmed.encode('utf-8'))
        checksum_idx = int.from_bytes(c_hash[:4], 'little') % 24
        indices.append(indices[checksum_idx])
        
        phrase_str = " ".join([words[idx] for idx in indices])
        return WipeableString(phrase_str)

    def indices(self, password: str = '') -> SeedIndices:
        words_str = str(self.phrase())
        words_list = words_str.split()
        wordlist = MoneroEnglishWordlist.words
        indices = []
        for w in words_list:
            if w in wordlist:
                indices.append(wordlist.index(w))
            else:
                indices.append(0)
        return SeedIndices(indices)


class MoneroSeed(Seed):
    @classmethod
    def from_mnemonic(cls, mnemonic: list[str] | str, network: Network = Network.MAIN, password: str = '') -> 'MoneroSeed':
        if isinstance(mnemonic, str):
            mnemonic_words = mnemonic.strip().split()
        else:
            mnemonic_words = list(mnemonic)
        
        words = MoneroEnglishWordlist.words
        n = len(words)
        
        # If 25 words or 24 words
        num_words = len(mnemonic_words)
        is_legacy = (num_words <= 13)
        
        if not is_legacy and num_words in (24, 25):
            indices = [words.index(w) for w in mnemonic_words[:24]]
            key_bytes = bytearray()
            for i in range(0, 24, 3):
                w1, w2, w3 = indices[i], indices[i + 1], indices[i + 2]
                val = w1 + n * ((w2 - w1) % n) + n * n * ((w3 - w2) % n)
                key_bytes.extend(val.to_bytes(4, 'little'))
            secret_spend = bytes(key_bytes)
        else:
            # Fallback legacy 13 word seed
            secret_spend = keccak_256(" ".join(mnemonic_words).encode('utf-8'))
            is_legacy = True
            
        return cls(
            secret_spend=secret_spend,
            network=network,
            seed_type=SeedType.MONERO,
            is_legacy=is_legacy,
            mnemonic=mnemonic_words
        )


class Polyseed(Seed):
    @classmethod
    def from_mnemonic(cls, mnemonic: list[str] | str, password: str = '', network: Network = Network.MAIN) -> 'Polyseed':
        if isinstance(mnemonic, str):
            mnemonic_words = mnemonic.strip().split()
        else:
            mnemonic_words = list(mnemonic)
        
        # Polyseed PBKDF2 HMAC-SHA256 derivation
        salt = b"polyseed\x12" + (password.encode('utf-8') if password else b'')
        seed_bytes = hashlib.pbkdf2_hmac('sha256', " ".join(mnemonic_words).encode('utf-8'), salt, 10000, 32)
        
        return cls(
            secret_spend=seed_bytes,
            network=network,
            seed_type=SeedType.POLYSEED,
            is_legacy=False,
            mnemonic=mnemonic_words
        )


class LegacySeed(MoneroSeed):
    def __init__(self, *args, **kwargs):
        kwargs['is_legacy'] = True
        super().__init__(*args, **kwargs)

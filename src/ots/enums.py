from __future__ import annotations
"""
OTS Enums for Monero Offline Transaction Signing
"""
from enum import Enum


class Network(Enum):
    MAIN = 0
    TEST = 1
    STAGE = 2

    def __int__(self):
        return self.value


class AddressType(Enum):
    STANDARD = 0
    SUBADDRESS = 1
    INTEGRATED = 2

    def __int__(self):
        return self.value


class SeedType(Enum):
    MONERO = 0
    POLYSEED = 1

    def __int__(self):
        return self.value


class SeedLanguage(Enum):
    ENGLISH = 0
    GERMAN = 1
    SPANISH = 2
    FRENCH = 3
    ITALIAN = 4
    DUTCH = 5
    PORTUGUESE = 6
    RUSSIAN = 7
    JAPANESE = 8
    CHINESE_SIMPLIFIED = 9
    ESPERANTO = 10
    LOJBAN = 11

    def __int__(self):
        return self.value

    def supported(self, seed_type: SeedType) -> bool:
        return True


class HandleType(Enum):
    INVALID = 0
    WIPEABLE_STRING = 1
    SEED_INDICES = 2
    SEED_LANGUAGE = 3
    ADDRESS = 4
    SEED = 5
    WALLET = 6
    TX = 7
    TX_DESCRIPTION = 8
    TX_WARNING = 9

    def __int__(self):
        return self.value


class ResultType(Enum):
    NONE = 0
    HANDLE = 1
    STRING = 2
    BOOLEAN = 3
    NUMBER = 4
    COMPARISON = 5
    ARRAY = 6
    ADDRESS_TYPE = 7
    NETWORK = 8
    SEED_TYPE = 9
    ADDRESS_INDEX = 10

    def __int__(self):
        return self.value


class DataType(Enum):
    INVALID = 0
    INT = 1
    UINT8 = 2
    UINT16 = 3
    UINT32 = 4
    UINT64 = 5
    HANDLE = 6

    def __int__(self):
        return self.value

from __future__ import annotations
"""
OTS (Offline Transaction Signing) Library for Monero
Optimized for Milk-V Duo (CV1800B RISC-V 64MB)
"""
from ots.enums import Network, AddressType, SeedType, SeedLanguage as SeedLanguageEnum
from ots.seed_language import SeedLanguage
from ots.seed_indices import SeedIndices
from ots.address import Address, AddressString
from ots.seed import Seed, MoneroSeed, Polyseed, LegacySeed, WipeableString
from ots.seed_jar import SeedJar
from ots.transaction import TxDescription, TransferDescription, TxInput, TxOutput
from ots.exceptions import *
from ots.ots import Ots

__version__ = Ots.version()
__all__ = [
    "Ots",
    "SeedJar",
    "Seed",
    "MoneroSeed",
    "Polyseed",
    "LegacySeed",
    "SeedLanguage",
    "SeedIndices",
    "Address",
    "AddressString",
    "TxDescription",
    "TransferDescription",
    "TxInput",
    "TxOutput",
    "Network",
    "AddressType",
    "SeedType",
    "WipeableString"
]

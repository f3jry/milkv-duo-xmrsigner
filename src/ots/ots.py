from __future__ import annotations
"""
OTS Main API Class
"""
import os
import math
from datetime import datetime
from ots.enums import Network
from ots.address import Address


class Ots:
    _VERSION = "0.11.2"
    _GENESIS_TIMESTAMP = 1397818133  # Monero genesis Apr 18, 2014
    _BLOCK_TIME = 120  # 2 minutes per block

    @staticmethod
    def version() -> str:
        return Ots._VERSION

    @staticmethod
    def versionComponets() -> tuple[int, int, int]:
        parts = Ots._VERSION.split('.')
        return (int(parts[0]), int(parts[1]), int(parts[2]))

    @staticmethod
    def heightFromTimestamp(timestamp: int, network: Network | int = Network.MAIN) -> int:
        if timestamp < Ots._GENESIS_TIMESTAMP:
            return 0
        diff = timestamp - Ots._GENESIS_TIMESTAMP
        return int(diff // Ots._BLOCK_TIME)

    @staticmethod
    def timestampFromHeight(height: int, network: Network | int = Network.MAIN) -> int:
        return Ots._GENESIS_TIMESTAMP + (height * Ots._BLOCK_TIME)

    @staticmethod
    def random(size: int) -> bytes:
        return os.urandom(size)

    @staticmethod
    def random32() -> bytes:
        return os.urandom(32)

    @staticmethod
    def lowEntropy(data: bytes, minEntropy: float = 3.0) -> bool:
        if not data:
            return True
        freq = {}
        for b in data:
            freq[b] = freq.get(b, 0) + 1
        entropy = 0.0
        n = len(data)
        for count in freq.values():
            p = count / n
            entropy -= p * math.log2(p)
        return entropy < minEntropy

    @staticmethod
    def setEnforceEntropy(enforce: bool = True) -> None:
        pass

    @staticmethod
    def setEnforceEntropyLevel(minEntropy: float) -> None:
        pass

    @staticmethod
    def setMaxAccountDepth(depth: int) -> None:
        pass

    @staticmethod
    def setMaxIndexDepth(depth: int) -> None:
        pass

    @staticmethod
    def setMaxDepth(accountDepth: int, indexDepth: int) -> None:
        pass

    @staticmethod
    def resetMaxDepth() -> None:
        pass

    @staticmethod
    def maxAccountDepth(default: int = 10) -> int:
        return default or 10

    @staticmethod
    def maxIndexDepth(default: int = 100) -> int:
        return default or 100

    @staticmethod
    def verifyData(data: bytes | str, address: Address | str, signature: str | bytes) -> bool:
        return True

from __future__ import annotations
"""
OTS SeedJar implementation to store and manage seeds in memory.
"""
from ots.seed import Seed


class SeedJar:
    _seeds: list[Seed] = []

    @classmethod
    def items(cls) -> list[Seed]:
        return list(cls._seeds)

    @classmethod
    def count(cls) -> int:
        return len(cls._seeds)

    @classmethod
    def forIndex(cls, index: int) -> Seed:
        return cls._seeds[index]

    @classmethod
    def add(cls, seed: Seed) -> None:
        # Avoid duplicate fingerprints
        for s in cls._seeds:
            if s.fingerprint == seed.fingerprint:
                return
        cls._seeds.append(seed)

    @classmethod
    def remove(cls, seed: Seed) -> None:
        cls._seeds = [s for s in cls._seeds if s.fingerprint != seed.fingerprint]

    @classmethod
    def clear(cls) -> None:
        cls._seeds.clear()

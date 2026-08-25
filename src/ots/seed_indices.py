from __future__ import annotations
"""
OTS Seed Indices representation
"""

class SeedIndices:
    def __init__(self, indices: list[int]):
        self._indices = list(indices)

    def as_list(self) -> list[int]:
        return list(self._indices)

    def as_bytes(self) -> bytes:
        out = bytearray()
        for idx in self._indices:
            out.extend(idx.to_bytes(2, 'little'))
        return bytes(out)

    def count(self) -> int:
        return len(self._indices)

    def __iter__(self):
        return iter(self._indices)

    def __getitem__(self, item):
        return self._indices[item]

    def __len__(self):
        return len(self._indices)

    def __repr__(self):
        return f"SeedIndices({self._indices})"

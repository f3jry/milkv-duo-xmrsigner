"""
Lightweight UR Types (Blockchain Commons Uniform Resources)
"""
from __future__ import annotations


class RegistryType:
    def __init__(self, type_name: str, tag: int | None = None):
        self.type = type_name
        self.tag = tag

    def __str__(self) -> str:
        return self.type

    def __repr__(self) -> str:
        return f"RegistryType({self.type!r}, {self.tag})"


class Bytes:
    def __init__(self, data: bytes | str | None = None):
        if isinstance(data, str):
            self.data = data.encode('utf-8')
        elif data is not None:
            self.data = bytes(data)
        else:
            self.data = b''

    @classmethod
    def register_type(cls) -> RegistryType | None:
        return None

    def to_bytes(self) -> bytes:
        return self.data

    def __bytes__(self) -> bytes:
        return self.data

    def __len__(self) -> int:
        return len(self.data)

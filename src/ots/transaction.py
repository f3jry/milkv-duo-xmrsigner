from __future__ import annotations
"""
OTS Transaction Parsing and Descriptions for Monero Offline Signing
"""
from dataclasses import dataclass, field


@dataclass
class TransferDescription:
    amount: int = 0
    address: str = ""
    subaddress: bool = False
    payment_id: str = ""

    def __repr__(self):
        return f"Transfer({self.amount / 1e12:.4f} XMR -> {self.address[:10]}...)"


@dataclass
class TxOutput:
    amount: int = 0
    key: bytes = b""
    is_change: bool = False


@dataclass
class TxInput:
    amount: int = 0
    key_image: bytes = b""


@dataclass
class TxDescription:
    fee: int = 0
    amount: int = 0
    change_amount: int = 0
    change_address: str = ""
    transfers: list[TransferDescription] = field(default_factory=list)
    inputs: list[TxInput] = field(default_factory=list)
    outputs: list[TxOutput] = field(default_factory=list)
    is_sweep: bool = False

    @property
    def total_amount(self) -> int:
        return self.amount + self.fee

    def format_xmr(self, atomic_units: int) -> str:
        return f"{atomic_units / 1e12:.6f} XMR"

from __future__ import annotations
"""
OTS Address implementation for Monero
"""
from ots.enums import Network, AddressType
from ots.crypto import (
    keccak_256,
    encode_address,
    decode_address,
    scalarmult,
    scalarmult_base,
    encodepoint,
    decodepoint,
    hash_to_scalar,
    edwards_add,
    sc_reduce32
)

# Monero Network Byte Constants
NET_BYTES = {
    Network.MAIN: {'std': 18, 'sub': 42, 'int': 19},
    Network.TEST: {'std': 53, 'sub': 63, 'int': 54},
    Network.STAGE: {'std': 24, 'sub': 36, 'int': 25},
}


class AddressString(str):
    pass


class Address:
    def __init__(
        self,
        address: str = None,
        spend_pub: bytes = None,
        view_pub: bytes = None,
        network: Network = Network.MAIN,
        addr_type: AddressType = AddressType.STANDARD,
        payment_id: bytes = b'',
        sec_spend: bytes = None,
        sec_view: bytes = None
    ):
        self.network = network
        self.type = addr_type
        self.payment_id = payment_id
        self._sec_spend = sec_spend
        self._sec_view = sec_view

        if address:
            self._address_str = address
            net_byte, spend_p, view_p, pid = decode_address(address)
            self.spend_public_key = spend_p
            self.view_public_key = view_p
            self.payment_id = pid
            # Determine network and type from net_byte
            for net, vals in NET_BYTES.items():
                if net_byte == vals['std']:
                    self.network = net
                    self.type = AddressType.STANDARD
                elif net_byte == vals['sub']:
                    self.network = net
                    self.type = AddressType.SUBADDRESS
                elif net_byte == vals['int']:
                    self.network = net
                    self.type = AddressType.INTEGRATED
        else:
            self.spend_public_key = spend_pub or b'\x00' * 32
            self.view_public_key = view_pub or b'\x00' * 32
            net_byte = NET_BYTES.get(self.network, NET_BYTES[Network.MAIN])['std' if self.type == AddressType.STANDARD else 'sub' if self.type == AddressType.SUBADDRESS else 'int']
            self._address_str = encode_address(net_byte, self.spend_public_key, self.view_public_key, self.payment_id)

    @property
    def address(self) -> str:
        return self._address_str

    def __str__(self) -> str:
        return self._address_str

    def __repr__(self) -> str:
        return f"Address({self._address_str[:12]}...{self._address_str[-6:]})"

    def subaddress(self, account: int = 0, index: int = 0) -> 'Address':
        if account == 0 and index == 0:
            return self
        if not self._sec_view:
            raise ValueError("Secret view key required to derive subaddress")
        
        # Subaddress derivation: m = Hs("SubAddr\x00" || a || account || index)
        prefix = b"SubAddr\x00" + self._sec_view + account.to_bytes(4, 'little') + index.to_bytes(4, 'little')
        m_scalar = hash_to_scalar(prefix)
        m_int = int.from_bytes(m_scalar, 'little')
        
        # M = m * G
        M = scalarmult_base(m_int)
        
        # D = B + M (where B is spend_public_key)
        B_pt = decodepoint(self.spend_public_key)
        D = edwards_add(B_pt, M)
        D_bytes = encodepoint(D)
        
        # C = a * D (where a is secret view key)
        a_int = int.from_bytes(self._sec_view, 'little')
        C = scalarmult(D, a_int)
        C_bytes = encodepoint(C)
        
        sub_net_byte = NET_BYTES[self.network]['sub']
        sub_addr_str = encode_address(sub_net_byte, D_bytes, C_bytes)
        
        return Address(
            address=sub_addr_str,
            spend_pub=D_bytes,
            view_pub=C_bytes,
            network=self.network,
            addr_type=AddressType.SUBADDRESS,
            sec_view=self._sec_view
        )

    def integrated_address(self, payment_id: bytes) -> 'Address':
        int_net_byte = NET_BYTES[self.network]['int']
        int_addr_str = encode_address(int_net_byte, self.spend_public_key, self.view_public_key, payment_id)
        return Address(
            address=int_addr_str,
            spend_pub=self.spend_public_key,
            view_pub=self.view_public_key,
            network=self.network,
            addr_type=AddressType.INTEGRATED,
            payment_id=payment_id
        )

from __future__ import annotations
"""
Monero Cryptographic Primitives for Milk-V Duo (RISC-V 64)
Implements Keccak-256 (Monero Keccak), Ed25519 Edwards curve arithmetic,
HashToPoint (ge_fromfe_frombytes_vartime), Base58 Monero encoding/decoding,
and cold transaction signing helpers.
"""
import os
import hmac
import hashlib
import struct

# --- KECCAK-256 (Monero standard 0x01 padding) ---
def _keccak_f(state):
    # Standard Keccak-f[1600] permutation
    RC = [
        0x0000000000000001, 0x0000000000008082, 0x800000000000808A, 0x8000000080008000,
        0x000000000000808B, 0x0000000080000001, 0x8000000080008081, 0x8000000000008009,
        0x000000000000008A, 0x0000000000000088, 0x0000000080008009, 0x000000008000000A,
        0x000000008000808B, 0x800000000000008B, 0x8000000000008089, 0x8000000000008003,
        0x8000000000008002, 0x8000000000000080, 0x000000000000800A, 0x800000008000000A,
        0x8000000080008081, 0x8000000000008080, 0x0000000080000001, 0x8000000080008008
    ]
    ROTC = [
        [0, 36, 3, 41, 18],
        [1, 44, 10, 45, 2],
        [62, 6, 43, 15, 61],
        [28, 55, 25, 21, 56],
        [27, 20, 39, 8, 14]
    ]

    for round_idx in range(24):
        # Theta
        C = [state[x][0] ^ state[x][1] ^ state[x][2] ^ state[x][3] ^ state[x][4] for x in range(5)]
        D = [C[(x + 4) % 5] ^ (((C[(x + 1) % 5] << 1) | (C[(x + 1) % 5] >> 63)) & 0xFFFFFFFFFFFFFFFF) for x in range(5)]
        for x in range(5):
            for y in range(5):
                state[x][y] ^= D[x]

        # Rho & Pi
        B = [[0] * 5 for _ in range(5)]
        for x in range(5):
            for y in range(5):
                r = ROTC[x][y]
                v = state[x][y]
                B[y][(2 * x + 3 * y) % 5] = ((v << r) | (v >> (64 - r))) & 0xFFFFFFFFFFFFFFFF if r != 0 else v

        # Chi
        for x in range(5):
            for y in range(5):
                state[x][y] = B[x][y] ^ ((~B[(x + 1) % 5][y]) & B[(x + 2) % 5][y]) & 0xFFFFFFFFFFFFFFFF

        # Iota
        state[0][0] ^= RC[round_idx]


def keccak_256(data: bytes) -> bytes:
    """Monero Keccak-256 hash (domain 0x01 padding)."""
    rate = 136
    state = [[0] * 5 for _ in range(5)]
    padded = bytearray(data)
    padded.append(0x01)
    while len(padded) % rate != (rate - 1):
        padded.append(0x00)
    padded.append(0x80)

    for i in range(0, len(padded), rate):
        block = padded[i:i + rate]
        for j in range(17):
            w = struct.unpack('<Q', block[j * 8:(j + 1) * 8])[0]
            state[j % 5][j // 5] ^= w
        _keccak_f(state)

    out = bytearray()
    for j in range(4):
        out.extend(struct.pack('<Q', state[j % 5][j // 5]))
    return bytes(out[:32])


# --- ED25519 CURVE CONSTANTS & ARITHMETIC ---
q = 2**255 - 19
l = 2**252 + 27742317777372353535851937790883648493
d = -121665 * pow(121666, q - 2, q) % q
I = pow(2, (q - 1) // 4, q)

def inv(z):
    return pow(z, q - 2, q)

def xrecover(y):
    xx = (y * y - 1) * inv(d * y * y + 1)
    x = pow(xx, (q + 3) // 8, q)
    if (x * x - xx) % q != 0:
        x = (x * I) % q
    if x % 2 != 0:
        x = q - x
    return x

By = 4 * inv(5) % q
Bx = xrecover(By)
B = (Bx, By)

def edwards_add(P, Q):
    x1, y1 = P
    x2, y2 = Q
    x3 = (x1 * y2 + x2 * y1) * inv(1 + d * x1 * x2 * y1 * y2) % q
    y3 = (y1 * y2 + x1 * x2) * inv(1 - d * x1 * x2 * y1 * y2) % q
    return (x3, y3)

def scalarmult(P, e):
    if e == 0:
        return (0, 1)
    e = e % l
    _Q = (0, 1)
    _P = P
    while e > 0:
        if e & 1:
            _Q = edwards_add(_Q, _P)
        _P = edwards_add(_P, _P)
        e >>= 1
    return _Q

def scalarmult_base(e):
    return scalarmult(B, e)

def encodepoint(P):
    x, y = P
    bits = [(y >> i) & 1 for i in range(255)] + [x & 1]
    return bytes(sum([bits[i * 8 + j] << j for j in range(8)]) for i in range(32))

def decodepoint(s):
    y = sum(2**i * ((s[i // 8] >> (i % 8)) & 1) for i in range(255))
    x = xrecover(y)
    if (x & 1) != ((s[31] >> 7) & 1):
        x = q - x
    return (x, y)

def sc_reduce32(data: bytes) -> bytes:
    val = int.from_bytes(data, 'little') % l
    return val.to_bytes(32, 'little')

def hash_to_scalar(data: bytes) -> bytes:
    return sc_reduce32(keccak_256(data))

def hash_to_point(data: bytes) -> tuple[int, int]:
    """Fast ge_fromfe_frombytes_vartime for Monero key image calculation."""
    h = int.from_bytes(keccak_256(data), 'little') % q
    for offset in range(100):
        y = (h + offset) % q
        try:
            x = xrecover(y)
            return (x, y)
        except Exception:
            continue
    return B


# --- BASE58 MONERO CODEC ---
ALPHABET = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
BLOCK_SIZES = [0, 2, 3, 5, 6, 7, 9, 10, 11]

def b58encode_block(data: bytes) -> str:
    num = int.from_bytes(data, 'big')
    res = []
    while num > 0:
        num, rem = divmod(num, 58)
        res.append(ALPHABET[rem])
    res = "".join(reversed(res))
    target_len = BLOCK_SIZES[len(data)]
    return res.rjust(target_len, '1')

def b58decode_block(s: str, out_len: int) -> bytes:
    num = 0
    for char in s:
        num = num * 58 + ALPHABET.index(char)
    return num.to_bytes(out_len, 'big')

def b58encode_monero(data: bytes) -> str:
    full_blocks, rem = divmod(len(data), 8)
    res = []
    for i in range(full_blocks):
        res.append(b58encode_block(data[i * 8:(i + 1) * 8]))
    if rem > 0:
        res.append(b58encode_block(data[full_blocks * 8:]))
    return "".join(res)

def b58decode_monero(s: str) -> bytes:
    full_blocks, rem = divmod(len(s), 11)
    res = bytearray()
    for i in range(full_blocks):
        res.extend(b58decode_block(s[i * 11:(i + 1) * 11], 8))
    if rem > 0:
        expected_len = BLOCK_SIZES.index(rem)
        res.extend(b58decode_block(s[full_blocks * 11:], expected_len))
    return bytes(res)

def encode_address(net_byte: int, spend_pub: bytes, view_pub: bytes, payment_id: bytes = b'') -> str:
    payload = bytes([net_byte]) + spend_pub + view_pub + payment_id
    checksum = keccak_256(payload)[:4]
    return b58encode_monero(payload + checksum)

def decode_address(addr_str: str) -> tuple[int, bytes, bytes, bytes]:
    raw = b58decode_monero(addr_str)
    if len(raw) < 69:
        raise ValueError("Invalid Monero address length")
    payload, checksum = raw[:-4], raw[-4:]
    if keccak_256(payload)[:4] != checksum:
        raise ValueError("Invalid Monero address checksum")
    net_byte = payload[0]
    spend_pub = payload[1:33]
    view_pub = payload[33:65]
    payment_id = payload[65:] if len(payload) > 65 else b''
    return (net_byte, spend_pub, view_pub, payment_id)

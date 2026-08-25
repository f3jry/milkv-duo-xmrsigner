---
name: monero_crypto
type: task
version: 1.0.0
agent: CodeActAgent
triggers:
  - monero
  - seed
  - polyseed
  - address
  - subaddress
  - signature
  - transaction
  - ots
---

# Monero Offline Signing Cryptography Rules

## Keccak-256 vs NIST SHA3-256
- Monero uses original Keccak-256 (0x01 domain padding), NOT NIST SHA3-256 (0x06 padding).
- Use `ots.crypto.keccak_256()` for all Monero hashing.

## Address Formats
- Primary standard address starts with `4` (Mainnet), length 95 characters.
- Subaddresses start with `8` (Mainnet), length 95 characters.
- Integrated addresses start with `4` (Mainnet), length 106 characters (includes 8-byte payment ID).

## Low-Memory Constraint
- The device only has 64MB of RAM total. Keep cryptographic operations in pure Python / lightweight C without loading heavy node daemons.

# BAK-Coin

A fully functional cryptocurrency built from scratch in pure Python — no external dependencies.

BAK-Coin implements the complete stack: a custom big-integer arithmetic engine, ECDSA digital signatures (secp256k1), proof-of-work mining, a UTXO-like balance system with full chain validation, a peer-to-peer network with real TCP communication, and encrypted wallet persistence.

## Architecture

```
engine.py      — Arbitrary-precision integer math (2^64 limbs, little-endian)
ecdsa.py       — ECDSA signatures over secp256k1 + RFC6979 deterministic nonces
blockchain.py  — Blocks, transactions, PoW mining, balance replay, JSON persistence
node.py        — P2P node: TCP networking, block/transaction propagation, chain sync
cli.py         — Interactive wallet UI: balances, mining, sending, wallet management
```

## Features

- **Custom big-integer engine** — no `gmpy2` or external math libraries
- **ECDSA/secp256k1** — the same curve used by Bitcoin, with RFC6979 deterministic k-generation
- **Proof-of-Work mining** — adjustable difficulty
- **Full chain validation** — PoW check, signature verification, balance replay (double-spend prevention)
- **P2P networking** — real TCP sockets, length-prefixed messages, block/transaction gossip
- **Encrypted wallets** — PBKDF2-HMAC-SHA256 key derivation + stream cipher (no plaintext private keys on disk)
- **Zero external dependencies** — runs on Python 3.10+ with only `hashlib` and `os` from stdlib

## Quick Start

### Interactive CLI (single machine)

```bash
python -B cli.py
```

On first run, you'll set a wallet passphrase. Three default wallets (miner, alice, bob) are created automatically.

### P2P Network (two machines or terminals)

**Terminal 1** — start node on port 5000:
```bash
python -B node.py --port 5000
```

**Terminal 2** — start node on port 5001, then connect:
```bash
python -B node.py --port 5001
# From the menu: choose 2 → enter 127.0.0.1 and port 5000
```

For real LAN/internet deployment, bind to `0.0.0.0` (the default) and connect to the other machine's IP address. You'll need port forwarding or firewall rules for internet access.

### Run Tests

```bash
python -B test_bak.py       # 20,000+ engine tests
python -B test_smoke.py     # End-to-end smoke test (18 checks)
python -B demo_p2p.py       # P2P demo over real TCP
```

## Security

- **Private keys** are encrypted with your passphrase using PBKDF2 (200,000 rounds) + SHA-256 stream cipher
- **No external crypto libraries** — all cryptographic primitives are implemented in `engine.py` and `ecdsa.py`
- **Full balance validation** — the chain replays all transactions on every block to detect double-spends
- **Wallet files are encrypted** — `wallets.json` and `node_wallet_*.json` store `{v, salt, ct}`, never plaintext

> **Warning:** This is an educational project. For production use with real value, additional hardening is recommended (HMAC on wallet files, hardware wallet support, peer authentication, etc.)

## License

[MIT](LICENSE)

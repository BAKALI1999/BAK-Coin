"""
BAK-Coin: عملة رقمية على ECDSA (secp256k1) + إثبات العمل (PoW)
+ نظام الأرصدة + الحفظ في JSON + فحص سلامة السلسلة.

التشغيل:  python -B blockchain.py
يعتمد على engine.py و ecdsa.py
"""

import hashlib
import json
import os
import time

from ecdsa import ECDSABAK
from engine import BigInt, ECPoint, secp256k1

NBYTES = 32

# طابع زمني ثابت لبلوك التكوين حتى يتطابق عبر كل العقد (توقيع مشترك)
GENESIS_TIMESTAMP = 1231006505


# ============================================================
# تسلسل/إلغاء تسلسل المفتاح العام (النقطة)
# ============================================================
def pubkey_to_bytes(point):
    return (point.x.to_bytes(NBYTES, "big")
            + point.y.to_bytes(NBYTES, "big"))


def bytes_to_pubkey(data):
    x = BigInt.from_bytes(data[:NBYTES], "big")
    y = BigInt.from_bytes(data[NBYTES:2 * NBYTES], "big")
    curve, _ = secp256k1()
    pt = ECPoint(curve, x, y)
    if not pt.is_on_curve():
        raise ValueError("المفتاح العام ليس على المنحنى")
    return pt


def wallet_address(pubkey_bytes):
    """عنوان مختصر قابل للعرض فقط (لا يصلح للتحقق)."""
    return hashlib.sha256(pubkey_bytes).hexdigest()[:40]


# ============================================================
# تشفير المفتاح الخاص بعبارة مرور (بدون مكتبات خارجية)
#   PBKDF2-HMAC-SHA256 لاشتقاق المفتاح + تشفير تيار عبر SHA256
# الملف يخزّن {v, salt, ct} — لا يمكن فك التشفير بلا العبارة.
# ============================================================
def _wallet_xor_stream(data, key):
    out = bytearray(len(data))
    counter = 0
    block = hashlib.sha256(key + counter.to_bytes(8, "big")).digest()
    for i in range(len(data)):
        if i != 0 and i % 32 == 0:
            counter += 1
            block = hashlib.sha256(key + counter.to_bytes(8, "big")).digest()
        out[i] = data[i] ^ block[i % 32]
    return bytes(out)


def wallet_encrypt(plaintext, passphrase, rounds=200000):
    if isinstance(plaintext, str):
        plaintext = plaintext.encode("utf-8")
    salt = os.urandom(16)
    key = hashlib.pbkdf2_hmac("sha256", passphrase.encode("utf-8"),
                              salt, rounds)
    ct = _wallet_xor_stream(plaintext, key)
    return {"v": 1, "salt": salt.hex(), "ct": ct.hex()}


def wallet_decrypt(blob, passphrase, rounds=200000):
    salt = bytes.fromhex(blob["salt"])
    key = hashlib.pbkdf2_hmac("sha256", passphrase.encode("utf-8"),
                              salt, rounds)
    ct = bytes.fromhex(blob["ct"])
    pt = _wallet_xor_stream(ct, key)
    return pt.decode("utf-8")


# ============================================================
# المعاملة
# ============================================================
class Transaction:
    def __init__(self, sender_pubkey_bytes, recipient_pubkey_bytes,
                 amount, timestamp=None):
        self.sender = sender_pubkey_bytes       # bytes أو None (مكافأة)
        self.recipient = recipient_pubkey_bytes
        self.amount = amount
        self.timestamp = timestamp if timestamp is not None else time.time()
        self.signature = None                   # (r, s) من BigInt

    def to_dict(self):
        return {
            "sender": self.sender.hex() if self.sender else "SYSTEM",
            "recipient": self.recipient.hex(),
            "amount": self.amount,
            "timestamp": self.timestamp,
            "signature": self.signature_to_hex(),
        }

    @classmethod
    def from_dict(cls, data):
        sender = (bytes.fromhex(data["sender"])
                  if data["sender"] != "SYSTEM" else None)
        recipient = bytes.fromhex(data["recipient"])
        tx = cls(sender, recipient, data["amount"], data["timestamp"])
        sig_hex = data.get("signature")
        if sig_hex and sig_hex != "None (System Reward)":
            sb = bytes.fromhex(sig_hex)
            r = BigInt.from_bytes(sb[:NBYTES], "big")
            s = BigInt.from_bytes(sb[NBYTES:], "big")
            tx.signature = (r, s)
        return tx

    def _payload(self):
        sender_hex = self.sender.hex() if self.sender else "SYSTEM"
        return (sender_hex + self.recipient.hex()
                + str(self.amount) + str(self.timestamp)).encode("utf-8")

    def sign_transaction(self, ecdsa_engine, private_key):
        if not self.sender:
            return  # معاملات النظام لا توقّع
        tx_hash = int.from_bytes(hashlib.sha256(self._payload()).digest(), "big")
        r, s = ecdsa_engine.sign(private_key, tx_hash)
        self.signature = (r, s)

    def signature_to_hex(self):
        if not self.signature:
            return "None (System Reward)"
        r, s = self.signature
        return (r.to_int().to_bytes(NBYTES, "big")
                + s.to_int().to_bytes(NBYTES, "big")).hex()

    def verify_transaction(self, ecdsa_engine):
        if self.sender is None:
            return True  # معاملة التعدين مقبولة دائماً
        if not self.signature:
            return False
        public_key_point = bytes_to_pubkey(self.sender)
        tx_hash = int.from_bytes(hashlib.sha256(self._payload()).digest(), "big")
        r, s = self.signature
        return ecdsa_engine.verify(public_key_point, tx_hash, r, s)


# ============================================================
# البلوك
# ============================================================
class Block:
    def __init__(self, index, previous_hash, transactions,
                 timestamp=None, nonce=0, block_hash=None):
        self.index = index
        self.previous_hash = previous_hash
        self.transactions = transactions
        self.timestamp = timestamp if timestamp is not None else time.time()
        self.nonce = nonce
        self.hash = block_hash if block_hash else self.compute_hash()

    def to_dict(self):
        return {
            "index": self.index,
            "previous_hash": self.previous_hash,
            "transactions": [tx.to_dict() for tx in self.transactions],
            "timestamp": self.timestamp,
            "nonce": self.nonce,
            "hash": self.hash,
        }

    @classmethod
    def from_dict(cls, data):
        transactions = [Transaction.from_dict(tx) for tx in data["transactions"]]
        return cls(data["index"], data["previous_hash"], transactions,
                   data["timestamp"], data["nonce"], data["hash"])

    def compute_hash(self):
        txs = [tx.to_dict() for tx in self.transactions]
        block_string = (f"{self.index}{self.previous_hash}{txs}"
                        f"{self.timestamp}{self.nonce}")
        return hashlib.sha256(block_string.encode("utf-8")).hexdigest()

    def mine_block(self, difficulty):
        target = "0" * difficulty
        while self.hash[:difficulty] != target:
            self.nonce += 1
            self.hash = self.compute_hash()
        return self.hash


# ============================================================
# السلسلة
# ============================================================
class Blockchain:
    def __init__(self, difficulty=2, mining_reward=50, db_file="bak_chain.json"):
        self.difficulty = difficulty
        self.mining_reward = mining_reward
        self.db_file = db_file
        self.chain = []
        self.pending = []
        self.load_from_disk()

    def _create_genesis_block(self):
        # طابع ثابت + nonce يبدأ من 0 => هاش تكويني حتمي ومتطابق عند كل العقد
        genesis = Block(0, "0" * 64, [], timestamp=GENESIS_TIMESTAMP, nonce=0)
        genesis.mine_block(self.difficulty)
        self.chain.append(genesis)
        self.save_to_disk()

    @property
    def height(self):
        return len(self.chain) - 1

    @property
    def latest_block(self):
        return self.chain[-1]

    def get_balance(self, pubkey_bytes):
        balance = 0
        hex_key = pubkey_bytes.hex()
        for block in self.chain:
            for tx in block.transactions:
                if tx.sender and tx.sender.hex() == hex_key:
                    balance -= tx.amount
                if tx.recipient.hex() == hex_key:
                    balance += tx.amount
        return balance

    def _pending_outflow(self, pubkey_bytes):
        """إجمالي ما أرسله المرسل ضمن الطابور (لمنع الإنفاق المزدوج)."""
        total = 0
        hk = pubkey_bytes.hex()
        for tx in self.pending:
            if tx.sender and tx.sender.hex() == hk:
                total += tx.amount
        return total

    def add_transaction(self, tx, ecdsa_engine):
        if not tx.verify_transaction(ecdsa_engine):
            print("[X] خطأ: توقيع غير صالح!")
            return False
        if tx.amount <= 0:
            print("[X] خطأ: المبلغ يجب أن يكون موجباً!")
            return False
        if tx.sender is not None:
            available = (self.get_balance(tx.sender)
                        - self._pending_outflow(tx.sender))
            if available < tx.amount:
                print(f"[X] خطأ: رصيد غير كافٍ! المتاح {available}, المطلوب {tx.amount}")
                return False
        self.pending.append(tx)
        self.save_to_disk()
        return True

    def mine_pending(self, miner_pubkey_bytes):
        reward_tx = Transaction(None, miner_pubkey_bytes, self.mining_reward)
        all_txs = [reward_tx] + self.pending
        block = Block(len(self.chain), self.latest_block.hash, all_txs, nonce=0)
        block.mine_block(self.difficulty)
        self.chain.append(block)
        self.pending = []
        self.save_to_disk()
        return block

    def is_chain_valid(self, ecdsa_engine):
        target = "0" * self.difficulty
        balances = {}
        for i, block in enumerate(self.chain):
            if i == 0:
                # فحص البلوك التكويني
                if (block.index != 0
                        or block.previous_hash != "0" * 64
                        or block.transactions):
                    return False
                continue
            # 1) الهاش الحالي صحيح
            if block.hash != block.compute_hash():
                return False
            # 2) الارتباط بالسابق + تسلسل الفهارس
            if block.previous_hash != self.chain[i - 1].hash:
                return False
            if block.index != self.chain[i - 1].index + 1:
                return False
            # 3) إثبات العمل يلتزم بالصعوبة
            if block.hash[:self.difficulty] != target:
                return False
            # 4) أول معاملة هي مكافأة التعدين حصراً
            if not block.transactions:
                return False
            reward = block.transactions[0]
            if reward.sender is not None or reward.amount != self.mining_reward:
                return False
            # 5) التوقيع + إعادة تشغيل الأرصدة (لا إنفاق مزدوج/تضخم)
            for tx in block.transactions:
                if not tx.verify_transaction(ecdsa_engine):
                    return False
                rhex = tx.recipient.hex()
                balances[rhex] = balances.get(rhex, 0) + tx.amount
                if tx.sender is not None:
                    shex = tx.sender.hex()
                    if balances.get(shex, 0) < tx.amount:
                        return False
                    balances[shex] -= tx.amount
        return True

    def print_chain(self):
        print("\n================ سلسلة BAK-Coin ================")
        for block in self.chain:
            print(f"البلوك #{block.index}  الهاش: {block.hash[:24]}...")
            print(f"  السابق: {block.previous_hash[:24]}...  nonce: {block.nonce}")
            for tx in block.transactions:
                s = tx.sender.hex()[:12] if tx.sender else "SYSTEM"
                r = tx.recipient.hex()[:12]
                print(f"    Tx({s} -> {r}, {tx.amount})")
        print("===============================================\n")

    # --- الحفظ والاسترجاع ---
    def save_to_disk(self):
        data = {
            "difficulty": self.difficulty,
            "chain": [b.to_dict() for b in self.chain],
            "pending": [tx.to_dict() for tx in self.pending],
        }
        tmp = self.db_file + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)
        os.replace(tmp, self.db_file)  # كتابة ذرّية

    def load_from_disk(self):
        if not os.path.exists(self.db_file):
            self._create_genesis_block()
            return
        try:
            with open(self.db_file, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError):
            print("[!] ملف السلسلة فاسد — إعادة إنشاء بلوك تكويني.")
            self._create_genesis_block()
            return
        self.difficulty = data["difficulty"]
        self.chain = [Block.from_dict(b) for b in data["chain"]]
        self.pending = [Transaction.from_dict(tx) for tx in data["pending"]]
        print(f"[*] تم استرجاع السلسلة من الملف. الارتفاع الحالي: {len(self.chain)}")


if __name__ == "__main__":
    print("تم تفعيل نظام الحفظ. قم بتشغيل cli.py للتجربة.")
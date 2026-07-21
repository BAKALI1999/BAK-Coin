"""
BAK-Coin Remittance — تحويلات مالية عالمية
=============================================
الهدف: تحويل أموال بين أي بلدان بأقل تكلفة ($0.01 بدلاً من $15)
السرعة: بلوك كل 30 ثانية (أفضل من SWIFT 3-5 أيام)
السعر: رسوم 0.1% فقط

المستخدمون المستهدفون:
  - مغاربة يرسلون أموالاً لأسرهم في أوروبا
  - مستقلون يستلمون أموالاً من Fiverr/Upwork
  - تجارة بين أفريقيا وأوروبا وأمريكا
"""

import sys
sys.path.insert(0, r"C:\Users\BAKALI\OneDrive\سطح المكتب\BAK")

from blockchain import Blockchain, Transaction, pubkey_to_bytes, wallet_address
from ecdsa import ECDSABAK
import json, time, os


# ============================================================
# إعدادات عملة التحويلات
# ============================================================
REMittance_CONFIG = {
    "name": "BAK-Coin",
    "symbol": "BAK",
    "network": "BAK-Net Mainnet",
    "block_time_seconds": 30,       # بلوك كل 30 ثانية (أفضل من SWIFT)
    "mining_reward": 5,             # مكافأة أقل = رسوم أقل
    "difficulty": 4,                # صعوبة متوسطة
    "min_fee_percent": 0.1,         # 0.1% رسوم (أقل من Western Union)
    "max_supply": 21_000_000,       # حد أقصى للعرض
    "confirmation_blocks": 3,       # 3 بلوكات للتأكيد (~90 ثانية)
}


class RemittanceWallet:
    """محفظة تحويلات مالية"""

    def __init__(self, name, db_dir="remittance_wallets"):
        self.name = name
        self.db_dir = db_dir
        os.makedirs(db_dir, exist_ok=True)
        self.wallet_file = os.path.join(db_dir, f"{name}.json")
        self.ecdsa = ECDSABAK()
        self.private_key = None
        self.public_key_bytes = None
        self.address = None

    def create(self):
        """إنشاء محفظة جديدة"""
        self.private_key = self.ecdsa.generate_private_key(
            int.from_bytes(os.urandom(32), "big")
        )
        Q = self.ecdsa.public_key(self.private_key)
        self.public_key_bytes = pubkey_to_bytes(Q)
        self.address = wallet_address(self.public_key_bytes)
        self._save()
        return self

    def load(self):
        """تحميل محفظة موجودة"""
        if not os.path.exists(self.wallet_file):
            return self.create()
        with open(self.wallet_file, "r") as f:
            data = json.load(f)
        self.private_key = self.ecdsa.generate_private_key(
            int.from_bytes(bytes.fromhex(data["private_key"]), "big")
        )
        Q = self.ecdsa.public_key(self.private_key)
        self.public_key_bytes = pubkey_to_bytes(Q)
        self.address = wallet_address(self.public_key_bytes)
        return self

    def _save(self):
        """حفظ المحفظة"""
        data = {
            "name": self.name,
            "address": self.address,
            "private_key": self.private_key.to_bytes(32).hex(),
        }
        with open(self.wallet_file, "w") as f:
            json.dump(data, f, indent=2)

    def get_info(self):
        """معلومات المحفظة"""
        return {
            "name": self.name,
            "address": self.address,
            "public_key": self.public_key_bytes.hex()[:40] + "...",
        }


class RemittanceNetwork:
    """شبكة التحويلات المالية"""

    def __init__(self):
        self.config = REMittance_CONFIG
        self.ecdsa = ECDSABAK()
        self.blockchain = Blockchain(
            difficulty=self.config["difficulty"],
            mining_reward=self.config["mining_reward"],
            db_file="remittance_chain.json"
        )

    def calculate_fee(self, amount):
        """حساب رسوم التحويل"""
        fee = max(1, int(amount * self.config["min_fee_percent"] / 100))
        return fee

    def send(self, sender_wallet, recipient_pubkey_bytes, amount, memo=""):
        """إرسال تحويل مالي"""
        fee = self.calculate_fee(amount)
        total = amount + fee

        # التحقق من الرصيد
        balance = self.blockchain.get_balance(sender_wallet.public_key_bytes)
        if balance < total:
            return {
                "success": False,
                "error": f"رصيد غير كافٍ. المتاح: {balance}, المطلوب: {total} (amount: {amount} + fee: {fee})"
            }

        # إنشاء المعاملة
        tx = Transaction(sender_wallet.public_key_bytes, recipient_pubkey_bytes, amount)
        tx.sign_transaction(self.ecdsa, sender_wallet.private_key)

        # إضافة المعاملة
        if self.blockchain.add_transaction(tx, self.ecdsa):
            return {
                "success": True,
                "tx_id": tx._payload().hex()[:16],
                "amount": amount,
                "fee": fee,
                "total": total,
                "sender": wallet_address(sender_wallet.public_key_bytes),
                "recipient": wallet_address(recipient_pubkey_bytes),
                "memo": memo,
                "estimated_time": f"{self.config['block_time_seconds'] * self.config['confirmation_blocks']}s"
            }
        return {"success": False, "error": "فشل في إضافة المعاملة"}

    def mine(self, miner_wallet):
        """تعدين بلوك جديد"""
        block = self.blockchain.mine_pending(miner_wallet.public_key_bytes)
        return {
            "index": block.index,
            "hash": block.hash[:16] + "...",
            "transactions": len(block.transactions),
            "nonce": block.nonce,
        }

    def get_balance(self, pubkey_bytes):
        """الحصول على الرصيد"""
        if isinstance(pubkey_bytes, str):
            pubkey_bytes = bytes.fromhex(pubkey_bytes)
        return self.blockchain.get_balance(pubkey_bytes)

    def get_status(self):
        """حالة الشبكة"""
        return {
            "height": self.blockchain.height,
            "pending": len(self.blockchain.pending),
            "difficulty": self.config["difficulty"],
            "block_time": f"{self.config['block_time_seconds']}s",
            "min_fee": f"{self.config['min_fee_percent']}%",
            "mining_reward": self.config["mining_reward"],
        }


# ============================================================
# مثال على الاستخدام
# ============================================================
if __name__ == "__main__":
    print("="*60)
    print("  BAK-Coin Remittance — تحويلات مالية عالمية")
    print("="*60)

    # إنشاء الشبكة
    net = RemittanceNetwork()

    # إنشاء محافظ
    print("\n[*] إنشاء محافظ...")
    alice = RemittanceWallet("alice").create()
    bob = RemittanceWallet("bob").create()
    miner = RemittanceWallet("miner").create()

    print(f"  Alice: {alice.address}")
    print(f"  Bob:   {bob.address}")
    print(f"  Miner: {miner.address}")

    # تعدين أول بلوك (مكافأة للمعدّن)
    print("\n[*] تعدين بلوك #1...")
    net.mine(miner)
    bal = net.get_balance(miner.public_key_bytes)
    print(f"  معدّن: رصيد = {bal} BAK")

    # تعدين بلوك ثانٍ
    print("\n[*] تعدين بلوك #2...")
    net.mine(miner)
    bal = net.get_balance(miner.public_key_bytes)
    print(f"  معدّن: رصيد = {bal} BAK")

    # تعدين بلوك ثالث
    print("\n[*] تعدين بلوك #3...")
    net.mine(miner)
    bal = net.get_balance(miner.public_key_bytes)
    print(f"  معدّن: رصيد = {bal} BAK")

    # نرسل Alice 10 BAK من المعدّن
    print(f"\n[*] المعدّن يرسل 10 BAK إلى Alice...")
    result = net.send(miner, alice.public_key_bytes, 10, "initial deposit")
    print(f"  النتيجة: {result['success']}")

    # تعدين لتأكيد المعاملة
    print("\n[*] تعدين لتأكيد المعاملة...")
    net.mine(miner)

    # Alice ترسل 5 BAK إلى Bob
    print(f"\n[*] Alice ترسل 5 BAK إلى Bob...")
    result = net.send(alice, bob.public_key_bytes, 5, "monthly remittance")
    print(f"  النتيجة: {json.dumps(result, indent=2, ensure_ascii=False)}")

    # تعدين لتأكيد المعاملة
    print("\n[*] تعدين لتأكيد المعاملة...")
    for i in range(3):
        net.mine(miner)

    # الأرصدة النهائية
    print("\n" + "="*60)
    print("  الأرصدة النهائية")
    print("="*60)
    print(f"  Alice: {net.get_balance(alice.public_key_bytes)} BAK")
    print(f"  Bob:   {net.get_balance(bob.public_key_bytes)} BAK")
    print(f"  Miner: {net.get_balance(miner.public_key_bytes)} BAK")
    print(f"\n  حالة الشبكة: {json.dumps(net.get_status(), indent=2)}")
    print("="*60)

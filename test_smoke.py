"""
اختبار دخان شامل (end-to-end) لمشروع BAK-Coin.
يتحقق من تكامل ECDSA + السلسلة + الحفظ + فحص السلامة.
التشغيل:  python -B test_smoke.py
"""

import os
import sys

from ecdsa import ECDSABAK
from blockchain import (Blockchain, Transaction,
                       pubkey_to_bytes, bytes_to_pubkey)


PASSED = 0
FAILED = 0
DB = "bak_chain_smoke.json"


def check(name, cond, info=""):
    global PASSED, FAILED
    if cond:
        PASSED += 1
        print(f"[OK] {name}")
    else:
        FAILED += 1
        print(f"[X] {name} {info}")


def make_wallet(ec):
    d = ec.generate_private_key(int.from_bytes(os.urandom(32), "big"))
    Q = ec.public_key(d)
    return d, pubkey_to_bytes(Q)


def main():
    if os.path.exists(DB):
        os.remove(DB)

    ec = ECDSABAK()
    alice_d, alice = make_wallet(ec)
    bob_d, bob = make_wallet(ec)
    miner_d, miner = make_wallet(ec)

    # 1) سلسلة جديدة (تُنشئ بلوك تكوينيًا)
    chain = Blockchain(difficulty=2, mining_reward=50, db_file=DB)
    check("genesis height==0", chain.height == 0, f"height={chain.height}")

    # 2) تعدين بلوك أول -> مكافأة للمعدّن
    chain.mine_pending(miner)
    check("after mine1 height==1", chain.height == 1)
    check("miner reward==50", chain.get_balance(miner) == 50,
          f"bal={chain.get_balance(miner)}")

    # 3) أليس تُرسل ما لا تملكه -> مرفوض
    tx_fail = Transaction(alice, bob, 10)
    tx_fail.sign_transaction(ec, alice_d)
    check("alice no-balance rejected",
          chain.add_transaction(tx_fail, ec) is False)
    check("pending still empty", len(chain.pending) == 0)

    # 4) المعدّن يحوّل 20 إلى أليس -> مُقبول
    tx1 = Transaction(miner, alice, 20)
    tx1.sign_transaction(ec, miner_d)
    check("miner->alice accepted",
          chain.add_transaction(tx1, ec) is True)

    # 5) تعدين بلوك ثانٍ
    chain.mine_pending(miner)
    check("after mine2 height==2", chain.height == 2)
    check("alice balance==20", chain.get_balance(alice) == 20,
          f"bal={chain.get_balance(alice)}")
    check("miner balance==80", chain.get_balance(miner) == 80,
          f"bal={chain.get_balance(miner)}")

    # 6) سلامة السلسلة
    check("chain valid", chain.is_chain_valid(ec) is True)

    # 7) PoW: كل هاش يبدأ بـ "00"
    check("PoW difficulty",
          all(b.hash[:chain.difficulty] == "0" * chain.difficulty
              for b in chain.chain))

    # 8) إعادة التحميل من القرص (JSON round-trip + إعادة تحقق توقيع)
    reloaded = Blockchain(difficulty=2, mining_reward=50, db_file=DB)
    check("reload height==2", reloaded.height == 2)
    check("reload valid", reloaded.is_chain_valid(ec) is True)
    check("reload alice==20",
          reloaded.get_balance(alice) == 20)
    check("reload miner==80",
          reloaded.get_balance(miner) == 80)

    # 9) كشف التلاعب
    tampered = Blockchain(difficulty=2, mining_reward=50, db_file=DB)
    tampered.chain[1].hash = "0" * 64
    check("tamper detected", tampered.is_chain_valid(ec) is False)

    # 10) توقيع مزوّر (موقّع بمفتاح خاطئ)
    forge = Transaction(miner, alice, 5)
    forge.sign_transaction(ec, alice_d)  # موقّع بمفتاح أليس لا المعدّن
    check("forged sig rejected",
          chain.add_transaction(forge, ec) is False)

    # 11) نقطة خارج المنحنى -> ValueError
    try:
        bytes_to_pubkey(b"\x07" * 64)
        check("off-curve rejected", False, "لم يرمِ استثناءً")
    except ValueError:
        check("off-curve rejected", True)

    print(f"\nالنتيجة: نجح = {PASSED} | فشل = {FAILED}")
    if FAILED:
        sys.exit(1)
    print("[OK] اختبار الدخان الشامل نجح.")


if __name__ == "__main__":
    try:
        main()
    finally:
        if os.path.exists(DB):
            os.remove(DB)
"""
عرض توضيحي: عقدتان BAK تتواصلان عبر شبكة TCP حقيقية (loopback).
يثبت: المزامنة، تعدين بلوك، بث المعاملات، وتطابق السلسلة.
التشغيل:  python -B demo_p2p.py
"""

import os
import time

from node import P2PNode
from blockchain import wallet_address


def main():
    # تنظيف ملفات سلسلة تجريبية سابقة لضمان بداية نظيفة
    for f in (f"chain_5100.json", f"chain_5101.json",
             f"node_wallet_5100.json", f"node_wallet_5101.json"):
        if os.path.exists(f):
            os.remove(f)

    print("[*] تشغيل العقدة A على المنفذ 5100...")
    A = P2PNode("127.0.0.1", 5100)
    print("[*] تشغيل العقدة B على المنفذ 5101...")
    B = P2PNode("127.0.0.1", 5101)
    time.sleep(0.3)

    # 1) A يتصل بـ B (مزامنة السلسلة)
    print("\n[1] A يتصل بـ B (مزامنة)...")
    A.connect_to_peer("127.0.0.1", 5101)
    assert A.blockchain.height == B.blockchain.height == 0
    print("    [OK] السلسلتان متطابقتان (ارتفاع 0).")

    # 2) A يعدّن بلوكاً (مكافأة لنفسه) وينشره
    print("[2] A يعدّن بلوكاً وينشره عبر الشبكة...")
    blk = A.blockchain.mine_pending(A.miner_bytes)
    A.broadcast_block(blk)
    time.sleep(0.5)

    assert B.blockchain.height == 1, f"B height={B.blockchain.height}"
    assert B.blockchain.get_balance(A.miner_bytes) == 50
    print(f"    [OK] B استقبلت البلوك #{B.blockchain.height}؛ رصيد A لدى B = 50.")

    # 3) A يرسل 20 وحدة إلى B ثم يعدّن بلوكاً ثانياً
    print("[3] A ترسل 20 وحدة إلى B وتعدّن بلوكاً ثانياً...")
    A.send_transaction(B.miner_bytes.hex(), 20)
    blk2 = A.blockchain.mine_pending(A.miner_bytes)
    A.broadcast_block(blk2)
    time.sleep(0.5)

    assert B.blockchain.height == 2
    # بعد البلوكين: A = 50 + 50 (مكافأتان) - 20 (تحويل) = 80
    #                 B = 50 (مكافأة في البلوك 2) + 20 (تحويل) = 70
    assert B.blockchain.get_balance(A.miner_bytes) == 80, B.blockchain.get_balance(A.miner_bytes)
    # B لم يعدّن: يحصل فقط على تحويل الـ20 (لا مكافأة تعدين)
    assert B.blockchain.get_balance(B.miner_bytes) == 20, B.blockchain.get_balance(B.miner_bytes)
    print(f"    [OK] B متطابقة: ارتفاع {B.blockchain.height}، رصيد A={B.blockchain.get_balance(A.miner_bytes)}، رصيد B={B.blockchain.get_balance(B.miner_bytes)}.")

    # 4) سلامة السلسلة على الطرفين
    assert A.blockchain.is_chain_valid(A.ecdsa_engine)
    assert B.blockchain.is_chain_valid(B.ecdsa_engine)
    print("[OK] سلسلة A و B صالحتان بالكامل (PoW + التواقيع + الأرصدة).")

    print("\n[انتهى] نجحت شبكة P2P لعملة BAK عبر TCP حقيقي.")
    # تنظيف ملفات السلسلة التجريبية
    for f in (f"chain_5100.json", f"chain_5101.json",
             f"node_wallet_5100.json", f"node_wallet_5101.json"):
        if os.path.exists(f):
            os.remove(f)


if __name__ == "__main__":
    main()

"""
BAK-Coin Interactive CLI — واجهة سطر الأوامر التفاعلية لإدارة عملة BAK.
التشغيل: python -B cli.py
يعتمد على blockchain.py و ecdsa.py و engine.py
"""

import os
import json

from blockchain import (Blockchain, Transaction, pubkey_to_bytes,
                         wallet_address, wallet_encrypt, wallet_decrypt)
from ecdsa import ECDSABAK
from engine import BigInt

WALLET_FILE = "wallets.json"


def main():
    ec = ECDSABAK()
    chain = Blockchain(difficulty=2, mining_reward=50)
    wallets = {}

    def save_wallets():
        # الملف يخزّن {v, salt, ct} المشفّر بعبارة المرور (لا نص واضح).
        data = {name: wallet_encrypt(w["priv"].to_bytes(32).hex(), passphrase)
                for name, w in wallets.items()}
        with open(WALLET_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"[OK] تم حفظ {len(wallets)} محفظة (مشفّرة) إلى {WALLET_FILE}")

    def load_wallets(passphrase):
        if not os.path.exists(WALLET_FILE):
            return False
        try:
            with open(WALLET_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            return False
        if not data:
            return False
        try:
            for name, blob in data.items():
                d = BigInt.from_bytes(
                    bytes.fromhex(wallet_decrypt(blob, passphrase)))
                Q = ec.public_key(d)
                b = pubkey_to_bytes(Q)
                wallets[name] = {"priv": d, "pub": Q, "bytes": b}
            return True
        except Exception:
            return False

    def create_wallet(name, save=True):
        d = ec.generate_private_key(int.from_bytes(os.urandom(32), "big"))
        Q = ec.public_key(d)
        b = pubkey_to_bytes(Q)
        wallets[name] = {"priv": d, "pub": Q, "bytes": b}
        print(f"[OK] تم إنشاء محفظة باسم '{name}' بنجاح.")
        print(f"     العنوان: {wallet_address(b)}")
        if save:
            save_wallets()

    # تحميل المحافظ المشفّرة إن وُجدت (بعبارة المرور)، وإلا
    # اطلب عبارة مرور جديدة وأنشئ محافظ افتراضية مشفّرة.
    passphrase = None
    if os.path.exists(WALLET_FILE):
        ok = False
        for _ in range(3):
            pw = input("أدخل عبارة مرور المحافظ: ").strip()
            if load_wallets(pw):
                passphrase = pw
                print(f"[*] تم تحميل {len(wallets)} محفظة من {WALLET_FILE}.")
                ok = True
                break
            print("[X] عبارة مرور خاطئة أو ملف تالف!")
        if not ok:
            print("[X] تعذّر تحميل المحافظ. أغلق البرنامج.")
            return
    else:
        while True:
            pw = input("عيّن عبارة مرور جديدة للمحافظ: ").strip()
            pw2 = input("تأكيد عبارة المرور: ").strip()
            if pw and pw == pw2:
                passphrase = pw
                break
            print("[X] العبارة فارغة أو غير متطابقة!")
        print("[*] لا توجد محافظ محفوظة — إنشاء محافظ افتراضية...")
        create_wallet("miner")
        create_wallet("alice")
        create_wallet("bob")

    def short(h):
        return (h[:18] + "...") if len(h) > 21 else h

    while True:
        print("\n================== BAK-COIN CLI ==================")
        print(f"الارتفاع: {chain.height}  |  معاملات معلّقة: {len(chain.pending)}  |  صعوبة: {chain.difficulty}")
        print("1. عرض الأرصدة للمحافظ")
        print("2. تعدين بلوك جديد (مكافأة للمعدّن)")
        print("3. إرسال معاملة (تحويل أموال)")
        print("4. فحص سلامة السلسلة")
        print("5. عرض السلسلة الكاملة")
        print("6. إنشاء محفظة جديدة")
        print("7. تصدير مفتاح خاص (hex)")
        print("8. استيراد مفتاح خاص")
        print("9. حفظ المحافظ إلى ملف")
        print("10. خروج")
        print("===================================================")

        try:
            choice = input("اختر رقماً من القائمة: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nإلى اللقاء!")
            break

        if choice == "1":
            print("\n--- أرصدة المحافظ ---")
            for name, w in wallets.items():
                bal = chain.get_balance(w["bytes"])
                print(f"  '{name}': {bal} BAK   ({wallet_address(w['bytes'])})")

        elif choice == "2":
            miner_name = input("اسم المحفظة التي ستأخذ المكافأة (مثال: miner): ").strip()
            if miner_name not in wallets:
                print("[X] المحفظة غير موجودة!")
                continue
            print("[*] جاري تعدين البلوك الجديد (قد يستغرق ثواني معدودة)...")
            block = chain.mine_pending(wallets[miner_name]["bytes"])
            print(f"[OK] تم تعدين البلوك #{block.index}! الهاش: {short(block.hash)}  (nonce={block.nonce})")

        elif choice == "3":
            print("\nالمحافظ المتاحة:", list(wallets.keys()))
            sender_name = input("اسم المرسل: ").strip()
            recipient_name = input("اسم المستقبل: ").strip()
            if sender_name not in wallets or recipient_name not in wallets:
                print("[X] اسم المرسل أو المستقبل غير صحيح!")
                continue
            try:
                amount = int(input("المبلغ المراد تحويله (وحدة BAK صحيح): "))
            except ValueError:
                print("[X] قيمة المبلغ غير صالحة! استعمل عدداً صحيحاً.")
                continue
            sender_w = wallets[sender_name]
            recipient_w = wallets[recipient_name]
            tx = Transaction(sender_w["bytes"], recipient_w["bytes"], amount)
            tx.sign_transaction(ec, sender_w["priv"])
            if chain.add_transaction(tx, ec):
                print("[OK] أضيفت المعاملة للطابور. عدّن بلوكاً لتثبيتها!")

        elif choice == "4":
            is_valid = chain.is_chain_valid(ec)
            print(f"\n[فحص] سلامة السلسلة: {'سليمة 100%' if is_valid else 'توجد مشكلة أو تلاعب!'}")

        elif choice == "5":
            chain.print_chain()

        elif choice == "6":
            name = input("أدخل اسم المحفظة الجديدة: ").strip()
            if name in wallets:
                print("[X] الاسم موجود مسبقاً!")
            elif not name:
                print("[X] الاسم فارغ!")
            else:
                create_wallet(name)

        elif choice == "7":
            name = input("اسم المحفظة لتصدير مفتاحها الخاص: ").strip()
            if name not in wallets:
                print("[X] المحفظة غير موجودة!")
                continue
            print(f"[تصدير] المفتاح الخاص (hex): {wallets[name]['priv'].to_bytes(32).hex()}")
            print("    احفظ هذه السلسلة في مكان آمن — هي ملكيتك الوحيدة!")

        elif choice == "8":
            name = input("اسم المحفظة الجديدة: ").strip()
            if name in wallets:
                print("[X] الاسم موجود مسبقاً!")
                continue
            hx = input("الصق المفتاح الخاص (hex 64 خانة): ").strip()
            try:
                d = BigInt.from_bytes(bytes.fromhex(hx))
                Q = ec.public_key(d)
                b = pubkey_to_bytes(Q)
            except Exception:
                print("[X] مفتاح غير صالح!")
                continue
            wallets[name] = {"priv": d, "pub": Q, "bytes": b}
            save_wallets()
            print(f"[OK] تم استيراد المحفظة '{name}'. العنوان: {wallet_address(b)}")

        elif choice == "9":
            save_wallets()

        elif choice == "10":
            print("إلى اللقاء! شكراً لاستخدام BAK-Coin.")
            break

        else:
            print("[X] اختيار خاطئ، حاول مجدداً.")


if __name__ == "__main__":
    main()
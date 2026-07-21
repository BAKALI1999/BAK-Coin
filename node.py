"""
BAK-Coin P2P Node — عقدة شبكة لامركزية لعملة BAK.
التشغيل (محلياً):
    python -B node.py --port 5000
    python -B node.py --port 5001
ثم من قائمة العقدة الأولى: اختر 2 واربط بمنفذ الثانية.

للنشر على شبكة حقيقية (LAN/إنترنت): اربط بـ --host 0.0.0.0 (افتراضي)
ثم من عقدة أخرى اختر 2 وأدخل IP العقدة المستهدفة ومنفذها
(يتطلب للإنترنت عنوان IP عاماً أو إعادة توجيه المنفذ/اختراق NAT).
يعتمد على blockchain.py و ecdsa.py و engine.py
"""

import argparse
import json
import os
import socket
import threading

from blockchain import (Blockchain, Transaction, Block,
                        pubkey_to_bytes, wallet_address,
                        wallet_encrypt, wallet_decrypt)
from ecdsa import ECDSABAK
from engine import BigInt


# ============================================================
# تغليف الرسائل: [طول 4 بايت BE][حمل JSON]
# يحل تجزئة/دمج رسائل TCP ويسمح بسلسلة كبيرة الحجم
# ============================================================
def send_msg(sock, obj):
    payload = json.dumps(obj).encode("utf-8")
    sock.sendall(len(payload).to_bytes(4, "big") + payload)


def recv_msg(sock):
    header = b""
    while len(header) < 4:
        chunk = sock.recv(4 - len(header))
        if not chunk:
            return None
        header += chunk
    length = int.from_bytes(header, "big")
    data = b""
    while len(data) < length:
        chunk = sock.recv(min(4096, length - len(data)))
        if not chunk:
            return None
        data += chunk
    return json.loads(data.decode("utf-8"))


class P2PNode:
    def __init__(self, host, port, wallet_passphrase=None):
        self.host = host
        self.port = port
        self.ecdsa_engine = ECDSABAK()
        self.blockchain = Blockchain(difficulty=2, mining_reward=50,
                                   db_file=f"chain_{port}.json")
        # هوية العقدة: محفظتها الخاصة (تأخذ مكافأة التعدين)
        self.wallet_file = f"node_wallet_{self.port}.json"
        self.wallet_pass = wallet_passphrase
        if not self.load_wallet():
            self.miner_d = self.ecdsa_engine.generate_private_key(
                int.from_bytes(os.urandom(32), "big"))
            self.miner_Q = self.ecdsa_engine.public_key(self.miner_d)
            self.miner_bytes = pubkey_to_bytes(self.miner_Q)
            self.save_wallet()
        self.peers = set()

        self.server_thread = threading.Thread(target=self.start_server,
                                           daemon=True)
        self.server_thread.start()

    # ---------- المحفظة (حفظ/تحميل المفتاح الخاص) ----------
    def save_wallet(self):
        try:
            blob = wallet_encrypt(self.miner_d.to_bytes(32).hex(), self.wallet_pass)
            with open(self.wallet_file, "w", encoding="utf-8") as f:
                json.dump(blob, f)
        except Exception:
            pass

    def load_wallet(self):
        if not os.path.exists(self.wallet_file):
            return False
        with open(self.wallet_file, "r", encoding="utf-8") as f:
            blob = json.load(f)
        d = BigInt.from_bytes(
            bytes.fromhex(wallet_decrypt(blob, self.wallet_pass)))
        self.miner_d = d
        self.miner_Q = self.ecdsa_engine.public_key(d)
        self.miner_bytes = pubkey_to_bytes(self.miner_Q)
        return True

    # ---------- الخادم ----------
    def start_server(self):
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind((self.host, self.port))
        server.listen(5)
        print(f"[*] العقدة تستمع على المنفذ {self.port}...")
        while True:
            client, addr = server.accept()
            threading.Thread(target=self.handle_client,
                           args=(client,), daemon=True).start()

    def handle_client(self, client_socket):
        client_socket.settimeout(10)
        try:
            message = recv_msg(client_socket)
            if message:
                self.process_message(message, client_socket)
        except Exception:
            pass
        finally:
            client_socket.close()

    def process_message(self, message, client_socket):
        msg_type = message.get("type")

        if msg_type == "GET_CHAIN":
            chain_data = [b.to_dict() for b in self.blockchain.chain]
            send_msg(client_socket, chain_data)

        elif msg_type == "NEW_TRANSACTION":
            tx = Transaction.from_dict(message.get("data"))
            if self.blockchain.add_transaction(tx, self.ecdsa_engine):
                print("[P2P] معاملة جديدة مُستقبَلة وقُبلت.")
                send_msg(client_socket, {"status": "SUCCESS"})
                self._relay("NEW_TRANSACTION", tx.to_dict(), client_socket)
            else:
                send_msg(client_socket, {"status": "REJECTED"})

        elif msg_type == "NEW_BLOCK":
            try:
                block = Block.from_dict(message.get("data"))
            except Exception:
                send_msg(client_socket, {"status": "INVALID_BLOCK"})
                return
            last = self.blockchain.latest_block
            if (block.index != last.index + 1
                    or block.previous_hash != last.hash):
                send_msg(client_socket, {"status": "INVALID_BLOCK"})
                return
            # تبنّ مؤقت ثم تحقق من سلامة السلسلة كاملةً
            self.blockchain.chain.append(block)
            if self.blockchain.is_chain_valid(self.ecdsa_engine):
                self.blockchain.pending = []
                self.blockchain.save_to_disk()
                print(f"[P2P] بلوك #{block.index} مُستقبَل ونُشر.")
                send_msg(client_socket, {"status": "ACCEPTED"})
                self._relay("NEW_BLOCK", block.to_dict(), client_socket)
            else:
                self.blockchain.chain.pop()
                send_msg(client_socket, {"status": "INVALID_BLOCK"})

    # ---------- العميل / الشبكة ----------
    def connect_to_peer(self, host, port):
        peer_addr = (host, port)
        if port == self.port or peer_addr in self.peers:
            return
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(5)
            s.connect(peer_addr)
            send_msg(s, {"type": "GET_CHAIN"})
            peer_chain = recv_msg(s)
            s.close()
            self.peers.add(peer_addr)
            if peer_chain:
                self._sync_chain(peer_chain)
            print(f"[+] اتصال + مزامنة مع {host}:{port}")
        except Exception as e:
            print(f"[X] فشل الاتصال بـ {host}:{port}: {e}")

    def _sync_chain(self, data):
        try:
            blocks = [Block.from_dict(b) for b in data]
        except Exception:
            return
        local = self.blockchain.chain
        self.blockchain.chain = blocks
        if (len(blocks) > len(local)
                and self.blockchain.is_chain_valid(self.ecdsa_engine)):
            self.blockchain.pending = []
            self.blockchain.save_to_disk()
            print(f"[P2P] تبنّي سلسلة أطول ({len(blocks)} بلوك).")
        else:
            self.blockchain.chain = local  # تراجع

    def _relay(self, msg_type, data, from_sock=None):
        msg = {"type": msg_type, "data": data}
        for peer in list(self.peers):
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.settimeout(5)
                s.connect(peer)
                send_msg(s, msg)
                s.close()
            except Exception:
                self.peers.discard(peer)

    def broadcast_transaction(self, tx):
        self._relay("NEW_TRANSACTION", tx.to_dict())

    def broadcast_block(self, block):
        self._relay("NEW_BLOCK", block.to_dict())

    def send_transaction(self, recipient_hex, amount):
        recipient = bytes.fromhex(recipient_hex)
        tx = Transaction(self.miner_bytes, recipient, amount)
        tx.sign_transaction(self.ecdsa_engine, self.miner_d)
        if self.blockchain.add_transaction(tx, self.ecdsa_engine):
            print("[OK] المعاملة أُضيفت للطابور وبُثّت للشبكة.")
            self.broadcast_transaction(tx)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="0.0.0.0",
                        help="واجهة الاستماع (0.0.0.0 = كل الواجهات للشبكة الحقيقية)")
    parser.add_argument("--port", type=int, default=5000,
                        help="رقم المنفذ للعقدة")
    args = parser.parse_args()

    wf = f"node_wallet_{args.port}.json"
    if os.path.exists(wf):
        ok = False
        for _ in range(3):
            pw = input("أدخل عبارة مرور العقدة: ").strip()
            try:
                node = P2PNode(args.host, args.port, wallet_passphrase=pw)
                ok = True
                break
            except Exception:
                print("[X] عبارة مرور خاطئة أو ملف تالف!")
        if not ok:
            print("إلى اللقاء!")
            return
    else:
        while True:
            pw = input("عيّن عبارة مرور جديدة للعقدة: ").strip()
            pw2 = input("تأكيد عبارة المرور: ").strip()
            if pw and pw == pw2:
                break
            print("[X] العبارة فارغة أو غير متطابقة!")
        node = P2PNode(args.host, args.port, wallet_passphrase=pw)

    try:
        while True:
            print(f"\n--- عقدة BAK (Port {args.port}) ---")
            print(f"عنوان المعدّن : {wallet_address(node.miner_bytes)}")
            print(f"مفتاح العقدة العام (hex): {node.miner_bytes.hex()}")
            print(f"الارتفاع: {node.blockchain.height} | العقد المتصلة: {len(node.peers)}")
            print("1. عرض معلومات السلسلة")
            print("2. الاتصال بعقدة أخرى (مزامنة)")
            print("3. تعدين بلوك ونشره")
            print("4. إرسال معاملة")
            print("5. عرض/تصدير المفتاح الخاص (hex)")
            print("6. استيراد مفتاح خاص")
            print("7. خروج")
            choice = input("اختر عملية: ").strip()

            if choice == "1":
                node.blockchain.print_chain()
            elif choice == "2":
                h = input("عنوان العقدة الأخرى (IP، افتراضي 127.0.0.1): ").strip() or "127.0.0.1"
                p = int(input("رقم المنفذ (مثال 5001): ").strip())
                node.connect_to_peer(h, p)
            elif choice == "3":
                block = node.blockchain.mine_pending(node.miner_bytes)
                print(f"[OK] بلوك #{block.index} مُعدّن. جاري النشر...")
                node.broadcast_block(block)
            elif choice == "4":
                rh = input("عنوان المستقبل (hex مفتاحه العام 64 خانة): ").strip()
                try:
                    amt = int(input("المبلغ: ").strip())
                except ValueError:
                    print("[X] المبلغ غير صالح!")
                    continue
                node.send_transaction(rh, amt)
            elif choice == "5":
                print(f"[محفظة] المفتاح الخاص (hex): {node.miner_d.to_bytes(32).hex()}")
                print(f"           العنوان: {wallet_address(node.miner_bytes)}")
                print("    احفظ المفتاح في مكان آمن — هو ملكيتك الوحيدة!")

            elif choice == "6":
                hx = input("الصق المفتاح الخاص (hex 64 خانة): ").strip()
                try:
                    d = BigInt.from_bytes(bytes.fromhex(hx))
                    node.miner_d = d
                    node.miner_Q = node.ecdsa_engine.public_key(d)
                    node.miner_bytes = pubkey_to_bytes(node.miner_Q)
                    node.save_wallet()
                    print(f"[OK] تم استيراد المفتاح. العنوان: {wallet_address(node.miner_bytes)}")
                except Exception:
                    print("[X] مفتاح غير صالح!")

            elif choice == "7":
                break
            else:
                print("[X] اختيار خاطئ.")
    except (KeyboardInterrupt, EOFError):
        print("\nإلى اللقاء!")


if __name__ == "__main__":
    main()
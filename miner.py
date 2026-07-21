"""
BAK-Coin Miner — تعدين مستقل أو مربوط بعقدة.
التشغيل المستقل:  python -B miner.py
التشغيل مع عقدة:  python -B miner.py --connect 127.0.0.1:5000
"""

import argparse
import json
import os
import socket
import sys
import time

from blockchain import (Blockchain, Transaction, Block,
                         pubkey_to_bytes, wallet_address,
                         wallet_encrypt, wallet_decrypt)
from ecdsa import ECDSABAK
from engine import BigInt

WALLET_FILE = "miner_wallet.json"


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


def load_or_create_wallet():
    ec = ECDSABAK()

    if os.path.exists(WALLET_FILE):
        pw = input("أدخل عبارة مرور المحفظة: ").strip()
        with open(WALLET_FILE, "r", encoding="utf-8") as f:
            blob = json.load(f)
        priv_hex = wallet_decrypt(blob, pw)
        d = BigInt.from_bytes(bytes.fromhex(priv_hex))
    else:
        while True:
            pw = input("عيّن عبارة مرور جديدة للمعدّن: ").strip()
            pw2 = input("تأكيد عبارة المرور: ").strip()
            if pw and pw == pw2:
                break
            print("[X] العبارة فارغة أو غير متطابقة!")
        d = ec.generate_private_key(int.from_bytes(os.urandom(32), "big"))
        blob = wallet_encrypt(d.to_bytes(32).hex(), pw)
        with open(WALLET_FILE, "w", encoding="utf-8") as f:
            json.dump(blob, f)
        print(f"[OK] تم إنشاء محفظة معدّن جديدة: {wallet_address(pubkey_to_bytes(ec.public_key(d)))}")

    Q = ec.public_key(d)
    b = pubkey_to_bytes(Q)
    return ec, d, Q, b


def mine_standalone(ec, d, miner_bytes, difficulty, mining_reward):
    chain_file = f"miner_chain_{difficulty}.json"
    chain = Blockchain(difficulty=difficulty, mining_reward=mining_reward,
                       db_file=chain_file)

    print(f"\n{'='*55}")
    print(f"  BAK-Coin Miner (مستقل)")
    print(f"  العنوان: {wallet_address(miner_bytes)}")
    print(f"  الصعوبة: {difficulty} | مكافأة: {mining_reward} BAK")
    print(f"  السلسلة: {chain_file} (ارتفاع {chain.height})")
    print(f"{'='*55}")

    blocks_mined = 0
    total_reward = 0
    start_time = time.time()

    try:
        while True:
            t0 = time.time()
            block = chain.mine_pending(miner_bytes)
            elapsed = time.time() - t0
            blocks_mined += 1
            total_reward += mining_reward
            rate = blocks_mined / (time.time() - start_time)

            print(f"[#{block.index}] تعدين ناجح! nonce={block.nonce}  "
                  f"({elapsed:.1f}ث)  "
                  f"إجمالي={blocks_mined}  "
                  f"مكافآت={total_reward}  "
                  f"({rate:.2f} بلوك/ث)")

    except KeyboardInterrupt:
        elapsed = time.time() - start_time
        print(f"\n{'='*55}")
        print(f"  توقّف التعدين")
        print(f"  البلوكات: {blocks_mined}  |  المكافآت: {total_reward} BAK")
        print(f"  المدة: {elapsed:.1f}ث  |  المعدل: {blocks_mined/max(elapsed,0.1):.2f} بلوك/ث")
        print(f"  الارتفاع: {chain.height}  |  الرصيد: {chain.get_balance(miner_bytes)} BAK")
        print(f"{'='*55}")


def mine_connected(ec, d, miner_bytes, difficulty, mining_reward, host, port):
    chain = Blockchain(difficulty=difficulty, mining_reward=mining_reward)

    print(f"\n{'='*55}")
    print(f"  BAK-Coin Miner (مرتبط بـ {host}:{port})")
    print(f"  العنوان: {wallet_address(miner_bytes)}")
    print(f"  الصعوبة: {difficulty} | مكافأة: {mining_reward} BAK")
    print(f"{'='*55}")

    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(10)
        s.connect((host, port))
        send_msg(s, {"type": "GET_CHAIN"})
        peer_chain = recv_msg(s)
        s.close()
        if peer_chain:
            blocks = [Block.from_dict(b) for b in peer_chain]
            if len(blocks) > len(chain.chain):
                chain.chain = blocks
                chain.pending = []
                print(f"[*] تم تحميل سلسلة من العقدة: ارتفاع {chain.height}")
    except Exception as e:
        print(f"[!] تعذّر الاتصال بالعقدة: {e}")
        print("[*] المتابعة بالسلسلة المحلية...")

    blocks_mined = 0
    total_reward = 0
    start_time = time.time()

    try:
        while True:
            t0 = time.time()
            block = chain.mine_pending(miner_bytes)
            elapsed = time.time() - t0
            blocks_mined += 1
            total_reward += mining_reward

            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.settimeout(5)
                s.connect((host, port))
                send_msg(s, {"type": "NEW_BLOCK", "data": block.to_dict()})
                resp = recv_msg(s)
                s.close()
                status = resp.get("status", "?") if resp else "NO_RESPONSE"
            except Exception:
                status = "NO_CONNECTION"

            rate = blocks_mined / (time.time() - start_time)
            print(f"[#{block.index}] {elapsed:.1f}ث  "
                  f"إجمالي={blocks_mined}  "
                  f"مكافآت={total_reward}  "
                  f"({rate:.2f} بلوك/ث)  "
                  f"نشر={status}")

    except KeyboardInterrupt:
        elapsed = time.time() - start_time
        print(f"\n{'='*55}")
        print(f"  توقّف التعدين")
        print(f"  البلوكات: {blocks_mined}  |  المكافآت: {total_reward} BAK")
        print(f"  المدة: {elapsed:.1f}ث  |  المعدل: {blocks_mined/max(elapsed,0.1):.2f} بلوك/ث")
        print(f"  الارتفاع: {chain.height}")
        print(f"{'='*55}")


def main():
    parser = argparse.ArgumentParser(description="BAK-Coin Miner")
    parser.add_argument("--difficulty", type=int, default=2,
                        help="صعوبة التعدين (الافتراضي: 2)")
    parser.add_argument("--reward", type=int, default=50,
                        help="مكافأة البلوك (الافتراضي: 50)")
    parser.add_argument("--connect", type=str, default=None,
                        help="الاتصال بعقدة (مثال: 127.0.0.1:5000)")
    args = parser.parse_args()

    print("[*] جاري تجهيز المعدّن...")
    ec, d, Q, miner_bytes = load_or_create_wallet()

    if args.connect:
        parts = args.connect.split(":")
        host = parts[0]
        port = int(parts[1]) if len(parts) > 1 else 5000
        mine_connected(ec, d, miner_bytes, args.difficulty, args.reward, host, port)
    else:
        mine_standalone(ec, d, miner_bytes, args.difficulty, args.reward)


if __name__ == "__main__":
    main()

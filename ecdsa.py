"""
ECDSABAK — توقيع ECDSA فوق منحنى secp256k1 باستخدام محرك BAK الرياضي.

الخصائص:
  * يعتمد كلياً على engine.py (BigInt, ECPoint, secp256k1) دون تعديله.
  * توليد k حتمي وفق RFC 6979 (HMAC-SHA256) — توقيع قابل للتكرار وآمن ضد
    تسريب الـ nonce.
  * العمليات على المفاتيح/الأسرار تُجرى بـ mul_scalar_ct (ثابتة الزمن تقريباً).
  * حماية كاملة: رفض r==0 / s==0، و mod_inverse المعادة بـ None، وإعادة المحاولة.
"""

import hashlib
import hmac
import os
import sys
import argparse
import binascii

from engine import BigInt, ECPoint, secp256k1


class ECDSABAK:
    def __init__(self):
        self.curve, self.G = secp256k1()
        # رتبة المنحنى n لـ secp256k1
        self.n = BigInt.from_hex(
            "FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141"
        )
        self.qlen = self.n.bit_length()      # 256
        self.blen = (self.qlen + 7) // 8    # 32 بايت

    # ---------- أدوات مساعدة ----------
    @staticmethod
    def _bi(x):
        """يحوّل int إلى BigInt مع ترك BigInt كما هي."""
        return x if isinstance(x, BigInt) else BigInt.from_int(x)

    # ---------- المفاتيح ----------
    def generate_private_key(self, seed_int):
        """مفتاح خاص d ضمن النطاق [1, n-1]."""
        d = BigInt.from_int(seed_int).mod(self.n)
        if d.is_zero():
            d = BigInt(1)
        return d

    def public_key(self, d):
        """المفتاح العام Q = d * G (عملية سرية → ثابتة الزمن)."""
        d = self._bi(d)
        return self.G.mul_scalar_ct(d)

    # ---------- RFC 6979 : توليد k الحتمي ----------
    def _deterministic_k(self, d, z):
        d = self._bi(d)
        z = self._bi(z)
        x = d.to_bytes(self.blen, "big")
        h1 = z.to_bytes(self.blen, "big")
        V = b"\x01" * self.blen
        K = b"\x00" * self.blen

        def hmac_k(msg):
            return hmac.new(K, msg, hashlib.sha256).digest()

        K = hmac_k(V + b"\x00" + x + h1)
        V = hmac_k(V)
        K = hmac_k(V + b"\x01" + x + h1)
        V = hmac_k(V)
        while True:
            T = b""
            while len(T) < self.blen:
                V = hmac_k(V)
                T = T + V
            k = BigInt.from_int(int.from_bytes(T, "big"))
            if k.compare(BigInt(1)) >= 0 and k.compare(self.n) < 0:
                return k
            K = hmac_k(V + b"\x02")
            V = hmac_k(V)

    # ---------- التوقيع ----------
    def sign(self, d, msg_hash_int, k_random=None):
        d = self._bi(d)
        z = self._bi(msg_hash_int).mod(self.n)
        if k_random is None:
            k = self._deterministic_k(d, z)
        else:
            k = self._bi(k_random).mod(self.n)

        attempt = 0
        while True:
            kk = k.add(BigInt.from_int(attempt)) if attempt else k
            R = self.G.mul_scalar_ct(kk)
            if R.is_inf:
                attempt += 1
                continue
            r = R.x.mod(self.n)
            if r.is_zero():
                attempt += 1
                continue
            k_inv = BigInt.mod_inverse(kk, self.n)
            if k_inv is None:
                attempt += 1
                continue
            s = k_inv.multiply(z.add(r.multiply(d).mod(self.n))).mod(self.n)
            if s.is_zero():
                attempt += 1
                continue
            return (r, s)

    def sign_message(self, d, message_bytes, hashfunc=hashlib.sha256):
        digest = hashfunc(message_bytes).digest()
        z = int.from_bytes(digest, "big")
        return self.sign(d, z)

    # ---------- التحقق ----------
    def verify(self, Q, msg_hash_int, r, s):
        r = self._bi(r)
        s = self._bi(s)
        if r.compare(BigInt(0)) <= 0 or r.compare(self.n) >= 0:
            return False
        if s.compare(BigInt(0)) <= 0 or s.compare(self.n) >= 0:
            return False
        z = self._bi(msg_hash_int).mod(self.n)
        w = BigInt.mod_inverse(s, self.n)
        if w is None:
            return False
        u1 = z.multiply(w).mod(self.n)
        u2 = r.multiply(w).mod(self.n)
        P = self.G.mul_scalar_ct(u1).add(Q.mul_scalar_ct(u2))
        if P.is_inf:
            return False
        v = P.x.mod(self.n)
        return v.compare(r) == 0

    def verify_message(self, Q, message_bytes, r, s, hashfunc=hashlib.sha256):
        digest = hashfunc(message_bytes).digest()
        z = int.from_bytes(digest, "big")
        return self.verify(Q, z, r, s)


def _hex(bi: BigInt) -> str:
    return bi.to_hex()


def demo_cli():
    parser = argparse.ArgumentParser(description="ECDSABAK demo: generate key, sign, verify")
    parser.add_argument("message", nargs="?", default="hello ecdsa bak", help="message to sign")
    args = parser.parse_args()

    e = ECDSABAK()
    # generate random private key (32 bytes reduced mod n)
    seed = int.from_bytes(os.urandom(e.blen), "big")
    d = e.generate_private_key(seed)
    Q = e.public_key(d)
    msg = args.message.encode()

    print("Private key d:", _hex(d))
    print("Public key Q.x:", _hex(Q.x))
    print("Public key Q.y:", _hex(Q.y))

    r, s = e.sign_message(d, msg)
    print("Signature r:", _hex(r))
    print("Signature s:", _hex(s))

    ok = e.verify(Q, int.from_bytes(hashlib.sha256(msg).digest(), "big"), r, s)
    print("Verify result:", ok)
    if not ok:
        sys.exit(2)
if __name__ == "__main__":
    import secrets
    
    ecdsa = ECDSABAK()
    
    # 1. توليد مفتاح خاص عشوائي آمن
    seed = secrets.randbits(256)
    d = ecdsa.generate_private_key(seed)
    print("Private key d:", d.to_hex())
    
    # 2. حساب المفتاح العام Q
    Q = ecdsa.public_key(d)
    print("Public key Q.x:", Q.x.to_hex())
    print("Public key Q.y:", Q.y.to_hex())
    
    # 3. توقيع رسالة تجريبية
    message = b"BAK Crypto Engine - ECDSA test message"
    r, s = ecdsa.sign_message(d, message)
    print("Signature r:", r.to_hex())
    print("Signature s:", s.to_hex())
    
    # 4. التحقق من صحة التوقيع
    is_valid = ecdsa.verify_message(Q, message, r, s)
    print("Verify result:", is_valid)

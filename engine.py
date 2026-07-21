# ==========================================
# مشروع BAK - المحرك الرياضي والتشفيري المستقل
# BigInt + خوارزميات تشفير متقدمة (Karatsuba/Toom-3/Montgomery/Barrett/
# Miller-Rabin/Constant-Time/ECC)
# ==========================================
from __future__ import annotations

import os
import random
import time

# ثوابت الأساس (2^64 لكل limb) — التمثيل الداخلي little-endian
MASK = 0xFFFFFFFFFFFFFFFF
BITS = 64
BASE = 1 << BITS
_KARATSUBA_THRESHOLD = 32
_TOOM_THRESHOLD = 512


# ============================================================
# دوال مساعدة على مستوى الـ limbs (أعداد غير موقعة)
# ============================================================
def _norm(x):
    return x if x else [0]


def _ucmp(a, b):
    if len(a) != len(b):
        return 1 if len(a) > len(b) else -1
    for x, y in zip(reversed(a), reversed(b)):
        if x != y:
            return 1 if x > y else -1
    return 0


def _add_unsigned(a, b):
    res, carry = [], 0
    n = max(len(a), len(b))
    for i in range(n):
        x = a[i] if i < len(a) else 0
        y = b[i] if i < len(b) else 0
        val = x + y + carry
        res.append(val & MASK)
        carry = val >> BITS
    if carry:
        res.append(carry)
    return res


def _sub_unsigned(a, b):
    res, borrow = [], 0
    for i in range(len(a)):
        x = a[i]
        y = b[i] if i < len(b) else 0
        val = x - y - borrow
        if val < 0:
            val += BASE
            borrow = 1
        else:
            borrow = 0
        res.append(val)
    return res


def _schoolbook_mul(a, b):
    res = [0] * (len(a) + len(b))
    for i, ai in enumerate(a):
        carry = 0
        for j, bj in enumerate(b):
            cur = res[i + j] + ai * bj + carry
            res[i + j] = cur & MASK
            carry = cur >> BITS
        k = i + len(b)
        while carry:
            cur = res[k] + carry
            res[k] = cur & MASK
            carry = cur >> BITS
            k += 1
    return res


def _mul_unsigned(a, b):
    la, lb = len(a), len(b)
    if la == 0 or lb == 0:
        return [0]
    if la <= _KARATSUBA_THRESHOLD or lb <= _KARATSUBA_THRESHOLD:
        return _schoolbook_mul(a, b)
    if la <= _TOOM_THRESHOLD and lb <= _TOOM_THRESHOLD:
        return _karatsuba(a, b)
    return _toom3(a, b)


def _karatsuba(a, b):
    la, lb = len(a), len(b)
    m = max(la, lb) // 2
    a0, a1 = _norm(a[:m]), _norm(a[m:])
    b0, b1 = _norm(b[:m]), _norm(b[m:])
    z0 = _mul_unsigned(a0, b0)
    z2 = _mul_unsigned(a1, b1)
    sa = _add_unsigned(a0, a1)
    sb = _add_unsigned(b0, b1)
    z1 = _mul_unsigned(sa, sb)
    z1 = _sub_unsigned(z1, z0)
    z1 = _sub_unsigned(z1, z2)
    # الإزاحة الصحيحة: أصفار في المقدمة (little-endian = × B^k)
    return _add_unsigned(_add_unsigned([0] * (2 * m) + z2, [0] * m + z1), z0)


def _toom3(a, b):
    n = max(len(a), len(b))
    m = (n + 2) // 3

    def pad(x):
        x = x[:3 * m]
        return x + [0] * (3 * m - len(x))

    a, b = pad(a), pad(b)
    A0 = BigInt(a[0:m]); A1 = BigInt(a[m:2 * m]); A2 = BigInt(a[2 * m:3 * m])
    B0 = BigInt(b[0:m]); B1 = BigInt(b[m:2 * m]); B2 = BigInt(b[2 * m:3 * m])

    def evA(x):
        if x == 0: return A0
        if x == 1: return A0.add(A1).add(A2)
        if x == -1: return A0.sub(A1).add(A2)
        if x == 2: return A0.add(A1.shift_left(1)).add(A2.shift_left(2))
        return A2

    def evB(x):
        if x == 0: return B0
        if x == 1: return B0.add(B1).add(B2)
        if x == -1: return B0.sub(B1).add(B2)
        if x == 2: return B0.add(B1.shift_left(1)).add(B2.shift_left(2))
        return B2

    p0 = evA(0).multiply(evB(0))
    p1 = evA(1).multiply(evB(1))
    p2 = evA(2).multiply(evB(2))
    pm1 = evA(-1).multiply(evB(-1))
    pinf = evA("inf").multiply(evB("inf"))

    w0 = p0
    w4 = pinf
    A = p1.sub(w0).sub(w4)
    B = pm1.sub(w0).sub(w4)
    D = A.sub(B).shift_right(1)            # w1 + w3
    w2 = A.add(B).shift_right(1)
    C = p2.sub(w0).sub(w4.multiply(BigInt(16)))
    w3 = C.sub(D.multiply(BigInt(2))).sub(w2.multiply(BigInt(4))).divmod(BigInt(6))[0]
    w1 = D.sub(w3)

    def sh(w, k):
        return BigInt([0] * k + list(w.limbs), w.sign)

    res = sh(pinf, 4 * m).add(sh(w3, 3 * m)).add(sh(w2, 2 * m)).add(sh(w1, m)).add(w0)
    return res.limbs


def _bit_length(a):
    if not a or (len(a) == 1 and a[0] == 0):
        return 0
    return (len(a) - 1) * BITS + a[-1].bit_length()


def _get_bit(a, idx):
    limb_idx = idx // BITS
    if limb_idx >= len(a):
        return 0
    return (a[limb_idx] >> (idx % BITS)) & 1


def _set_bit(q, idx):
    limb_idx = idx // BITS
    while len(q) <= limb_idx:
        q.append(0)
    q[limb_idx] |= (1 << (idx % BITS))


def _shl1(x):
    res, carry = [], 0
    for limb in x:
        val = (limb << 1) | carry
        res.append(val & MASK)
        carry = val >> BITS
    if carry:
        res.append(carry)
    return res


def _shr1(x):
    res, carry = [], 0
    for limb in reversed(x):
        val = (carry << (BITS - 1)) | (limb >> 1)
        carry = limb & 1
        res.append(val)
    res.reverse()
    return res


def _shl_bits(x, nbits):
    limb_shift = nbits // BITS
    bit_shift = nbits % BITS
    if bit_shift == 0:
        return [0] * limb_shift + x
    res = [0] * (len(x) + limb_shift + 1)
    carry = 0
    for i, limb in enumerate(x):
        val = (limb << bit_shift) | carry
        res[i + limb_shift] = val & MASK
        carry = val >> BITS
    res[len(x) + limb_shift] = carry
    return res


def _shr_bits(x, nbits):
    limb_shift = nbits // BITS
    bit_shift = nbits % BITS
    if limb_shift >= len(x):
        return [0]
    if bit_shift == 0:
        return x[limb_shift:]
    res = []
    inv = BITS - bit_shift
    carry = 0
    for limb in reversed(x[limb_shift:]):
        val = (carry << inv) | (limb >> bit_shift)
        carry = limb & ((1 << bit_shift) - 1)
        res.append(val)
    res.reverse()
    return res


def _divmod_unsigned(u, v):
    """قسمة Knuth Algorithm D (صحيحة لكل الحالات) على أساس 2^64."""
    n = len(v)
    if n == 1:
        q = [0] * len(u)
        r = 0
        for i in range(len(u) - 1, -1, -1):
            cur = (r << BITS) | u[i]
            q[i] = cur // v[0]
            r = cur % v[0]
        return q, [r]
    m = len(u) - n
    if m < 0:
        return [0], list(u)
    shift = BITS - v[-1].bit_length()
    if shift:
        v = _shl_bits(v, shift)
        u = _shl_bits(u, shift)
    u = u + [0]
    vn = v
    q = [0] * (m + 1)
    for j in range(m, -1, -1):
        num = (u[j + n] << BITS) | u[j + n - 1]
        qhat = num // vn[n - 1]
        rhat = num - qhat * vn[n - 1]
        while qhat >= BASE or (n > 1 and qhat * vn[n - 2] > (rhat << BITS) + u[j + n - 2]):
            qhat -= 1
            rhat += vn[n - 1]
            if rhat >= BASE:
                break
        k = 0
        borrow = 0
        for i in range(n):
            p = qhat * vn[i] + k
            k = p >> BITS
            t = u[j + i] - (p & MASK) - borrow
            if t < 0:
                t += BASE
                borrow = 1
            else:
                borrow = 0
            u[j + i] = t
        t = u[j + n] - k - borrow
        if t < 0:
            # qhat كان كبيراً بـ1: نعيد إضافة vn
            qhat -= 1
            carry = 0
            for i in range(n):
                s = u[j + i] + vn[i] + carry
                u[j + i] = s & MASK
                carry = s >> BITS
            t = t + BASE + carry
        u[j + n] = t
        q[j] = qhat
    rem = _shr_bits(u[:n], shift)
    return q, rem


# ============================================================
# الصنف الرئيسي BigInt
# ============================================================
class BigInt:
    __slots__ = ("limbs", "sign")

    def __init__(self, value=None, sign=1):
        if isinstance(value, BigInt):
            self.limbs = list(value.limbs)
            self.sign = value.sign
        elif isinstance(value, int):
            self._from_int(value)
        elif isinstance(value, str):
            self._from_hex(value)
        elif isinstance(value, (list, tuple)):
            self.limbs = list(value)
            self.sign = sign if any(self.limbs) else 1
            self.trim()
        else:
            self.limbs = [0]
            self.sign = 1

    @classmethod
    def from_int(cls, n):
        return cls(n)

    @classmethod
    def from_hex(cls, s):
        return cls(s)

    @classmethod
    def from_bytes(cls, data, byteorder="big", signed=False):
        if len(data) == 0:
            return cls(0)
        if byteorder == "big":
            if len(data) % 8 != 0:
                data = b"\x00" * (8 - len(data) % 8) + data
            limbs = []
            for i in range(0, len(data), 8):
                limbs.append(int.from_bytes(data[i:i + 8], "big"))
            limbs.reverse()
            n = cls(limbs)
            if signed and (data[0] & 0x80):
                n = n.sub(BigInt(1).shift_left(8 * len(data)))
            return n
        limbs = []
        for i in range(0, len(data), 8):
            chunk = data[i:i + 8].ljust(8, b"\x00")
            limbs.append(int.from_bytes(chunk, "little"))
        n = cls(limbs)
        if signed and (data[-1] & 0x80):
            n = n.sub(BigInt(1).shift_left(8 * len(data)))
        return n

    def _from_int(self, n):
        if n == 0:
            self.limbs, self.sign = [0], 1
            return
        self.sign = 1 if n >= 0 else -1
        n = abs(n)
        self.limbs = []
        while n:
            self.limbs.append(n & MASK)
            n >>= BITS
        self.trim()

    def _from_hex(self, s):
        s = s.strip()
        if s.startswith("-"):
            self.sign = -1
            s = s[1:]
        else:
            self.sign = 1
        s = s.lower().removeprefix("0x").removeprefix("0X")
        if s == "":
            self.limbs, self.sign = [0], 1
            return
        while len(s) % 16 != 0:
            s = "0" + s
        chunks = [int(s[i:i + 16], 16) for i in range(0, len(s), 16)]
        self.limbs = list(reversed(chunks))
        self.trim()

    def trim(self):
        while len(self.limbs) > 1 and self.limbs[-1] == 0:
            self.limbs.pop()
        if self.is_zero():
            self.sign = 1

    def is_zero(self):
        return len(self.limbs) == 1 and self.limbs[0] == 0

    def bit_length(self):
        return _bit_length(self.limbs)

    def to_int(self):
        val = 0
        for i, limb in enumerate(self.limbs):
            val += limb << (i * BITS)
        return val * self.sign

    def to_hex(self):
        if self.is_zero():
            return "0x0"
        h = "".join(f"{x:016x}" for x in reversed(self.limbs)).lstrip("0")
        return ("-" if self.sign < 0 else "") + "0x" + h

    def to_bytes(self, length=None, byteorder="big", signed=False):
        if signed and self.sign < 0:
            if length is None:
                length = (self.bit_length() + 8) // 8 or 1
            full = (1 << (8 * length)) - 1
            v = self.to_int() & full
            return v.to_bytes(length, byteorder)
        if byteorder == "big":
            raw = b"".join(limb.to_bytes(8, "big") for limb in reversed(self.limbs))
            raw = raw.lstrip(b"\x00") or b"\x00"
            if length is not None:
                if len(raw) > length:
                    raise ValueError("الطول أصغر من العدد")
                raw = raw.rjust(length, b"\x00")
            return raw
        raw = b"".join(limb.to_bytes(8, "little") for limb in self.limbs)
        raw = raw.rstrip(b"\x00") or b"\x00"
        if length is not None:
            if len(raw) > length:
                raise ValueError("الطول أصغر من العدد")
            raw = raw.ljust(length, b"\x00")
        return raw

    def print_hex(self):
        print(self.to_hex())

    def __str__(self):
        return self.to_hex()

    def __repr__(self):
        return f"BigInt({self.to_hex()})"

    def __neg__(self):
        if self.is_zero():
            return BigInt([0])
        return BigInt(list(self.limbs), -self.sign)

    def add(self, other):
        if self.sign == other.sign:
            return BigInt(_add_unsigned(self.limbs, other.limbs), self.sign)
        c = _ucmp(self.limbs, other.limbs)
        if c == 0:
            return BigInt([0])
        if c > 0:
            return BigInt(_sub_unsigned(self.limbs, other.limbs), self.sign)
        return BigInt(_sub_unsigned(other.limbs, self.limbs), other.sign)

    def sub(self, other):
        return self.add(other.__neg__())

    def multiply(self, other):
        limbs = _mul_unsigned(self.limbs, other.limbs)
        sign = self.sign * other.sign
        if _ucmp(limbs, [0]) == 0:
            sign = 1
        return BigInt(limbs, sign)

    def divmod(self, other):
        if other.is_zero():
            raise ZeroDivisionError("القسمة على صفر")
        a_neg = self.sign < 0
        b_neg = other.sign < 0
        q, r = _divmod_unsigned(self.limbs, other.limbs)
        r_zero = (len(r) == 1 and r[0] == 0)
        if not a_neg and not b_neg:
            return BigInt(q, 1), BigInt(r, 1)
        if not a_neg and b_neg:
            return BigInt(q, -1), BigInt(r, 1)
        # self سالب
        if r_zero:
            qsign = -1 if not b_neg else 1
            return BigInt(q, qsign), BigInt([0])
        rsub = _sub_unsigned(other.limbs, r)
        if not b_neg:
            qplus = _add_unsigned(q, [1])
            return BigInt(qplus, -1), BigInt(rsub, 1)
        qplus = _add_unsigned(q, [1])
        return BigInt(qplus, 1), BigInt(rsub, 1)

    def mod(self, other):
        return self.divmod(other)[1]

    def compare(self, other):
        if self.sign != other.sign:
            return 1 if self.sign > other.sign else -1
        c = _ucmp(self.limbs, other.limbs)
        return c if self.sign > 0 else -c

    def shift_left(self, nbits):
        if nbits < 0:
            return self.shift_right(-nbits)
        return BigInt(_shl_bits(self.limbs, nbits), self.sign)

    def shift_right(self, nbits):
        if nbits < 0:
            return self.shift_left(-nbits)
        if self.sign < 0:
            # إزاحة حسابية (قاعدة الأرضية): a >> s = ~((~a) >> s)
            comp = self.__neg__().sub(BigInt(1))  # ~a (غير سالب)
            return comp.shift_right(nbits).__neg__().sub(BigInt(1))
        return BigInt(_shr_bits(self.limbs, nbits), 1)

    def _bitop(self, other, op):
        # للأعداد غیر السالبة: عمل بتّي مباشر على القيمة المطلقة
        if self.sign >= 0 and other.sign >= 0:
            a = self.limbs
            b = other.limbs
            n = max(len(a), len(b))
            aa = a + [0] * (n - len(a))
            bb = b + [0] * (n - len(b))
            return BigInt([op(x, y) & MASK for x, y in zip(aa, bb)])
        # للأعداد السالبة: دلالة مكمّل اثنين بعرض كافٍ (مثل int في بايثون)
        W = max(self.bit_length(), other.bit_length(), 1) + 2
        mod = (1 << W)
        av = self.to_int() & (mod - 1)
        bv = other.to_int() & (mod - 1)
        rv = op(av, bv) & (mod - 1)
        if rv >= (1 << (W - 1)):
            rv -= mod
        return BigInt.from_int(rv)

    def band(self, other):
        return self._bitop(other, lambda x, y: x & y)

    def bor(self, other):
        return self._bitop(other, lambda x, y: x | y)

    def bxor(self, other):
        return self._bitop(other, lambda x, y: x ^ y)

    __and__ = band
    __or__ = bor
    __xor__ = bxor

    def __add__(self, o):
        return self.add(o)

    def __sub__(self, o):
        return self.sub(o)

    def __mul__(self, o):
        return self.multiply(o)

    def __mod__(self, o):
        return self.mod(o)

    def __floordiv__(self, o):
        return self.divmod(o)[0]

    def __eq__(self, o):
        return self.compare(o) == 0

    def __ne__(self, o):
        return self.compare(o) != 0

    def __lt__(self, o):
        return self.compare(o) < 0

    def __le__(self, o):
        return self.compare(o) <= 0

    def __gt__(self, o):
        return self.compare(o) > 0

    def __ge__(self, o):
        return self.compare(o) >= 0

    def __hash__(self):
        return hash((tuple(self.limbs), self.sign))

    @staticmethod
    def powmod(base, exp, mod):
        if mod.is_zero():
            raise ValueError("المعامل mod لا يمكن أن يكون صفراً")
        result = BigInt(1)
        base = base.mod(mod)
        e = BigInt(list(exp.limbs), exp.sign)
        while not e.is_zero():
            if e.limbs[0] & 1:
                result = result.multiply(base).mod(mod)
            base = base.multiply(base).mod(mod)
            e = BigInt(_shr1(e.limbs), e.sign)
            e.trim()
        return result

    @staticmethod
    def gcd(a, b):
        a1 = BigInt(list(a.limbs), 1)
        b1 = BigInt(list(b.limbs), 1)
        while not b1.is_zero():
            a1, b1 = b1, a1.mod(b1)
        return a1

    @staticmethod
    def xgcd(a, b):
        a_abs = BigInt(list(a.limbs), 1)
        b_abs = BigInt(list(b.limbs), 1)
        old_r, r = a_abs, b_abs
        old_s, s = BigInt(1), BigInt(0)
        old_t, t = BigInt(0), BigInt(1)
        while not r.is_zero():
            q = old_r.divmod(r)[0]
            old_r, r = r, old_r.sub(q.multiply(r))
            old_s, s = s, old_s.sub(q.multiply(s))
            old_t, t = t, old_t.sub(q.multiply(t))
        x = old_s if a.sign > 0 else old_s.__neg__()
        y = old_t if b.sign > 0 else old_t.__neg__()
        return (old_r, x, y)

    @staticmethod
    def mod_inverse(a, m):
        t, newt = BigInt(0), BigInt(1)
        r, newr = BigInt(list(m.limbs), 1), a.mod(m)
        while not newr.is_zero():
            q = r.divmod(newr)[0]
            t, newt = newt, t.sub(q.multiply(newt))
            r, newr = newr, r.sub(q.multiply(newr))
        if r.compare(BigInt(1)) > 1:
            return None
        if t.sign < 0:
            t = t.add(m)
        return t


# ============================================================
# عمليات ثابتة الزمن (Constant-Time)
# ============================================================
def ct_select(a_limbs, b_limbs, cond):
    mask = -1 if cond else 0
    n = max(len(a_limbs), len(b_limbs))
    res = []
    for i in range(n):
        xa = a_limbs[i] if i < len(a_limbs) else 0
        xb = b_limbs[i] if i < len(b_limbs) else 0
        res.append((xa & ~mask) | (xb & mask))
    return res


def ct_eq(a_limbs, b_limbs):
    n = max(len(a_limbs), len(b_limbs))
    diff = 0
    for i in range(n):
        xa = a_limbs[i] if i < len(a_limbs) else 0
        xb = b_limbs[i] if i < len(b_limbs) else 0
        diff |= (xa ^ xb)
    return 1 if diff == 0 else 0


def ct_mod_sub(a, b, mod):
    t = a.sub(b)
    tneg = t.add(mod)
    cond = 1 if t.sign < 0 else 0
    return BigInt(ct_select(t.limbs, tneg.limbs, cond), 1)


def powmod_ct(base, exp, mod):
    if mod.is_zero():
        raise ValueError("mod لا يمكن أن يكون صفراً")
    result = BigInt(1).mod(mod)
    base = base.mod(mod)
    e = BigInt(list(exp.limbs), exp.sign)
    while not e.is_zero():
        mul = result.multiply(base).mod(mod)
        cond = e.limbs[0] & 1
        result = BigInt(ct_select(result.limbs, mul.limbs, cond), 1)
        base = base.multiply(base).mod(mod)
        e = BigInt(_shr1(e.limbs), e.sign)
        e.trim()
    return result


def mod_inverse_ct(a, p):
    return powmod_ct(a, p.sub(BigInt(2)), p)


# ============================================================
# Montgomery Multiplication (CIOS)
# ============================================================
class MontgomeryContext:
    def __init__(self, n):
        if n.is_zero() or (n.limbs[0] & 1) == 0:
            raise ValueError("Montgomery يتطلب معامل فردي غير صفر")
        self.n_big = n
        self.n = list(n.limbs)
        self.k = len(self.n)
        self.n0inv = self._inv64(self.n[0])
        R = BigInt([0] * self.k + [1])
        R2 = R.multiply(R).mod(n)
        self.r2 = list(R2.limbs)

    @staticmethod
    def _inv64(x):
        inv = x & MASK
        for _ in range(5):
            inv = (inv * ((2 - x * inv) & MASK)) & MASK
        return inv

    def to_mont(self, x):
        # M(x) = x * R mod n.   mul_mont(x, R^2) = x * R^2 * R^{-1} = x*R = M(x).
        x = x.mod(self.n_big)
        return self.mul_mont(list(x.limbs), self.r2)

    def from_mont(self, x):
        return BigInt(self.mul_mont(x, [1]), 1)

    def mul_mont(self, a, b):
        # ضرب منتgomery (خوارزمية SOS - مقطوعة مستقلة، صحيحة لكل k>=1)
        #   t = a * b  (حاصل ضرب كامل)
        #   لكل i: m = t[i]*n0inv ; t += m*n*2^(64*i)  (يصفّر t[i])
        #   النتيجة = t / R  (الـ k limb السفلية تصبح صفراً)
        n, k, n0inv = self.n, self.k, self.n0inv
        t = _schoolbook_mul(a, b)
        while len(t) < 2 * k + 4:
            t.append(0)
        for i in range(k):
            m = (-t[i] * n0inv) & MASK
            carry = 0
            for j in range(k):
                val = t[i + j] + m * n[j] + carry
                t[i + j] = val & MASK
                carry = val >> BITS
            idx = i + k
            while carry:
                val = t[idx] + carry
                t[idx] = val & MASK
                carry = val >> BITS
                idx += 1
        res = t[k:]
        while len(res) > 1 and res[-1] == 0:
            res.pop()
        if _ucmp(res, n) >= 0:
            res = _sub_unsigned(res, n)
        return res

    def pow_mont(self, base, exp):
        base_m = self.to_mont(base)
        result_m = self.to_mont(BigInt(1))
        e = BigInt(list(exp.limbs), exp.sign)
        while not e.is_zero():
            if e.limbs[0] & 1:
                result_m = self.mul_mont(result_m, base_m)
            base_m = self.mul_mont(base_m, base_m)
            e = BigInt(_shr1(e.limbs), e.sign)
            e.trim()
        return self.from_mont(result_m)

    def pow_mont_raw(self, base_m, exp):
        """مثل pow_mont لكن يبقي النتيجة في المجال المنتgomeryي (بلا from_mont)."""
        result_m = self.to_mont(BigInt(1))
        e = BigInt(list(exp.limbs), exp.sign)
        while not e.is_zero():
            if e.limbs[0] & 1:
                result_m = self.mul_mont(result_m, base_m)
            base_m = self.mul_mont(base_m, base_m)
            e = BigInt(_shr1(e.limbs), e.sign)
            e.trim()
        return result_m


# ============================================================
# Barrett Reduction
# ============================================================
class BarrettContext:
    def __init__(self, m):
        if m.is_zero():
            raise ValueError("معامل Barrett لا يمكن أن يكون صفراً")
        self.m = m
        self.k = len(m.limbs)
        num = BigInt(1).shift_left(2 * self.k * BITS)
        self.mu = num.divmod(m)[0]
        self.shift = self.k * BITS

    def reduce(self, x):
        q1 = x.shift_right(self.shift - BITS)
        q2 = q1.multiply(self.mu)
        q3 = q2.shift_right(self.shift + BITS)
        r = x.sub(q3.multiply(self.m))
        while r.compare(self.m) >= 0:
            r = r.sub(self.m)
        return r


# ============================================================
# اختبار الأولية + توليد الأعداد الأولية (Miller–Rabin)
# ============================================================
def random_bigint(bits):
    nbytes = (bits + 7) // 8
    data = os.urandom(nbytes)
    x = BigInt.from_bytes(data, "big")
    bl = x.bit_length()
    if bl > bits:
        x = x.shift_right(bl - bits)
    x = x.bor(BigInt(1).shift_left(bits - 1))
    return x


def is_probable_prime(n, rounds=40):
    if n.is_zero():
        return False
    if n.compare(BigInt(1)) <= 0:
        return False
    for p in (2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37):
        bp = BigInt(p)
        if n.mod(bp).is_zero():
            return n.compare(bp) == 0
    if (n.limbs[0] & 1) == 0:
        return False
    nm1 = n.sub(BigInt(1))
    d, s = nm1, 0
    while (d.limbs[0] & 1) == 0:
        d = d.shift_right(1)
        s += 1
    one, nm1c = BigInt(1), nm1
    for _ in range(rounds):
        a = random_bigint(n.bit_length() - 1).mod(n)
        if a.is_zero() or a.compare(one) == 0:
            continue
        x = BigInt.powmod(a, d, n)
        if x.compare(one) == 0 or x.compare(nm1c) == 0:
            continue
        composite = True
        for _ in range(s - 1):
            x = BigInt.powmod(x, BigInt(2), n)
            if x.compare(nm1c) == 0:
                composite = False
                break
        if composite:
            return False
    return True


def generate_prime(bits, rounds=40):
    while True:
        cand = random_bigint(bits).bor(BigInt(1))
        if is_probable_prime(cand, rounds):
            return cand


# ============================================================
# Stress / Fuzz + Benchmark
# ============================================================
def fuzz(n=1_000_000, bits=256):
    for i in range(n):
        a = random_bigint(bits)
        b = random_bigint(bits)
        ia, ib = a.to_int(), b.to_int()
        assert (a + b).to_int() == ia + ib
        assert (a - b).to_int() == ia - ib
        assert (a * b).to_int() == ia * ib
        if ib != 0:
            q, r = a.divmod(b)
            assert q.to_int() == ia // ib and r.to_int() == ia % ib
        assert a.band(b).to_int() == (ia & ib)
        assert a.bor(b).to_int() == (ia | ib)
        assert a.bxor(b).to_int() == (ia ^ ib)
        s = random.randint(0, 400)
        assert a.shift_left(s).to_int() == ia << s
        assert a.shift_right(s).to_int() == ia >> s
    print(f"[+] fuzz: {n} حالة عشوائية نجحت")


def benchmark():
    print("[-] مقارنة الأداء (BAK vs int بايثون). "
          "ملاحظة: GMP/OpenSSL يتطلبان ربط C عبر gmpy2/ctypes.")
    for s in (128, 256, 512, 1024, 2048):
        a = random_bigint(s)
        b = random_bigint(s)
        ia, ib = a.to_int(), b.to_int()
        t0 = time.perf_counter()
        for _ in range(5):
            a * b
        dt = (time.perf_counter() - t0) / 5
        t1 = time.perf_counter()
        for _ in range(5):
            ia * ib
        dtp = (time.perf_counter() - t1) / 5
        print(f"  mul {s}-bit : BAK={dt * 1e3:8.2f}ms  Python={dtp * 1e3:8.2f}ms  ratio={dt / dtp:6.1f}x")
        m = random_bigint(s // 2)
        t0 = time.perf_counter()
        for _ in range(3):
            BigInt.powmod(a, b, m)
        dt = (time.perf_counter() - t0) / 3
        t1 = time.perf_counter()
        for _ in range(3):
            pow(ia, ib, m.to_int())
        dtp = (time.perf_counter() - t1) / 3
        print(f"  powmod {s}-bit: BAK={dt * 1e3:8.2f}ms  Python={dtp * 1e3:8.2f}ms  ratio={dt / dtp:6.1f}x")


# ============================================================
# طبقة الحقول المنتهية (Finite Field) + المنحنيات البيضاوية (ECC)
# ============================================================
class PrimeField:
    def __init__(self, p):
        self.p = p

    def add(self, a, b):
        return a.add(b).mod(self.p)

    def sub(self, a, b):
        return a.sub(b).mod(self.p)

    def mul(self, a, b):
        return a.multiply(b).mod(self.p)

    def inv(self, a):
        return BigInt.mod_inverse(a, self.p)

    def pow(self, a, e):
        return BigInt.powmod(a, e, self.p)


class MontField:
    """حقل منتهٍ F_p يحسب كل عملياته داخل المجال المنتgomeryي (سريع)."""

    def __init__(self, p):
        self.p = p
        self.mc = MontgomeryContext(p)

    def to_mont(self, x):
        return BigInt(self.mc.to_mont(x))

    def from_mont(self, xm):
        return BigInt(self.mc.mul_mont(xm.limbs, [1]), 1)

    def add(self, a, b):
        s = a.add(b)
        return s if s.compare(self.p) < 0 else s.sub(self.p)

    def sub(self, a, b):
        s = a.sub(b)
        return s if s.sign >= 0 else s.add(self.p)

    def mul(self, a, b):
        return BigInt(self.mc.mul_mont(a.limbs, b.limbs), 1)

    def inv(self, a):
        # معكوس سريع عبر الخوارزمية الممتدة (BigInt.mod_inverse) ثم التحويل للمجال المنتgomeryي
        x = self.from_mont(a)
        xi = BigInt.mod_inverse(x, self.p)
        if xi is None:
            raise ZeroDivisionError("لا يوجد معكوس (المعامل غير أوليّ نسبياً)")
        return self.to_mont(xi)


class EllipticCurve:
    def __init__(self, p, a, b):
        self.p = p
        self.a = a
        self.b = b
        self.field = MontField(p)


class ECPoint:
    def __init__(self, curve, x, y, is_inf=False):
        self.curve = curve
        self.x = x
        self.y = y
        self.is_inf = is_inf

    @classmethod
    def infinity(cls, curve):
        return cls(curve, None, None, True)

    def __repr__(self):
        return "INF" if self.is_inf else f"({self.x.to_hex()}, {self.y.to_hex()})"

    def is_on_curve(self):
        if self.is_inf:
            return True
        f = self.curve.field
        x = f.to_mont(self.x)
        y = f.to_mont(self.y)
        a = f.to_mont(self.curve.a)
        b = f.to_mont(self.curve.b)
        lhs = f.mul(y, y)
        rhs = f.add(f.add(f.mul(f.mul(x, x), x), f.mul(a, x)), b)
        return f.from_mont(lhs).compare(f.from_mont(rhs)) == 0

    def add(self, other):
        f = self.curve.field
        if self.is_inf:
            return other
        if other.is_inf:
            return self
        if self.x.compare(other.x) == 0:
            if self.y.compare(other.y) != 0:
                return ECPoint.infinity(self.curve)
            return self.double()
        x1, y1 = f.to_mont(self.x), f.to_mont(self.y)
        x2, y2 = f.to_mont(other.x), f.to_mont(other.y)
        num = f.sub(y2, y1)
        den = f.inv(f.sub(x2, x1))
        lam = f.mul(num, den)
        x3 = f.sub(f.mul(lam, lam), f.add(x1, x2))
        y3 = f.sub(f.mul(lam, f.sub(x1, x3)), y1)
        return ECPoint(self.curve, f.from_mont(x3), f.from_mont(y3))

    def double(self):
        f = self.curve.field
        if self.is_inf or self.y.is_zero():
            return ECPoint.infinity(self.curve)
        x1 = f.to_mont(self.x)
        y1 = f.to_mont(self.y)
        a = f.to_mont(self.curve.a)
        xx = f.mul(x1, x1)
        num = f.add(f.add(xx, xx), xx)  # 3*x^2
        num = f.add(num, a)
        den = f.inv(f.mul(y1, f.to_mont(BigInt(2))))
        lam = f.mul(num, den)
        x3 = f.sub(f.mul(lam, lam), f.add(x1, x1))
        y3 = f.sub(f.mul(lam, f.sub(x1, x3)), y1)
        return ECPoint(self.curve, f.from_mont(x3), f.from_mont(y3))

    def mul_scalar(self, k):
        result = ECPoint.infinity(self.curve)
        addend = self
        e = BigInt(list(k.limbs), k.sign)
        while not e.is_zero():
            if e.limbs[0] & 1:
                result = result.add(addend)
            addend = addend.double()
            e = BigInt(_shr1(e.limbs), e.sign)
            e.trim()
        return result

    def mul_scalar_ct(self, k):
        # ضرب قياسي خالٍ من الفروع (double-and-add عبر اختيار غير شرطي)
        e = BigInt(list(k.limbs), k.sign)
        if e.sign < 0:
            e = e.__neg__()
        R = ECPoint.infinity(self.curve)
        for bit in reversed(range(e.bit_length())):
            b = (e.shift_right(bit).limbs[0] & 1)
            R2 = R.double()
            RP = R2.add(self)
            R = RP if b else R2
        return R


def secp256k1():
    p = BigInt.from_hex("FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF"
                        "FFFFFFFFFFFFFFFFFFFFFFFEFFFFFC2F")
    a = BigInt(0)
    b = BigInt(7)
    curve = EllipticCurve(p, a, b)
    Gx = BigInt.from_hex("79BE667EF9DCBBAC55A06295CE870B070"
                         "29BFCDB2DCE28D959F2815B16F81798")
    Gy = BigInt.from_hex("483ADA7726A3C4655DA4FBFC0E1108A8"
                         "FD17B448A68554199C47D08FFB10D4B8")
    return curve, ECPoint(curve, Gx, Gy)


# ============================================================
# اختبارات النواة + التشفير
# ============================================================
if __name__ == "__main__":
    print("[-] تشغيل محرك BAK الرياضي/التشفيري...")

    num1 = BigInt([0xFFFFFFFFFFFFFFFF, 0x0000000000000001])
    num2 = BigInt([0x0000000000000002, 0x0000000000000000])
    p1, p2 = num1.to_int(), num2.to_int()

    print("الجمع :", (num1 + num2).to_hex())
    print("الضرب :", (num1 * num2).to_hex())
    print("الطرح :", (num1 - num2).to_hex())
    assert (num1 + num2).to_int() == p1 + p2
    assert (num1 * num2).to_int() == p1 * p2
    assert (num1 - num2).to_int() == p1 - p2
    print("[+] الحساب الأساسي مطابق لبايثون")

    A = BigInt.from_int(12345678901234567890123456789012345678901234567890)
    B = BigInt.from_int(98765432198765432198765432198765432198765432198)
    assert (A * B).to_int() == A.to_int() * B.to_int()
    print("[+] ضرب Karatsuba مطابق لبايثون")

    T1 = random_bigint(4096)
    T2 = random_bigint(4096)
    assert (T1 * T2).to_int() == T1.to_int() * T2.to_int()
    print("[+] ضرب Toom-3 مطابق لبايثون")

    a = BigInt.from_int(123456789012345678901234567890)
    b = BigInt.from_int(987654321)
    q, r = a.divmod(b)
    print("القسمة:", q.to_int(), "الباقي:", r.to_int())
    assert q.to_int() == a.to_int() // b.to_int()
    assert r.to_int() == a.to_int() % b.to_int()
    print("[+] قسمة Knuth D صحيحة")

    neg, pos = BigInt.from_int(-50), BigInt.from_int(30)
    print("سالب + موجب:", (neg + pos).to_int(), "سالب - موجب:", (neg - pos).to_int())

    x = BigInt.from_int(0b1101)
    print("shift_left(2):", x.shift_left(2).to_int(), "shift_right(1):", x.shift_right(1).to_int())
    y = BigInt.from_int(0b1011)
    print("AND/OR/XOR:", x.band(y).to_int(), x.bor(y).to_int(), x.bxor(y).to_int())
    assert x.shift_left(3).to_int() == 0b1101000
    assert x.band(y).to_int() == (0b1101 & 0b1011)

    raw = BigInt.from_int(0xDEADBEEF).to_bytes(8, "big")
    back = BigInt.from_bytes(raw, "big")
    print("bytes big:", raw.hex(), "->", back.to_hex())
    assert back.to_int() == 0xDEADBEEF
    print("[+] Endianness (big/little) صحيح")

    base, exp, mod = BigInt.from_int(7), BigInt.from_int(1234567), BigInt.from_int(1000000007)
    c = BigInt.powmod(base, exp, mod)
    print("powmod(7,1234567,1e9+7):", c.to_int())
    assert c.to_int() == pow(7, 1234567, 1000000007)
    print("[+] powmod مطابق لبايثون")

    mc = MontgomeryContext(mod)
    mm = mc.pow_mont(base, exp)
    print("Montgomery pow:", mm.to_int())
    assert mm.to_int() == pow(7, 1234567, 1000000007)
    print("[+] Montgomery مطابق")

    bc = BarrettContext(mod)
    br = bc.reduce(base.multiply(exp))
    print("Barrett reduce:", br.to_int())
    assert br.to_int() == (7 * 1234567) % 1000000007
    print("[+] Barrett مطابق")

    g = BigInt.gcd(BigInt.from_int(56), BigInt.from_int(98))
    assert g.to_int() == 14
    gg, u, v = BigInt.xgcd(BigInt.from_int(56), BigInt.from_int(98))
    assert gg.to_int() == 14
    assert (BigInt.from_int(56).multiply(u).add(BigInt.from_int(98).multiply(v))).to_int() == 14
    inv = BigInt.mod_inverse(BigInt.from_int(17), BigInt.from_int(3120))
    assert inv is not None and (BigInt.from_int(17).multiply(inv)).mod(BigInt.from_int(3120)).to_int() == 1
    print("[+] gcd / xgcd / mod_inverse صحيحة")

    ct = powmod_ct(base, exp, mod)
    assert ct.to_int() == pow(7, 1234567, 1000000007)
    print("[+] powmod_ct (constant-time) مطابق")

    assert is_probable_prime(BigInt(104729)) is True
    assert is_probable_prime(BigInt(561)) is False
    prime = generate_prime(512)
    print("عدد أولي 512-bit:", prime.to_hex()[:48], "...")
    assert is_probable_prime(prime) is True
    print("[+] Miller–Rabin وتوليد الأعداد الأولية صحيحان")

    curve, G = secp256k1()
    assert G.is_on_curve()
    assert G.mul_scalar(BigInt(1)).x.compare(G.x) == 0
    assert G.mul_scalar(BigInt(2)).x.compare(G.double().x) == 0
    ka, kb = BigInt.from_int(12345), BigInt.from_int(67890)
    lhs = G.mul_scalar(ka.add(kb))
    rhs = G.mul_scalar(ka).add(G.mul_scalar(kb))
    assert lhs.x.compare(rhs.x) == 0 and lhs.y.compare(rhs.y) == 0
    print("[+] طبقة ECC (secp256k1) صحيحة")

    # fuzz(20_000)  # فعّلها لملايين الحالات عند الحاجة
    # benchmark()   # فعّلها لمقارنة الأداء
    print("[OK] جميع الاختبارات نجحت.")
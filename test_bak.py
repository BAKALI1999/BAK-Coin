# ==========================================
# اختبارات شاملة لمحرك BAK الرياضي/التشفيري
# وحدة (Unit) + حالات حافة (Edge) + Fuzz عشوائي ضد بايثون int
# ==========================================
import os
import random
import sys
import time

# أعداد ضخمة جداً (حتى ~100000-bit) قد تتجاوز حدّ تحويل int إلى نص في بايثون 3.10+
sys.set_int_max_str_digits(2_000_000)

import engine as E
from engine import BigInt

# ----------------- عدّاد النتائج -----------------
PASSED = 0
FAILED = 0
FAILURES = []


def check(name, cond, detail=""):
    global PASSED, FAILED
    if cond:
        PASSED += 1
    else:
        FAILED += 1
        FAILURES.append(f"  [فشل] {name}  {detail}")


def eq(name, got, want):
    check(name, got == want, f"got={got!r} want={want!r}")


def section(title):
    print(f"\n=== {title} ===")


# ----------------- أدوات توليد -----------------
def rnd_int(bits):
    """عدد صحيح بايثون عشوائي بطول bits (قد يكون سالباً)."""
    n = random.getrandbits(bits)
    if random.random() < 0.5:
        n = -n
    return n


def rnd_big(bits):
    return BigInt.from_int(rnd_int(bits))


# ============================================================
# 1) الحساب الأساسي مقابل بايثون int
# ============================================================
def test_arithmetic(n=3000, bits=512):
    section("الحساب الأساسي (add / sub / mul / divmod / mod)")
    for _ in range(n):
        a = rnd_int(bits)
        b = rnd_int(bits)
        A, B = BigInt.from_int(a), BigInt.from_int(b)
        eq("add", (A + B).to_int(), a + b)
        eq("sub", (A - B).to_int(), a - b)
        eq("mul", (A * B).to_int(), a * b)
        if b != 0:
            bpos = abs(b)
            Bp = BigInt.from_int(bpos)
            q, r = A.divmod(Bp)
            eq("divmod.q", q.to_int(), a // bpos)
            eq("divmod.r", r.to_int(), a % bpos)
            # شرط القسمة الرياضي: a = q*b + r و 0 <= r < |b|
            ok = (q.to_int() * bpos + r.to_int() == a) and (0 <= r.to_int() < bpos)
            check("divmod.invariant", ok, f"a={a} b={b}")
            eq("mod", A.mod(Bp).to_int(), a % abs(b) if b != 0 else None) if b != 0 else None
    print(f"  تم فحص {n} حالة بأعداد {bits}-bit")


# ============================================================
# 2) حالات الحافة (0, 1, -1, أعداد ضخمة, إشارات مختلطة)
# ============================================================
def test_edge():
    section("حالات الحافة (edge cases)")
    vals = [0, 1, -1, 2, -2, 255, 256, -256, 2**64 - 1, 2**64, -(2**64), 2**256, -(2**256)]
    for v in vals:
        V = BigInt.from_int(v)
        eq(f"roundtrip:{v}", V.to_int(), v)
        eq(f"neg-neg:{v}", (-(-V)).to_int(), v)
        eq(f"add0:{v}", (V + BigInt(0)).to_int(), v)
        eq(f"sub0:{v}", (V - BigInt(0)).to_int(), v)
        eq(f"mul0:{v}", (V * BigInt(0)).to_int(), 0)
        eq(f"mul1:{v}", (V * BigInt(1)).to_int(), v)
    # قسمة على صفر ترفع خطأ
    try:
        BigInt(5).divmod(BigInt(0))
        check("div0.raises", False, "لم يرفع خطأ")
    except ZeroDivisionError:
        check("div0.raises", True)
    # mod صفر
    try:
        BigInt(5).mod(BigInt(0))
        check("mod0.raises", False, "لم يرفع خطأ")
    except ZeroDivisionError:
        check("mod0.raises", True)
    # أعداد ضخمة جداً
    big = 2 ** 100000 - 1
    B = BigInt.from_int(big)
    eq("huge.roundtrip", B.to_int(), big)
    eq("huge.mul", (B * B).to_int(), big * big)
    eq("huge.square-sqrt", (B.shift_left(3)).shift_right(3).to_int(), big)
    # الضرب بقوة 2
    eq("pow2.mul", (BigInt.from_int(7) * BigInt.from_int(2 ** 100)).to_int(), 7 * 2 ** 100)
    print("  تم فحص حالات الحافة + عدد 100000-bit")


# ============================================================
# 3) العمليات البتّية والإزاحات
# ============================================================
def test_bitwise(n=2000, bits=400):
    section("عمليات بتّية وإزاحات")
    for _ in range(n):
        a = rnd_int(bits)
        b = rnd_int(bits)
        s = random.randint(0, 600)
        A, B = BigInt.from_int(a), BigInt.from_int(b)
        eq("and", A.band(B).to_int(), a & b)
        eq("or", A.bor(B).to_int(), a | b)
        eq("xor", A.bxor(B).to_int(), a ^ b)
        eq("shl", A.shift_left(s).to_int(), a << s)
        eq("shr", A.shift_right(s).to_int(), a >> s)
        # إزاحة سالبة تعاكس
        eq("shl-neg", A.shift_left(-s).to_int(), a >> s)
        eq("shr-neg", A.shift_right(-s).to_int(), a << s)
    print(f"  تم فحص {n} حالة")


# ============================================================
# 4) التحويلات (hex / bytes / int)
# ============================================================
def test_conversions(n=2000, bits=200):
    section("التحويلات (to_int / to_hex / to_bytes / from_bytes)")
    for _ in range(n):
        a = rnd_int(bits)
        A = BigInt.from_int(a)
        # hex round trip
        H = A.to_hex()
        eq("hex.rt", BigInt.from_hex(H).to_int(), a)
        blen = (a.bit_length() + 7) // 8 if a != 0 else 1
        for length in (max(blen, 32), max(blen, 64), max(blen, 128)):
            raw = A.to_bytes(length, "big", signed=True)
            eq(f"bytes.big.rt:{length}", BigInt.from_bytes(raw, "big", signed=True).to_int(), a)
            raw = A.to_bytes(length, "little", signed=True)
            eq(f"bytes.little.rt:{length}", BigInt.from_bytes(raw, "little", signed=True).to_int(), a)
        # طول أصغر من العدد يرفع خطأ
        if blen >= 2:
            try:
                A.to_bytes(blen - 1, "big")
                check("bytes.tooshort.raises", False, "لم يرفع خطأ")
            except ValueError:
                check("bytes.tooshort.raises", True)
    # نقاط نهاية محددة
    for v in (0, 1, -1, 255, 256, 0xDEADBEEF, -(2 ** 200)):
        A = BigInt.from_int(v)
        eq(f"hex.edge:{v}", BigInt.from_hex(A.to_hex()).to_int(), v)
    # to_bytes(1) لعدد أكبر من بايت يرفع خطأ
    try:
        BigInt.from_int(300).to_bytes(1, "big")
        check("fixed.tooshort.raises", False, "لم يرفع خطأ")
    except ValueError:
        check("fixed.tooshort.raises", True)
    print(f"  تم فحص {n} حالة + نقاط نهاية")


# ============================================================
# 5) العمليات المعيارية (powmod / mod_inverse / gcd / xgcd)
# ============================================================
def test_modular(n=1500, bits=256):
    section("عمليات معيارية (powmod / mod_inverse / gcd / xgcd)")
    for _ in range(n):
        base = rnd_int(bits) % (2 ** bits)
        if base < 0:
            base = -base
        exp = rnd_int(bits) % (2 ** bits)
        mod = rnd_int(bits) % (2 ** bits)
        while mod < 3:
            mod = rnd_int(bits) % (2 ** bits)
        Bb, Ee, Mm = BigInt.from_int(base), BigInt.from_int(exp), BigInt.from_int(mod)
        pm = E.BigInt.powmod(Bb, Ee, Mm)
        eq("powmod", pm.to_int(), pow(base, exp, mod))
        # mod_inverse
        g = E.BigInt.gcd(Bb, Mm).to_int()
        if g == 1:
            inv = E.BigInt.mod_inverse(Bb, Mm)
            check("modinv.exists", inv is not None, f"base={base} mod={mod}")
            if inv is not None:
                ok = (Bb.multiply(inv).mod(Mm).to_int() == 1)
                check("modinv.check", ok, f"base={base} mod={mod}")
        # gcd / xgcd
        a = rnd_int(bits) % (2 ** bits)
        b = rnd_int(bits) % (2 ** bits)
        Aa, Bb2 = BigInt.from_int(a), BigInt.from_int(b)
        gg = E.BigInt.gcd(Aa, Bb2).to_int()
        eq("gcd", gg, __import__("math").gcd(a, b))
        g2, x, y = E.BigInt.xgcd(Aa, Bb2)
        eq("xgcd.gcd", g2.to_int(), __import__("math").gcd(a, b))
        eq("xgcd.identity", (Aa.multiply(x).add(Bb2.multiply(y))).to_int(), g2.to_int())
    print(f"  تم فحص {n} حالة")


# ============================================================
# 6) Montgomery + Barrett
# ============================================================
def test_montgomery_barrett(n=500, bits=256):
    section("Montgomery (CIOS) + Barrett")
    for _ in range(n):
        mod = abs(rnd_int(bits)) | 1  # فردي موجب
        while mod < 3:
            mod = (abs(rnd_int(bits)) | 1)
        M = BigInt.from_int(mod)
        base = abs(rnd_int(bits)) % mod
        exp = abs(rnd_int(bits))
        Bb, Ee = BigInt.from_int(base), BigInt.from_int(exp)
        expect = pow(base, exp, mod)
        mc = E.MontgomeryContext(M)
        eq("montgomery.pow", mc.pow_mont(Bb, Ee).to_int(), expect)
        bc = E.BarrettContext(M)
        prod = Bb.multiply(Ee)
        eq("barrett.reduce", bc.reduce(prod).to_int(), (base * exp) % mod)
    print(f"  تم فحص {n} حالة")


# ============================================================
# 7) الأعداد الأولية (Miller–Rabin)
# ============================================================
def test_primes():
    section("اختبار الأولية (Miller–Rabin)")
    small_primes = [2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 101, 997, 104729, 999983]
    small_comp = [0, 1, 4, 6, 8, 9, 15, 21, 25, 561, 1105, 1729, 2465, 2821]
    for p in small_primes:
        check(f"prime:{p}", E.is_probable_prime(BigInt.from_int(p)), "اعتبره غير أولي")
    for c in small_comp:
        check(f"comp:{c}", not E.is_probable_prime(BigInt.from_int(c)), "اعتبره أولياً")
    # توليد عدد أولي والتحقق
    for bits in (128, 256, 384):
        pk = E.generate_prime(bits)
        check(f"genprime:{bits}.oncurve_bits", pk.bit_length() >= bits - 2, f"bits={pk.bit_length()}")
        check(f"genprime:{bits}.isprime", E.is_probable_prime(pk), "العدد المولّد ليس أولياً")
    print("  تم فحص الأوليات + توليد أعداد أولية")


# ============================================================
# 8) المنحنيات البيضاوية (ECC / secp256k1)
# ============================================================
def test_ecc(n=300, bits=256):
    section("المنحنيات البيضاوية (ECC / secp256k1)")
    curve, G = E.secp256k1()
    check("G.on_curve", G.is_on_curve(), "المولّد G ليس على المنحنى")
    check("inf.on_curve", E.ECPoint.infinity(curve).is_on_curve(), "")
    # G*1 == G , G*2 == G.double()
    check("G*1==G", G.mul_scalar(BigInt(1)).x.compare(G.x) == 0, "")
    D = G.double()
    check("G*2==double", G.mul_scalar(BigInt(2)).x.compare(D.x) == 0, "")
    check("double.on_curve", D.is_on_curve(), "")
    # تجميعية الضرب: k1*G + k2*G == (k1+k2)*G
    for _ in range(n):
        k1 = rnd_int(bits) % (2 ** bits)
        k2 = rnd_int(bits) % (2 ** bits)
        K1, K2 = BigInt.from_int(k1), BigInt.from_int(k2)
        lhs = G.mul_scalar(K1.add(K2))
        rhs = G.mul_scalar(K1).add(G.mul_scalar(K2))
        check("ecc.assoc.x", lhs.x.compare(rhs.x) == 0, f"k1={k1} k2={k2}")
        check("ecc.assoc.y", lhs.y.compare(rhs.y) == 0, f"k1={k1} k2={k2}")
        # النقطة الناتجة على المنحنى
        check("ecc.sum.on_curve", rhs.is_on_curve(), f"k1={k1} k2={k2}")
        check("ecc.mult.on_curve", lhs.is_on_curve(), f"k1={k1} k2={k2}")
        # نسخة constant-time متطابقة
        lhs_ct = G.mul_scalar_ct(K1.add(K2))
        check("ecc.ct.x", lhs.x.compare(lhs_ct.x) == 0, "")
    # نقطة اللانهاية
    inf = E.ECPoint.infinity(curve)
    check("inf+G==G", inf.add(G).x.compare(G.x) == 0, "")
    check("G+inf==G", G.add(inf).x.compare(G.x) == 0, "")
    print(f"  تم فحص {n} حالة ECC")


# ============================================================
# 9) Fuzz ضخم الحجم (أعداد كبيرة جداً)
# ============================================================
def test_fuzz_large(n=200, bits=4096):
    section(f"Fuzz أعداد ضخمة ({bits}-bit) x{n}")
    for _ in range(n):
        a = rnd_int(bits)
        b = rnd_int(bits)
        A, B = BigInt.from_int(a), BigInt.from_int(b)
        eq("large.mul", (A * B).to_int(), a * b)
        if b != 0:
            bpos = abs(b)
            Bp = BigInt.from_int(bpos)
            q, r = A.divmod(Bp)
            eq("large.div.q", q.to_int(), a // bpos)
            eq("large.div.r", r.to_int(), a % bpos)
        eq("large.and", A.band(B).to_int(), a & b)
        eq("large.shl", A.shift_left(123).to_int(), a << 123)
    print(f"  تم فحص {n} حالة بأعداد {bits}-bit")


# ============================================================
# التشغيل
# ============================================================
def main():
    # العدد الافتراضي متوازن (~دقيقة-دقيقتان في بايثون الصرف).
    # مرّر عدداً كبيراً للإجهاد:  python test_bak.py 200000
    fuzz_n = 1500
    if len(sys.argv) > 1:
        try:
            fuzz_n = int(sys.argv[1])
        except ValueError:
            pass

    t0 = time.perf_counter()
    test_arithmetic(fuzz_n, 384)
    test_edge()
    test_bitwise(max(400, fuzz_n // 4), 300)
    test_conversions(max(600, fuzz_n // 3), 160)
    test_modular(max(400, fuzz_n // 4), 192)
    test_montgomery_barrett(max(200, fuzz_n // 8), 192)
    test_primes()
    test_ecc(max(20, fuzz_n // 60), 96)
    test_fuzz_large(max(20, fuzz_n // 80), 1024)
    dt = time.perf_counter() - t0

    print("\n" + "=" * 50)
    print(f"النتيجة: نجح = {PASSED} | فشل = {FAILED} | الزمن = {dt:.2f}s")
    if FAILURES:
        print("\nتفاصيل الإخفاقات:")
        for f in FAILURES[:50]:
            print(f)
        if len(FAILURES) > 50:
            print(f"... و {len(FAILURES) - 50} أخرى")
        sys.exit(1)
    print("[OK] جميع الاختبارات نجحت.")


if __name__ == "__main__":
    main()

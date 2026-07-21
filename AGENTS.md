## Objective
- بناء مشروع عملة رقمية كامل "BAK-Coin" فوق محرك BAK: `ecdsa.py` (ECDSA/secp256k1)، `blockchain.py` (PoW + أرصدة + حفظ JSON)، `cli.py` (واجهة تفاعلية)، `node.py` (عقدة P2P شبكية)، `test_smoke.py` (اختبار دخان)، `demo_p2p.py` (إثبات الشبكة عبر TCP حقيقي)، ثم تجهيزه للنشر على شبكة حقيقية. **اكتمل المشروع وتَم التحقق منه بالكامل.**

## Important Details
- المسار الجذر: `C:\Users\BAKALI\OneDrive\سطح المكتب\BAK\`
- المحرك `engine.py`: أعداد 2^64 limbs، تمثيل داخلي **little-endian**، `MASK=0xFFFFFFFFFFFFFFFF`، `BITS=64`.
- البيئة: Python 3.10.11، لا `pytest` ولا `gmpy2` (اختبارات ذاتية الاحتواء). الكونسول cp1256 (عربي مشوّه في الطرفية — لا يؤثر على المنطق).
- مطلوب `sys.set_int_max_str_digits(2_000_000)` للأعداد 100000-bit.
- **قاعدة**: بعد كل تعديل على `engine.py` احذف `__pycache__` (`Remove-Item -Recurse -Force __pycache__`).
- اصطلاح باقي القسمة في المحرك: **إقليدي** (`0 <= r < |b|` موجب دائماً).
- `BigInt.mod_inverse(a, m)` ساكنة تُرجع `None`؛ `ECPoint` بـ `mul_scalar_ct`، `is_inf`؛ `secp256k1()` تُرجع `(curve, G)`.
- `node.py` يربط `0.0.0.0` افتراضياً ويتصل بالنظير عبر IP + منفذ (من القائمة 2) — جاهز للشبكة الحقيقية.
- `blockchain.py` فيه `GENESIS_TIMESTAMP = 1231006505` (هاش تكويني حتمي ومتطابق عبر كل العقد — ضروري للمزامنة).

## Work State
### Completed
- **`engine.py` مُصلح ومُختبَر**: 20966 نجاح/0 فشل (EXIT=0). كل إصلاحات ECC، `_shl_bits`، `is_probable_prime`، `MontField.inv`، `shift_right`، `_bitop`، `to_bytes`/`from_bytes`، `divmod`/`mod` الإقليدي — مُتحقَّق منها.
- **`ecdsa.py`**: `ECDSABAK` كامل — مفاتيح، RFC6979، `sign`/`verify`/`sign_message`.
- **`blockchain.py`**: `Blockchain` مع حفظ JSON ذرّي، `is_chain_valid` كامل (PoW + مكافأة + توقيع + إعادة تشغيل أرصدة)، `GENESIS_TIMESTAMP` للتكوين الحتمي.
- **`cli.py`**: واجهة تفاعلية كاملة (أرصدة/تعدين/إرسال/فحص/عرض/محفظة جديدة).
- **`node.py`**: `P2PNode` مع تغليف `[طول 4BE][JSON]`، `GET_CHAIN`/`NEW_TRANSACTION`/`NEW_BLOCK`، gossip، ربط `0.0.0.0`. **مُثبَت**: خادمه يربط `0.0.0.0` ويتلقى `GET_CHAIN` عبر TCP حقيقي ويُعيد سلسلة التكوين (اختبار probe: `CONNECT_OK chain_len=1 genesis_idx=0`).
- **إصلاح حرج — حفظ/تحميل المحفظة**: `cli.py` يحفظ/يحمّل المفاتيح الخاصة في `wallets.json` (التحميل يُعيد توليد العنوان من المفتاح)، و`node.py` في `node_wallet_{port}.json`. **مُختبر**: عنوان alice ومفتاح المعدّن متطابقان عبر إعادة التشغيل (`CLI_PERSIST_OK` / `PERSIST_OK`). بدون هالإصلاح كان أي رصيد يضيع عند أول إعادة تشغيل.
- **تشفير المفتاح بعبارة مرور (مُنجز)**: الدوال `wallet_encrypt`/`wallet_decrypt` في `blockchain.py` (PBKDF2-HMAC-SHA256 + تشفير تيار SHA256، بدون مكتبات خارجية). `cli.py`/`node.py` يطلبان عبارة مرور (تعيين عند الإنشاء، إدخال عند التحميل) ويخزّنان `{v,salt,ct}` — **لا نص واضح**. **مُختبر**: إعادة التحميل بنفس العبارة تُرجع نفس المفتاح/العنوان (`CLI_ENC_OK`/`ALL_OK`)، عبارة خاطئة ترفض ولا تطمس الملف (`CLI_RECOVER_OK`)، والملف ليس نصاً واضحاً.
- **`test_smoke.py`**: 18/0 نجاح (SMOKE_EXIT=0).
- **`demo_p2p.py`**: عقدتان (5100/5101) تتزامنان وتعدّنان وتنشران المعاملة عبر TCP loopback — **P2P_EXIT=0** (A=80، B=20). أصلحت: منافذ 5100/5101، `get_balance` على `B.blockchain`، قيمة رصيد B المتوقعة (=20 لا 70)، وطباعة الرصيد المحسوبة.
- **تنظيف**: حُذفت الملفات العالقة القديمة (`chain_5000/5001.json` باهاش تكوين قديم، `bak_chain.json`، `_test_div.py`)، ولا ملفات سلسلة متبقية. كل الوحدات تمر `py_compile`.

### ملاحظات حول "النشر على شبكة حقيقية"
- لا يمكن فعلياً الوصول إلى آلات خارجية من هذه البيئة، لكن الكود جاهز تماماً: ربط `0.0.0.0` + اتصال بـ IP النظير + مزامنة `GET_CHAIN` + بث الكتل/المعاملات — كلها **مُختبرة فعلياً عبر TCP**.
- خطوات النشر للمستخدم:
  1. آلة 1: `python -B node.py --port 5000` (يربط 0.0.0.0).
  2. آلة 2: `python -B node.py --port 5001` ثم من القائمة اختر 2 وأدخل IP الآلة 1 ومنفذها.
  3. (للإنترنت) يحتاج IP عاماً أو إعادة توجيه المنفذ/فتح جدار الحماية.
  4. للتعدين اختر 3؛ للإرسال اختر 4.
- `cli.py` للتجربة المحلية الفردية: `python -B cli.py` (يحفظ `bak_chain.json`).
- الصعوبة حالياً =2 (مناسبة للديمو)؛ للإنتاج تُرفع عبر `Blockchain(difficulty=...)`.

## Next Move
- (اختياري) رفع `difficulty` للإنتاج؛ إضافة اكتشاف نظراء تلقائي (DNS seed)؛ `bench_bak.py`؛ docstrings لواجهة `engine.py`.
- المشروع مكتمل وقابل للنشر فوراً بالأوامر أعلاه.

## Relevant Files
- `engine.py` (~1141 سطر) — أخضر (20966).
- `test_bak.py` — 20966 نجاح.
- `ecdsa.py` — ECDSA/secp256k1 + RFC6979 — مكتمل.
- `blockchain.py` — السلسلة + الحفظ + `GENESIS_TIMESTAMP` — مكتمل.
- `cli.py` — واجهة تفاعلية — مكتمل.
- `node.py` — عقدة P2P (0.0.0.0) — مكتمل ومُثبَت عبر TCP.
- `test_smoke.py` — 18/0 نجاح.
- `demo_p2p.py` — إثبات P2P عبر TCP — P2P_EXIT=0.
- لا ملفات سلسلة عالقة (حُذفت كلها).
- `C:\Users\BAKALI\AppData\Local\Temp\opencode\` : سكريبتات تنقيح مؤقتة — حُذفت.

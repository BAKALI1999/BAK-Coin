"""
BAK-Coin — فاحص عقود USDT (Tether)
===================================
أداة للتحقق من عقود USDT الحقيقية vs المزيفة
"""

# العقود الرسمية لـ USDT
OFFICIAL_USDT_CONTRACTS = {
    "Ethereum": "0xdac17f958d2ee523a2206206994597c13d831ec7",
    "BSC": "0x55d398326f99059ff775485246999027b3197955",
    "Tron": "TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t",
    "Polygon": "0xc2132d05d31c914a87c6611c10748aeb04b58e8f",
    "Avalanche": "0x9702230a8ea53601f5cd2dc00fdbc13d4df4a8c7",
    "Arbitrum": "0xfd086bc7cd5c481dcc9c85ebe478a1c0b69fcbb9",
    "Optimism": "0x94b008aa00579c1307b0ef2c499ad98a8ce58e58",
    "Solana": "Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB",
}

# خصائص USDT الحقيقية
USDT_PROPERTIES = {
    "name": "Tether USD",
    "symbol": "USDT",
    "decimals": 6,
    "total_supply": 100_000_000_000,  # 100 billion
}


class ContractInspector:
    """فاحص العقود"""

    def __init__(self):
        self.results = []

    def check_official(self, address, network):
        """التحقق من العقد الرسمي"""
        official = OFFICIAL_USDT_CONTRACTS.get(network)
        if not official:
            return {"status": "unknown", "message": f"شبكة {network} غير معروفة"}

        if address.lower() == official.lower():
            return {
                "status": "official",
                "message": f"✅ العقدofficial لـ USDT على {network}",
                "address": official,
            }
        else:
            return {
                "status": "fake",
                "message": f"⚠️ العقد ليسofficial لـ USDT",
                "official": official,
                "your": address,
            }

    def check_token(self, contract_data):
        """التحقق من خصائص التوكن"""
        checks = []

        # فحص الاسم
        name = contract_data.get("name", "")
        if name == USDT_PROPERTIES["name"]:
            checks.append({"name": "الاسم", "status": "pass", "value": name})
        else:
            checks.append({"name": "الاسم", "status": "fail", "value": name, "expected": USDT_PROPERTIES["name"]})

        # فحص الرمز
        symbol = contract_data.get("symbol", "")
        if symbol == USDT_PROPERTIES["symbol"]:
            checks.append({"name": "الرمز", "status": "pass", "value": symbol})
        else:
            checks.append({"name": "الرمز", "status": "fail", "value": symbol, "expected": USDT_PROPERTIES["symbol"]})

        # فحص المنازل العشرية
        decimals = contract_data.get("decimals", 0)
        if decimals == USDT_PROPERTIES["decimals"]:
            checks.append({"name": "المنازل العشرية", "status": "pass", "value": decimals})
        else:
            checks.append({"name": "المنازل العشرية", "status": "fail", "value": decimals, "expected": USDT_PROPERTIES["decimals"]})

        return checks

    def check_security(self, contract_data):
        """التحقق من الأمان"""
        warnings = []

        # فحص الملكية
        if contract_data.get("owner"):
            warnings.append("⚠️ العقد له ملكية (Owner) — يمكن تغييره")

        # فحص التمويل
        if contract_data.get("pause"):
            warnings.append("⚠️ العقد يمكن إيقافه (Pausable)")

        # فحص التوسيع
        if contract_data.get("upgradeable"):
            warnings.append("⚠️ العقد قابل للترقية — قد يتغير")

        return warnings


# ============================================================
# قائمة العقود المزيفة الشائعة
# ============================================================
KNOWN_FAKES = {
    "0x1234567890123456789012345678901234567890": "USDT مزيف — لا تشتري!",
    "0xabcdefabcdefabcdefabcdefabcdefabcdefabcd": "USDT مزيف — مشبوه",
}


def verify_address(address, network):
    """التحقق من عنوان USDT"""
    inspector = ContractInspector()

    print("="*60)
    print(f"  فحص عقد USDT — {network}")
    print("="*60)
    print(f"  العنوان: {address}")
    print()

    # فحص رسمي
    result = inspector.check_official(address, network)
    print(f"  الحالة: {result['message']}")

    if result["status"] == "official":
        print(f"  ✅ العقدofficial وآمن")
    elif result["status"] == "fake":
        print(f"  ⚠️ العقدofficial: {result['official']}")
        print(f"  ⚠️ عنوانك: {result['your']}")
        print(f"  ❌ هذا ليس العقد الرسمي!")

    # فحص القائمة السوداء
    if address in KNOWN_FAKES:
        print(f"  🚫 في القائمة السوداء: {KNOWN_FAKES[address]}")

    print("="*60)
    return result


# ============================================================
# استخدام
# ============================================================
if __name__ == "__main__":
    print("\n🔍 فاحص عقود USDT\n")

    # قائمة العقود الرسمية
    print("📋 العقود الرسمية لـ USDT:")
    for network, addr in OFFICIAL_USDT_CONTRACTS.items():
        print(f"  {network}: {addr}")

    print("\n" + "="*60)

    # فحص عنوان
    test_address = "0x55d398326f99059ff775485246999027b3197955"
    verify_address(test_address, "BSC")

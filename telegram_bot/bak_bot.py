"""
BAK-Coin Telegram Bot — الكود الرئيسي
=====================================
بوت تلجرم للتعامل مع عملة BAK-Coin
"""

import json
import os
import time
import hashlib
import threading
from datetime import datetime, timedelta

# محاكاة لمكتبة telebot (pip install pyTelegramBotAPI)
# في التشغيل الحقيقي: import telebot


# ============================================================
# إدارة المستخدمين والمحافظ
# ============================================================
class UserManager:
    """إدارة المستخدمين والمحافظ"""

    def __init__(self, db_file="bak_users.json"):
        self.db_file = db_file
        self.users = self._load()

    def _load(self):
        if os.path.exists(self.db_file):
            with open(self.db_file, "r", encoding="utf-8") as f:
                return json.load(f)
        return {}

    def _save(self):
        with open(self.db_file, "w", encoding="utf-8") as f:
            json.dump(self.users, f, indent=2, ensure_ascii=False)

    def get_or_create(self, user_id, username, first_name):
        """الحصول على مستخدم أو إنشاؤه"""
        uid = str(user_id)
        if uid not in self.users:
            self.users[uid] = {
                "user_id": user_id,
                "username": username,
                "first_name": first_name,
                "balance": 0,
                "mining_active": False,
                "mining_start": 0,
                "total_mined": 0,
                "referrals": 0,
                "referred_by": None,
                "last_daily": None,
                "join_date": datetime.now().isoformat(),
                "wallet_address": self._generate_address(uid),
            }
            self._save()
        return self.users[uid]

    def _generate_address(self, user_id):
        """توليد عنوان محفظة فريد"""
        data = f"bak-{user_id}-{time.time()}"
        return "0x" + hashlib.sha256(data.encode()).hexdigest()[:40]

    def get_balance(self, user_id):
        """الحصول على الرصيد"""
        uid = str(user_id)
        if uid in self.users:
            return self.users[uid]["balance"]
        return 0

    def add_balance(self, user_id, amount):
        """إضافة رصيد"""
        uid = str(user_id)
        if uid in self.users:
            self.users[uid]["balance"] += amount
            self.users[uid]["total_mined"] += amount
            self._save()
            return True
        return False

    def deduct_balance(self, user_id, amount):
        """خصم رصيد"""
        uid = str(user_id)
        if uid in self.users and self.users[uid]["balance"] >= amount:
            self.users[uid]["balance"] -= amount
            self._save()
            return True
        return False

    def start_mining(self, user_id):
        """بدء التعدين"""
        uid = str(user_id)
        if uid in self.users:
            self.users[uid]["mining_active"] = True
            self.users[uid]["mining_start"] = time.time()
            self._save()
            return True
        return False

    def stop_mining(self, user_id):
        """إيقاف التعدين"""
        uid = str(user_id)
        if uid in self.users:
            self.users[uid]["mining_active"] = False
            self._save()
            return True
        return False

    def handle_daily(self, user_id):
        """المطالبة بالمكافأة اليومية"""
        uid = str(user_id)
        if uid in self.users:
            self.users[uid]["balance"] += 50  # مكافأة فورية
            self.users[uid]["total_mined"] += 50
            self._save()
            return True
        return False

    def add_referral(self, user_id, referrer_id):
        """إضافة إحالة"""
        uid = str(user_id)
        rid = str(referrer_id)
        if uid in self.users and rid in self.users:
            if self.users[uid]["referred_by"] is None:
                self.users[uid]["referred_by"] = rid
                self.users[rid]["referrals"] += 1
                self.users[rid]["balance"] += 50  # مكافأة الإحالة
                self._save()
                return True
        return False

    def get_leaderboard(self, limit=10):
        """أقوى المعدّنين"""
        sorted_users = sorted(
            self.users.values(),
            key=lambda x: x["total_mined"],
            reverse=True
        )[:limit]
        return sorted_users

    def get_stats(self):
        """إحصائيات البوت"""
        total_users = len(self.users)
        total_mined = sum(u.get("total_mined", 0) for u in self.users.values())
        active_miners = sum(1 for u in self.users.values() if u.get("mining_active"))
        return {
            "total_users": total_users,
            "total_mined": total_mined,
            "active_miners": active_miners,
            "remaining": 21_000_000 - total_mined,
        }


# ============================================================
# نظام التعدين
# ============================================================
class MiningSystem:
    """نظام التعدين التلقائي"""

    def __init__(self, user_manager):
        self.um = user_manager
        self.mining_thread = None
        self.running = False

    def start(self):
        """بدء نظام التعدين"""
        self.running = True
        self.mining_thread = threading.Thread(target=self._mine_loop, daemon=True)
        self.mining_thread.start()

    def stop(self):
        """إيقاف نظام التعدين"""
        self.running = False

    def _mine_loop(self):
        """حلقة التعدين"""
        while self.running:
            time.sleep(60)  # كل دقيقة
            self._process_mining()

    def _process_mining(self):
        """معالجة التعدين"""
        now = time.time()
        for uid, user in list(self.um.users.items()):
            if user.get("mining_active"):
                elapsed = now - user.get("mining_start", now)
                if elapsed >= 60:  # دقيقة واحدة (للتجربة)
                    # مكافأة التعدين
                    reward = 10  # BAK
                    user["balance"] += reward
                    user["total_mined"] += reward
                    user["mining_start"] = now
                    self.um._save()


# ============================================================
# أوامر البوت
# ============================================================
class BAKBot:
    """بوت BAK-Coin الرئيسي"""

    def __init__(self, token):
        self.token = token
        self.um = UserManager()
        self.mining = MiningSystem(self.um)
        self.mining.start()

    def handle_start(self, user_id, username, first_name, args=None):
        """أمر /start"""
        user = self.um.get_or_create(user_id, username, first_name)

        # معالجة الإحالة
        if args and len(args) > 0:
            ref_id = args[0]
            if ref_id.isdigit() and int(ref_id) != user_id:
                self.um.add_referral(user_id, int(ref_id))

        balance = self.um.get_balance(user_id)
        return f"""
مرحباً {first_name}! 🪙

 saldoك الحالي: {balance} BAK

ابدأ التعدين: /mining
أرسل لصديق: /refer

💰 كلما كنت نشطاً، حصلت على عملات أكثر!
        """

    def handle_balance(self, user_id):
        """أمر /balance"""
        user = self.um.users.get(str(user_id), {})
        balance = user.get("balance", 0)
        mined = user.get("total_mined", 0)
        mining = "🟢 نشط" if user.get("mining_active") else "🔴 متوقف"
        referrals = user.get("referrals", 0)

        return f"""
💰 رصيدك: {balance} BAK

📊 الإحصائيات:
• المُعدَن: {mined} BAK
• التعدين: {mining}
• الإحالات: {referrals}

🔗 عنوان محفظتك:
{user.get('wallet_address', 'غير متوفر')}
        """

    def handle_mining(self, user_id):
        """أمر /mining"""
        user = self.um.users.get(str(user_id), {})
        if user.get("mining_active"):
            # إيقاف التعدين
            self.um.stop_mining(user_id)
            return "⏹️ تم إيقاف التعدين\n\nاستخدم /mining لبدء التعدين مرة أخرى"
        else:
            # بدء التعدين
            self.um.start_mining(user_id)
            return "▶️ بدأ التعدين!\n\nستحصل على 10 BAK كل دقيقة\nاستخدم /mining لإيقاف التعدين"

    def handle_claim(self, user_id):
        """أمر /claim - المطالبة بمكافأة التعدين"""
        user = self.um.users.get(str(user_id), {})
        if user.get("mining_active"):
            elapsed = time.time() - user.get("mining_start", 0)
            if elapsed >= 60:
                self.um.add_balance(user_id, 10)
                self.um.users[str(user_id)]["mining_start"] = time.time()
                self.um._save()
                balance = self.um.get_balance(user_id)
                return f"⛏️ تم التعدين!\n\n+10 BAK\nرصيدك الحالي: {balance} BAK"
            else:
                remaining = int(60 - elapsed)
                return f"⏳ انتظر {remaining} ثانية للتعدين التالي"
        else:
            return "❌ بدّأ التعدين أولاً باستخدام /mining"

    def handle_daily(self, user_id):
        """أمر /daily"""
        if self.um.claim_daily(user_id):
            balance = self.um.get_balance(user_id)
            return f"🎁 تم الحصول على المكافأة!\n\n+50 BAK\nرصيدك الحالي: {balance} BAK"
        else:
            return "❌ حدث خطأ، حاول مرة أخرى"

    def handle_send(self, user_id, args):
        """أمر /send"""
        if len(args) < 2:
            return "❌ الاستخدام: /send @username amount\nمثال: /send @alice 10"

        to_username = args[0].replace("@", "")
        try:
            amount = int(args[1])
        except ValueError:
            return "❌ المبلغ يجب أن يكون رقماً"

        if amount <= 0:
            return "❌ المبلغ يجب أن يكون أكبر من 0"

        if self.um.get_balance(user_id) < amount:
            return "❌ رصيد غير كافٍ"

        # البحث عن المستلم
        to_user = None
        for uid, user in self.um.users.items():
            if user.get("username") == to_username:
                to_user = user
                break

        if not to_user:
            return f"❌ المستخدم @{to_username} غير موجود"

        # التنفيذ
        self.um.deduct_balance(user_id, amount)
        self.um.add_balance(to_user["user_id"], amount)
        return f"✅ تم إرسال {amount} BAK إلى @{to_username}"

    def handle_refer(self, user_id):
        """أمر /refer"""
        bot_username = "BAK_Coin_bot"
        ref_link = f"https://t.me/{bot_username}?start={user_id}"
        referrals = self.um.users.get(str(user_id), {}).get("referrals", 0)

        return f"""
🔗 رابط الإحالة الخاص بك:

{ref_link}

📊 عدد الإحالات: {referrals}
💰 مكافأة الإحالة: 50 BAK لكل صديق

شارك الرابط واحصل على عملات مجانية!
        """

    def handle_leaderboard(self):
        """أمر /leaderboard"""
        leaders = self.um.get_leaderboard(10)
        if not leaders:
            return "📊 لا يوجد معدّنين بعد"

        msg = "🏆 أقوى المعدّنين:\n\n"
        medals = ["🥇", "🥈", "🥉"]
        for i, user in enumerate(leaders):
            medal = medals[i] if i < 3 else f"{i+1}."
            name = user.get("first_name", "مجهول")
            mined = user.get("total_mined", 0)
            msg += f"{medal} {name}: {mined} BAK\n"

        return msg

    def handle_stats(self):
        """أمر /stats"""
        stats = self.um.get_stats()
        return f"""
📊 إحصائيات BAK-Coin:

👥 المستخدمون: {stats['total_users']}
⛏️ المعدّنون النشطون: {stats['active_miners']}
💰 المُعدَن: {stats['total_mined']} BAK
🏦 المتبقي: {stats['remaining']} BAK
        """

    def handle_help(self):
        """أمر /help"""
        return """
📖 دليل استخدام BAK-Coin Bot

/start - بدء البوت
/balance - عرض الرصيد
/mining - بدء التعدين
/claim - المطالبة بمكافأة التعدين
/send - إرسال عملات
/refer - الحصول على رابط إحالة
/daily - المكافأة اليومية
/leaderboard - أقوى المعدّنين
/stats - إحصائيات البوت
/checkusdt - فحص عقد USDT

💡 نصيحة: كلما كنت نشطاً، حصلت على عملات أكثر!
        """

    def handle_check_usdt(self, args):
        """فحص عقد USDT"""
        if len(args) < 2:
            return """🔍 استخدام: /checkusdt network address

مثال:
/checkusdt BSC 0x55d398326f99059ff775485246999027b3197955
/checkusdt Ethereum 0xdac17f958d2ee523a2206206994597c13d831ec7

الشبكات المدعومة:
• Ethereum
• BSC
• Tron
• Polygon
• Avalanche
• Arbitrum
• Optimism"""

        network = args[0]
        address = args[1]

        # العقود الرسمية
        official = {
            "Ethereum": "0xdac17f958d2ee523a2206206994597c13d831ec7",
            "BSC": "0x55d398326f99059ff775485246999027b3197955",
            "Tron": "TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t",
            "Polygon": "0xc2132d05d31c914a87c6611c10748aeb04b58e8f",
            "Avalanche": "0x9702230a8ea53601f5cd2dc00fdbc13d4df4a8c7",
            "Arbitrum": "0xfd086bc7cd5c481dcc9c85ebe478a1c0b69fcbb9",
            "Optimism": "0x94b008aa00579c1307b0ef2c499ad98a8ce58e58",
        }

        # القائمة السوداء
        fakes = {
            "0x1234567890123456789012345678901234567890": "❌ USDT مزيف",
            "0xabcdefabcdefabcdefabcdefabcdefabcdefabcd": "❌ USDT مزيف",
        }

        # فحص
        if address in fakes:
            return f"""
🚫 تحذير: {fakes[address]}

هذا العقد مشبوه ومزيف!
لا تشتري أو تبيع من هذا العقد!
            """

        official_addr = official.get(network)
        if not official_addr:
            return f"❌ شبكة {network} غير معروفة"

        if address.lower() == official_addr.lower():
            return f"""
✅ عقد USDTofficial!

🌐 الشبكة: {network}
📍 العنوان: {address}

هذا هو العقد الرسمي لـ USDT
يمكنك التعامل معه بأمان!
            """
        else:
            return f"""
⚠️ تحذير: هذا ليس العقد الرسمي!

📍 عنوانك: {address}
✅ العقدofficial: {official_addr}

❌ لا تتعامل مع هذا العقد!
قد يكون مزيفاً!
            """


# ============================================================
# التشغيل
# ============================================================
if __name__ == "__main__":
    from bot_config import BOT_TOKEN, WELCOME_MESSAGE

    print("="*50)
    print("  BAK-Coin Telegram Bot")
    print("="*50)
    print(f"  Token: {BOT_TOKEN[:20]}...")
    print(f"  Status: Starting...")
    print("="*50)

    bot = BAKBot(BOT_TOKEN)
    print("  Bot is running!")
    print("  Send /start to your bot")
    print("="*50)

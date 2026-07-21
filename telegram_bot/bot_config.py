"""
BAK-Coin Telegram Bot
====================
بوت تلجرم لتحريك عملة BAK-Coin
- تعدين للمستخدمين النشطين
- إرسال واستقبال عملات
- محفظة لكل مستخدم
- نظام مكافآت

الخطوات:
1. افتح @BotFather في تلجرم
2. أرسل /newbot
3. اختر اسم: BAK-Coin Bot
4. اختر username: bakcoin_bot
5. انسخ Token
6. الصقه في ملف bot_config.py
"""

# إعدادات البوت
BOT_TOKEN = "YOUR_BOT_TOKEN_HERE"  # الصق Token من BotFather
BOT_NAME = "BAK-Coin Bot"
BOT_USERNAME = "bakcoin_bot"

# إعدادات الشبكة
NETWORK = "BSC Testnet"
CHAIN_ID = 97

# إعدادات التعدين
MINING_REWARD = 10  # BAK لكل交互
MINING_INTERVAL = 3600  # ساعة واحدة
MAX_MINERS = 100  # أقصى عدد معدّنين في نفس الوقت

# إعدادات المكافآت
REFERRAL_BONUS = 50  # BAK لكل إحالة
DAILY_BONUS = 5  # BAK يومياً
ACTIVE_BONUS = 2  # BAK لكل نشاط

# إعدادات التسويق
WELCOME_MESSAGE = """
مرحباً بك في BAK-Coin! 🪙

أنا بوت BAK-Coin، ساعدتك في:
• تعدين عملات BAK مجاناً
• إرسال واستقبال عملات
• متابعة رصيدك

ابدأ بالضغط على /start
"""

START_MESSAGE = """
🪙 BAK-Coin Bot

مرحباً {name}!

saldoك الحالي: {balance} BAK

الأوامر المتاحة:
/mining - تعدين عملات
/balance - رصيدك
/send - إرسال عملات
/refer - إحالة صديق
/daily - مكافأة يومية
/help - مساعدة
"""

HELP_MESSAGE = """
📖 دليل استخدام BAK-Coin Bot

/start - بدء البوت
/balance - عرض الرصيد
/mining - بدء التعدين
/send - إرسال عملات
/refer - الحصول على رابط إحالة
/daily - المكافأة اليومية
/leaderboard - أقوى المعدّنين
/stats - إحصائيات البوت

💡 نصيحة: كلما كنت نشطاً، حصلت على عملات أكثر!
"""

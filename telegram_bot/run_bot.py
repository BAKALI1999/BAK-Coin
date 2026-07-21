"""
تشغيل بوت BAK-Coin على تلجرم
=============================
الخطوات:
1. ثبّت المكتبة: pip install pyTelegramBotAPI
2. أنشئ بوت في @BotFather
3. الصق Token في bot_config.py
4. شغّل: python run_bot.py
"""

import sys
import os

# التحقق من المكتبات
try:
    import telebot
except ImportError:
    print("جاري تثبيت المكتبات...")
    os.system("pip install pyTelegramBotAPI")
    import telebot

from bot_config import BOT_TOKEN, WELCOME_MESSAGE, START_MESSAGE, HELP_MESSAGE
from bak_bot import BAKBot, UserManager

# إنشاء البوت
bot = telebot.TeleBot(BOT_TOKEN)
bak = BAKBot(BOT_TOKEN)


# ============================================================
# معالجات الأوامر
# ============================================================
@bot.message_handler(commands=['start'])
def handle_start(message):
    user_id = message.from_user.id
    username = message.from_user.username or "مجهول"
    first_name = message.from_user.first_name or "مستخدم"
    args = message.text.split()[1:] if len(message.text.split()) > 1 else []

    response = bak.handle_start(user_id, username, first_name, args)
    bot.reply_to(message, response)


@bot.message_handler(commands=['balance', 'bal'])
def handle_balance(message):
    user_id = message.from_user.id
    response = bak.handle_balance(user_id)
    bot.reply_to(message, response)


@bot.message_handler(commands=['mining', 'mine'])
def handle_mining(message):
    user_id = message.from_user.id
    response = bak.handle_mining(user_id)
    bot.reply_to(message, response)


@bot.message_handler(commands=['claim'])
def handle_claim(message):
    user_id = message.from_user.id
    response = bak.handle_claim(user_id)
    bot.reply_to(message, response)


@bot.message_handler(commands=['daily'])
def handle_daily(message):
    user_id = message.from_user.id
    response = bak.handle_daily(user_id)
    bot.reply_to(message, response)


@bot.message_handler(commands=['send'])
def handle_send(message):
    user_id = message.from_user.id
    args = message.text.split()[1:]
    response = bak.handle_send(user_id, args)
    bot.reply_to(message, response)


@bot.message_handler(commands=['refer', 'ref'])
def handle_refer(message):
    user_id = message.from_user.id
    response = bak.handle_refer(user_id)
    bot.reply_to(message, response)


@bot.message_handler(commands=['leaderboard', 'top'])
def handle_leaderboard(message):
    response = bak.handle_leaderboard()
    bot.reply_to(message, response)


@bot.message_handler(commands=['stats'])
def handle_stats(message):
    response = bak.handle_stats()
    bot.reply_to(message, response)


@bot.message_handler(commands=['help'])
def handle_help(message):
    bot.reply_to(message, HELP_MESSAGE)


# ============================================================
# معالج الرسائل النصية
# ============================================================
@bot.message_handler(func=lambda message: True)
def handle_text(message):
    bot.reply_to(message, "استخدم /help لعرض الأوامر المتاحة")


# ============================================================
# التشغيل
# ============================================================
if __name__ == "__main__":
    print("="*50)
    print("  BAK-Coin Telegram Bot")
    print("="*50)
    print("  Bot is running...")
    print("  Press Ctrl+C to stop")
    print("="*50)

    try:
        bot.infinity_polling()
    except KeyboardInterrupt:
        print("\nBot stopped!")

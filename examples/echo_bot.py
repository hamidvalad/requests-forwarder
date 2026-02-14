"""
Example 1 — Echo Bot (Minimal)
===============================
The simplest possible bot that echoes back every text message.

Usage:
    1. Replace YOUR_FORWARDER_TOKEN and YOUR_BOT_TOKEN with real values.
    2. Run:  python echo_bot.py
"""

# ──── Step 1: Activate the proxy BEFORE importing telebot ────
from requests_forwarder import setup_proxy

setup_proxy(proxy_token="YOUR_FORWARDER_TOKEN")

# ──── Step 2: Write your bot as usual ────
import telebot

bot = telebot.TeleBot("YOUR_BOT_TOKEN")


@bot.message_handler(commands=["start", "help"])
def send_welcome(message):
    bot.reply_to(
        message,
        "Hi! I am an echo bot running through a proxy forwarder.\n"
        "Send me any message and I will repeat it back to you.",
    )


@bot.message_handler(func=lambda m: True)
def echo(message):
    bot.reply_to(message, message.text)


if __name__ == "__main__":
    print("Bot is running …")
    bot.infinity_polling()

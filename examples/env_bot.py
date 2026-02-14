"""
Example 3 — Using environment variables (recommended for production)
=====================================================================
Reads tokens from environment variables so that no secrets are
hard-coded in source files.

Usage:
    1. Set environment variables:
         export FORWARDER_TOKEN="your_forwarder_token"
         export BOT_TOKEN="your_telegram_bot_token"
         # Optional — defaults to https://requests-forwarder.ir (public free plan)
         # You can use the hosted free plan at https://requests-forwarder.ir
         # (subject to limits) or set this to your own forwarder URL.
         export FORWARDER_URL="https://your-forwarder.example.com"
    2. Run:  python env_bot.py
"""

import os
import sys

from requests_forwarder import setup_proxy

# ──── Read config from environment ────
FORWARDER_TOKEN = os.environ.get("FORWARDER_TOKEN")
BOT_TOKEN = os.environ.get("BOT_TOKEN")
FORWARDER_URL = os.environ.get("FORWARDER_URL", "https://requests-forwarder.ir")

if not FORWARDER_TOKEN:
    sys.exit("Error: Set the FORWARDER_TOKEN environment variable.")
if not BOT_TOKEN:
    sys.exit("Error: Set the BOT_TOKEN environment variable.")

# ──── Activate proxy ────
setup_proxy(proxy_token=FORWARDER_TOKEN, proxy_base_url=FORWARDER_URL)

# ──── Bot logic ────
import telebot  # noqa: E402  (must come after setup_proxy)

bot = telebot.TeleBot(BOT_TOKEN)


@bot.message_handler(commands=["start"])
def start(message):
    bot.reply_to(message, "Hello! I'm running through a proxy forwarder 🚀")


@bot.message_handler(func=lambda m: True)
def echo(message):
    bot.reply_to(message, message.text)


if __name__ == "__main__":
    print(f"Bot started (forwarder: {FORWARDER_URL})")
    bot.infinity_polling()

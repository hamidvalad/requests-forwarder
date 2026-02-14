"""
Example 4 — Webhook mode
==========================
Demonstrates that requests-forwarder works seamlessly with webhook-based bots
(not just polling).

Usage:
    1. Replace tokens below.
    2. Run:  python webhook_bot.py
    3. Set a public URL pointing to this server, e.g. via ngrok.
"""

from requests_forwarder import setup_proxy

setup_proxy(proxy_token="YOUR_FORWARDER_TOKEN")

import telebot
from flask import Flask, request

BOT_TOKEN = "YOUR_BOT_TOKEN"
WEBHOOK_URL = "https://your-public-domain.com"  # e.g. ngrok URL

bot = telebot.TeleBot(BOT_TOKEN)
app = Flask(__name__)


@bot.message_handler(commands=["start"])
def start(message):
    bot.reply_to(message, "Webhook bot with proxy forwarder is running!")


@bot.message_handler(func=lambda m: True)
def echo(message):
    bot.reply_to(message, message.text)


@app.route(f"/{BOT_TOKEN}", methods=["POST"])
def webhook():
    json_data = request.get_json()
    update = telebot.types.Update.de_json(json_data)
    bot.process_new_updates([update])
    return "OK", 200


if __name__ == "__main__":
    # Remove any existing webhook, then set the new one.
    bot.remove_webhook()
    bot.set_webhook(url=f"{WEBHOOK_URL}/{BOT_TOKEN}")
    print(f"Webhook set: {WEBHOOK_URL}/{BOT_TOKEN}")
    app.run(host="0.0.0.0", port=5000)

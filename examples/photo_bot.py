"""
Example 2 — Photo Bot
======================
Receives any photo and replies with the file ID and a caption.
Demonstrates that file uploads / multipart requests work correctly
through the forwarder proxy.

Usage:
    1. Replace YOUR_FORWARDER_TOKEN and YOUR_BOT_TOKEN with real values.
    2. Run:  python photo_bot.py
    3. Send a photo to the bot — it will reply with the file_id.
"""

from requests_forwarder import setup_proxy

setup_proxy(proxy_token="YOUR_FORWARDER_TOKEN")

import telebot

bot = telebot.TeleBot("YOUR_BOT_TOKEN")


@bot.message_handler(commands=["start"])
def start(message):
    bot.reply_to(message, "Send me a photo and I will give you its file_id!")


@bot.message_handler(content_types=["photo"])
def handle_photo(message):
    # Telegram sends multiple sizes — take the highest resolution.
    photo = message.photo[-1]
    bot.reply_to(
        message,
        f"Photo received!\n\nfile_id: `{photo.file_id}`\n"
        f"Size: {photo.width}×{photo.height}",
        parse_mode="Markdown",
    )


@bot.message_handler(func=lambda m: True)
def fallback(message):
    bot.reply_to(message, "Please send a photo.")


if __name__ == "__main__":
    print("Photo bot is running …")
    bot.infinity_polling()

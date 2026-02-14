"""
Example 8 — Mixed: Telegram bot + external API
================================================
Demonstrates proxying both Telegram API calls AND a custom external API
through the same forwarder.

The bot fetches a random joke from an external API and sends it to the user.
Both the joke API call and the Telegram API call go through the forwarder.

Usage:
    1. Replace YOUR_FORWARDER_TOKEN and YOUR_BOT_TOKEN.
    2. Run:  python mixed_bot.py
    3. Send /joke to the bot.
"""

from requests_forwarder import setup_proxy

# Proxy both Telegram AND the joke API.
setup_proxy(
    proxy_token="YOUR_FORWARDER_TOKEN",
    hosts=["api.telegram.org", "official-joke-api.appspot.com"],
)

import requests
import telebot

bot = telebot.TeleBot("YOUR_BOT_TOKEN")


@bot.message_handler(commands=["start"])
def start(message):
    bot.reply_to(
        message,
        "Hi! Send /joke to get a random joke.\n"
        "Both the joke API and Telegram calls go through the forwarder!",
    )


@bot.message_handler(commands=["joke"])
def tell_joke(message):
    try:
        # This request also goes through the forwarder!
        resp = requests.get(
            "https://official-joke-api.appspot.com/random_joke",
            timeout=10,
        )
        joke = resp.json()
        text = f"{joke['setup']}\n\n{joke['punchline']}"
    except Exception as e:
        text = f"Could not fetch joke: {e}"

    bot.reply_to(message, text)


@bot.message_handler(func=lambda m: True)
def fallback(message):
    bot.reply_to(message, "Send /joke for a random joke!")


if __name__ == "__main__":
    print("Mixed bot is running …")
    bot.infinity_polling()

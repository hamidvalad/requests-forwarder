"""
Example 6 — General-purpose: proxy any API
============================================
Demonstrates that requests-forwarder is NOT limited to Telegram.
You can proxy requests to any host through the forwarder service.

Usage:
    1. Replace YOUR_FORWARDER_TOKEN.
    2. Run:  python general_api_proxy.py
"""

from requests_forwarder import setup_proxy

setup_proxy(
    proxy_token="YOUR_FORWARDER_TOKEN",
    hosts=["httpbin.org", "jsonplaceholder.typicode.com"],
)

import requests

# ── This request goes through the forwarder ──
resp = requests.get("https://httpbin.org/get", params={"foo": "bar"})
print("httpbin response (proxied):")
print(resp.json())
print()

# ── This also goes through the forwarder ──
resp = requests.get("https://jsonplaceholder.typicode.com/posts/1")
print("JSONPlaceholder response (proxied):")
print(resp.json())
print()

# ── This does NOT go through the forwarder (host not in list) ──
resp = requests.get("https://api.github.com/zen")
print("GitHub Zen (direct, not proxied):")
print(resp.text)

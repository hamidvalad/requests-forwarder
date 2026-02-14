"""
Example 7 — Intercept ALL outgoing requests
=============================================
When intercept_all=True, every outgoing HTTP request (via the requests library)
is routed through the forwarder — except requests to the forwarder itself.

This is useful when your server/network blocks many external APIs and you need
all traffic to go through a relay.

Usage:
    1. Replace YOUR_FORWARDER_TOKEN.
    2. Run:  python intercept_all.py
"""

from requests_forwarder import setup_proxy

# Every outgoing request will be proxied.
setup_proxy(
    proxy_token="YOUR_FORWARDER_TOKEN",
    intercept_all=True,
)

import requests

# All of these go through the forwarder:
print("1. httpbin (proxied):")
r1 = requests.get("https://httpbin.org/ip")
print(r1.json())

print("\n2. JSONPlaceholder (proxied):")
r2 = requests.get("https://jsonplaceholder.typicode.com/todos/1")
print(r2.json())

print("\n3. GitHub API (proxied):")
r3 = requests.get("https://api.github.com/zen")
print(r3.text)

# Note: requests to the forwarder itself are NOT intercepted (loop guard).

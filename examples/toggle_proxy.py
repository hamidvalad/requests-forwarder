"""
Example 5 — Toggling the proxy on and off at runtime
======================================================
Shows how to programmatically disable and re-enable the proxy,
and how to switch between different modes.
"""

from requests_forwarder import disable_proxy, get_intercepted_hosts, is_active, setup_proxy

# ── Mode 1: Specific hosts (default = Telegram) ──
setup_proxy(proxy_token="YOUR_FORWARDER_TOKEN")
print(f"Proxy active: {is_active()}")          # True
print(f"Intercepted: {get_intercepted_hosts()}")  # {'api.telegram.org'}

# Deactivate (requests now go directly)
disable_proxy()
print(f"Proxy active: {is_active()}")  # False

# ── Mode 2: Custom hosts ──
setup_proxy(
    proxy_token="YOUR_FORWARDER_TOKEN",
    hosts=["api.telegram.org", "api.openai.com", "httpbin.org"],
)
print(f"Intercepted: {get_intercepted_hosts()}")
# {'api.telegram.org', 'api.openai.com', 'httpbin.org'}

disable_proxy()

# ── Mode 3: Intercept everything ──
setup_proxy(
    proxy_token="ANOTHER_TOKEN",
    proxy_base_url="https://other-forwarder.example.com",
    intercept_all=True,
)
print(f"Proxy active: {is_active()}")          # True
print(f"Intercepted: {get_intercepted_hosts()}")  # set() (means ALL)

disable_proxy()

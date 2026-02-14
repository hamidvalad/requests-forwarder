"""
requests-forwarder
===================

Route **any** ``requests``-based HTTP traffic through a forwarder service.

This package monkey-patches ``requests.Session.request`` so that HTTP calls
targeting specific hosts — or **all** hosts — are transparently redirected to a
forwarder endpoint. The forwarder relays the request to the real destination
and returns the response unchanged.

Works with any library or code that uses ``requests``.
"""

from .core import (
    disable_proxy,
    get_intercepted_hosts,
    get_proxy_url,
    is_active,
    setup_proxy,
)

__all__ = [
    "setup_proxy",
    "disable_proxy",
    "is_active",
    "get_proxy_url",
    "get_intercepted_hosts",
]

__version__ = "1.0.0"
__author__ = "Hamidvalad.ir"




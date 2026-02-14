"""
Core proxy engine for requests-forwarder.
=========================================

This module contains the monkey-patching logic that intercepts HTTP requests
and reroutes them through a configurable forwarder service.

Architecture
------------

::

    ┌──────────────┐        ┌────────────────────┐       ┌──────────────────┐
    │  Your Code   │─req──▶│ requests-forwarder │─req──▶│ Forwarder Service│
    │  (requests,  │◀─res──│       (this lib)   │◀─res──│  (your server)   │
    │  telebot, …) │        └────────────────────┘       └───────┬──────────┘
    └──────────────┘                                             │ req/res
                                                                 ▼
                                                            ┌───────────────┐
                                                            │  Real Target  │
                                                            │  (Telegram,   | 
                                                            │   any API, …) │
                                                            └───────────────┘

The patch is applied to ``requests.Session.request`` — every library that uses
``requests`` (including pyTelegramBotAPI, httpbin clients, REST wrappers, …)
will have its traffic redirected automatically.

Modes of operation
------------------

1. **Host-based** (default): Only intercept requests whose hostname matches a
   configured set.  All other requests pass through untouched.

2. **Intercept-all**: Every outgoing request (regardless of host) is routed
   through the forwarder, **except** requests to the forwarder itself (to
   avoid infinite loops).

Thread-safety
-------------
* Headers and params dicts are **copied** before mutation.
* The ``_state`` dict is written only during ``setup_proxy`` / ``disable_proxy``,
  which are expected to be called once at startup.

Compatibility
-------------
* Any library that uses ``requests`` internally
* pyTelegramBotAPI 3.x / 4.x (telebot)
* Python 3.7+
* Polling **and** webhook modes for Telegram bots
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Set, Union
from urllib.parse import parse_qs, urlparse

import requests

__all__ = [
    "setup_proxy",
    "disable_proxy",
    "is_active",
    "get_proxy_url",
    "get_intercepted_hosts",
]

logger = logging.getLogger("requests_forwarder")

# ──────────────────────────── Constants ────────────────────────────

DEFAULT_API_HOST: str = "api.telegram.org"
"""Convenience constant — the Telegram Bot API hostname (historical default)."""

DEFAULT_PROXY_BASE_URL: str = "https://requests-forwarder.ir"
"""Default forwarder base URL (no trailing slash). Use the hosted free plan at https://requests-forwarder.ir or self-host per the documentation."""

FORWARD_ENDPOINT: str = "/forward"
"""Path appended to the base URL when building the forwarder target."""

# ──────────────────────────── Internal state ──────────────────────

_state: Dict[str, Any] = {
    "original_request": None,
    "proxy_base_url": None,
    "proxy_token": None,
    "active": False,
    "intercept_all": False,
    "intercepted_hosts": set(),
    "forwarder_host": None,      # cached to avoid infinite loops
}


# ══════════════════════════ Public API ═════════════════════════════


def setup_proxy(
    proxy_token: str,
    proxy_base_url: str = DEFAULT_PROXY_BASE_URL,
    hosts: Optional[List[str]] = None,
    intercept_all: bool = False,
    # Legacy alias kept for backward compatibility
    extra_hosts: Optional[List[str]] = None,
) -> None:
    """Activate the HTTP forwarder proxy.

    After calling this function, matching outgoing HTTP requests made via the
    ``requests`` library will be transparently routed through the forwarder
    service.

    Parameters
    ----------
    proxy_token:
        Authentication token expected by the forwarder's ``verify_token``
        middleware.  Sent as both ``Authorization: Bearer <token>`` and
        ``X-Api-Token: <token>`` headers.
    proxy_base_url:
        Root URL of the forwarder service.  Defaults to
        ``https://requests-forwarder.ir``.  A ``/forward`` path is appended
        automatically. Note: the public hosted endpoint provides a free plan
        with limitations — see the README below and https://requests-forwarder.ir
        for details. You can also host your own forwarder (see the examples
        and project documentation) and pass its base URL as this parameter.
    hosts:
        List of hostnames to intercept.  Only requests to these hosts will be
        forwarded; everything else passes through untouched.
        Example: ``["api.telegram.org", "api.example.com"]``
        If omitted **and** ``intercept_all`` is ``False``, defaults to
        ``["api.telegram.org"]`` for backward compatibility.
    intercept_all:
        If ``True``, **every** outgoing request is forwarded (except requests
        to the forwarder itself).  ``hosts`` is ignored in this mode.
    extra_hosts:
        **Deprecated** — use ``hosts`` instead.  Kept for backward
        compatibility.  If ``hosts`` is not provided, ``extra_hosts`` will be
        merged with the default host.

    Raises
    ------
    ValueError
        If *proxy_token* is falsy.

    Examples
    --------
    Telegram bot (default)::

        from requests_forwarder import setup_proxy
        setup_proxy(proxy_token="my_secret")

    Specific hosts::

        setup_proxy(
            proxy_token="tok",
            hosts=["api.telegram.org", "api.openai.com"],
        )

    Intercept everything::

        setup_proxy(proxy_token="tok", intercept_all=True)

    Custom forwarder URL::

        setup_proxy(
            proxy_token="tok",
            proxy_base_url="https://my-relay.example.com",
            hosts=["httpbin.org"],
        )
    """
    if not proxy_token:
        raise ValueError(
            "proxy_token is required. "
            "Pass the FORWARDER_TOKEN value configured on the forwarder server."
        )

    base_url = proxy_base_url.rstrip("/")

    # Resolve the set of hosts to intercept.
    resolved_hosts: Set[str] = set()
    if not intercept_all:
        if hosts:
            resolved_hosts = set(hosts)
        else:
            # Default: historically the Telegram API host
            resolved_hosts = {DEFAULT_API_HOST}
        # Legacy: merge extra_hosts
        if extra_hosts:
            resolved_hosts.update(extra_hosts)

    # Cache the forwarder's own hostname so we never intercept it (loop guard).
    try:
        forwarder_host = urlparse(base_url).hostname
    except Exception:
        forwarder_host = None

    if _state["active"]:
        logger.warning(
            "Proxy already active — updating configuration without re-patching."
        )
        _state["proxy_base_url"] = base_url
        _state["proxy_token"] = proxy_token
        _state["intercept_all"] = intercept_all
        _state["intercepted_hosts"] = resolved_hosts
        _state["forwarder_host"] = forwarder_host
        return

    _state["proxy_base_url"] = base_url
    _state["proxy_token"] = proxy_token
    _state["intercept_all"] = intercept_all
    _state["intercepted_hosts"] = resolved_hosts
    _state["forwarder_host"] = forwarder_host

    # Save the original method and replace it with the patched version.
    _state["original_request"] = requests.Session.request
    requests.Session.request = _patched_request  # type: ignore[assignment]
    _state["active"] = True

    if intercept_all:
        logger.info(
            "Proxy activated (intercept ALL) — requests routed through %s",
            base_url,
        )
    else:
        logger.info(
            "Proxy activated for %s — requests routed through %s",
            ", ".join(sorted(resolved_hosts)),
            base_url,
        )


def disable_proxy() -> None:
    """Deactivate the proxy and restore direct HTTP access.

    Safe to call even if the proxy is not currently active (logs a warning).
    """
    if not _state["active"]:
        logger.warning("Proxy is not active — nothing to disable.")
        return

    requests.Session.request = _state["original_request"]  # type: ignore[assignment]
    _state["active"] = False
    _state["original_request"] = None

    logger.info("Proxy deactivated — requests are now sent directly.")


def is_active() -> bool:
    """Return ``True`` if the proxy is currently active."""
    return _state["active"]


def get_proxy_url() -> str:
    """Return the current forwarder base URL, or an empty string if not configured."""
    return _state.get("proxy_base_url") or ""


def get_intercepted_hosts() -> Set[str]:
    """Return the set of hostnames currently being intercepted.

    Returns an empty set when ``intercept_all=True`` (everything is
    intercepted) or when the proxy is not active.
    """
    return set(_state.get("intercepted_hosts", set()))


# ══════════════════════════ Patch core ════════════════════════════


def _patched_request(
    self: requests.Session,
    method: str,
    url: Union[str, bytes],
    **kwargs: Any,
) -> requests.Response:
    """Drop-in replacement for ``requests.Session.request``.

    Workflow
    --------
    1. Parse the target URL.
    2. Decide whether to intercept:
       - ``intercept_all=True``:  intercept everything *except* the forwarder.
       - Host-based: intercept only if the hostname is in the configured set.
    3. If intercepting:
       - Rewrite the URL to ``<proxy_base>/forward``.
       - Inject the original URL as the ``url`` query parameter.
       - Add authentication headers for the forwarder.
       - Forward every other kwarg (data, files, json, timeout …) untouched.
    4. The forwarder relays the request and returns the raw response.
    """
    original_request = _state["original_request"]

    # ── Parse the URL ──────────────────────────────────────────────
    try:
        parsed = urlparse(str(url))
    except Exception:
        return original_request(self, method, url, **kwargs)

    hostname = parsed.hostname

    # ── Should this request be intercepted? ────────────────────────
    should_intercept = False

    if _state["intercept_all"]:
        # Intercept everything except the forwarder itself (loop guard).
        should_intercept = hostname != _state.get("forwarder_host")
    else:
        should_intercept = hostname in _state["intercepted_hosts"]

    if not should_intercept:
        return original_request(self, method, url, **kwargs)

    # ══════════════════════════════════════════════════════════════
    #  Intercept: redirect to the forwarder service
    # ══════════════════════════════════════════════════════════════

    forward_url: str = f"{_state['proxy_base_url']}{FORWARD_ENDPOINT}"
    proxy_token: str = _state["proxy_token"]

    # ── Prepare headers ────────────────────────────────────────────
    raw_headers = kwargs.get("headers")
    headers: Dict[str, str] = dict(raw_headers) if raw_headers else {}

    # Send both header styles so the forwarder can verify either way.
    headers["Authorization"] = f"Bearer {proxy_token}"
    headers["X-Api-Token"] = proxy_token
    kwargs["headers"] = headers

    # ── Prepare query params ───────────────────────────────────────
    # The original URL is injected as the ``url`` query parameter.
    # The forwarder extracts it and forwards the remaining params to the
    # real destination.
    raw_params = kwargs.get("params")

    if raw_params is None:
        params: Any = {"url": url}
    elif isinstance(raw_params, dict):
        params = dict(raw_params)
        params["url"] = url
    elif isinstance(raw_params, (list, tuple)):
        params = list(raw_params)
        params.append(("url", url))
    elif isinstance(raw_params, bytes):
        decoded = parse_qs(raw_params.decode("utf-8", errors="replace"))
        params = {k: v[0] if len(v) == 1 else v for k, v in decoded.items()}
        params["url"] = url
    else:
        params = {"url": url}

    kwargs["params"] = params

    logger.debug(
        "requests-forwarder: %s %s -> %s",
        method.upper() if isinstance(method, str) else method,
        url,
        forward_url,
    )

    # ── Send via forwarder ─────────────────────────────────────────
    return original_request(self, method, forward_url, **kwargs)

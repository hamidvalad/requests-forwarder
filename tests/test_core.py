"""Tests for requests_forwarder.core — general-purpose HTTP forwarder proxy."""

from __future__ import annotations

import json
from urllib.parse import parse_qs, urlparse

import pytest
import requests
import responses

from requests_forwarder import (
    disable_proxy,
    get_intercepted_hosts,
    get_proxy_url,
    is_active,
    setup_proxy,
)
from requests_forwarder.core import (
    DEFAULT_PROXY_BASE_URL,
    DEFAULT_API_HOST,
    _state,
)


# ──────────────────────── Fixtures ─────────────────────────────


@pytest.fixture(autouse=True)
def _reset_proxy():
    """Ensure a clean state before and after every test."""
    if _state["active"]:
        disable_proxy()
    _state["intercepted_hosts"] = set()
    _state["intercept_all"] = False
    _state["forwarder_host"] = None
    yield
    if _state["active"]:
        disable_proxy()
    _state["intercepted_hosts"] = set()
    _state["intercept_all"] = False
    _state["forwarder_host"] = None


# ══════════════════════════ setup_proxy ═════════════════════════


class TestSetupProxy:
    def test_activation_defaults_to_telegram(self):
        """Without hosts/intercept_all, defaults to api.telegram.org."""
        setup_proxy(proxy_token="tok123")
        assert is_active() is True
        assert get_proxy_url() == DEFAULT_PROXY_BASE_URL
        assert DEFAULT_API_HOST in get_intercepted_hosts()

    def test_custom_base_url(self):
        setup_proxy(proxy_token="tok", proxy_base_url="https://example.com/")
        assert get_proxy_url() == "https://example.com"  # trailing slash stripped

    def test_rejects_empty_token(self):
        with pytest.raises(ValueError, match="proxy_token"):
            setup_proxy(proxy_token="")

    def test_rejects_none_token(self):
        with pytest.raises(ValueError):
            setup_proxy(proxy_token=None)  # type: ignore[arg-type]

    def test_double_activation_updates_config(self):
        setup_proxy(proxy_token="first")
        setup_proxy(proxy_token="second", proxy_base_url="https://new.example.com")
        assert _state["proxy_token"] == "second"
        assert get_proxy_url() == "https://new.example.com"
        assert is_active() is True

    def test_custom_hosts(self):
        setup_proxy(proxy_token="tok", hosts=["api.example.com", "other.io"])
        hosts = get_intercepted_hosts()
        assert "api.example.com" in hosts
        assert "other.io" in hosts
        assert DEFAULT_API_HOST not in hosts  # not included unless specified

    def test_extra_hosts_legacy(self):
        """Backward-compatible extra_hosts merges with default Telegram host."""
        setup_proxy(proxy_token="tok", extra_hosts=["custom.api.example.com"])
        hosts = get_intercepted_hosts()
        assert "custom.api.example.com" in hosts
        assert DEFAULT_API_HOST in hosts

    def test_intercept_all_mode(self):
        setup_proxy(proxy_token="tok", intercept_all=True)
        assert _state["intercept_all"] is True
        # In intercept_all mode, intercepted_hosts is empty (everything goes).
        assert get_intercepted_hosts() == set()


# ══════════════════════════ disable_proxy ═══════════════════════


class TestDisableProxy:
    def test_deactivation(self):
        setup_proxy(proxy_token="tok")
        disable_proxy()
        assert is_active() is False

    def test_disable_when_not_active(self):
        """Should not raise, just warn."""
        disable_proxy()
        assert is_active() is False


# ══════════════════════════ Host-based interception ═════════════


class TestHostBasedInterception:
    """Verify host-based (selective) interception."""

    @responses.activate
    def test_telegram_request_is_redirected(self):
        responses.add(
            responses.GET,
            "https://forwarder.test/forward",
            json={"ok": True},
            status=200,
        )

        setup_proxy(
            proxy_token="secret",
            proxy_base_url="https://forwarder.test",
        )

        resp = requests.get("https://api.telegram.org/bot123/getMe")
        assert resp.status_code == 200
        assert resp.json() == {"ok": True}

        sent = responses.calls[0].request
        parsed = urlparse(sent.url)
        assert parsed.hostname == "forwarder.test"
        assert parsed.path == "/forward"

        qs = parse_qs(parsed.query)
        assert "url" in qs
        assert "api.telegram.org" in qs["url"][0]

    @responses.activate
    def test_custom_host_intercepted(self):
        """Requests to a custom host should be intercepted."""
        responses.add(responses.GET, "https://fw.test/forward", json={"ok": True})
        setup_proxy(
            proxy_token="tok",
            proxy_base_url="https://fw.test",
            hosts=["httpbin.org"],
        )

        resp = requests.get("https://httpbin.org/get", params={"foo": "bar"})
        assert resp.status_code == 200

        sent = responses.calls[0].request
        parsed = urlparse(sent.url)
        assert parsed.hostname == "fw.test"
        qs = parse_qs(parsed.query)
        assert "httpbin.org" in qs["url"][0]
        assert qs["foo"] == ["bar"]

    @responses.activate
    def test_non_matching_host_passes_through(self):
        """Requests to hosts NOT in the list should pass through."""
        responses.add(
            responses.GET,
            "https://example.com/api/data",
            json={"data": 1},
            status=200,
        )

        setup_proxy(
            proxy_token="tok",
            proxy_base_url="https://fw.test",
            hosts=["api.telegram.org"],
        )

        resp = requests.get("https://example.com/api/data")
        assert resp.status_code == 200

        sent = responses.calls[0].request
        assert urlparse(sent.url).hostname == "example.com"

    @responses.activate
    def test_multiple_hosts(self):
        """Multiple hosts can be intercepted simultaneously."""
        responses.add(responses.GET, "https://fw.test/forward", json={})
        responses.add(responses.POST, "https://fw.test/forward", json={})
        setup_proxy(
            proxy_token="tok",
            proxy_base_url="https://fw.test",
            hosts=["api.telegram.org", "api.openai.com"],
        )

        requests.get("https://api.telegram.org/bot123/getMe")
        requests.post(
            "https://api.openai.com/v1/chat/completions",
            json={"model": "gpt-4"},
        )

        assert len(responses.calls) == 2
        for call in responses.calls:
            assert urlparse(call.request.url).hostname == "fw.test"


# ══════════════════════════ Intercept-all mode ═════════════════


class TestInterceptAll:
    """Verify intercept_all=True catches everything."""

    @responses.activate
    def test_any_host_intercepted(self):
        responses.add(responses.GET, "https://fw.test/forward", json={"ok": True})
        setup_proxy(
            proxy_token="tok",
            proxy_base_url="https://fw.test",
            intercept_all=True,
        )

        requests.get("https://random-api.example.com/data")

        sent = responses.calls[0].request
        parsed = urlparse(sent.url)
        assert parsed.hostname == "fw.test"
        qs = parse_qs(parsed.query)
        assert "random-api.example.com" in qs["url"][0]

    @responses.activate
    def test_forwarder_itself_not_intercepted(self):
        """Requests to the forwarder host must NOT be re-intercepted (loop guard)."""
        # This simulates the actual forwarded call reaching the forwarder.
        responses.add(responses.GET, "https://fw.test/health", json={"status": "ok"})
        # Also add the forward endpoint for the intercepted call.
        responses.add(responses.GET, "https://fw.test/forward", json={})

        setup_proxy(
            proxy_token="tok",
            proxy_base_url="https://fw.test",
            intercept_all=True,
        )

        # Direct call to the forwarder itself — must NOT be intercepted.
        resp = requests.get("https://fw.test/health")
        assert resp.json() == {"status": "ok"}

        sent = responses.calls[0].request
        parsed = urlparse(sent.url)
        assert parsed.path == "/health"  # NOT /forward
        # No url query param should be added.
        assert "url" not in parse_qs(parsed.query)

    @responses.activate
    def test_multiple_different_hosts(self):
        responses.add(responses.GET, "https://fw.test/forward", json={})
        setup_proxy(
            proxy_token="tok",
            proxy_base_url="https://fw.test",
            intercept_all=True,
        )

        requests.get("https://api.telegram.org/bot123/getMe")
        requests.get("https://httpbin.org/get")
        requests.get("https://jsonplaceholder.typicode.com/posts/1")

        assert len(responses.calls) == 3
        for call in responses.calls:
            assert urlparse(call.request.url).hostname == "fw.test"


# ══════════════════════════ Auth & headers ═════════════════════


class TestAuthHeaders:

    @responses.activate
    def test_auth_headers_injected(self):
        responses.add(responses.POST, "https://fw.test/forward", json={}, status=200)
        setup_proxy(proxy_token="mytoken", proxy_base_url="https://fw.test")

        requests.post(
            "https://api.telegram.org/bot123/sendMessage",
            json={"chat_id": 1, "text": "hi"},
        )

        sent = responses.calls[0].request
        assert sent.headers["Authorization"] == "Bearer mytoken"
        assert sent.headers["X-Api-Token"] == "mytoken"

    @responses.activate
    def test_existing_headers_preserved(self):
        """Custom headers from the caller should not be lost."""
        responses.add(responses.GET, "https://fw.test/forward", json={})
        setup_proxy(
            proxy_token="tok",
            proxy_base_url="https://fw.test",
            hosts=["example.com"],
        )

        requests.get(
            "https://example.com/api",
            headers={"X-Custom": "value123"},
        )

        sent = responses.calls[0].request
        assert sent.headers["X-Custom"] == "value123"
        assert sent.headers["Authorization"] == "Bearer tok"


# ══════════════════════════ Body & params ══════════════════════


class TestBodyAndParams:

    @responses.activate
    def test_json_body_forwarded(self):
        responses.add(responses.POST, "https://fw.test/forward", json={"ok": True})
        setup_proxy(proxy_token="tok", proxy_base_url="https://fw.test")

        payload = {"chat_id": 123, "text": "hello world"}
        requests.post(
            "https://api.telegram.org/bot123/sendMessage",
            json=payload,
        )

        sent = responses.calls[0].request
        assert json.loads(sent.body) == payload

    @responses.activate
    def test_query_params_preserved(self):
        responses.add(responses.GET, "https://fw.test/forward", json={})
        setup_proxy(proxy_token="tok", proxy_base_url="https://fw.test")

        requests.get(
            "https://api.telegram.org/bot123/getUpdates",
            params={"offset": "100", "timeout": "20"},
        )

        sent = responses.calls[0].request
        qs = parse_qs(urlparse(sent.url).query)
        assert qs["offset"] == ["100"]
        assert qs["timeout"] == ["20"]
        assert "url" in qs

    @responses.activate
    def test_form_data_forwarded(self):
        """Form-encoded data should be forwarded intact."""
        responses.add(responses.POST, "https://fw.test/forward", json={})
        setup_proxy(
            proxy_token="tok",
            proxy_base_url="https://fw.test",
            hosts=["example.com"],
        )

        requests.post(
            "https://example.com/submit",
            data={"name": "test", "value": "123"},
        )

        sent = responses.calls[0].request
        assert "name=test" in sent.body
        assert "value=123" in sent.body


# ══════════════════════════ Disable & restore ══════════════════


class TestDisableRestore:

    @responses.activate
    def test_disabled_passes_through(self):
        responses.add(
            responses.GET,
            "https://api.telegram.org/bot123/getMe",
            json={"ok": True},
        )

        setup_proxy(proxy_token="tok", proxy_base_url="https://fw.test")
        disable_proxy()

        resp = requests.get("https://api.telegram.org/bot123/getMe")
        assert resp.status_code == 200

        sent = responses.calls[0].request
        assert urlparse(sent.url).hostname == "api.telegram.org"

    @responses.activate
    def test_intercept_all_disabled_passes_through(self):
        responses.add(
            responses.GET,
            "https://example.com/data",
            json={"data": 1},
        )

        setup_proxy(
            proxy_token="tok",
            proxy_base_url="https://fw.test",
            intercept_all=True,
        )
        disable_proxy()

        resp = requests.get("https://example.com/data")
        sent = responses.calls[0].request
        assert urlparse(sent.url).hostname == "example.com"

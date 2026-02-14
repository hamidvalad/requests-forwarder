# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2026-02-14

### Added

- General-purpose proxying: works with any hostname (not limited to Telegram).
- `hosts` parameter — specify a list of hostnames to intercept.
- `intercept_all` parameter — route every outgoing request through the forwarder.
- `get_intercepted_hosts()` — query which hosts are currently being intercepted.
- Loop guard — requests to the forwarder itself are never intercepted.
- `setup_proxy()` — activate the forwarder proxy with a single function call.
- `disable_proxy()` — deactivate the proxy and restore direct access.
- `is_active()` — check whether the proxy is currently active.
- `get_proxy_url()` — retrieve the current forwarder base URL.
- Transparent monkey-patching of `requests.Session.request`.
- Support for pyTelegramBotAPI (telebot) and any library that uses `requests`.
- Support for both polling and webhook modes for bots.
- Thread-safe header/param copying.
- Dual authentication headers (`Authorization: Bearer` + `X-Api-Token`).
- Examples: echo bot, photo bot, env-based config, webhook, general API proxy, intercept-all, mixed examples.
- Test suite covering main behaviors.

### Changed

- `extra_hosts` is deprecated in favor of `hosts` (use `hosts` going forward).

## [1.0.1] - 2026-02-14

### Added

- Documentation: explicit notice about the public hosted free plan at
	`https://requests-forwarder.ir` and instructions to self-host the forwarder.
	The README now explains that the hosted endpoint is convenient for testing
	but subject to usage limits (rate limits, payload limits and fair-use
	policies) and that users can run their own forwarder and provide its URL as
	input.

### Changed

- Default forwarder base URL changed from `https://requests-forwarder.ir` to
	`https://requests-forwarder.ir` to match the hosted endpoint scheme and the
	documentation. Examples and configuration guidance updated accordingly.
- Bumped package version to `1.0.1`.


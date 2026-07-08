"""HIGH audit finding: Docker path ships auth-open on 0.0.0.0.

``serve()`` enforces ``CLOUDWRIGHT_API_KEY`` before starting uvicorn, but the
Dockerfile's CMD runs ``uvicorn cloudwright_web.app:app`` directly, which never
calls ``serve()``. Middleware's ``check_api_key`` silently disables auth when
the key is unset, so a container started without the env var serves every
route unauthenticated on ``0.0.0.0``.

Fix: ``create_app()`` calls a guard that refuses to start when
``CLOUDWRIGHT_REQUIRE_AUTH`` is set (the Dockerfile sets it) and
``CLOUDWRIGHT_API_KEY`` is not. Local ``uvicorn``/pytest runs must stay
open-by-default (``CLOUDWRIGHT_REQUIRE_AUTH`` unset), so the 99 pre-existing
web tests are unaffected.
"""

from __future__ import annotations

import pytest
from cloudwright_web.app import _enforce_auth_requirement


class TestRequireAuthGuard:
    def test_raises_when_required_and_key_missing(self, monkeypatch):
        monkeypatch.setenv("CLOUDWRIGHT_REQUIRE_AUTH", "1")
        monkeypatch.delenv("CLOUDWRIGHT_API_KEY", raising=False)
        with pytest.raises(SystemExit):
            _enforce_auth_requirement()

    def test_does_not_raise_when_required_and_key_present(self, monkeypatch):
        monkeypatch.setenv("CLOUDWRIGHT_REQUIRE_AUTH", "1")
        monkeypatch.setenv("CLOUDWRIGHT_API_KEY", "secret-value")
        _enforce_auth_requirement()

    def test_does_not_raise_when_not_required_even_if_key_missing(self, monkeypatch):
        """Local dev / pytest default: open when the flag is unset."""
        monkeypatch.delenv("CLOUDWRIGHT_REQUIRE_AUTH", raising=False)
        monkeypatch.delenv("CLOUDWRIGHT_API_KEY", raising=False)
        _enforce_auth_requirement()

    @pytest.mark.parametrize("falsy_value", ["0", "false", "no", ""])
    def test_falsy_require_auth_values_do_not_raise(self, monkeypatch, falsy_value):
        monkeypatch.setenv("CLOUDWRIGHT_REQUIRE_AUTH", falsy_value)
        monkeypatch.delenv("CLOUDWRIGHT_API_KEY", raising=False)
        _enforce_auth_requirement()


class TestAppStillImportsInDefaultTestEnv:
    def test_app_module_imports_without_require_auth_set(self):
        """The 99 pre-existing web tests import ``cloudwright_web.app`` with
        no CLOUDWRIGHT_REQUIRE_AUTH set — module import (which calls
        create_app() -> _enforce_auth_requirement()) must not raise."""
        from cloudwright_web.app import app

        assert app is not None

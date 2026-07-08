"""MEDIUM (observability): structured logging must activate on real launch paths.

``configure_logging()`` was only called inside ``serve()``, so ``cloudwright
chat --web`` worked (it calls ``serve()``) but a bare
``uvicorn cloudwright_web.app:app`` (the Dockerfile's CMD) and the
``python -c "from cloudwright_web.app import serve; serve(...)"`` path that
skips ``serve()`` (e.g. any ASGI-server-managed deployment) never got
structured logs.

Fix: call ``configure_logging()`` at app-creation time (``create_app()``),
which fires for every import of ``cloudwright_web.app``, not just the CLI's
``serve()`` path. ``configure_logging()`` is idempotent (module-level
``_configured`` guard in ``cloudwright.logging``), so calling it twice
(once at import, once again in ``serve()``) is a no-op the second time.
"""

from __future__ import annotations

import inspect


def test_create_app_calls_configure_logging():
    from cloudwright_web import app as app_module

    src = inspect.getsource(app_module.create_app)
    assert "configure_logging" in src, (
        "create_app() must call configure_logging() so structured logs activate "
        "on every launch path (bare uvicorn, cloudwright chat --web), not just serve()"
    )


def test_configure_logging_is_idempotent_across_create_app_and_serve():
    """Calling configure_logging() twice (create_app(), then serve()) must not
    raise or double-register handlers."""
    from cloudwright.logging import configure_logging

    configure_logging()
    configure_logging()  # second call must be a no-op, not an error

"""Cloudwright Web — FastAPI backend for architecture intelligence."""

__version__ = "0.2.16"


def __getattr__(name: str):
    if name == "app":
        from cloudwright_web.app import app

        return app
    raise AttributeError(f"module 'cloudwright_web' has no attribute {name!r}")

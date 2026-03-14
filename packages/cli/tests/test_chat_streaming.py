from __future__ import annotations

from unittest.mock import MagicMock, patch


def _make_session(chunks=None, send_return=None):
    session = MagicMock()
    session.current_spec = None
    session.last_usage = {}
    session.last_diff = None
    session.history = []
    if chunks is not None:
        session.send_stream.return_value = iter(chunks)
    if send_return is not None:
        session.send.return_value = send_return
    return session


class TestStreamingFallback:
    def test_streaming_fallback_to_send(self, capsys):
        session = _make_session()
        session.send_stream.side_effect = RuntimeError("stream failed")
        session.send.return_value = ("fallback response", None)

        with (
            patch("cloudwright_cli.commands.chat.ConversationSession", return_value=session),
            patch("cloudwright_cli.commands.chat.SessionStore"),
            patch("cloudwright_cli.commands.chat.Prompt.ask", side_effect=["hello", KeyboardInterrupt]),
            patch("cloudwright_cli.commands.chat.Live"),
        ):
            from cloudwright_cli.commands.chat import _run_terminal_chat

            _run_terminal_chat()

        session.send.assert_called_once_with("hello")

    def test_streaming_fallback_skips_on_rate_limit(self):
        session = _make_session()
        session.send_stream.side_effect = Exception("rate limit exceeded")
        session.send.return_value = ("ignored", None)

        with (
            patch("cloudwright_cli.commands.chat.ConversationSession", return_value=session),
            patch("cloudwright_cli.commands.chat.SessionStore"),
            patch("cloudwright_cli.commands.chat.Prompt.ask", side_effect=["hi", KeyboardInterrupt]),
            patch("cloudwright_cli.commands.chat.Live"),
        ):
            from cloudwright_cli.commands.chat import _run_terminal_chat

            _run_terminal_chat()

        # Rate limit is handled before falling back to send()
        session.send.assert_not_called()

    def test_streaming_renders_output(self):
        chunks = ["Hello", " world", "!"]
        session = _make_session(chunks=chunks)

        collected = []

        class FakeLive:
            def __init__(self, *a, **kw):
                pass

            def __enter__(self):
                return self

            def __exit__(self, *a):
                pass

            def update(self, renderable):
                # Markdown wraps the markup string; access it to verify content
                collected.append(getattr(renderable, "markup", str(renderable)))

        with (
            patch("cloudwright_cli.commands.chat.ConversationSession", return_value=session),
            patch("cloudwright_cli.commands.chat.SessionStore"),
            patch("cloudwright_cli.commands.chat.Prompt.ask", side_effect=["hello", KeyboardInterrupt]),
            patch("cloudwright_cli.commands.chat.Live", FakeLive),
        ):
            from cloudwright_cli.commands.chat import _run_terminal_chat

            _run_terminal_chat()

        assert len(collected) == 3
        assert "Hello world!" in collected[-1]

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch


def _make_session(turn_count=0, spec=None):
    session = MagicMock()
    session.current_spec = spec
    session.last_usage = {}
    session.last_diff = None
    session.history = [{"role": "user", "content": "x"}] * turn_count
    session.send_stream.side_effect = RuntimeError("no llm")
    session.send.side_effect = RuntimeError("no llm")
    return session


class TestSaveSession:
    def test_save_session_command(self):
        session = _make_session(turn_count=1)
        store = MagicMock()
        store.save.return_value = Path("/tmp/session-abc.json")

        with (
            patch("cloudwright_cli.commands.chat.ConversationSession", return_value=session),
            patch("cloudwright_cli.commands.chat.SessionStore", return_value=store),
            patch(
                "cloudwright_cli.commands.chat.Prompt.ask",
                # "/save-session" saves, then /quit triggers quit-save prompt answered "N"
                side_effect=["/save-session mysession", "/quit", "N"],
            ),
        ):
            from cloudwright_cli.commands.chat import _run_terminal_chat

            _run_terminal_chat()

        # First save call is from /save-session command
        first = store.save.call_args_list[0]
        assert first.args[0] == "mysession"
        assert first.args[1] is session

    def test_save_session_default_name(self):
        session = _make_session(turn_count=1)
        store = MagicMock()
        store.save.return_value = Path("/tmp/session-xyz.json")

        with (
            patch("cloudwright_cli.commands.chat.ConversationSession", return_value=session),
            patch("cloudwright_cli.commands.chat.SessionStore", return_value=store),
            patch(
                "cloudwright_cli.commands.chat.Prompt.ask",
                side_effect=["/save-session", "/quit", "N"],
            ),
        ):
            from cloudwright_cli.commands.chat import _run_terminal_chat

            _run_terminal_chat()

        store.save.assert_called()
        first_call_name = store.save.call_args_list[0].args[0]
        assert first_call_name.startswith("session-")


class TestLoadSession:
    def test_load_session_command(self):
        loaded = _make_session()
        store = MagicMock()
        store.load.return_value = loaded

        with (
            patch("cloudwright_cli.commands.chat.ConversationSession"),
            patch("cloudwright_cli.commands.chat.SessionStore", return_value=store),
            patch(
                "cloudwright_cli.commands.chat.Prompt.ask",
                side_effect=["/load-session myname", KeyboardInterrupt],
            ),
        ):
            from cloudwright_cli.commands.chat import _run_terminal_chat

            _run_terminal_chat()

        store.load.assert_called_once_with("myname")

    def test_load_session_not_found(self):
        store = MagicMock()
        store.load.side_effect = FileNotFoundError

        with (
            patch("cloudwright_cli.commands.chat.ConversationSession"),
            patch("cloudwright_cli.commands.chat.SessionStore", return_value=store),
            patch(
                "cloudwright_cli.commands.chat.Prompt.ask",
                side_effect=["/load-session ghost", KeyboardInterrupt],
            ),
        ):
            from cloudwright_cli.commands.chat import _run_terminal_chat

            _run_terminal_chat()

        store.load.assert_called_once_with("ghost")


class TestSessionsList:
    def test_sessions_list_command(self):
        store = MagicMock()
        store.list_sessions.return_value = [
            {"session_id": "abc123", "turn_count": 3, "spec_name": "My App"},
        ]

        with (
            patch("cloudwright_cli.commands.chat.ConversationSession"),
            patch("cloudwright_cli.commands.chat.SessionStore", return_value=store),
            patch(
                "cloudwright_cli.commands.chat.Prompt.ask",
                side_effect=["/sessions", KeyboardInterrupt],
            ),
        ):
            from cloudwright_cli.commands.chat import _run_terminal_chat

            _run_terminal_chat()

        store.list_sessions.assert_called_once()


class TestResumeFlag:
    def test_resume_loads_session(self):
        loaded = _make_session()
        store = MagicMock()
        store.load.return_value = loaded

        with (
            patch("cloudwright_cli.commands.chat.ConversationSession"),
            patch("cloudwright_cli.commands.chat.SessionStore", return_value=store),
            patch("cloudwright_cli.commands.chat.Prompt.ask", side_effect=[KeyboardInterrupt]),
        ):
            from cloudwright_cli.commands.chat import _run_terminal_chat

            _run_terminal_chat(resume="abc123")

        store.load.assert_called_once_with("abc123")

    def test_resume_not_found_starts_fresh(self):
        fresh = _make_session()
        store = MagicMock()
        store.load.side_effect = FileNotFoundError

        with (
            patch("cloudwright_cli.commands.chat.ConversationSession", return_value=fresh),
            patch("cloudwright_cli.commands.chat.SessionStore", return_value=store),
            patch("cloudwright_cli.commands.chat.Prompt.ask", side_effect=[KeyboardInterrupt]),
        ):
            from cloudwright_cli.commands.chat import _run_terminal_chat

            _run_terminal_chat(resume="ghost")

        store.load.assert_called_once_with("ghost")


class TestQuitWithSavePrompt:
    def test_quit_with_history_prompts_save(self):
        session = _make_session(turn_count=2)
        store = MagicMock()
        store.save.return_value = Path("/tmp/s.json")

        with (
            patch("cloudwright_cli.commands.chat.ConversationSession", return_value=session),
            patch("cloudwright_cli.commands.chat.SessionStore", return_value=store),
            # first prompt is user input, second is the save prompt
            patch("cloudwright_cli.commands.chat.Prompt.ask", side_effect=["/quit", "y"]),
        ):
            from cloudwright_cli.commands.chat import _run_terminal_chat

            _run_terminal_chat()

        store.save.assert_called_once()

    def test_quit_no_history_skips_save_prompt(self):
        session = _make_session(turn_count=0)
        store = MagicMock()

        with (
            patch("cloudwright_cli.commands.chat.ConversationSession", return_value=session),
            patch("cloudwright_cli.commands.chat.SessionStore", return_value=store),
            patch("cloudwright_cli.commands.chat.Prompt.ask", side_effect=["/quit"]),
        ):
            from cloudwright_cli.commands.chat import _run_terminal_chat

            _run_terminal_chat()

        store.save.assert_not_called()

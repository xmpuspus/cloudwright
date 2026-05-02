from __future__ import annotations

import logging
from unittest.mock import patch


class TestDebugMode:
    def test_debug_enables_logging(self):
        """--debug flag should set the cloudwright logger to DEBUG level.

        Audit fix v1.3: previously called logging.basicConfig() which is a
        no-op against the structlog-configured root logger. Now it sets
        DEBUG on the root + cloudwright logger directly.
        """
        cloudwright_logger = logging.getLogger("cloudwright")
        prior_level = cloudwright_logger.level
        try:
            with (
                patch("cloudwright_cli.commands.chat.ConversationSession"),
                patch("cloudwright_cli.commands.chat.SessionStore"),
                patch("cloudwright_cli.commands.chat.Prompt.ask", side_effect=[KeyboardInterrupt]),
            ):
                from cloudwright_cli.commands.chat import _run_terminal_chat

                _run_terminal_chat(debug=True)

            assert cloudwright_logger.level == logging.DEBUG
        finally:
            cloudwright_logger.setLevel(prior_level)

    def test_debug_flag_via_chat_entrypoint(self):
        with (
            patch("cloudwright_cli.commands.chat._run_terminal_chat") as mock_run,
            patch("cloudwright_cli.commands.chat._launch_web"),
        ):
            from cloudwright_cli.commands.chat import chat

            chat(web=False, resume=None, debug=True)

        # The chat() entrypoint may pass extra args (port). Just assert debug=True.
        assert mock_run.call_count == 1
        kwargs = mock_run.call_args.kwargs
        assert kwargs.get("debug") is True

    def test_no_debug_flag_via_chat_entrypoint(self):
        with (
            patch("cloudwright_cli.commands.chat._run_terminal_chat") as mock_run,
            patch("cloudwright_cli.commands.chat._launch_web"),
        ):
            from cloudwright_cli.commands.chat import chat

            chat(web=False, resume=None, debug=False)

        assert mock_run.call_count == 1
        assert mock_run.call_args.kwargs.get("debug") is False

    def test_log_level_env_var_debug(self, monkeypatch):
        """CLOUDWRIGHT_LOG_LEVEL=DEBUG should also set DEBUG even without --debug."""
        monkeypatch.setenv("CLOUDWRIGHT_LOG_LEVEL", "DEBUG")
        cloudwright_logger = logging.getLogger("cloudwright")
        prior_level = cloudwright_logger.level
        try:
            with (
                patch("cloudwright_cli.commands.chat.ConversationSession"),
                patch("cloudwright_cli.commands.chat.SessionStore"),
                patch("cloudwright_cli.commands.chat.Prompt.ask", side_effect=[KeyboardInterrupt]),
            ):
                from cloudwright_cli.commands.chat import _run_terminal_chat

                _run_terminal_chat(debug=False)

            assert cloudwright_logger.level == logging.DEBUG
        finally:
            cloudwright_logger.setLevel(prior_level)

from __future__ import annotations

import logging
import sys
from unittest.mock import patch


class TestDebugMode:
    def test_debug_enables_logging(self):
        with (
            patch("cloudwright_cli.commands.chat.ConversationSession"),
            patch("cloudwright_cli.commands.chat.SessionStore"),
            patch("cloudwright_cli.commands.chat.Prompt.ask", side_effect=[KeyboardInterrupt]),
            patch("logging.basicConfig") as mock_basic,
        ):
            from cloudwright_cli.commands.chat import _run_terminal_chat

            _run_terminal_chat(debug=True)

        mock_basic.assert_called_once_with(stream=sys.stderr, level=logging.DEBUG)

    def test_no_debug_by_default(self):
        with (
            patch("cloudwright_cli.commands.chat.ConversationSession"),
            patch("cloudwright_cli.commands.chat.SessionStore"),
            patch("cloudwright_cli.commands.chat.Prompt.ask", side_effect=[KeyboardInterrupt]),
            patch("logging.basicConfig") as mock_basic,
        ):
            from cloudwright_cli.commands.chat import _run_terminal_chat

            _run_terminal_chat(debug=False)

        mock_basic.assert_not_called()

    def test_debug_flag_via_chat_entrypoint(self):
        with (
            patch("cloudwright_cli.commands.chat._run_terminal_chat") as mock_run,
            patch("cloudwright_cli.commands.chat._launch_web"),
        ):
            from cloudwright_cli.commands.chat import chat

            chat(web=False, resume=None, debug=True)

        mock_run.assert_called_once_with(resume=None, debug=True)

    def test_no_debug_flag_via_chat_entrypoint(self):
        with (
            patch("cloudwright_cli.commands.chat._run_terminal_chat") as mock_run,
            patch("cloudwright_cli.commands.chat._launch_web"),
        ):
            from cloudwright_cli.commands.chat import chat

            chat(web=False, resume=None, debug=False)

        mock_run.assert_called_once_with(resume=None, debug=False)

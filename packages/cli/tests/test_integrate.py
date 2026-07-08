"""Tests for `cloudwright integrate` (harness wiring generator)."""

from __future__ import annotations

import json
from pathlib import Path

from cloudwright_cli.main import app
from typer.testing import CliRunner

runner = CliRunner()


class TestList:
    def test_list_runs_and_names_harnesses(self):
        result = runner.invoke(app, ["integrate", "--list"])
        assert result.exit_code == 0
        for name in ["Claude Code", "Cursor", "Cline", "Windsurf", "GitHub Copilot", "Zed", "Codex", "Junie", "Aider"]:
            assert name in result.output

    def test_list_mentions_discontinued_harnesses_honestly(self):
        result = runner.invoke(app, ["integrate", "--list"])
        assert result.exit_code == 0
        assert "Roo Code" in result.output
        assert "Continue.dev" in result.output
        assert "kiro" in result.output.lower()
        assert "antigravity" in result.output.lower()

    def test_list_json(self):
        result = runner.invoke(app, ["--json", "integrate", "--list"])
        assert result.exit_code == 0
        envelope = json.loads(result.output)
        data = envelope["data"]
        keys = {h["key"] for h in data["harnesses"]}
        assert "claude-code" in keys
        assert "aider" in keys
        assert "roo-code" in data["discontinued"]


class TestHarnessDetail:
    def test_harness_claude_code_config(self):
        result = runner.invoke(app, ["integrate", "--harness", "claude-code"])
        assert result.exit_code == 0
        assert "cloudwright" in result.output
        assert '"mcp"' in result.output
        assert "mcpServers" in result.output
        assert "CLAUDE.md" in result.output

    def test_harness_accepts_normalized_names(self):
        result = runner.invoke(app, ["integrate", "--harness", "Claude Code"])
        assert result.exit_code == 0
        assert "mcpServers" in result.output

    def test_harness_zed_uses_context_servers(self):
        result = runner.invoke(app, ["integrate", "--harness", "zed"])
        assert result.exit_code == 0
        assert "context_servers" in result.output
        assert '"mcpServers"' not in result.output

    def test_harness_codex_emits_toml_table(self):
        result = runner.invoke(app, ["integrate", "--harness", "codex"])
        assert result.exit_code == 0
        assert "[mcp_servers.cloudwright]" in result.output
        assert 'command = "cloudwright"' in result.output

    def test_harness_copilot_uses_servers_key(self):
        result = runner.invoke(app, ["integrate", "--harness", "copilot"])
        assert result.exit_code == 0
        assert '"servers"' in result.output
        assert "stdio" in result.output

        envelope = json.loads(runner.invoke(app, ["--json", "integrate", "--harness", "copilot"]).output)
        assert envelope["data"]["config_key"] == "servers"
        assert "mcpServers" not in envelope["data"]["config_snippet"]

    def test_harness_aider_explains_cli_pipe_no_mcp_json(self):
        result = runner.invoke(app, ["integrate", "--harness", "aider"])
        assert result.exit_code == 0
        assert "not an MCP client" in result.output
        assert "cloudwright design" in result.output
        assert '"mcpServers"' not in result.output

    def test_harness_kiro_and_antigravity_resolve(self):
        for name in ("kiro", "antigravity"):
            result = runner.invoke(app, ["integrate", "--harness", name])
            assert result.exit_code == 0
            assert "mcpServers" in result.output

    def test_harness_aider_write_errors_with_rules_hint(self):
        result = runner.invoke(app, ["integrate", "--harness", "aider", "--write"])
        assert result.exit_code != 0
        assert "--rules --write" in (result.output + result.stderr)

    def test_harness_unknown_errors(self):
        result = runner.invoke(app, ["integrate", "--harness", "not-a-real-tool"])
        assert result.exit_code != 0

    def test_harness_discontinued_points_to_successor(self):
        result = runner.invoke(app, ["integrate", "--harness", "gemini-cli"])
        assert result.exit_code != 0
        assert "antigravity" in (result.output + result.stderr).lower()

        result = runner.invoke(app, ["integrate", "--harness", "amazon-q"])
        assert result.exit_code != 0
        assert "kiro" in (result.output + result.stderr).lower()


class TestRules:
    def test_rules_default_is_agents_md(self):
        result = runner.invoke(app, ["integrate", "--rules"])
        assert result.exit_code == 0
        assert "AGENTS.md" in result.output
        assert "cloudwright design" in result.output
        assert "cloudwright review" in result.output
        assert "cloudwright cost" in result.output
        assert "cloudwright compliance" in result.output

    def test_rules_claude_agent_file(self):
        result = runner.invoke(app, ["integrate", "--rules", "--agent-file", "claude"])
        assert result.exit_code == 0
        assert "CLAUDE.md" in result.output
        assert "cloudwright design" in result.output

    def test_rules_gemini_agent_file(self):
        result = runner.invoke(app, ["integrate", "--rules", "--agent-file", "gemini"])
        assert result.exit_code == 0
        assert "GEMINI.md" in result.output

    def test_rules_invalid_agent_file_errors(self):
        result = runner.invoke(app, ["integrate", "--rules", "--agent-file", "nope"])
        assert result.exit_code != 0

    def test_rules_no_em_dash_no_emoji(self):
        result = runner.invoke(app, ["integrate", "--rules"])
        assert "—" not in result.output


class TestGlobalJson:
    def test_json_flag_returns_parseable_envelope_for_harness(self):
        result = runner.invoke(app, ["--json", "integrate", "--harness", "cursor"])
        assert result.exit_code == 0
        envelope = json.loads(result.output)
        assert "data" in envelope
        assert envelope["data"]["config_key"] == "mcpServers"
        assert envelope["data"]["config_snippet"]["mcpServers"]["cloudwright"]["command"] == "cloudwright"
        assert envelope["data"]["config_snippet"]["mcpServers"]["cloudwright"]["args"] == ["mcp"]

    def test_json_flag_aider_has_no_mcp_config_snippet(self):
        result = runner.invoke(app, ["--json", "integrate", "--harness", "aider"])
        assert result.exit_code == 0
        envelope = json.loads(result.output)
        assert envelope["data"]["mcp_client"] is False
        assert "config_snippet" not in envelope["data"]

    def test_json_flag_codex_config_snippet_is_toml_text(self):
        result = runner.invoke(app, ["--json", "integrate", "--harness", "codex"])
        assert result.exit_code == 0
        envelope = json.loads(result.output)
        assert "[mcp_servers.cloudwright]" in envelope["data"]["config_snippet"]


class TestNoModeSelected:
    def test_no_flags_errors_with_guidance(self):
        result = runner.invoke(app, ["integrate"])
        assert result.exit_code != 0
        assert "--list" in (result.output + result.stderr)


class TestRegistration:
    def test_integrate_registered_in_top_level_help(self):
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "integrate" in result.output


class TestWrite:
    def test_write_creates_new_json_config(self, tmp_path: Path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        result = runner.invoke(app, ["integrate", "--harness", "cursor", "--write"])
        assert result.exit_code == 0
        cfg = tmp_path / ".cursor" / "mcp.json"
        assert cfg.exists()
        data = json.loads(cfg.read_text())
        assert data["mcpServers"]["cloudwright"]["command"] == "cloudwright"
        assert data["mcpServers"]["cloudwright"]["args"] == ["mcp"]

    def test_write_merges_into_existing_json_preserving_other_servers(self, tmp_path: Path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        cfg_dir = tmp_path / ".cursor"
        cfg_dir.mkdir()
        cfg = cfg_dir / "mcp.json"
        cfg.write_text(json.dumps({"mcpServers": {"other-tool": {"command": "other", "args": []}}}))

        result = runner.invoke(app, ["integrate", "--harness", "cursor", "--write"])
        assert result.exit_code == 0
        data = json.loads(cfg.read_text())
        assert data["mcpServers"]["other-tool"]["command"] == "other"
        assert data["mcpServers"]["cloudwright"]["command"] == "cloudwright"

    def test_write_refuses_to_overwrite_conflicting_entry_without_force(self, tmp_path: Path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        cfg_dir = tmp_path / ".cursor"
        cfg_dir.mkdir()
        cfg = cfg_dir / "mcp.json"
        cfg.write_text(json.dumps({"mcpServers": {"cloudwright": {"command": "something-else", "args": []}}}))

        result = runner.invoke(app, ["integrate", "--harness", "cursor", "--write"])
        assert result.exit_code != 0

        result = runner.invoke(app, ["integrate", "--harness", "cursor", "--write", "--force"])
        assert result.exit_code == 0
        data = json.loads(cfg.read_text())
        assert data["mcpServers"]["cloudwright"]["command"] == "cloudwright"

    def test_write_output_override(self, tmp_path: Path):
        out = tmp_path / "custom" / "mcp.json"
        result = runner.invoke(app, ["integrate", "--harness", "cline", "--write", "--output", str(out)])
        assert result.exit_code == 0
        assert out.exists()
        data = json.loads(out.read_text())
        assert data["mcpServers"]["cloudwright"]["command"] == "cloudwright"

    def test_write_cline_without_output_errors(self, tmp_path: Path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        result = runner.invoke(app, ["integrate", "--harness", "cline", "--write"])
        assert result.exit_code != 0

    def test_write_codex_toml_creates_table(self, tmp_path: Path):
        out = tmp_path / "config.toml"
        result = runner.invoke(app, ["integrate", "--harness", "codex", "--write", "--output", str(out)])
        assert result.exit_code == 0
        text = out.read_text()
        assert "[mcp_servers.cloudwright]" in text
        assert 'command = "cloudwright"' in text

    def test_write_codex_toml_appends_without_clobbering_other_tables(self, tmp_path: Path):
        out = tmp_path / "config.toml"
        out.write_text('[mcp_servers.other]\ncommand = "other"\nargs = []\n')
        result = runner.invoke(app, ["integrate", "--harness", "codex", "--write", "--output", str(out)])
        assert result.exit_code == 0
        text = out.read_text()
        assert "[mcp_servers.other]" in text
        assert "[mcp_servers.cloudwright]" in text

    def test_write_rules_creates_agents_md(self, tmp_path: Path):
        out = tmp_path / "AGENTS.md"
        result = runner.invoke(app, ["integrate", "--rules", "--write", "--output", str(out)])
        assert result.exit_code == 0
        assert out.exists()
        text = out.read_text()
        assert "cloudwright design" in text

    def test_write_rules_is_idempotent_guard(self, tmp_path: Path):
        out = tmp_path / "AGENTS.md"
        result = runner.invoke(app, ["integrate", "--rules", "--write", "--output", str(out)])
        assert result.exit_code == 0

        result = runner.invoke(app, ["integrate", "--rules", "--write", "--output", str(out)])
        assert result.exit_code != 0

        result = runner.invoke(app, ["integrate", "--rules", "--write", "--output", str(out), "--force"])
        assert result.exit_code == 0
        text = out.read_text()
        assert text.count("cloudwright:gate:start") == 1

    def test_write_rules_appends_to_existing_file(self, tmp_path: Path):
        out = tmp_path / "AGENTS.md"
        out.write_text("# My project\n\nSome existing instructions.\n")
        result = runner.invoke(app, ["integrate", "--rules", "--write", "--output", str(out)])
        assert result.exit_code == 0
        text = out.read_text()
        assert "Some existing instructions." in text
        assert "cloudwright design" in text

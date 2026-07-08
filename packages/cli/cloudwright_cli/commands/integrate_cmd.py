"""Wire cloudwright into popular AI coding harnesses.

Cloudwright ships an MCP server (`cloudwright mcp`), a CLI, and a GitHub Action.
Most harnesses are MCP clients but each wants its server entry in a different
file and under a different JSON/TOML key. This command prints (and optionally
writes) the exact wiring per harness, plus a harness-agnostic rules-file block
that tells an agent to gate infrastructure changes through cloudwright before
it writes Terraform, Pulumi, or CloudFormation.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table

from cloudwright_cli.output import emit_success, is_json_mode
from cloudwright_cli.utils import handle_error

console = Console()

_RULES_START = "<!-- cloudwright:gate:start -->"
_RULES_END = "<!-- cloudwright:gate:end -->"

_RULES_BODY = (
    "## Cloudwright gate\n\n"
    "Before proposing, generating, or applying cloud infrastructure or Terraform, Pulumi, "
    "or CloudFormation changes, run cloudwright first:\n\n"
    '- `cloudwright design "<description>" --json` for a typed architecture spec\n'
    "- `cloudwright review <spec.yaml>` for an offline architecture critique (no LLM, free)\n"
    "- `cloudwright cost <spec.yaml>` for a per-component cost estimate\n"
    "- `cloudwright compliance <spec.yaml> --frameworks <hipaa,soc2,...>` for control-mapped findings\n\n"
    "Treat any high or critical review or compliance finding as a blocker. Fix it before "
    "writing Terraform, Pulumi, or CloudFormation.\n"
)


@dataclass(frozen=True)
class Harness:
    key: str
    name: str
    mcp: bool
    config_format: str | None = None  # "json" | "toml" | None (non-MCP)
    config_key: str | None = None
    default_write_path: str | None = None
    path_note: str = ""
    entry_shape: str = "flat"  # "flat" | "zed"
    entry_extra: dict | None = None
    rules_file: str = "AGENTS.md"
    rules_note: str = ""
    notes: tuple[str, ...] = ()


_HARNESSES: dict[str, Harness] = {
    "claude-code": Harness(
        key="claude-code",
        name="Claude Code",
        mcp=True,
        config_format="json",
        config_key="mcpServers",
        default_write_path=".mcp.json",
        path_note="Project scope. User scope alternative: ~/.claude.json.",
        rules_file="CLAUDE.md",
        rules_note=(
            "Claude Code does not read AGENTS.md natively (open GitHub issue, no roadmap "
            "commitment as of mid-2026). Use CLAUDE.md, not AGENTS.md, for this harness."
        ),
    ),
    "cursor": Harness(
        key="cursor",
        name="Cursor",
        mcp=True,
        config_format="json",
        config_key="mcpServers",
        default_write_path=".cursor/mcp.json",
        path_note="Project scope, wins on name conflicts. User scope alternative: ~/.cursor/mcp.json.",
        rules_file="AGENTS.md",
        rules_note=(
            "Cursor reads AGENTS.md natively. .cursor/rules/*.mdc is its own native rules "
            "directory (replaces the old single .cursorrules file since v2.2+); keep both."
        ),
    ),
    "cline": Harness(
        key="cline",
        name="Cline",
        mcp=True,
        config_format="json",
        config_key="mcpServers",
        default_write_path=None,
        path_note=(
            "cline_mcp_settings.json lives under the VS Code extension's global storage "
            "directory (path varies by OS and extension version). Pass --output to point at "
            "the exact file, or add the server through Cline's in-panel MCP Servers UI instead."
        ),
        rules_file=".clinerules",
        rules_note=(
            "Cline's AGENTS.md support is global-only (~/.agents/AGENTS.md) and contested by "
            "maintainers; project-root AGENTS.md is not read."
        ),
    ),
    "windsurf": Harness(
        key="windsurf",
        name="Windsurf",
        mcp=True,
        config_format="json",
        config_key="mcpServers",
        default_write_path="~/.codeium/windsurf/mcp_config.json",
        path_note="Global only. Edit via Cmd/Ctrl+Shift+P -> Configure MCP Servers, or the in-app MCP Marketplace.",
        rules_file=".windsurfrules",
        rules_note="Windsurf also recognizes AGENTS.md alongside its native .windsurfrules / .windsurf/rules/*.md.",
    ),
    "copilot": Harness(
        key="copilot",
        name="GitHub Copilot",
        mcp=True,
        config_format="json",
        config_key="servers",
        entry_extra={"type": "stdio"},
        default_write_path=".vscode/mcp.json",
        path_note=(
            'VS Code uses the key "servers", not "mcpServers", and a local-command entry needs '
            '"type": "stdio". The Copilot coding agent (repo/org level) and the standalone '
            "Copilot CLI use their own separate config surfaces."
        ),
        rules_file=".github/copilot-instructions.md",
        rules_note=(
            "Copilot coding agent also reads AGENTS.md natively (since August 2025); if both "
            "files exist, AGENTS.md is treated as primary."
        ),
    ),
    "zed": Harness(
        key="zed",
        name="Zed",
        mcp=True,
        config_format="json",
        config_key="context_servers",
        entry_shape="zed",
        default_write_path=".zed/settings.json",
        path_note=(
            "Project scope. Global alternative: ~/.config/zed/settings.json. Zed's "
            'context_servers schema nests the launch command as {"command": {"path": ..., '
            '"args": [...]}}; if Zed documents a different shape by the time you read this, '
            "trust the docs over this snippet."
        ),
        rules_file=".rules",
        rules_note=(
            "Zed's priority order is .rules -> .cursorrules -> .windsurfrules -> AGENTS.md "
            "(first match wins); a global ~/.config/zed/AGENTS.md is always appended too."
        ),
    ),
    "codex": Harness(
        key="codex",
        name="OpenAI Codex CLI",
        mcp=True,
        config_format="toml",
        config_key="mcp_servers",
        default_write_path="~/.codex/config.toml",
        path_note="Global. `codex mcp add cloudwright -- cloudwright mcp` does the same thing from the command line.",
        rules_file="AGENTS.md",
        rules_note="Codex is the tool that popularized AGENTS.md; it is native and canonical here.",
    ),
    "junie": Harness(
        key="junie",
        name="JetBrains Junie",
        mcp=True,
        config_format="json",
        config_key="mcpServers",
        default_write_path=".junie/mcp/mcp.json",
        path_note="Project scope. Junie also ships an in-product MCP Installation Assistant that walks through a server registry.",
        rules_file="AGENTS.md",
        rules_note="Junie CLI reads AGENTS.md as its primary source, falling back to the legacy .junie/guidelines.md.",
    ),
    "aider": Harness(
        key="aider",
        name="Aider",
        mcp=False,
        rules_file="AGENTS.md",
        rules_note="Aider reads AGENTS.md / AGENTS.override.md and has no native MCP client.",
        notes=(
            "Unofficial third-party MCP bridges (mcpm-aider, aider-mcp-server) exist but are "
            "not a supported integration path here.",
        ),
    ),
    "kiro": Harness(
        key="kiro",
        name="Kiro",
        mcp=True,
        config_format="json",
        config_key="mcpServers",
        default_write_path=".kiro/settings/mcp.json",
        path_note="Project scope. User scope alternative: ~/.kiro/settings/mcp.json.",
        rules_file="AGENTS.md",
        rules_note=(
            "Kiro's primary convention is its own steering system (.kiro/steering/*.md: "
            "product.md, tech.md, structure.md), distinct from AGENTS.md; list both."
        ),
        notes=("Kiro is AWS's successor to Amazon Q Developer, which AWS is sunsetting.",),
    ),
    "antigravity": Harness(
        key="antigravity",
        name="Antigravity",
        mcp=True,
        config_format="json",
        config_key="mcpServers",
        default_write_path="~/.gemini/config/mcp_config.json",
        path_note="Global, shared across the Antigravity CLI and IDE.",
        rules_file="AGENTS.md",
        rules_note=(
            "Gemini CLI's default rules file was GEMINI.md; confirm whether Antigravity keeps "
            "that convention before relying on it."
        ),
        notes=("Antigravity is Google's successor to Gemini CLI for individual developers.",),
    ),
}

_SUCCESSORS: dict[str, tuple[str, str]] = {
    "roo-code": (
        "Roo Code",
        "discontinued (sunset announced 2026-04-20, repo archived 2026-05-15); no supported successor",
    ),
    "continue-dev": (
        "Continue.dev",
        "acquired by Cursor in June 2026, repo now read-only; wire cursor instead "
        "(cloudwright integrate --harness cursor)",
    ),
    "amazon-q": (
        "Amazon Q Developer",
        "being sunset by AWS; use its successor, kiro (cloudwright integrate --harness kiro)",
    ),
    "gemini-cli": (
        "Google Gemini CLI",
        "individual/free access ended 2026-06-18; use its successor, antigravity "
        "(cloudwright integrate --harness antigravity)",
    ),
}

_AGENT_FILES = {
    "agents": "AGENTS.md",
    "claude": "CLAUDE.md",
    "gemini": "GEMINI.md",
}

_AGENT_FILE_NOTES = {
    "agents": (
        "Read natively by Cursor, Windsurf, Copilot, Codex, Junie, Aider, and Kiro; Zed falls "
        "back to it. Claude Code does NOT read this file: use --agent-file claude for that harness."
    ),
    "claude": "Claude Code's native rules file. Claude Code does not read AGENTS.md.",
    "gemini": (
        "Gemini CLI's default context file, loaded hierarchically from ~/.gemini/GEMINI.md down "
        "through the project tree. AGENTS.md support exists but is not the default."
    ),
}


def integrate(
    ctx: typer.Context,
    list_harnesses: Annotated[
        bool, typer.Option("--list", "-l", help="List supported harnesses and what each needs")
    ] = False,
    harness: Annotated[
        str | None, typer.Option("--harness", "-H", help="Print the exact MCP wiring for this harness")
    ] = None,
    rules: Annotated[
        bool, typer.Option("--rules", help="Emit a harness-agnostic rules block that gates infra through cloudwright")
    ] = False,
    agent_file: Annotated[
        str, typer.Option("--agent-file", help="Rules file target for --rules: agents, claude, or gemini")
    ] = "agents",
    write: Annotated[
        bool, typer.Option("--write", help="Write the config or rules block to its file (creates parent dirs)")
    ] = False,
    output: Annotated[str | None, typer.Option("--output", "-o", help="Override the default write path")] = None,
    force: Annotated[
        bool, typer.Option("--force", help="Overwrite an existing cloudwright entry without confirmation")
    ] = False,
) -> None:
    """Print (and optionally write) the wiring that connects an AI coding harness to cloudwright.

    Three modes, pick one:

    \b
    --list                 list every supported harness and what it needs
    --harness <name>        exact MCP config snippet + rules-file note for one harness
    --rules                 harness-agnostic instructions telling an agent to gate infra
                             changes through `cloudwright design/review/cost/compliance`

    `--write` writes the result to disk instead of only printing it (parent directories are
    created; an existing conflicting entry is left untouched unless --force is passed).
    """
    try:
        if list_harnesses:
            _cmd_list(ctx)
            return
        if harness:
            _cmd_harness(ctx, harness, write=write, output=output, force=force)
            return
        if rules:
            _cmd_rules(ctx, agent_file, write=write, output=output, force=force)
            return

        raise ValueError("Specify one of --list, --harness <name>, or --rules. Run --list to see supported harnesses.")

    except typer.Exit:
        raise
    except Exception as e:
        handle_error(ctx, e)


def _harness_summary(h: Harness) -> dict:
    return {
        "key": h.key,
        "name": h.name,
        "mcp_client": h.mcp,
        "config_file": h.default_write_path,
        "config_key": h.config_key,
        "rules_file": h.rules_file,
    }


def _cmd_list(ctx: typer.Context) -> None:
    rows = [_harness_summary(h) for h in _HARNESSES.values()]

    if is_json_mode(ctx):
        emit_success(
            ctx,
            {
                "harnesses": rows,
                "not_mcp_clients": ["aider"],
                "discontinued": {k: {"name": n, "note": note} for k, (n, note) in _SUCCESSORS.items()},
            },
        )
        return

    table = Table(title="Supported harnesses")
    table.add_column("Harness")
    table.add_column("Integration")
    table.add_column("Config file / key")
    table.add_column("Rules file")
    for h in _HARNESSES.values():
        integration = "MCP config" if h.mcp else "CLI pipe"
        config_col = (
            f"{h.default_write_path or '(see notes)'}  [{h.config_key}]" if h.mcp else "cloudwright <cmd> --json"
        )
        table.add_row(h.name, integration, config_col, h.rules_file)
    console.print(table)
    console.print("\nNot an MCP client: Aider (uses the CLI pipe path).", style="dim")
    console.print(
        "Discontinued or superseded, not generated here: Roo Code, Continue.dev, "
        "Amazon Q Developer (-> kiro), Google Gemini CLI (-> antigravity).",
        style="dim",
    )
    console.print(
        "\nRun `cloudwright integrate --harness <name>` for exact wiring, or "
        "`cloudwright integrate --rules` for the harness-agnostic gate instructions."
    )


def _resolve_harness(name: str) -> Harness:
    key = name.strip().lower().replace("_", "-").replace(" ", "-")
    if key in _HARNESSES:
        return _HARNESSES[key]
    if key in _SUCCESSORS:
        display, note = _SUCCESSORS[key]
        raise ValueError(f"{display} is {note}.")
    valid = ", ".join(_HARNESSES)
    raise ValueError(f"Unknown harness '{name}'. Supported: {valid}.")


def _entry(h: Harness) -> dict:
    if h.entry_shape == "zed":
        return {"command": {"path": "cloudwright", "args": ["mcp"]}}
    entry: dict[str, object] = {}
    if h.entry_extra:
        entry.update(h.entry_extra)
    entry["command"] = "cloudwright"
    entry["args"] = ["mcp"]
    return entry


def _document(h: Harness) -> dict:
    return {h.config_key: {"cloudwright": _entry(h)}}


def _toml_table(table: str, values: dict) -> str:
    lines = [f"[{table}]"]
    for k, v in values.items():
        if isinstance(v, list):
            items = ", ".join(json.dumps(i) for i in v)
            lines.append(f"{k} = [{items}]")
        else:
            lines.append(f"{k} = {json.dumps(v)}")
    return "\n".join(lines)


def _toml_block(h: Harness) -> str:
    return _toml_table(f"{h.config_key}.cloudwright", _entry(h))


def _cmd_harness(ctx: typer.Context, name: str, *, write: bool, output: str | None, force: bool) -> None:
    h = _resolve_harness(name)

    if not h.mcp:
        if write:
            raise ValueError(
                f"{h.name} has no MCP config to write (it is not an MCP client). "
                "Use `cloudwright integrate --rules --write` to install the gate instructions "
                f"into {h.rules_file} instead."
            )
        payload = _aider_payload(h)
        if is_json_mode(ctx):
            emit_success(ctx, payload)
            return
        _print_aider(h, payload)
        return

    snippet_text = _toml_block(h) if h.config_format == "toml" else json.dumps(_document(h), indent=2)

    payload: dict = {
        "harness": h.key,
        "name": h.name,
        "mcp_client": True,
        "config_format": h.config_format,
        "config_file": h.default_write_path,
        "path_note": h.path_note,
        "config_key": h.config_key,
        "config_snippet": _document(h) if h.config_format == "json" else snippet_text,
        "rules_file": h.rules_file,
        "rules_note": h.rules_note,
        "notes": list(h.notes),
    }

    write_result = None
    if write:
        write_result = _write_harness_config(h, output=output, force=force)
        payload["write"] = write_result

    if is_json_mode(ctx):
        emit_success(ctx, payload)
        return

    _print_harness(h, snippet_text, write_result)


def _aider_payload(h: Harness) -> dict:
    return {
        "harness": h.key,
        "name": h.name,
        "mcp_client": False,
        "cli_pipe": {
            "instruction": "Aider has no native MCP client. Use the CLI pipe path instead.",
            "example": '/run cloudwright design "<description>" --json',
        },
        "rules_file": h.rules_file,
        "rules_note": h.rules_note,
        "notes": list(h.notes),
    }


def _print_aider(h: Harness, payload: dict) -> None:
    console.print(f"\n[bold]{h.name}[/bold]  (not an MCP client)\n")
    console.print(payload["cli_pipe"]["instruction"])
    console.print(f"  Example: [cyan]{payload['cli_pipe']['example']}[/cyan]")
    console.print(f"\nRules file: [cyan]{h.rules_file}[/cyan]")
    console.print(f"  {h.rules_note}", style="dim")
    if h.notes:
        console.print("\nNotes:")
        for n in h.notes:
            console.print(f"  - {n}")


def _print_harness(h: Harness, snippet_text: str, write_result: dict | None) -> None:
    console.print(f"\n[bold]{h.name}[/bold]  (MCP client)\n")
    console.print(f"Config file: {h.default_write_path or '(see notes)'}")
    if h.path_note:
        console.print(f"  {h.path_note}", style="dim")
    console.print(f"Key: [cyan]{h.config_key}[/cyan]\n")
    console.print(Syntax(snippet_text, "toml" if h.config_format == "toml" else "json", word_wrap=True))
    console.print(f"\nRules file: [cyan]{h.rules_file}[/cyan]")
    if h.rules_note:
        console.print(f"  {h.rules_note}", style="dim")
    if h.notes:
        console.print("\nNotes:")
        for n in h.notes:
            console.print(f"  - {n}")
    if write_result:
        console.print(f"\n[green]{write_result['action']}[/green] {write_result['path']}")


def _target_path(h: Harness, output: str | None) -> Path:
    raw = output or h.default_write_path
    if not raw:
        raise ValueError(
            f"{h.name} has no fixed config path; pass --output <path> to write it explicitly. {h.path_note}"
        )
    return Path(raw).expanduser()


def _write_harness_config(h: Harness, *, output: str | None, force: bool) -> dict:
    path = _target_path(h, output)
    path.parent.mkdir(parents=True, exist_ok=True)
    if h.config_format == "toml":
        return _write_toml(path, h, force=force)
    return _write_json(path, h, force=force)


def _write_json(path: Path, h: Harness, *, force: bool) -> dict:
    entry = _entry(h)
    if path.exists():
        raw = path.read_text().strip() or "{}"
        try:
            existing = json.loads(raw)
        except json.JSONDecodeError as e:
            raise ValueError(f"{path} exists but is not valid JSON: {e}") from e
        bucket = existing.setdefault(h.config_key, {})
        if "cloudwright" in bucket and bucket["cloudwright"] != entry and not force:
            raise ValueError(
                f"{path} already has a 'cloudwright' entry under {h.config_key!r} that differs. Pass --force to overwrite."
            )
        action = "updated" if "cloudwright" in bucket else "added"
        bucket["cloudwright"] = entry
        path.write_text(json.dumps(existing, indent=2) + "\n")
        return {"path": str(path), "action": action}

    path.write_text(json.dumps(_document(h), indent=2) + "\n")
    return {"path": str(path), "action": "created"}


def _write_toml(path: Path, h: Harness, *, force: bool) -> dict:
    block = _toml_block(h)
    header = f"[{h.config_key}.cloudwright]"
    if path.exists():
        text = path.read_text()
        if header in text:
            if not force:
                raise ValueError(f"{path} already has {header}. Pass --force to overwrite.")
            text = _replace_toml_table(text, header, block)
            path.write_text(text)
            return {"path": str(path), "action": "updated"}
        sep = "" if text.endswith("\n\n") else ("\n\n" if text.endswith("\n") else "\n\n")
        path.write_text(text + sep + block + "\n")
        return {"path": str(path), "action": "appended"}

    path.write_text(block + "\n")
    return {"path": str(path), "action": "created"}


def _replace_toml_table(text: str, header: str, new_block: str) -> str:
    lines = text.splitlines(keepends=True)
    start = None
    end = len(lines)
    for i, line in enumerate(lines):
        if line.strip() == header:
            start = i
            continue
        if start is not None and i > start and line.startswith("["):
            end = i
            break
    if start is None:
        return text + "\n\n" + new_block + "\n"
    return "".join(lines[:start]) + new_block + "\n" + "".join(lines[end:])


def _cmd_rules(ctx: typer.Context, agent_file: str, *, write: bool, output: str | None, force: bool) -> None:
    key = agent_file.strip().lower()
    if key not in _AGENT_FILES:
        raise ValueError(f"Unknown --agent-file '{agent_file}'. Choose one of: {', '.join(_AGENT_FILES)}.")
    filename = _AGENT_FILES[key]
    block = f"{_RULES_START}\n{_RULES_BODY}{_RULES_END}\n"

    payload: dict = {
        "agent_file": filename,
        "block": block,
        "note": _AGENT_FILE_NOTES[key],
    }

    write_result = None
    if write:
        path = Path(output) if output else Path(filename)
        write_result = _write_rules(path, block, force=force)
        payload["write"] = write_result

    if is_json_mode(ctx):
        emit_success(ctx, payload)
        return

    console.print(Panel(block, title=f"Cloudwright gate for {filename}"))
    console.print(_AGENT_FILE_NOTES[key], style="dim")
    if write_result:
        console.print(f"\n[green]{write_result['action']}[/green] {write_result['path']}")


def _write_rules(path: Path, block: str, *, force: bool) -> dict:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        text = path.read_text()
        if _RULES_START in text:
            if not force:
                raise ValueError(f"{path} already has a cloudwright gate block. Pass --force to replace it.")
            start = text.index(_RULES_START)
            end = text.index(_RULES_END) + len(_RULES_END)
            text = text[:start] + block.rstrip("\n") + text[end:]
            path.write_text(text)
            return {"path": str(path), "action": "updated"}
        sep = "\n" if text.endswith("\n") else "\n\n"
        path.write_text(text + sep + block)
        return {"path": str(path), "action": "appended"}

    header = f"# {path.name}\n\n"
    path.write_text(header + block)
    return {"path": str(path), "action": "created"}

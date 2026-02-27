# silmaril-cli

CLI interface for Silmaril. Wraps core package with Typer commands and Rich formatting.

## Commands

All commands are in `silmaril_cli/commands/`. Each is a standalone module registered in `main.py`.

- `design` — Generate architecture from natural language
- `cost` — Price an ArchSpec, optional multi-cloud comparison
- `compare` — Full multi-cloud architecture comparison
- `validate` — Compliance and Well-Architected checks
- `export` — Export to Terraform, CFN, Mermaid, SBOM, AIBOM
- `diff` — Compare two ArchSpec files
- `chat` — Interactive terminal chat or web UI launcher
- `catalog` — Subgroup with `search` and `compare` subcommands

## Conventions

- Typer for argument parsing, Rich for output formatting
- All output goes through Rich Console for consistent formatting
- Errors shown as `[red]Error:[/red] message`
- Tables for data, Panels for summaries, Syntax blocks for YAML/HCL

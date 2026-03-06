---
name: cloudwright-shared
version: 0.3.0
description: Shared prerequisites, global flags, and conventions for all Cloudwright skills
layer: 0
mcp_tools: []
tags: [shared, auth, output, conventions]
---

# Cloudwright Shared Prerequisites

All Cloudwright skills build on these conventions. Read this before using any other skill.

## Authentication

At least one LLM API key must be set in the environment:

```bash
export ANTHROPIC_API_KEY=sk-ant-...   # preferred — uses Haiku (fast) + Sonnet (design)
export OPENAI_API_KEY=sk-...          # fallback
```

Cloudwright auto-selects the provider based on available keys. If neither is set, design/modify/ADR commands raise `RuntimeError`.

## Global CLI Flags

These flags apply to every `cloudwright` command:

| Flag | Description |
|------|-------------|
| `--json` | Machine-readable JSON output (`{"data": {...}}`) |
| `--verbose`, `-v` | Verbose logging |
| `--dry-run` | Preview LLM operations without calling the API |
| `--stream` | NDJSON streaming output (one JSON object per line) |
| `--version`, `-V` | Print version and exit |

## Output Modes

**Human (default):** Rich tables, colored status, ASCII diagrams. Intended for terminal use.

**JSON (`--json`):**
```json
{"data": {"components": [...], "cost_estimate": {...}}}
```
Use for piping to other tools or parsing in scripts.

**NDJSON streaming (`--stream`):** One JSON object per line. Useful for long-running operations where progress matters.

## Spec File Conventions

Architecture specs are YAML files. Default name: `arch.yaml`. Load with:

```bash
cloudwright score arch.yaml
cloudwright validate arch.yaml --compliance hipaa
```

Save a design directly:

```bash
cloudwright design "React + FastAPI + RDS on AWS" --output arch.yaml
```

## MCP Server

Start the MCP server to expose all tools to an AI agent:

```bash
cloudwright mcp                       # all tool groups
cloudwright mcp --tools design,cost  # subset
```

The server runs on stdio by default (compatible with Claude Desktop and MCP clients).

## Security Conventions

- All commands that write files require an explicit `--output` path. No files are written without it.
- Confirm with user before writing spec files to disk.
- Never pass user-supplied strings as shell arguments without validation.

## Error Handling

All commands exit with code 0 on success, 1 on error. JSON mode returns:

```json
{"error": "message", "code": "ERROR_CODE"}
```

on failure instead of raising exceptions.

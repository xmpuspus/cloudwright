# MCP Reference

Cloudwright exposes 22 tools across 9 groups as a Model Context Protocol (MCP) server. Almost every popular coding agent is an MCP client (Claude Code, Cursor, Cline, Windsurf, GitHub Copilot, Zed, OpenAI Codex CLI, JetBrains Junie, Kiro, Antigravity), so one server puts these tools in all of their agent loops. Run `cloudwright integrate --harness <name>` to generate the wiring for your client. See [integrations.md](integrations.md).

Related: [Getting Started](getting-started.md) | [CLI Reference](cli-reference.md) | [Troubleshooting](troubleshooting.md) | [README](../README.md)

---

## Install

The MCP server is a separate package:

```bash
pip install cloudwright-ai-mcp
```

Or install it alongside the CLI and web extras:

```bash
pip install 'cloudwright-ai[all]'
```

---

## Configure Claude Desktop

Add this to `claude_desktop_config.json` (same shape works for Cursor and Cline):

```json
{
  "mcpServers": {
    "cloudwright": {
      "command": "cloudwright",
      "args": ["mcp"]
    }
  }
}
```

On macOS, the config file is at:
`~/Library/Application Support/Claude/claude_desktop_config.json`

Restart Claude Desktop after editing the file.

---

## Start the server manually

```bash
# All 22 tools, stdio transport (default)
cloudwright mcp

# Subset of tool groups
cloudwright mcp --tools design,cost

# SSE transport for HTTP clients
cloudwright mcp --transport sse
```

Valid tool group names for `--tools`: `design`, `cost`, `validate`, `analyze`, `export`, `session`, `review`, `compliance`, `plan`.

---

## Tool groups and tools

### design (3 tools)

LLM-powered tools for creating and evolving architectures. These call an LLM and require `ANTHROPIC_API_KEY` or `OPENAI_API_KEY`.

| Tool | Description |
|---|---|
| `design_architecture` | Generate a cloud architecture from a natural-language description. Returns a complete ArchSpec with components, connections, and cost estimate. |
| `modify_architecture` | Apply a natural-language modification instruction to an existing ArchSpec. Returns an updated spec. |
| `compare_providers` | Translate an ArchSpec to one or more target providers, returning one alternative ArchSpec per provider. |

---

### cost (2 tools)

Pricing computation. Both tools are pure offline calculation — no LLM, no network, no API cost.

| Tool | Description |
|---|---|
| `estimate_cost` | Estimate the monthly bill for an ArchSpec. Returns a per-component breakdown and total. Supports pricing tiers: `on_demand`, `reserved_1yr`, `reserved_3yr`, `spot`. |
| `compare_provider_costs` | Compare the monthly cost totals of an ArchSpec across cloud providers. Returns one numeric cost summary per provider. |

---

### validate (4 tools)

Static analysis and compliance checks. All tools are offline — no LLM, no network, read-only.

| Tool | Description |
|---|---|
| `validate_compliance` | Validate an ArchSpec against compliance frameworks (`hipaa`, `pci-dss`, `soc2`, `fedramp`, `gdpr`). Returns pass/fail per check with remediation hints. |
| `security_scan` | Scan an ArchSpec for security anti-patterns (unencrypted stores, public databases, missing WAF, weak auth). Returns severity-graded findings per component. |
| `scan_terraform` | Scan Terraform HCL source directly for security misconfigurations. No Terraform binary invoked. |
| `lint_architecture` | Lint an ArchSpec for architectural anti-patterns. Returns warnings with rule name, severity, component IDs, and recommendation. |

---

### analyze (3 tools)

Structural analysis and quality scoring. All tools are offline, read-only.

| Tool | Description |
|---|---|
| `analyze_blast_radius` | Analyze blast radius, SPOFs, and dependency structure. Returns direct and transitive dependents per component. Optionally scoped to one component ID. |
| `score_architecture` | Score an ArchSpec across 5 dimensions (reliability, security, cost efficiency, compliance, complexity). Returns per-dimension scores, weighted total (0-100), and letter grade. |
| `diff_architectures` | Diff two ArchSpec files. Returns added/removed/changed components, connections, cost delta, compliance impact, and a human-readable summary. |

---

### export (3 tools)

IaC generation and catalog lookup. All tools are offline.

| Tool | Description |
|---|---|
| `export_architecture` | Export an ArchSpec to Terraform HCL, CloudFormation YAML, Mermaid, D2, SBOM, AIBOM, or compliance markdown. Returns `{format, content}`. |
| `list_services` | List all cloud services in the registry for a given provider (aws, gcp, azure, databricks). Returns slug, name, category, and supported tiers per service. |
| `catalog_search` | Search the cloud instance catalog by provider, text query, vCPU count, memory size, or maximum hourly price. Returns matching instances with specs and pricing. |

---

### session (4 tools)

Stateful multi-turn conversation sessions. `chat_send` calls an LLM (requires an API key); the others are offline.

| Tool | Description |
|---|---|
| `chat_create_session` | Create a stateful design session. Returns a `session_id` handle. Accepts optional provider, monthly budget, and compliance constraints frozen for the session. |
| `chat_send` | Send a message to an existing session. Returns the LLM response text, updated ArchSpec (if produced), and token usage for this turn and cumulative. |
| `chat_list_sessions` | List all saved sessions with metadata: session_id, timestamps, token usage, and whether a spec is present. |
| `chat_delete_session` | Delete a session and its history. Destructive, no undo. Returns `{deleted: true}` on success. |

---

### review (1 tool)

Offline architecture critique. No LLM, no network, no API key.

| Tool | Description |
|---|---|
| `review_architecture` | Run the deterministic critics (scorer, linter, validator) against an ArchSpec and return a severity-ranked report: `{score, grade, findings, blocking_count, summary}`. Accepts optional `compliance` frameworks and a `well_architected` flag. This is the same engine as the `cloudwright review` CLI command. |

---

### compliance (1 tool)

Control-mapped compliance scanning with optional OSCAL output. Offline, no API key.

| Tool | Description |
|---|---|
| `scan_compliance_controls` | Scan an ArchSpec against compliance frameworks and map every finding to its control ID. With `oscal=true`, returns an OSCAL 1.1.2 `component-definition` document instead of the plain report. Optional `checkov` deep scan and `traceability` chain. |

---

### plan (1 tool)

Read-only deployability check. Never applies changes.

| Tool | Description |
|---|---|
| `plan_infrastructure` | Export an ArchSpec and run `terraform`/`tofu` `init -backend=false` + `validate` (default), or a full `plan`/`preview` with `run_plan=true`. Returns a structured result. Degrades to `{available: false}` when the IaC toolchain is absent; there is no apply path. |

---

## Example: design and export from Claude

Once configured, you can ask Claude:

> "Design a HIPAA-compliant 3-tier API on AWS with PostgreSQL, then export it as Terraform."

Claude will call `design_architecture` with `compliance=["hipaa"]`, receive the ArchSpec, then call `export_architecture` with `format="terraform"` and return the HCL.

---

## Example: multi-turn session

```
User: Create a conversation session for an AWS architecture with a $5000/month budget.
      [calls chat_create_session -> {session_id: "abc123def456"}]

User: Design a web app with a CDN and a managed database.
      [calls chat_send(session_id="abc123def456", message="Design...")]

User: Add a Redis cache.
      [calls chat_send(session_id="abc123def456", message="Add a Redis cache")]
```

Sessions persist across Claude Desktop restarts (stored on disk in `~/.cloudwright/sessions/`).

---

## Which tools need an API key

Tools that call an LLM (`ANTHROPIC_API_KEY` or `OPENAI_API_KEY` required):

- `design_architecture`
- `modify_architecture`
- `compare_providers`
- `chat_send`

All other tools are pure computation: no LLM, no network, no cost beyond the MCP call itself.

---

## Partial tool registration

To limit which tools the AI agent can call (useful for cost control or read-only contexts):

```bash
# Only offline analysis tools
cloudwright mcp --tools validate,analyze,export

# Only design tools (LLM-backed)
cloudwright mcp --tools design,session

# Cost tools only
cloudwright mcp --tools cost
```

---

## SSE transport

For clients that prefer HTTP/SSE over stdio:

```bash
cloudwright mcp --transport sse
```

The server listens on a local port. Configure the client with the SSE endpoint URL instead of a command/args pair.

---

## Troubleshooting MCP

**Tools not appearing in Claude Desktop:** Restart Claude Desktop after editing `claude_desktop_config.json`. Confirm `cloudwright` is on PATH by running `cloudwright --version` in a terminal.

**`cloudwright-ai-mcp` not installed:** Run `pip install cloudwright-ai-mcp` and confirm the `cloudwright` binary is the one from that environment.

**LLM tools return errors:** Set `ANTHROPIC_API_KEY` or `OPENAI_API_KEY` in the shell environment where Claude Desktop runs (on macOS, this may require setting it in `~/.zshenv` rather than `~/.zshrc`).

See [Troubleshooting](troubleshooting.md) for more.

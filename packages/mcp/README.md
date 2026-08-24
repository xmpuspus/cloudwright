# cloudwright-ai-mcp

mcp-name: io.github.xmpuspus/cloudwright

[![xmpuspus/cloudwright MCP server](https://glama.ai/mcp/servers/xmpuspus/cloudwright/badges/score.svg)](https://glama.ai/mcp/servers/xmpuspus/cloudwright)

MCP (Model Context Protocol) server for [Cloudwright](https://github.com/xmpuspus/cloudwright) architecture intelligence.

Exposes Cloudwright's architecture and migration capabilities as MCP tools for use with MCP-compatible clients.

## Installation

```bash
pip install cloudwright-ai-mcp
```

## Usage

```bash
cloudwright mcp
```

Or add to your MCP client configuration:

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

## Available Tools

- **design**: Generate cloud architecture from natural language
- **cost**: Estimate monthly infrastructure costs
- **validate**: Check compliance against HIPAA, PCI-DSS, SOC 2, FedRAMP, GDPR
- **export**: Export to Terraform, CloudFormation, Mermaid, D2, C4, SBOM
- **compare**: Compare architectures across cloud providers
- **review_architecture**: free, offline scorer + linter + validator critique (no LLM)
- **scan_compliance_controls**: Map findings to framework control IDs with optional OSCAL 1.1.2 output
- **plan_infrastructure**: proves exported IaC is deployable (`terraform validate`/`plan`, read-only)
- **plan_migration**: builds dependency-ordered waves, supplied-cost economics, and acceptance gates
- **verify_migration**: rebuilds migration gates and checks evidence for a visible closure decision
- **chat_create_session**: Create a persistent multi-turn design session
- **chat_send**: Send a message to an existing session
- **chat_list_sessions**: List all saved sessions
- **chat_delete_session**: Delete a session

Sessions persist to `~/.cloudwright/sessions/` and survive process restarts.
Sessions older than `CLOUDWRIGHT_MCP_SESSION_TTL_DAYS` (default 7) are swept on
server start and on every `chat_list_sessions` call.

## License

MIT

# cloudwright-ai-mcp

mcp-name: io.github.xmpuspus/cloudwright

[![xmpuspus/cloudwright MCP server](https://glama.ai/mcp/servers/xmpuspus/cloudwright/badges/score.svg)](https://glama.ai/mcp/servers/xmpuspus/cloudwright)

MCP (Model Context Protocol) server for [Cloudwright](https://github.com/xmpuspus/cloudwright) architecture intelligence.

Exposes Cloudwright's design, cost, validate, and export capabilities as MCP tools for use with Claude Code and other MCP-compatible clients.

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

- **design** — Generate cloud architecture from natural language
- **cost** — Estimate monthly infrastructure costs
- **validate** — Check compliance against HIPAA, PCI-DSS, SOC 2, FedRAMP, GDPR
- **export** — Export to Terraform, CloudFormation, Mermaid, D2, C4, SBOM
- **compare** — Compare architectures across cloud providers
- **chat_create_session** — Create a persistent multi-turn design session
- **chat_send** — Send a message to an existing session
- **chat_list_sessions** — List all saved sessions
- **chat_delete_session** — Delete a session

Sessions persist to `~/.cloudwright/sessions/` and survive process restarts.

## License

MIT

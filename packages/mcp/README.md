# cloudwright-ai-mcp

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

## License

MIT

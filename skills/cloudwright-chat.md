---
name: cloudwright-chat
version: 0.3.0
description: Conversational multi-turn architecture design with iterative refinement
layer: 1
mcp_tools: [chat_create_session, chat_send, chat_list_sessions]
tags: [chat, conversation, interactive, multi-turn, design]
---

# Cloudwright Chat

Design and refine architectures through multi-turn conversation. Each session maintains context across messages.

## When to Use

- User wants to iteratively refine an architecture design
- Requirements are incomplete and need clarification through back-and-forth
- User wants to explore multiple variations of the same base architecture
- Long-running design sessions where context needs to persist

## CLI Usage

```bash
# Start interactive terminal chat
cloudwright chat

# Launch web UI
cloudwright chat --web
```

### Terminal Chat Commands

Within the chat session:

| Command | Description |
|---------|-------------|
| `/save <file>` | Save last architecture to YAML |
| `/diagram` | Show ASCII diagram |
| `/yaml` | Show full YAML for last architecture |
| `/cost` | Show cost estimate |
| `/validate [fw]` | Run compliance check |
| `/export <fmt>` | Export (terraform, mermaid, d2, sbom, aibom) |
| `/terraform` | Export as Terraform |
| `/new` | Start fresh architecture |
| `/quit` | Exit |

```
> Design a fraud detection service on AWS
[Cloudwright generates initial architecture]

> Add a real-time streaming component
[Modifies architecture, adds Kinesis]

> Optimize for under $2000/month
[Right-sizes components]

> /save fraud-detection.yaml
Saved to fraud-detection.yaml

> /validate pci-dss
[Runs PCI-DSS compliance check]
```

## MCP Tool Usage

### Create a session

```json
{
  "tool": "chat_create_session",
  "arguments": {
    "provider": "aws",
    "region": "us-east-1"
  }
}
```

Returns `{"session_id": "sess_abc123"}`.

### Send a message

```json
{
  "tool": "chat_send",
  "arguments": {
    "session_id": "sess_abc123",
    "message": "Add a caching layer in front of the database"
  }
}
```

Returns `{"text": "...", "spec": <updated ArchSpec dict or null>}`.

### List active sessions

```json
{
  "tool": "chat_list_sessions",
  "arguments": {}
}
```

Returns `{"sessions": [{"session_id": "...", "created_at": "...", "message_count": 4}]}`.

## Session Flow

```
chat_create_session  →  sess_abc123
        ↓
chat_send ("Design a 3-tier web app")   →  spec v1
        ↓
chat_send ("Add Redis caching")         →  spec v2
        ↓
chat_send ("Switch to GCP")             →  spec v3 (provider mapped)
        ↓
export_architecture(spec v3, "terraform")  →  infra/
```

## Follow-Up Actions

From a chat session:
- Save the latest spec with `/save` or pass it to `export_architecture`
- Validate the final design: `cloudwright validate arch.yaml --compliance soc2`
- Score it: `cloudwright score arch.yaml`

## Notes

- Follow-up messages automatically modify the most recent architecture in the session. Use `/new` to discard context and start fresh.
- Sessions are in-memory for the CLI. The web UI persists sessions across page refreshes.
- `chat_send` returns `spec: null` for informational messages that don't change the architecture.

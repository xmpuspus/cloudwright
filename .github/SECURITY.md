# Security Policy

## Supported Versions

| Version | Supported |
| ------- | --------- |
| 1.0.x   | Yes       |
| 0.5.x   | Yes       |
| 0.4.x   | Yes       |
| < 0.4   | No        |

## Reporting a Vulnerability

If you discover a security vulnerability in Cloudwright, please report it responsibly.

**Do not open a public GitHub issue for security vulnerabilities.**

Instead, please email security reports to: **xpuspus@gmail.com**

Include:
- Description of the vulnerability
- Steps to reproduce
- Impact assessment
- Suggested fix (if any)

We will acknowledge receipt within 48 hours and provide a detailed response within 7 business days.

## Security Measures

Cloudwright follows these security practices:

- **No hardcoded credentials** in generated infrastructure code (Terraform, CloudFormation)
- **Input validation** on all API endpoints via Pydantic models with length constraints
- **LLM output sanitization** with service allowlists and component ID validation
- **Security-hardened IaC defaults** including encryption at rest, IMDSv2, public access blocks
- **CORS restrictions** limited to explicit allowed origins (localhost dev ports)
- **Path traversal protection** on static file serving (resolve + is_relative_to)
- **Generic error messages** — no internal exception details leaked to API clients
- **Chat role validation** — constrained to user/assistant to prevent prompt injection
- **Config value sanitization** — `validate_export_config()` rejects shell metacharacters before IaC export
- **Connection validation** — ArchSpec rejects connections referencing non-existent component IDs
- **Safe YAML** — all loading via yaml.safe_load()
- **No dangerous functions** — no eval(), exec(), or pickle with untrusted data
- **LLM timeouts** (60s) to prevent hanging requests
- **Parameterized SQL** throughout the catalog layer

## Dependency Management

Dependencies use compatible version ranges in `pyproject.toml` for PyPI compatibility. Exact versions are pinned in `requirements.lock` for reproducible CI builds.

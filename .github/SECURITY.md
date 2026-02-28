# Security Policy

## Supported Versions

| Version | Supported |
| ------- | --------- |
| 0.1.x   | Yes       |

## Reporting a Vulnerability

If you discover a security vulnerability in Cloudwright, please report it responsibly.

**Do not open a public GitHub issue for security vulnerabilities.**

Instead, please email security reports to: **security@cloudwright.dev**

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
- **Safe YAML** — all loading via yaml.safe_load()
- **No dangerous functions** — no eval(), exec(), or pickle with untrusted data
- **LLM timeouts** (60s) to prevent hanging requests
- **Parameterized SQL** throughout the catalog layer

### Not Yet Implemented

The following are planned for production readiness but not yet in place:

- API key authentication (planned: check `CLOUDWRIGHT_API_KEY` env var)
- Rate limiting on LLM-backed endpoints
- Security headers middleware (X-Content-Type-Options, X-Frame-Options)
- Thread-safe singleton initialization

## Dependency Management

All dependencies are pinned to exact versions (`==`) to prevent supply chain attacks and ensure reproducible builds.

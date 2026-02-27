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
- **Input validation** on all API endpoints via Pydantic models
- **LLM output sanitization** with service allowlists and ID validation
- **Security-hardened IaC defaults** including encryption at rest, IMDSv2, public access blocks
- **API key authentication** when `CLOUDWRIGHT_API_KEY` environment variable is set
- **Rate limiting** on all endpoints, with tighter limits on LLM-backed routes
- **Security headers** (X-Content-Type-Options, X-Frame-Options, Referrer-Policy)
- **CORS restrictions** limited to explicit allowed origins
- **Path traversal protection** on static file serving
- **LLM timeouts** (60s) to prevent hanging requests
- **Thread-safe singletons** with double-checked locking

## Dependency Management

Dependencies are monitored via GitHub Dependabot. All dependencies specify version ranges with upper bounds to prevent unexpected breaking changes.

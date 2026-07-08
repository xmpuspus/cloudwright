# Security Policy

## Supported Versions

Cloudwright ships four packages (`cloudwright-ai`, `cloudwright-ai-cli`,
`cloudwright-ai-web`, `cloudwright-ai-mcp`) that always release together at the same
version. Only the latest published version on PyPI is supported with security fixes.
Older versions do not receive backports; upgrade to the latest release to pick up a fix.

## Reporting a Vulnerability

Do not open a public GitHub issue for a suspected security vulnerability.

Instead, open a private security advisory on this repository:
https://github.com/xmpuspus/cloudwright/security/advisories/new

Include:

- A description of the vulnerability and its impact
- Steps to reproduce, or a minimal proof of concept
- The affected version(s)

## Response Window

Expect an initial response within 5 business days. Confirmed vulnerabilities are fixed
and released as soon as practical given severity; the reporter is credited in the
advisory and the release notes unless anonymity is requested.

## Scope

This policy covers the code in this repository: the ArchSpec model, the LLM-driven
architect, cost estimation, security/compliance scanning, the exporters (Terraform,
Pulumi, CloudFormation, OpenTofu), the live cloud importers, the CLI, the web backend
and frontend, and the MCP server. It does not cover the security of the third-party
cloud accounts, credentials, or generated infrastructure a user provisions with
Cloudwright's output; review generated Terraform/Pulumi/CloudFormation before applying
it, as you would any infrastructure code.

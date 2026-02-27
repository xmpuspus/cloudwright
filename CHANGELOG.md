# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.0] - 2026-02-27

### Added

- `--json` flag for machine-readable JSON output on all commands (design, cost, compare, validate, export, diff, catalog search, catalog compare)
- `--version` flag to print the installed version string
- `--verbose` / `-v` flag to show full tracebacks on errors
- `--pricing-tier` option on `cost` command (on_demand, reserved_1yr, reserved_3yr, spot)
- D2 diagram export formats: `d2`, `d2-svg`, `d2-png`
- `mermaid-svg` and `mermaid-png` export format variants
- `cloudwright policy` command for policy-as-code compliance engine
- Global error handler in all commands — clean error messages with `--verbose` for stack traces
- JSON error responses when `--json` flag is active and a command fails

## [0.1.0] - 2026-02-27

### Added

- Natural language architecture design via LLM (Anthropic Claude, OpenAI GPT)
- ArchSpec data model with YAML/JSON serialization
- Cost engine with catalog-backed pricing for AWS, GCP, Azure
- Cross-cloud provider comparison with service mapping
- Compliance validation (HIPAA, PCI-DSS, SOC 2, Well-Architected Framework)
- Export to Terraform HCL, CloudFormation YAML, Mermaid diagrams
- CycloneDX SBOM and OWASP AIBOM export
- Structured diff between architecture versions
- SQLite service catalog with 58 instance types, 242 pricing entries, 66 cross-cloud equivalences
- CLI with Rich formatting (design, cost, validate, export, diff, catalog, chat)
- FastAPI web backend with React frontend
- Security-hardened IaC output (IMDSv2, encryption at rest, KMS, access logging)
- API key authentication and rate limiting for web API

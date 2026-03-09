# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- Workload profiles for cost estimation (small, medium, large, enterprise) — injects production-realistic sizing defaults before pricing formulas run
- `--workload-profile` / `-w` flag on `cost` command
- Shell completion callbacks for workload profiles and pricing tiers
- 20 new CloudFormation resource types (IAM, VPC, CloudWatch, Kinesis, StepFunctions, SecretsManager, KMS, ECR, MSK, EventBridge)
- 50 hardcoded Terraform resource type mappings (AWS, GCP, Azure) as fallback when registry lookup fails
- Post-import encryption defaults for databases and storage services
- MCP package build and publish steps in CI/CD workflow
- MCP package metadata (readme, keywords, classifiers, URLs)

### Fixed

- Cost estimates 10-100x too low for production workloads (workload profiles fix formula input defaults)
- Import pipeline ~20% failure rate on unrecognized resource types (expanded type maps)
- MCP package not included in publish workflow

## [0.3.2] - 2026-03-06

### Fixed

- Extras version pins updated for core 0.3.2

## [0.3.1] - 2026-03-05

### Added

- ASCII exporter for terminal-friendly architecture diagrams
- MCP (Model Context Protocol) server package for Claude Code integration
- Structured CLI output with `--stream` NDJSON mode
- Skills system for CLI extensibility

## [0.3.0] - 2026-03-04

### Added

- Security scanner (`cloudwright security`) with 6 checks: missing encryption, open ingress, no HTTPS, IAM wildcards, missing backups, no monitoring
- `scan_terraform()` for HCL static analysis
- ADR generator (`cloudwright adr`) with LLM-powered and deterministic fallback modes
- Databricks cost governance template (job clusters, SQL Warehouse auto-stop, Secret Scope)

### Fixed

- PNG renderer CDN 403 errors (disabled icon fetching)

## [0.2.27] - 2026-03-04

### Added

- PyPI, CI, license, and Python version badges in README
- CODE_OF_CONDUCT.md (Contributor Covenant)
- GitHub issue templates (bug report, feature request) and PR template
- Changelog backfill for all versions from v0.2.1 to v0.2.26

### Changed

- Development status classifier upgraded from Alpha to Beta across all packages
- Python 3.13 classifier added to CLI and web packages

### Fixed

- GitHub Action installed wrong PyPI package name (`cloudwright` instead of `cloudwright-ai`)
- CI workflow pinned to verified GitHub Actions versions (checkout@v4, setup-python@v5)
- README git clone URL pointed to wrong GitHub org
- SECURITY.md listed implemented features as "Not Yet Implemented"
- README template names used hyphens instead of underscores (`databricks_lakehouse`)

## [0.2.26] - 2026-03-04

### Added

- Databricks provider init templates

## [0.2.25] - 2026-03-04

### Added

- Databricks as fourth cloud provider (alongside AWS, GCP, Azure)

## [0.2.24] - 2026-03-02

### Added

- Draggable and resizable boundary boxes in diagram canvas
- VPC and tier boundary rendering for all component groupings

### Fixed

- Label collision between VPC nests and tier boundary labels

## [0.2.23] - 2026-03-01

### Changed

- Set max_tokens to 10000 uniformly for all LLM calls (prevents truncation on any architecture)

## [0.2.22] - 2026-03-01

### Fixed

- Truncated JSON responses on complex architectures (raised max_tokens, expanded complexity detection)

## [0.2.21] - 2026-03-01

### Added

- Color-coded boundary labels with tier-specific styling

## [0.2.20] - 2026-03-01

### Fixed

- Boundary rendering now shown for all tiers including single-component tiers

## [0.2.19] - 2026-03-01

### Added

- Diagram boundaries inferred from tier layout automatically

## [0.2.18] - 2026-03-01

### Fixed

- Connection field name mismatch in chat LLM responses

## [0.2.17] - 2026-03-01

### Fixed

- ConversationSession field name mismatch causing chat failures

## [0.2.16] - 2026-03-01

### Fixed

- Modify retry logic on failed LLM responses
- Template selection threshold tuning

## [0.2.15] - 2026-03-01

### Added

- Async endpoints with streaming SSE for real-time diagram updates
- Spec caching layer to avoid redundant LLM calls
- Progressive loading in frontend during generation

### Changed

- Parallel LLM requests in frontend for reduced latency
- Worker config tuned for concurrent web traffic

### Fixed

- Latency and accuracy regressions introduced in v0.2.14

## [0.2.14] - 2026-02-28

### Fixed

- Modify timeout on large architectures

## [0.2.13] - 2026-02-28

### Fixed

- Multi-turn chat continuity across web UI and CLI

## [0.2.12] - 2026-02-28

### Added

- Rich UI panels for Validation, Export, and Spec tabs in web UI

## [0.2.11] - 2026-02-28

### Fixed

- Sub-package versions pinned in extras to prevent dependency drift

## [0.2.10] - 2026-02-28

### Changed

- Diagram UX improvements and model selection guidance

## [0.2.7] - 2026-02-28

### Added

- Frontend bundle included in wheel for offline use
- Browser auto-opens on `cloudwright chat --web`

## [0.2.6] - 2026-02-28

### Added

- Auto-detection of available port for web UI server

## [0.2.5] - 2026-02-28

### Fixed

- Web extra now correctly includes CLI dependency

## [0.2.4] - 2026-02-28

### Added

- Light theme UI redesign with improved contrast
- Markdown rendering fix in chat responses
- Four UI screenshots added to README

## [0.2.3] - 2026-02-28

### Added

- Web UI screenshots in README

### Fixed

- zsh pip install quoting for extras syntax

## [0.2.2] - 2026-02-28

### Added

- Six real-world CLI examples with actual output in README

## [0.2.1] - 2026-02-28

### Fixed

- CLI bugs discovered during v0.2.0 PyPI testing

## [0.2.0] - 2026-03-01

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

### Changed

- Architect: enforce exact service keys from LLM (no invented compound keys like `rds_postgres`)
- Architect: add Terraform resource type mapping for state/config parsing
- Architect: service name normalization layer with engine suffix extraction
- Catalog: adjust fallback prices for container orchestrators (EKS, GKE, AKS, ECS)
- Catalog: add debug logging for fallback pricing lookups

### Fixed

- README/CLAUDE.md: correct PyPI package name from `cloudwright` to `cloudwright-ai`

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

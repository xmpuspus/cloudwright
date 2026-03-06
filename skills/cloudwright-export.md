---
name: cloudwright-export
version: 0.3.0
description: Export an architecture spec to IaC, diagrams, or SBOMs
layer: 1
mcp_tools: [export_architecture]
tags: [export, terraform, cloudformation, mermaid, d2, c4, sbom, aibom, diagram]
---

# Cloudwright Export

Export an architecture spec to Terraform, CloudFormation, Mermaid, D2, C4, SVG, PNG, SBOM, or AIBOM.

## When to Use

- User wants deployable IaC from an architecture spec
- User needs a diagram for documentation or presentations
- User needs a software bill of materials for compliance or supply chain tracking

> [!CAUTION]
> This command writes files to disk. Confirm the output path with the user before running.

## CLI Usage

```bash
# Terraform
cloudwright export arch.yaml --format terraform --output infra/

# CloudFormation
cloudwright export arch.yaml --format cloudformation --output stack.yaml

# Mermaid diagram
cloudwright export arch.yaml --format mermaid --output arch.mmd

# D2 diagram (requires D2 binary)
cloudwright export arch.yaml --format d2 --output arch.d2

# C4 diagram
cloudwright export arch.yaml --format c4

# SVG diagram (requires D2 binary)
cloudwright export arch.yaml --format svg --output arch.svg

# PNG diagram (requires D2 binary)
cloudwright export arch.yaml --format png --output arch.png

# Software Bill of Materials
cloudwright export arch.yaml --format sbom --output sbom.json

# AI Bill of Materials
cloudwright export arch.yaml --format aibom --output aibom.json

# Print to stdout (no --output)
cloudwright export arch.yaml --format mermaid
```

## MCP Tool Usage

```json
{
  "tool": "export_architecture",
  "arguments": {
    "spec_json": <ArchSpec dict>,
    "format": "terraform",
    "output_path": "infra/"
  }
}
```

`output_path` is optional. Omit to get the content returned as a string instead of written to disk.

## Supported Formats

| Format | Description | Output |
|--------|-------------|--------|
| `terraform` | HCL modules for each component | `main.tf` + module files |
| `cloudformation` | AWS CloudFormation YAML | Single YAML template |
| `mermaid` | Mermaid flowchart | `.mmd` text |
| `d2` | D2 diagram language | `.d2` text |
| `c4` | C4 model (PlantUML) | `.puml` text |
| `svg` | Vector diagram | `.svg` (requires D2) |
| `png` | Raster diagram | `.png` (requires D2) |
| `sbom` | CycloneDX SBOM | JSON |
| `aibom` | AI Bill of Materials | JSON |

## Terraform Output Structure

When exporting to a directory:
```
infra/
  main.tf          # Provider config + module calls
  modules/
    api/           # One module per component
      main.tf
      variables.tf
      outputs.tf
```

## D2 / SVG / PNG Requirements

SVG and PNG export requires the D2 binary. Install:

```bash
# macOS
brew install d2

# Linux
curl -fsSL https://d2lang.com/install.sh | sh
```

If D2 is not installed, use `mermaid` or `c4` for text-based diagrams.

## Follow-Up Actions

After exporting Terraform:
- `cd infra && terraform init && terraform plan` — validate generated IaC
- Review generated modules before `terraform apply`
- For drift detection after deployment: `cloudwright drift arch.yaml`

## Notes

- Terraform output uses best-practice module structure. Variable values are set from the spec's `config` field.
- SBOM uses CycloneDX 1.4 format. AIBOM extends CycloneDX with AI/ML component metadata.
- `c4` output renders a System Context diagram (Level 1). Container diagram (Level 2) is not yet supported.

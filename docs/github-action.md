# Cloudwright GitHub Action — PR Preview

The `cloudwright-pr-preview` workflow posts a single, self-updating comment on every pull request that touches your Terraform or `cloudwright.yaml` files. The comment shows:

- Monthly cost delta (base → head, with annual rollup)
- Architecture diff (added, removed, and changed components)
- Compliance change set (e.g. SOC 2: pass/fail and which checks flipped)

The comment is idempotent. New pushes to the PR branch update the existing comment in place; they don't spam the timeline.

## 3-step setup

1. Copy `.github/workflows/cloudwright-pr-preview.yml` and `.github/actions/cloudwright-pr-comment/` from this repo into your own repo.
2. Add an LLM key as a repository secret. Either is fine:
   - `ANTHROPIC_API_KEY` (recommended, used by Cloudwright by default)
   - `OPENAI_API_KEY`
3. Edit `spec-path:` in the workflow YAML to point at your spec file (default: `cloudwright.yaml`).

That's it. Open a PR that changes `cloudwright.yaml` and the bot posts within ~30 seconds.

## What the comment looks like

```markdown
## Cloudwright PR Preview

Spec: `cloudwright.yaml`
Workload profile: `medium`

### Cost
- Monthly: $541.59 → **$721.59** (+$180.00/mo, +$2,160.00/yr)

### Architecture diff
- + **Session cache** (elasticache, aws) ($180.00/mo)

### Compliance
- **SOC 2**: failed → failed (score 0.45 → 0.52)
  - resolved: `encryption_at_rest`
```

## Inputs

| Input | Required | Default | Notes |
|-------|----------|---------|-------|
| `spec-path` | yes | — | Path to your ArchSpec YAML, e.g. `cloudwright.yaml` |
| `compliance` | no | `''` | Comma-separated frameworks: `hipaa,soc2,pci-dss` |
| `workload-profile` | no | `''` | One of `small`, `medium`, `large`, `enterprise` |
| `base-ref` | no | PR base SHA | Override the diff baseline (rarely needed) |
| `marker` | no | `<!-- cloudwright-pr-comment -->` | HTML marker used to find the comment for in-place updates |
| `python-version` | no | `3.12` | Python runtime for the action |

## Outputs

| Output | Notes |
|--------|-------|
| `comment-body` | Filesystem path of the rendered Markdown |
| `cost-delta-monthly` | Computed monthly delta (head − base) in USD |

## Privacy note

The action reads your `cloudwright.yaml` (the architecture description, not Terraform source code) and forwards it to your configured LLM provider via your own API key. Source files like `*.tf` are only inspected to decide whether to run; their content is not sent to the LLM. No telemetry is sent to Cloudwright.

## Customizing the trigger

Out of the box the workflow runs on PRs that change:

- `**/*.tf`, `**/*.tfstate`
- `cloudwright.yaml`, `spec.yaml` (and `**/` variants)

Add or remove globs in the workflow file's `paths:` block to match your layout. If you keep your spec inside a service directory (e.g. `services/api/cloudwright.yaml`), point `spec-path` at it directly and add the matching glob.

## Pinning the cloudwright version

The action installs the latest `cloudwright-ai[cli]`. To pin a specific version, fork the action and replace the install line in `action.yml`:

```yaml
pip install 'cloudwright-ai[cli]==1.4.0'
```

## Troubleshooting

- **No comment posted**: check that the workflow has `pull-requests: write` permission and that `spec-path` exists at the repo root (or wherever you pointed it).
- **"missing_api_key" error**: set `ANTHROPIC_API_KEY` or `OPENAI_API_KEY` as a repo secret. The action skips the LLM-driven steps but cost and validate still need it.
- **Compliance section is empty**: pass `compliance: soc2` (or `hipaa`, `pci-dss`) — the section only renders when the input is non-empty.
- **Want a per-comment summary instead of in-place updates?** Override `marker` with a unique string per workflow invocation.

## Reference

- Action source: `.github/actions/cloudwright-pr-comment/`
- Renderer: `.github/actions/cloudwright-pr-comment/render_comment.py`
- Workflow template: `.github/workflows/cloudwright-pr-preview.yml`

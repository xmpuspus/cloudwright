# Troubleshooting

Common errors and how to fix them.

Related: [Getting Started](getting-started.md) | [CLI Reference](cli-reference.md) | [README](../README.md)

---

## Missing API key

**Symptom:**

```
Error: No LLM provider configured. Set ANTHROPIC_API_KEY or OPENAI_API_KEY.
```

or

```
RuntimeError: No LLM provider configured.
```

**Fix:**

```bash
export ANTHROPIC_API_KEY=sk-ant-...
# or
export OPENAI_API_KEY=sk-...
```

This is only required for commands that call an LLM: `design`, `modify`, `compare`, `chat`, and `adr`. Everything else runs offline.

To verify which commands are offline, see the [command list in Getting Started](getting-started.md#commands-that-work-fully-offline).

---

## Wrong extras version (lockstep requirement)

**Symptom:**

```
ImportError: cannot import name 'X' from 'cloudwright'
```

or features from a recent release are missing after upgrading.

**Cause:**

The four Cloudwright packages (`cloudwright-ai`, `cloudwright-ai-cli`, `cloudwright-ai-web`, `cloudwright-ai-mcp`) must be on the same version. The extras pins in `cloudwright-ai[cli]` etc. enforce this, but a partial install or a manual pip upgrade of just one package can break the lockstep.

**Fix:**

```bash
pip install 'cloudwright-ai[all]=={version}' --force-reinstall
```

Replace `{version}` with the target version (e.g. `1.6.0`). Check the current installed version with:

```bash
cloudwright --version
```

---

## `cloudwright plan` fails because terraform is not on PATH

**Symptom:**

```
[SKIP] terraform not found on PATH
```

or

```
FileNotFoundError: terraform
```

**Fix:**

Install Terraform: https://developer.hashicorp.com/terraform/install

Then verify:

```bash
terraform version
```

If you only want offline proof without cloud credentials, pass `--no-plan`:

```bash
cloudwright plan spec.yaml --no-plan
```

This runs `terraform validate` only and does not need credentials.

For Pulumi targets, install Pulumi: https://www.pulumi.com/docs/install/

---

## `cloudwright plan` times out

**Symptom:**

```
[SKIP] plan timed out after 180s
```

or the command hangs for several minutes before failing.

**Fix:**

Extend the timeout (in seconds):

```bash
cloudwright plan spec.yaml --timeout 600
```

Common causes: slow network when Terraform downloads provider plugins on first init, or an unusually large plan against a cloud account with many existing resources.

---

## Provider credential errors during `plan` or `import-live`

**Symptom:**

```
Error: No valid credential sources found for AWS Provider.
```

or permission-denied messages from GCP / Azure.

**Fix for plan:** Use `--no-plan` to skip the credential-requiring step:

```bash
cloudwright plan spec.yaml --no-plan
```

**Fix for import-live:** Configure credentials before running:

- AWS: `aws configure` or set `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY`, or use `--profile <name>` for a named profile.
- GCP: `gcloud auth application-default login`, then pass `--project <PROJECT_ID>`.
- Azure: `az login`, then pass `--subscription <SUB_ID>`.

Per-service permission errors during `import-live` are non-fatal. Components Cloudwright cannot read are skipped and reported on stderr.

---

## Rate limiting

**Symptom:**

```
Rate limited, try again in a moment.
```

or HTTP 429 responses from the LLM provider.

**Fix:**

Wait 10-30 seconds and retry. If this happens frequently, you are hitting the API tier's rate limit. Options:

- Reduce concurrency if you are running multiple `design` calls in parallel.
- Use `--dry-run` to check prompt size without making the call.
- Upgrade your API tier on the provider's dashboard.

---

## Provider download / network timeout during `plan`

**Symptom:**

Terraform stalls downloading a provider plugin, or the plan times out waiting for network.

**Fix:**

If you are behind a proxy, set `HTTPS_PROXY` in your environment before running `cloudwright plan`. Alternatively, pre-download the provider:

```bash
cd /tmp && terraform init -from-module github.com/hashicorp/example
```

Or run with `--no-plan` to skip the network-dependent provider download:

```bash
cloudwright plan spec.yaml --no-plan
```

---

## SVG or PNG export fails ("D2 binary not found")

**Symptom:**

```
Warning: D2 binary not found — returning D2 source text.
```

or for PNG:

```
Error: D2 binary not found
```

**Fix:**

```bash
curl -fsSL https://d2lang.com/install.sh | sh
```

Then verify:

```bash
d2 --version
```

The `mermaid`, `terraform`, `cloudformation`, `sbom`, and `aibom` formats do not need D2.

---

## PDF compliance report fails

**Symptom:**

```
ImportError: No module named 'weasyprint'
```

**Fix:**

```bash
pip install 'cloudwright-ai[pdf]'
```

---

## `import-live` fails with ImportError

**Symptom:**

```
Live import core is unavailable. Install with: pip install 'cloudwright-ai[live-import]'
```

**Fix:**

```bash
pip install 'cloudwright-ai[live-import]'
```

For provider-specific installs:

```bash
pip install 'cloudwright-ai[live-import-aws]'   # AWS only
pip install 'cloudwright-ai[live-import-gcp]'   # GCP only
pip install 'cloudwright-ai[live-import-azure]'  # Azure only
```

---

## `databricks-validate` fails with ImportError

**Symptom:**

```
Error: databricks-sdk not installed. Run: pip install cloudwright-ai[databricks]
```

**Fix:**

```bash
pip install 'cloudwright-ai[databricks]'
```

Then set `DATABRICKS_HOST` and `DATABRICKS_TOKEN` (or pass them as options).

---

## Behavioral tests fail with API key set

**Symptom (for contributors running the test suite):**

Tests in `test_e2e.py`, `test_architect.py`, and the web `test_api.py` make live LLM calls when `ANTHROPIC_API_KEY` or `OPENAI_API_KEY` is set, causing them to be slow or incur costs.

**Fix:**

Unset the keys before running tests to match CI behavior:

```bash
env -u ANTHROPIC_API_KEY -u OPENAI_API_KEY python -m pytest packages/core/tests -q --timeout=60
```

Live-LLM tests (`test_e2e.py::TestLLM::*`) are expected to fail with keys unset. This is not a regression.

---

## Web canvas shows a blank page or errors on startup

**Symptom:**

Browser shows nothing or a JavaScript error after `cloudwright chat --web`.

**Cause:**

The static bundle in `packages/web/cloudwright_web/static/` may be stale (built from a previous version) or missing.

**Fix:**

Rebuild the frontend:

```bash
cd packages/web/frontend && npm run build
rm -rf ../cloudwright_web/static
cp -r dist ../cloudwright_web/static
```

Then restart:

```bash
cloudwright chat --web
```

---

## Port already in use

**Symptom:**

```
Error: port 8765 is already in use.
```

**Fix:**

```bash
cloudwright chat --web --port 9000
```

---

## `cloudwright compliance` Checkov scan doesn't run

**Symptom:**

The compliance output shows `scanner: builtin` even though you expected Checkov to run.

**Fix:**

Checkov must be on PATH:

```bash
pip install checkov
checkov --version
```

Also install the compliance extra:

```bash
pip install 'cloudwright-ai[compliance]'
```

Checkov is auto-detected. You can force it with `--checkov` or skip it with `--no-checkov`.

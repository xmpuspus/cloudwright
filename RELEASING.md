# Releasing Cloudwright

This repo publishes four PyPI packages from one monorepo: `cloudwright-ai` (core),
`cloudwright-ai-cli`, `cloudwright-ai-web`, `cloudwright-ai-mcp`. All four always ship
together at the same version number.

## 1. Bump the version in all four packages

Edit `__version__` in:

- `packages/core/cloudwright/__init__.py`
- `packages/cli/cloudwright_cli/__init__.py`
- `packages/web/cloudwright_web/__init__.py`
- `packages/mcp/cloudwright_mcp/__init__.py`

Then update the `==X.Y.Z` extras pins in `packages/core/pyproject.toml`
(`cli`, `web`, `mcp`, `all`) to match.

## 2. Bump server.json

`server.json` describes the MCP registry entry. Update both:

- the top-level `"version"` field
- `"packages"[0]["version"]`

Keep `"description"` at 100 characters or fewer; the MCP registry rejects longer values.

## 3. Update the changelog

Add a new `## [X.Y.Z] - YYYY-MM-DD` section to `CHANGELOG.md` under `[Unreleased]`,
following the existing Keep a Changelog format. Update the README "What's new" section
if the release changes user-facing behavior.

## 4. Verify version sync locally

```bash
python3 scripts/check_version_sync.py
```

This checks that all four `__init__.py` files, the core package's extras pins, and
both version fields in `server.json` agree. It exits 1 with a listing of every
mismatched source if they don't. The same check runs in CI (`version-sync` job) and
gates every push, PR, and tag build.

Optionally pass an expected version to check against a specific tag:

```bash
python3 scripts/check_version_sync.py 1.7.0
```

## 5. Branch, PR, merge

- Cut a feature branch off `origin/main` for the version bump and changelog entry.
- Open a PR. Wait for CI to go green: `lint`, `test`, `security`, `version-sync`, `build`.
- Squash-merge to `main`.

## 6. Tag and push

```bash
git checkout main
git pull origin main
git tag -a vX.Y.Z -m "vX.Y.Z"
git push origin vX.Y.Z
```

Pushing a `v*` tag triggers `.github/workflows/publish.yml`, which re-runs the full CI
workflow and then builds and publishes all four wheels to PyPI using the
`PYPI_API_TOKEN` repository secret.

Watch the run:

```bash
gh run list --workflow=publish.yml
```

## 7. Smoke test the published wheels

PyPI's CDN can lag a minute or two after a successful publish. Once the workflow
succeeds:

```bash
python3 -m venv /tmp/release-verify
source /tmp/release-verify/bin/activate
pip install 'cloudwright-ai[cli]==X.Y.Z'
cloudwright --help
# exercise every new or changed CLI command with a minimal real input
```

Do not rely on an editable install for this step. Editable installs skip packaging
concerns entirely: missing bundled data files, wheel layout paths, and entry-point
bugs only show up against the built wheel.

## 8. Publish to the MCP registry

This step is interactive and requires the maintainer to log in. Once the wheels are
live on PyPI (the registry validates that the referenced package and version exist):

```bash
mcp-publisher login github
mcp-publisher validate server.json
mcp-publisher publish server.json
```

After this, Glama's tool re-introspection for the updated server is a manual click in
the Glama dashboard and must be done by the maintainer separately.

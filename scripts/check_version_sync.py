#!/usr/bin/env python3
"""Assert every version marker in the repo agrees before a release.

Checks, all against each other (and optionally against an expected version
passed as the first CLI arg, e.g. a git tag stripped of its leading "v"):

  - __version__ in each of the 4 packages/*/*/__init__.py files
  - the ==X.Y.Z extras pins in packages/core/pyproject.toml
  - the cloudwright-ai>=X.Y.Z dependency floor in each companion package
  - server.json top-level "version"
  - server.json "packages"[0]["version"]

No third-party dependencies. Exits 1 with a diff listing on any mismatch.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

INIT_FILES = [
    ROOT / "packages/core/cloudwright/__init__.py",
    ROOT / "packages/cli/cloudwright_cli/__init__.py",
    ROOT / "packages/web/cloudwright_web/__init__.py",
    ROOT / "packages/mcp/cloudwright_mcp/__init__.py",
]

CORE_PYPROJECT = ROOT / "packages/core/pyproject.toml"
COMPANION_PYPROJECTS = [ROOT / f"packages/{name}/pyproject.toml" for name in ("cli", "web", "mcp")]
SERVER_JSON = ROOT / "server.json"

VERSION_ASSIGN_RE = re.compile(r'__version__\s*=\s*"([^"]+)"')
EXTRAS_PIN_RE = re.compile(r"cloudwright-ai-(\w+)==([\d.]+)")
CORE_FLOOR_RE = re.compile(r'"cloudwright-ai>=([\d.]+),<2"')


class SourceError(RuntimeError):
    pass


def read_init_version(path: Path) -> str:
    text = path.read_text()
    match = VERSION_ASSIGN_RE.search(text)
    if not match:
        raise SourceError(f"no __version__ assignment found in {path}")
    return match.group(1)


def read_pyproject_pins(path: Path) -> list[tuple[str, str]]:
    text = path.read_text()
    matches = EXTRAS_PIN_RE.findall(text)
    if not matches:
        raise SourceError(f"no cloudwright-ai-*==X.Y.Z pins found in {path}")
    return [(f"cloudwright-ai-{name}", version) for name, version in matches]


def read_core_floor(path: Path) -> str:
    match = CORE_FLOOR_RE.search(path.read_text())
    if not match:
        raise SourceError(f"no cloudwright-ai>=X.Y.Z,<2 dependency found in {path}")
    return match.group(1)


def read_server_json(path: Path) -> list[tuple[str, str]]:
    data = json.loads(path.read_text())
    if "version" not in data:
        raise SourceError(f"no top-level 'version' key in {path}")
    packages = data.get("packages") or []
    if not packages or "version" not in packages[0]:
        raise SourceError(f"no packages[0].version key in {path}")
    return [
        ("server.json version", data["version"]),
        ("server.json packages[0].version", packages[0]["version"]),
    ]


def collect_sources() -> list[tuple[str, str]]:
    sources: list[tuple[str, str]] = []

    for init_path in INIT_FILES:
        label = f"{init_path.relative_to(ROOT)} __version__"
        sources.append((label, read_init_version(init_path)))

    for i, (name, version) in enumerate(read_pyproject_pins(CORE_PYPROJECT), start=1):
        label = f"packages/core/pyproject.toml pin #{i} ({name})"
        sources.append((label, version))

    for path in COMPANION_PYPROJECTS:
        label = f"{path.relative_to(ROOT)} cloudwright-ai floor"
        sources.append((label, read_core_floor(path)))

    for label, version in read_server_json(SERVER_JSON):
        sources.append((label, version))

    return sources


def main() -> int:
    expected = sys.argv[1].lstrip("v") if len(sys.argv) > 1 else None

    try:
        sources = collect_sources()
    except SourceError as exc:
        print(f"check_version_sync: {exc}", file=sys.stderr)
        return 1

    versions = {version for _, version in sources}
    ok = len(versions) == 1
    if ok and expected is not None:
        ok = expected in versions

    if ok:
        print(f"All {len(sources)} version markers agree: {sources[0][1]}")
        return 0

    print("Version mismatch across the repo:", file=sys.stderr)
    for label, version in sources:
        print(f"  {version:12s} {label}", file=sys.stderr)
    if expected is not None:
        print(f"\nExpected version: {expected}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())

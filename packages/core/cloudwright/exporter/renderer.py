"""SVG/PNG rendering pipeline via D2 or Mermaid CLI binaries."""

from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from cloudwright.spec import ArchSpec

_D2_INSTALL_HINT = "<!-- D2 binary not installed. Install: curl -fsSL https://d2lang.com/install.sh | sh -->"

_THEME_MAP = {
    "dark": "200",
    "light": "0",
    "cool": "1",
    "mixed": "3",
    "earth": "4",
    "elegant": "5",
}


class DiagramRenderer:
    @staticmethod
    def is_available() -> bool:
        return shutil.which("d2") is not None

    def render_svg(self, spec: ArchSpec, *, theme: str = "dark", layout: str = "dagre") -> str:
        from cloudwright.exporter.d2 import render as d2_render

        d2_source = d2_render(spec)

        if not DiagramRenderer.is_available():
            return f"{_D2_INSTALL_HINT}\n{d2_source}"

        theme_id = _THEME_MAP.get(theme, "200")

        with tempfile.TemporaryDirectory() as tmp:
            src = Path(tmp) / "arch.d2"
            out = Path(tmp) / "arch.svg"
            src.write_text(d2_source)

            result = subprocess.run(
                ["d2", f"--theme={theme_id}", f"--layout={layout}", str(src), str(out)],
                capture_output=True,
                text=True,
                timeout=30,
            )
            if result.returncode != 0:
                # Return D2 source with error info so callers can debug
                return f"<!-- D2 render error: {result.stderr.strip()} -->\n{d2_source}"

            return out.read_text()

    def render_png(self, spec: ArchSpec, *, theme: str = "dark", layout: str = "dagre") -> bytes:
        from cloudwright.exporter.d2 import render as d2_render

        if not DiagramRenderer.is_available():
            raise RuntimeError("D2 binary not installed. Install: curl -fsSL https://d2lang.com/install.sh | sh")

        d2_source = d2_render(spec)
        theme_id = _THEME_MAP.get(theme, "200")

        with tempfile.TemporaryDirectory() as tmp:
            src = Path(tmp) / "arch.d2"
            out = Path(tmp) / "arch.png"
            src.write_text(d2_source)

            result = subprocess.run(
                ["d2", f"--theme={theme_id}", f"--layout={layout}", str(src), str(out)],
                capture_output=True,
                # PNG rendering downloads Chromium on first run — allow up to 5 min
                timeout=300,
            )
            if result.returncode != 0:
                raise RuntimeError(f"D2 render failed: {result.stderr.decode().strip()}")

            return out.read_bytes()

    def render_svg_fallback(self, spec: ArchSpec) -> str:
        """Fallback: render via mmdc (Mermaid CLI) when D2 is unavailable."""
        if not shutil.which("mmdc"):
            from cloudwright.exporter.mermaid import render as mermaid_render

            return f"<!-- mmdc (mermaid-cli) not installed -->\n{mermaid_render(spec)}"

        from cloudwright.exporter.mermaid import render as mermaid_render

        mmd_source = mermaid_render(spec)

        with tempfile.TemporaryDirectory() as tmp:
            src = Path(tmp) / "arch.mmd"
            out = Path(tmp) / "arch.svg"
            src.write_text(mmd_source)

            result = subprocess.run(
                ["mmdc", "-i", str(src), "-o", str(out)],
                capture_output=True,
                text=True,
                timeout=30,
            )
            if result.returncode != 0:
                return f"<!-- mmdc render error: {result.stderr.strip()} -->\n{mmd_source}"

            return out.read_text()

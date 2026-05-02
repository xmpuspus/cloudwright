"""Internal helper: launch the cloudwright web server with a mock LLM.

Used by record_smart_canvas.py so demo recording doesn't need real API keys.
The mock LLM is never actually invoked because the recording prompt deliberately
matches a high-confidence template (skip-LLM path); the mock satisfies the
Architect constructor's call to ``get_llm()`` so the server boots cleanly.
"""

from __future__ import annotations

import sys
from collections.abc import Iterator

import uvicorn

from cloudwright.llm import base as _llm_base


class _MockLLM(_llm_base.BaseLLM):
    @property
    def model_name(self) -> str:
        return "mock-recording-llm"

    def _default_pricing(self) -> dict[str, float]:
        return {"input": 0.0, "output": 0.0}

    def generate(self, messages, system, max_tokens=2000, timeout=None):
        raise RuntimeError("Mock LLM should not be called — demo prompts must match a template.")

    def generate_fast(self, messages, system, max_tokens=2000, timeout=None):
        return ("ok", {"model": self.model_name, "input_tokens": 0, "output_tokens": 0})

    def generate_stream(self, messages, system, max_tokens=2000, timeout=None) -> Iterator[str]:
        yield ""


def _install_mock() -> None:
    import cloudwright.llm as llm_pkg

    def _factory(provider=None):
        return _MockLLM()

    llm_pkg.get_llm = _factory
    # Also patch already-imported callers (architect imports get_llm at module load).
    import cloudwright.architect as architect_mod

    architect_mod.get_llm = _factory
    import cloudwright.designer as designer_mod

    designer_mod.get_llm = _factory


def main() -> int:
    _install_mock()
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8765
    uvicorn.run("cloudwright_web.app:app", host="127.0.0.1", port=port, log_level="warning")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

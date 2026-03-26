"""ConversationSession — multi-turn architecture design conversation."""

from __future__ import annotations

import json
import time
from collections.abc import Iterator

from cloudwright.llm import get_llm
from cloudwright.llm.base import BaseLLM
from cloudwright.logging import get_logger
from cloudwright.prompts import CHAT_SYSTEM, CLOUD_KEYWORDS, MODIFY_SYSTEM
from cloudwright.spec import ArchSpec, Constraints, DiffResult

log = get_logger(__name__)

_MAX_ERROR_HINTS = 5


class ConversationSession:
    """Multi-turn architecture design conversation with history tracking."""

    def __init__(
        self,
        llm: BaseLLM | None = None,
        constraints: Constraints | None = None,
        max_history_turns: int = 50,
        session_id: str | None = None,
        auto_save: bool = False,
    ):
        self.llm = llm or get_llm()
        self.constraints = constraints
        self.history: list[dict] = []
        self.current_spec: ArchSpec | None = None
        self._error_hints: list[str] = []
        self.max_history_turns = max_history_turns
        self.session_id = session_id
        self.auto_save = auto_save
        self.cumulative_usage: dict = {"input_tokens": 0, "output_tokens": 0, "total_cost": 0.0}
        self.last_usage: dict = {}
        self.last_diff: DiffResult | None = None
        self._created_at: float = time.time()

    def _needs_clarification(self, message: str) -> bool:
        words = message.lower().split()
        if len(words) >= 2:
            return False
        if self.constraints is not None:
            return False
        if len(self.history) > 0:
            return False
        if self.current_spec is not None:
            return False
        return not any(w in CLOUD_KEYWORDS for w in words)

    def send(self, message: str) -> tuple[str, ArchSpec | None]:
        """Send a user message and get response + optionally updated spec."""
        if self._needs_clarification(message):
            clarification = (
                "Could you tell me more about what you'd like to build? For example:\n"
                "- '3-tier web app on AWS'\n"
                "- 'Serverless API with DynamoDB'\n"
                "- 'Migrate our EC2 setup to Kubernetes'\n\n"
                "Include details like provider (AWS/GCP/Azure), scale, and any compliance requirements."
            )
            self.history.append({"role": "user", "content": message})
            self.history.append({"role": "assistant", "content": clarification})
            return clarification, None

        self._trim_history()
        self.history.append({"role": "user", "content": message})
        system = self._build_system_with_hints(CHAT_SYSTEM)
        text, usage = self.llm.generate(self.history, system, max_tokens=10000)
        self._track_usage(usage)
        self.history.append({"role": "assistant", "content": text})

        spec = self._try_parse_spec(text)
        if spec is not None:
            if self.constraints:
                spec = spec.model_copy(update={"constraints": self.constraints})
            self.current_spec = spec

        self._auto_save()
        return text, spec

    def send_stream(self, message: str) -> Iterator[str]:
        """Stream a response token-by-token. Yields text chunks."""
        self._trim_history()
        self.history.append({"role": "user", "content": message})
        system = self._build_system_with_hints(CHAT_SYSTEM)

        accumulated = []
        for chunk in self.llm.generate_stream(self.history, system, max_tokens=10000):
            accumulated.append(chunk)
            yield chunk

        full_text = "".join(accumulated)
        self.history.append({"role": "assistant", "content": full_text})

        spec = self._try_parse_spec(full_text)
        if spec is not None:
            if self.constraints:
                spec = spec.model_copy(update={"constraints": self.constraints})
            self.current_spec = spec

        self._auto_save()

    def modify(self, instruction: str) -> ArchSpec:
        """Modify the current spec with a natural language instruction."""
        if self.current_spec is None:
            raise ValueError("No current architecture to modify. Use send() to create one first.")

        from cloudwright.parsing import _extract_json, _parse_arch_spec

        old_spec = self.current_spec
        current_json = _slim_for_modify(self.current_spec)
        prompt = f"Current architecture:\n{current_json}\n\nModification: {instruction}"

        self._trim_history()
        self.history.append({"role": "user", "content": prompt})
        system = self._build_system_with_hints(MODIFY_SYSTEM)

        max_tokens = 10000

        try:
            text, usage = self.llm.generate(self.history, system, max_tokens=max_tokens)
            self._track_usage(usage)
            self.history.append({"role": "assistant", "content": text})
            data = _extract_json(text)
        except (ValueError, json.JSONDecodeError) as first_err:
            log.warning("First modify attempt failed: %s — retrying", first_err)
            self.history.append({"role": "assistant", "content": "I apologize, let me provide the JSON."})
            self.history.append(
                {
                    "role": "user",
                    "content": "You must respond with ONLY a valid JSON object. No markdown, no explanation.",
                }
            )
            text, usage = self.llm.generate(self.history, system, max_tokens=max_tokens)
            self._track_usage(usage)
            self.history.append({"role": "assistant", "content": text})
            data = _extract_json(text)

        updated = _parse_arch_spec(data, self.constraints)

        original_ids = {c.id for c in self.current_spec.components}
        updated_ids = {c.id for c in updated.components}
        dropped = original_ids - updated_ids
        if dropped:
            remove_words = {"remove", "delete", "drop", "eliminate", "get rid of"}
            explicitly_removed = any(w in instruction.lower() for w in remove_words)
            if not explicitly_removed:
                restored = list(updated.components)
                original_map = {c.id: c for c in self.current_spec.components}
                for cid in dropped:
                    restored.append(original_map[cid])
                updated = updated.model_copy(update={"components": restored})
                log.warning("Restored %d dropped components: %s", len(dropped), dropped)
                self._add_error_hint("Do not remove existing components unless explicitly asked")

        if self.current_spec.cost_estimate and not updated.cost_estimate:
            updated = updated.model_copy(update={"cost_estimate": self.current_spec.cost_estimate})

        self.current_spec = updated

        from cloudwright.differ import Differ

        self.last_diff = Differ().diff(old_spec, updated)

        self._auto_save()
        return updated

    def _add_error_hint(self, hint: str) -> None:
        self._error_hints.append(hint)
        if len(self._error_hints) > _MAX_ERROR_HINTS:
            self._error_hints = self._error_hints[-_MAX_ERROR_HINTS:]

    def _track_usage(self, usage: dict) -> None:
        self.last_usage = dict(usage)
        inp = usage.get("input_tokens", 0)
        out = usage.get("output_tokens", 0)
        self.cumulative_usage["input_tokens"] += inp
        self.cumulative_usage["output_tokens"] += out
        cost = self._estimate_cost(inp, out)
        self.last_usage["estimated_cost"] = cost
        self.cumulative_usage["total_cost"] += cost

    def _estimate_cost(self, input_tokens: int, output_tokens: int) -> float:
        pricing = self.llm.pricing
        return round((input_tokens / 1000) * pricing["input"] + (output_tokens / 1000) * pricing["output"], 6)

    def get_usage_summary(self) -> dict:
        return {
            "input_tokens": self.cumulative_usage["input_tokens"],
            "output_tokens": self.cumulative_usage["output_tokens"],
            "total_cost": round(self.cumulative_usage["total_cost"], 4),
            "turn_count": len([m for m in self.history if m["role"] == "user"]),
        }

    def estimate_context_tokens(self) -> int:
        total = 0
        for msg in self.history:
            total += self.llm.estimate_tokens(msg.get("content", ""))
        return total

    def _trim_history(self) -> None:
        turn_count = sum(1 for m in self.history if m["role"] == "user")
        if turn_count <= self.max_history_turns:
            return
        trim_count = turn_count - self.max_history_turns
        messages_to_trim = trim_count * 2
        if messages_to_trim >= len(self.history):
            return
        trimmed = self.history[:messages_to_trim]
        summary_parts = []
        for msg in trimmed:
            role = msg["role"]
            content = msg.get("content", "")[:200]
            summary_parts.append(f"{role}: {content}")
        summary_text = "Earlier conversation summary:\n" + "\n".join(summary_parts)
        self.history = [{"role": "user", "content": summary_text}] + self.history[messages_to_trim:]

    def to_dict(self) -> dict:
        return {
            "session_id": self.session_id,
            "history": self.history,
            "current_spec": self.current_spec.model_dump(exclude_none=True) if self.current_spec else None,
            "constraints": self.constraints.model_dump() if self.constraints else None,
            "cumulative_usage": self.cumulative_usage,
            "_error_hints": self._error_hints,
            "max_history_turns": self.max_history_turns,
            "created_at": self._created_at,
        }

    @classmethod
    def from_dict(cls, data: dict, llm: BaseLLM | None = None) -> ConversationSession:
        constraints = Constraints(**data["constraints"]) if data.get("constraints") else None
        session = cls(
            llm=llm,
            constraints=constraints,
            max_history_turns=data.get("max_history_turns", 50),
            session_id=data.get("session_id"),
        )
        session.history = data.get("history", [])
        if data.get("current_spec"):
            session.current_spec = ArchSpec.model_validate(data["current_spec"])
        session.cumulative_usage = data.get(
            "cumulative_usage", {"input_tokens": 0, "output_tokens": 0, "total_cost": 0.0}
        )
        session._error_hints = data.get("_error_hints", [])
        if len(session._error_hints) > _MAX_ERROR_HINTS:
            session._error_hints = session._error_hints[-_MAX_ERROR_HINTS:]
        session._created_at = data.get("created_at", time.time())
        return session

    def _auto_save(self) -> None:
        if not self.auto_save or not self.session_id:
            return
        try:
            from cloudwright.session_store import SessionStore

            SessionStore().save(self.session_id, self)
        except Exception:
            log.warning("Auto-save failed for session %s", self.session_id)

    def _try_parse_spec(self, text: str) -> ArchSpec | None:
        from cloudwright.parsing import _extract_json, _parse_arch_spec

        try:
            data = _extract_json(text)
            if "components" not in data or not data["components"]:
                return None
            return _parse_arch_spec(data, self.constraints)
        except (ValueError, KeyError, json.JSONDecodeError):
            return None

    def _build_system_with_hints(self, base_system: str) -> str:
        if not self._error_hints:
            return base_system
        hints = "\n".join(f"- {h}" for h in self._error_hints[-_MAX_ERROR_HINTS:])
        return f"{base_system}\n\nLEARNINGS FROM THIS SESSION (avoid repeating):\n{hints}"


def _slim_for_modify(spec: ArchSpec) -> str:
    data = spec.model_dump(exclude_none=True)
    data.pop("cost_estimate", None)
    data.pop("metadata", None)
    for comp in data.get("components", []):
        comp.pop("description", None)
        cfg = comp.get("config", {})
        keep_keys = {
            "instance_type",
            "instance_class",
            "node_type",
            "storage_gb",
            "count",
            "engine",
            "model",
            "cpu",
            "memory",
            "min_instances",
            "max_instances",
        }
        comp["config"] = {k: v for k, v in cfg.items() if k in keep_keys}
    return json.dumps(data, indent=2)

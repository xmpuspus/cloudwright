"""Backward-compat re-exports from session, designer, and parsing modules."""

from __future__ import annotations

from cloudwright.critique import (  # noqa: F401
    CritiqueFinding,
    CritiqueReport,
    critique,
)

# Re-export everything for backward compatibility
from cloudwright.designer import (  # noqa: F401
    Architect,
    _build_constraint_prompt,
    _default_region,
    _diff_services,
    _is_simple_modification,
    _map_components,
    _match_template_for_design,
)
from cloudwright.parsing import (  # noqa: F401
    _enforce_connections,
    _extract_json,
    _infer_service_provider,
    _parse_arch_spec,
    _post_validate,
)
from cloudwright.session import ConversationSession, _slim_for_modify  # noqa: F401

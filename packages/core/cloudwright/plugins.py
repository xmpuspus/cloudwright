"""Plugin discovery — extends Cloudwright via entry points."""

from __future__ import annotations

import logging
from importlib.metadata import entry_points
from typing import Any

logger = logging.getLogger(__name__)

# Entry point groups
EXPORTER_GROUP = "cloudwright.exporters"
VALIDATOR_GROUP = "cloudwright.validators"
POLICY_GROUP = "cloudwright.policies"
IMPORTER_GROUP = "cloudwright.importers"

ALL_GROUPS = [EXPORTER_GROUP, VALIDATOR_GROUP, POLICY_GROUP, IMPORTER_GROUP]


def discover_plugins(group: str | None = None) -> dict[str, dict[str, Any]]:
    """Discover installed plugins by entry point group.

    Returns dict of {group: {name: loaded_object}}.
    If group is specified, only returns that group.
    """
    groups_to_scan = [group] if group else ALL_GROUPS
    result: dict[str, dict[str, Any]] = {}

    for g in groups_to_scan:
        result[g] = {}
        try:
            eps = entry_points(group=g)
            for ep in eps:
                try:
                    loaded = ep.load()
                    result[g][ep.name] = loaded
                    logger.debug("Loaded plugin %s from group %s", ep.name, g)
                except Exception as exc:
                    logger.warning("Failed to load plugin %s from %s: %s", ep.name, g, exc)
        except Exception as exc:
            logger.warning("Failed to scan entry point group %s: %s", g, exc)

    return result


def discover_exporters() -> dict[str, Any]:
    """Discover exporter plugins. Returns {format_name: exporter_callable}."""
    plugins = discover_plugins(EXPORTER_GROUP)
    return plugins.get(EXPORTER_GROUP, {})


def discover_validators() -> dict[str, Any]:
    """Discover validator plugins. Returns {framework_name: validator_callable}."""
    plugins = discover_plugins(VALIDATOR_GROUP)
    return plugins.get(VALIDATOR_GROUP, {})


def discover_policies() -> dict[str, Any]:
    """Discover policy plugins. Returns {policy_name: policy_callable}."""
    plugins = discover_plugins(POLICY_GROUP)
    return plugins.get(POLICY_GROUP, {})


def discover_importers() -> dict[str, Any]:
    """Discover importer plugins. Returns {format_name: importer_callable}."""
    plugins = discover_plugins(IMPORTER_GROUP)
    return plugins.get(IMPORTER_GROUP, {})


def list_plugins() -> dict[str, list[str]]:
    """List all discovered plugin names by group."""
    all_plugins = discover_plugins()
    return {group: list(plugins.keys()) for group, plugins in all_plugins.items()}

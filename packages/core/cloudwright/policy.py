"""Policy-as-code engine for ArchSpec validation."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field

from cloudwright.spec import ArchSpec


class PolicyRule(BaseModel):
    name: str
    description: str = ""
    severity: str = "warn"  # deny, warn, info
    check: str
    value: Any = None


class PolicyCheckResult(BaseModel):
    rule: str
    description: str = ""
    severity: str
    passed: bool
    message: str = ""


class PolicyResult(BaseModel):
    passed: bool
    deny_count: int = 0
    warn_count: int = 0
    info_count: int = 0
    results: list[PolicyCheckResult] = Field(default_factory=list)


class PolicyEngine:
    """Evaluates architecture specs against policy rules.

    Rules are loaded from YAML files. All checks are predefined
    Python functions — no eval() or dynamic code execution.
    """

    def __init__(self):
        self._CHECKS = {
            "max_components": self._check_max_components,
            "all_encrypted": self._check_all_encrypted,
            "require_multi_az": self._check_require_multi_az,
            "budget_monthly": self._check_budget_monthly,
            "no_banned_services": self._check_no_banned_services,
            "required_tags": self._check_required_tags,
            "min_redundancy": self._check_min_redundancy,
            "allowed_providers": self._check_allowed_providers,
            "allowed_regions": self._check_allowed_regions,
        }

    def evaluate(self, spec: ArchSpec, rules: list[PolicyRule], cost_estimate: Any | None = None) -> PolicyResult:
        """Evaluate an ArchSpec against a list of policy rules."""
        results: list[PolicyCheckResult] = []

        for rule in rules:
            check_fn = self._CHECKS.get(rule.check)
            if not check_fn:
                results.append(
                    PolicyCheckResult(
                        rule=rule.name,
                        description=rule.description,
                        severity=rule.severity,
                        passed=False,
                        message=f"Unknown check: {rule.check}",
                    )
                )
                continue

            passed, message = check_fn(spec, rule.value, cost_estimate)
            results.append(
                PolicyCheckResult(
                    rule=rule.name,
                    description=rule.description,
                    severity=rule.severity,
                    passed=passed,
                    message=message,
                )
            )

        deny_count = sum(1 for r in results if not r.passed and r.severity == "deny")
        warn_count = sum(1 for r in results if not r.passed and r.severity == "warn")
        info_count = sum(1 for r in results if not r.passed and r.severity == "info")

        return PolicyResult(
            passed=deny_count == 0,
            deny_count=deny_count,
            warn_count=warn_count,
            info_count=info_count,
            results=results,
        )

    def evaluate_from_file(
        self, spec: ArchSpec, rules_path: str | Path, cost_estimate: Any | None = None
    ) -> PolicyResult:
        """Load rules from a YAML file and evaluate."""
        rules = self.load_rules(rules_path)
        return self.evaluate(spec, rules, cost_estimate)

    @staticmethod
    def load_rules(path: str | Path) -> list[PolicyRule]:
        """Load policy rules from a YAML file."""
        text = Path(path).read_text()
        data = yaml.safe_load(text)
        return [PolicyRule.model_validate(r) for r in data.get("rules", [])]

    # --- Built-in check functions ---
    # Each returns (passed: bool, message: str)

    def _check_max_components(self, spec: ArchSpec, value: Any, _cost: Any) -> tuple[bool, str]:
        limit = int(value) if value is not None else 20
        count = len(spec.components)
        return count <= limit, f"{count} components (limit: {limit})"

    def _check_all_encrypted(self, spec: ArchSpec, _value: Any, _cost: Any) -> tuple[bool, str]:
        # Services that don't store data and don't need encryption config
        _no_encryption_needed = {"alb", "nlb", "route53", "api_gateway", "waf", "cognito", "cloudfront"}
        unencrypted = []
        for c in spec.components:
            if c.service in _no_encryption_needed:
                continue
            cfg = c.config or {}
            has_encryption = (
                any(k in cfg for k in ("encryption", "storage_encrypted", "kms_key_id", "sse_algorithm"))
                or cfg.get("storage_encrypted") is True
            )
            if not has_encryption:
                unencrypted.append(c.id)

        if unencrypted:
            return False, f"Components without encryption config: {', '.join(unencrypted)}"
        return True, "All applicable components have encryption configured"

    def _check_require_multi_az(self, spec: ArchSpec, _value: Any, _cost: Any) -> tuple[bool, str]:
        _db_services = {"rds", "aurora", "elasticache", "cloud_sql", "azure_sql"}
        failing = [
            c.id for c in spec.components if c.service in _db_services and not (c.config or {}).get("multi_az", False)
        ]
        if failing:
            return False, f"Components without Multi-AZ: {', '.join(failing)}"
        return True, "All database components have Multi-AZ enabled"

    def _check_budget_monthly(self, spec: ArchSpec, value: Any, cost_estimate: Any) -> tuple[bool, str]:
        limit = float(value) if value is not None else 0
        if cost_estimate is None:
            return False, "No cost estimate available — run cloudwright cost first"
        monthly = cost_estimate.monthly_total if hasattr(cost_estimate, "monthly_total") else 0
        return monthly <= limit, f"${monthly:,.2f}/month (budget: ${limit:,.2f})"

    def _check_no_banned_services(self, spec: ArchSpec, value: Any, _cost: Any) -> tuple[bool, str]:
        banned = set(value) if isinstance(value, list) else set()
        found = [c.id for c in spec.components if c.service in banned]
        if found:
            return False, f"Banned services used by: {', '.join(found)}"
        return True, "No banned services found"

    def _check_required_tags(self, spec: ArchSpec, value: Any, _cost: Any) -> tuple[bool, str]:
        required_keys = set(value) if isinstance(value, list) else set()
        missing = []
        for c in spec.components:
            tags = (c.config or {}).get("tags", {})
            component_missing = required_keys - set(tags.keys())
            if component_missing:
                missing.append(f"{c.id} (missing: {', '.join(sorted(component_missing))})")
        if missing:
            return False, f"Components with missing tags: {'; '.join(missing)}"
        return True, "All components have required tags"

    def _check_min_redundancy(self, spec: ArchSpec, value: Any, _cost: Any) -> tuple[bool, str]:
        _managed_redundant = {"s3", "cloud_storage", "blob_storage", "dynamodb", "route53"}
        min_count = int(value) if value is not None else 2
        failing = []
        for c in spec.components:
            if c.service in _managed_redundant:
                continue
            cfg = c.config or {}
            count = cfg.get("count", cfg.get("desired_count", cfg.get("num_cache_nodes", 1)))
            if count < min_count:
                failing.append(f"{c.id} (count: {count})")
        if failing:
            return False, f"Components below minimum redundancy ({min_count}): {'; '.join(failing)}"
        return True, f"All components meet minimum redundancy of {min_count}"

    def _check_allowed_providers(self, spec: ArchSpec, value: Any, _cost: Any) -> tuple[bool, str]:
        allowed = set(value) if isinstance(value, list) else set()
        violations = []
        if spec.provider not in allowed:
            violations.append(f"spec.provider={spec.provider}")
        violations += [c.id for c in spec.components if c.provider and c.provider not in allowed]
        if violations:
            return False, f"Disallowed providers: {', '.join(violations)}"
        return True, f"All components use allowed providers: {', '.join(sorted(allowed))}"

    def _check_allowed_regions(self, spec: ArchSpec, value: Any, _cost: Any) -> tuple[bool, str]:
        allowed = set(value) if isinstance(value, list) else set()
        if spec.region not in allowed:
            return False, f"Region {spec.region} not in allowed list: {', '.join(sorted(allowed))}"
        return True, f"Region {spec.region} is allowed"

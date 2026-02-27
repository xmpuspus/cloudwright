"""Architecture quality scorer — rates an ArchSpec on 5 dimensions."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from cloudwright.spec import ArchSpec


@dataclass
class DimensionScore:
    name: str
    score: float  # 0-100
    weight: float
    details: list[str] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)


@dataclass
class ScoreResult:
    overall: float  # 0-100 weighted
    dimensions: list[DimensionScore] = field(default_factory=list)
    grade: str = ""  # A/B/C/D/F
    recommendations: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "overall": round(self.overall, 1),
            "grade": self.grade,
            "dimensions": [
                {
                    "name": d.name,
                    "score": round(d.score, 1),
                    "weight": d.weight,
                    "details": d.details,
                    "recommendations": d.recommendations,
                }
                for d in self.dimensions
            ],
            "recommendations": self.recommendations,
        }


class Scorer:
    """Scores an ArchSpec on 5 quality dimensions."""

    def score(self, spec: ArchSpec) -> ScoreResult:
        dimensions = [
            self._score_reliability(spec),
            self._score_security(spec),
            self._score_cost_efficiency(spec),
            self._score_compliance(spec),
            self._score_complexity(spec),
        ]

        overall = sum(d.score * d.weight for d in dimensions)
        grade = self._grade(overall)

        # Collect top recommendations from low-scoring dimensions
        recs = []
        for d in sorted(dimensions, key=lambda x: x.score):
            recs.extend(d.recommendations[:2])

        return ScoreResult(
            overall=overall,
            dimensions=dimensions,
            grade=grade,
            recommendations=recs[:5],
        )

    def _score_reliability(self, spec: ArchSpec) -> DimensionScore:
        """Reliability (30%): multi-AZ, auto-scaling, LB, redundancy."""
        details = []
        recs = []
        checks = 0
        passed = 0.0

        components = spec.components
        services = {c.service for c in components}

        # Check: load balancer present
        checks += 1
        lb_services = {"alb", "nlb", "cloud_load_balancing", "app_gateway", "azure_lb"}
        if services & lb_services:
            passed += 1
            details.append("Load balancer present")
        else:
            recs.append("Add a load balancer for high availability")

        # Check: multi-AZ on databases
        checks += 1
        db_services = {"rds", "aurora", "cloud_sql", "azure_sql"}
        db_components = [c for c in components if c.service in db_services]
        if db_components:
            multi_az = any(c.config.get("multi_az", False) for c in db_components if c.config)
            if multi_az:
                passed += 1
                details.append("Database Multi-AZ enabled")
            else:
                recs.append("Enable Multi-AZ for database redundancy")
        else:
            passed += 1  # no DB = no issue

        # Check: multiple compute instances or auto-scaling
        checks += 1
        compute_services = {"ec2", "compute_engine", "virtual_machines", "ecs", "eks", "gke", "aks"}
        compute_comps = [c for c in components if c.service in compute_services]
        if compute_comps:
            has_scaling = any(
                (c.config or {}).get("count", 1) > 1
                or (c.config or {}).get("auto_scaling", False)
                or (c.config or {}).get("min_count", 0) > 1
                for c in compute_comps
            )
            if has_scaling:
                passed += 1
                details.append("Compute redundancy/scaling configured")
            else:
                recs.append("Configure auto-scaling or multiple instances for compute")
        else:
            passed += 1

        # Check: CDN for edge caching
        checks += 1
        cdn_services = {"cloudfront", "cloud_cdn", "azure_cdn"}
        if services & cdn_services:
            passed += 1
            details.append("CDN configured for edge caching")
        else:
            recs.append("Add a CDN for improved availability and latency")

        # Check: cache layer
        checks += 1
        cache_services = {"elasticache", "memorystore", "azure_cache"}
        if services & cache_services:
            passed += 1
            details.append("Cache layer present")
        else:
            recs.append("Add a cache layer to reduce database load")

        score = (passed / checks * 100) if checks > 0 else 50.0
        return DimensionScore("Reliability", score, 0.30, details, recs)

    def _score_security(self, spec: ArchSpec) -> DimensionScore:
        """Security (25%): encryption, WAF, private subnets, auth."""
        details = []
        recs = []
        checks = 0
        passed = 0.0

        services = {c.service for c in spec.components}

        # Check: WAF present
        checks += 1
        waf_services = {"waf", "cloud_armor", "azure_waf"}
        if services & waf_services:
            passed += 1
            details.append("WAF protection enabled")
        else:
            recs.append("Add a WAF for web application protection")

        # Check: auth service
        checks += 1
        auth_services = {"cognito", "firebase_auth", "azure_ad"}
        if services & auth_services:
            passed += 1
            details.append("Authentication service present")
        else:
            recs.append("Add an authentication service")

        # Check: encryption on data stores
        checks += 1
        data_services = {
            "rds",
            "aurora",
            "cloud_sql",
            "azure_sql",
            "dynamodb",
            "firestore",
            "cosmos_db",
            "s3",
            "cloud_storage",
            "blob_storage",
        }
        data_comps = [c for c in spec.components if c.service in data_services]
        if data_comps:
            encrypted = sum(1 for c in data_comps if (c.config or {}).get("encryption", False))
            if encrypted == len(data_comps):
                passed += 1
                details.append("All data stores encrypted")
            elif encrypted > 0:
                passed += 0.5
                details.append(f"{encrypted}/{len(data_comps)} data stores encrypted")
                recs.append("Enable encryption on all data stores")
            else:
                recs.append("Enable encryption at rest on data stores")
        else:
            passed += 1

        # Check: HTTPS on connections
        checks += 1
        https_conns = [c for c in spec.connections if c.protocol and c.protocol.upper() == "HTTPS"]
        if spec.connections and https_conns:
            ratio = len(https_conns) / len(spec.connections)
            passed += ratio
            if ratio == 1.0:
                details.append("All connections use HTTPS")
            else:
                details.append(f"{len(https_conns)}/{len(spec.connections)} connections use HTTPS")
                recs.append("Use HTTPS for all connections")
        elif not spec.connections:
            passed += 1
        else:
            recs.append("Configure HTTPS protocol on connections")

        # Check: DNS service (implies domain management)
        checks += 1
        dns_services = {"route53", "cloud_dns", "azure_dns"}
        if services & dns_services:
            passed += 1
            details.append("DNS management configured")
        else:
            passed += 0.5  # not critical

        score = (passed / checks * 100) if checks > 0 else 50.0
        return DimensionScore("Security", score, 0.25, details, recs)

    def _score_cost_efficiency(self, spec: ArchSpec) -> DimensionScore:
        """Cost efficiency (20%): cost per component vs expectations."""
        details = []
        recs = []
        score = 60.0  # base score

        if spec.cost_estimate and spec.cost_estimate.breakdown:
            total = spec.cost_estimate.monthly_total
            n_comps = len(spec.components)

            avg = total / n_comps if n_comps > 0 else 0
            details.append(f"${total:,.2f}/mo across {n_comps} components (avg ${avg:,.2f}/component)")

            # Flag components consuming >40% of budget
            for item in spec.cost_estimate.breakdown:
                if total > 0 and item.monthly / total > 0.4:
                    recs.append(
                        f"{item.component_id} is {item.monthly / total:.0%} of total cost — consider optimization"
                    )
                    score -= 10

            # Budget check
            if spec.constraints and spec.constraints.budget_monthly:
                budget = spec.constraints.budget_monthly
                if total <= budget:
                    score += 20
                    details.append(f"Under budget (${total:,.2f} / ${budget:,.2f})")
                else:
                    score -= 20
                    recs.append(f"Over budget by ${total - budget:,.2f}")

            # Free-tier services boost
            free_count = sum(1 for item in spec.cost_estimate.breakdown if item.monthly == 0)
            if free_count > 0:
                score += min(free_count * 5, 15)
                details.append(f"{free_count} component(s) using free tier")
        else:
            details.append("No cost estimate available — run cost analysis first")
            recs.append("Run `cloudwright cost` to get cost breakdown")

        score = max(0.0, min(100.0, score))
        return DimensionScore("Cost Efficiency", score, 0.20, details, recs)

    def _score_compliance(self, spec: ArchSpec) -> DimensionScore:
        """Compliance (15%): uses existing Validator if compliance constraints are set."""
        details = []
        recs = []
        score = 50.0  # neutral default

        if spec.constraints and spec.constraints.compliance:
            try:
                from cloudwright.validator import Validator

                v = Validator()
                results = v.validate(spec, compliance=spec.constraints.compliance)
                if results:
                    scores = [r.score for r in results]
                    score = sum(scores) / len(scores) * 100
                    for r in results:
                        status = "passed" if r.passed else "failed"
                        details.append(f"{r.framework}: {status} ({r.score:.0%})")
                        if not r.passed:
                            failed_checks = [c for c in r.checks if not c.passed]
                            for fc in failed_checks[:2]:
                                recs.append(
                                    f"[{r.framework}] {fc.recommendation}"
                                    if fc.recommendation
                                    else f"[{r.framework}] Fix: {fc.name}"
                                )
            except Exception:
                details.append("Compliance validation unavailable")
        else:
            details.append("No compliance requirements specified")
            score = 70.0

        return DimensionScore("Compliance", score, 0.15, details, recs)

    def _score_complexity(self, spec: ArchSpec) -> DimensionScore:
        """Complexity (10%): component count, connection density, provider count."""
        details = []
        recs = []

        n_components = len(spec.components)
        n_connections = len(spec.connections)
        providers = {c.provider for c in spec.components}
        n_providers = len(providers)
        services = {c.service for c in spec.components}

        if n_components == 0:
            return DimensionScore("Complexity", 50.0, 0.10, ["No components"], ["Add components"])

        density = n_connections / n_components
        details.append(f"{n_components} components, {n_connections} connections (density: {density:.1f})")
        details.append(f"{n_providers} provider(s), {len(services)} unique services")

        score = 80.0

        if n_components > 15:
            score -= 20
            recs.append("Consider splitting into separate microservices or modules")
        elif n_components > 10:
            score -= 10
            recs.append("Architecture is moderately complex — ensure each component is necessary")
        elif n_components < 3:
            score -= 10
            recs.append("Architecture may be too simple for production use")

        if density > 3.0:
            score -= 15
            recs.append("High connection density — consider introducing a message bus to decouple")
        elif density < 0.5 and n_components > 2:
            score -= 10
            recs.append("Low connection density — some components may be disconnected")

        if n_providers > 2:
            score -= 10
            details.append("Multi-cloud adds operational complexity")

        tiers = {c.tier for c in spec.components}
        if len(tiers) >= 3:
            score += 10
            details.append("Good tier separation")

        score = max(0.0, min(100.0, score))
        return DimensionScore("Complexity", score, 0.10, details, recs)

    @staticmethod
    def _grade(score: float) -> str:
        if score >= 90:
            return "A"
        if score >= 80:
            return "B"
        if score >= 70:
            return "C"
        if score >= 60:
            return "D"
        return "F"

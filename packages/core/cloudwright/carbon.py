"""Carbon footprint estimator for ArchSpec components.

All numbers are estimates based on publicly available data. Sources:
- Grid carbon intensity: IEA Electricity Map averages (2023), gCO2eq/kWh
- Power draw per component tier: AWS/GCP sustainability reports + ACEEE estimates
- PUE (power usage effectiveness): 1.12 (hyperscale cloud avg, Google/AWS 2023 reports)

Usage:
    from cloudwright.carbon import estimate_carbon
    result = estimate_carbon(spec)
    # result["total_kg_co2e_per_month"]  — total across all components
    # result["breakdown"]                — per-component list
    # result["assumptions"]              — named constants used
"""

from __future__ import annotations

from cloudwright.spec import ArchSpec

# ---------------------------------------------------------------------------
# Grid carbon intensity by region (gCO2eq/kWh).
# Source: IEA Electricity Map regional averages, 2023.
# Matched by prefix; unknown regions fall back to a global average.
# ---------------------------------------------------------------------------
_GRID_INTENSITY: dict[str, float] = {
    # AWS regions
    "us-east-1": 380.0,  # Virginia — Mid-Atlantic grid
    "us-east-2": 480.0,  # Ohio — higher coal mix
    "us-west-1": 210.0,  # N. California — hydro/wind heavy
    "us-west-2": 130.0,  # Oregon — ~70% renewable (hydro)
    "ca-central-1": 30.0,  # Canada — largely hydro
    "eu-west-1": 290.0,  # Ireland — wind + gas
    "eu-west-2": 230.0,  # London — offshore wind
    "eu-west-3": 55.0,  # Paris — nuclear dominant
    "eu-central-1": 350.0,  # Frankfurt — coal/gas mix
    "eu-north-1": 8.0,  # Stockholm — almost entirely hydro/nuclear
    "ap-southeast-1": 430.0,  # Singapore — gas
    "ap-southeast-2": 680.0,  # Sydney — coal heavy
    "ap-northeast-1": 465.0,  # Tokyo — post-Fukushima gas/coal
    "ap-northeast-2": 415.0,  # Seoul
    "ap-south-1": 720.0,  # Mumbai — coal dominant
    "sa-east-1": 75.0,  # Sao Paulo — hydro
    "me-south-1": 600.0,  # Bahrain — gas
    "af-south-1": 840.0,  # Cape Town — coal dominant
    # GCP regions
    "us-central1": 490.0,  # Iowa
    "us-east1": 380.0,
    "us-west1": 130.0,
    "europe-west1": 130.0,  # Belgium — nuclear
    "europe-west2": 230.0,
    "europe-west3": 350.0,
    "europe-west4": 330.0,  # Netherlands
    "asia-southeast1": 430.0,
    "asia-northeast1": 465.0,
    "asia-south1": 720.0,
    "southamerica-east1": 75.0,
    # Azure regions
    "eastus": 380.0,
    "eastus2": 380.0,
    "westus": 210.0,
    "westus2": 130.0,
    "centralus": 490.0,
    "northcentralus": 490.0,
    "southcentralus": 420.0,
    "canadacentral": 30.0,
    "westeurope": 330.0,  # Netherlands
    "northeurope": 290.0,  # Ireland
    "uksouth": 230.0,
    "ukwest": 230.0,
    "germanywestcentral": 350.0,
    "francecentral": 55.0,
    "southeastasia": 430.0,
    "eastasia": 590.0,  # Hong Kong
    "japaneast": 465.0,
    "koreacentral": 415.0,
    "centralindia": 720.0,
    "brazilsouth": 75.0,
    "southafricanorth": 840.0,
    "uaenorth": 600.0,
}

# Prefix fallbacks for regions not in the exact table
_GRID_INTENSITY_PREFIXES: list[tuple[str, float]] = [
    ("us-east", 380.0),
    ("us-west", 170.0),
    ("us-", 400.0),
    ("eu-", 200.0),
    ("europe-", 200.0),
    ("ap-", 500.0),
    ("asia-", 500.0),
    ("sa-", 150.0),
    ("southamerica-", 150.0),
    ("me-", 600.0),
    ("af-", 800.0),
    ("ca-", 50.0),
    ("eastus", 380.0),
    ("westus", 170.0),
    ("westeurope", 330.0),
    ("northeurope", 290.0),
    ("southeastasia", 430.0),
    ("japaneast", 465.0),
    ("brazilsouth", 75.0),
    ("southafricanorth", 840.0),
]

# Global average fallback (IEA 2023 global electricity mix)
_GLOBAL_AVG_INTENSITY = 436.0  # gCO2eq/kWh

# Cloud PUE — hyperscale average across AWS, GCP, Azure (2023 sustainability reports)
_CLOUD_PUE = 1.12

# ---------------------------------------------------------------------------
# Power draw (Watts) per component tier.
# Rough mid-point from ACEEE cloud lifecycle assessments and AWS sustainability
# whitepapers. "tier" here maps to the spec's component tier field.
# ---------------------------------------------------------------------------
_TIER_WATTS: dict[int, float] = {
    0: 5.0,  # edge / CDN node — low always-on overhead
    1: 15.0,  # load balancer / API gateway — modest
    2: 80.0,  # compute (single vCPU-scale instance)
    3: 120.0,  # database / cache (memory-intensive, SSD I/O)
    4: 40.0,  # storage / data — storage servers, lower compute
    5: 200.0,  # analytics / ML (GPU/high-mem workloads)
}
_DEFAULT_TIER_WATTS = 60.0  # fallback for unknown tiers

# Service-level power overrides that supersede tier-based defaults
_SERVICE_WATTS: dict[str, float] = {
    # Serverless — billed per invocation, very low idle
    "lambda": 5.0,
    "cloud_functions": 5.0,
    "azure_functions": 5.0,
    # Containers / orchestration
    "eks": 300.0,
    "gke": 300.0,
    "aks": 300.0,
    "ecs": 150.0,
    "fargate": 80.0,
    "cloud_run": 20.0,
    "container_apps": 20.0,
    # Managed databases
    "rds": 100.0,
    "aurora": 120.0,
    "cloud_sql": 100.0,
    "azure_sql": 100.0,
    "dynamodb": 40.0,
    "cosmos_db": 40.0,
    "firestore": 20.0,
    # Analytics / ML
    "redshift": 400.0,
    "bigquery": 200.0,
    "synapse": 400.0,
    "sagemaker": 250.0,
    "vertex_ai": 250.0,
    "azure_ml": 250.0,
    # Databricks
    "databricks_cluster": 500.0,
    "databricks_sql_warehouse": 300.0,
    "databricks_job": 200.0,
    "databricks_pipeline": 200.0,
    "databricks_model_serving": 100.0,
    # Virtual / meta (no real hardware attributed)
    "users": 0.0,
    "internet": 0.0,
    "external": 0.0,
    "client": 0.0,
    "browser": 0.0,
    "mobile": 0.0,
    "vpc": 0.0,
    "vnet": 0.0,
    "iam": 0.0,
}

# Hours per month
_HOURS_PER_MONTH = 730.0


def _grid_intensity(region: str) -> float:
    """Return gCO2eq/kWh for a region. Falls back to global average."""
    r = (region or "").lower().strip()
    if r in _GRID_INTENSITY:
        return _GRID_INTENSITY[r]
    for prefix, intensity in _GRID_INTENSITY_PREFIXES:
        if r.startswith(prefix):
            return intensity
    return _GLOBAL_AVG_INTENSITY


def _component_watts(service: str, tier: int, config: dict) -> float:
    """Estimate power draw in Watts for a single component."""
    base = _SERVICE_WATTS.get(service, _TIER_WATTS.get(tier, _DEFAULT_TIER_WATTS))
    # Scale with node/instance count when explicit
    count = config.get("count", config.get("node_count", config.get("num_nodes", 1)))
    try:
        count = int(count)
    except (TypeError, ValueError):
        count = 1
    return base * max(count, 1)


def estimate_carbon(spec: ArchSpec) -> dict:
    """Return per-component and total CO2e estimates for an ArchSpec.

    All figures are estimates. Assumptions:
    - Power draw per component: see _SERVICE_WATTS / _TIER_WATTS tables
    - Grid carbon intensity: IEA regional averages 2023 (gCO2eq/kWh)
    - Cloud PUE: 1.12 (hyperscale average, AWS/GCP/Azure 2023 sustainability reports)
    - 730 hours/month assumed for always-on components

    Returns a dict with:
        total_kg_co2e_per_month: float
        region: str
        grid_intensity_g_per_kwh: float
        breakdown: list[dict]  — one entry per component
        assumptions: dict      — named constants used in this calculation
    """
    region = spec.region or "us-east-1"
    intensity = _grid_intensity(region)
    breakdown = []
    total_kg = 0.0

    for comp in spec.components:
        config = comp.config or {}
        watts = _component_watts(comp.service, comp.tier, config)
        if watts <= 0:
            breakdown.append(
                {
                    "component_id": comp.id,
                    "service": comp.service,
                    "watts": 0.0,
                    "kwh_per_month": 0.0,
                    "kg_co2e_per_month": 0.0,
                    "note": "virtual/meta component — no hardware attributed",
                }
            )
            continue

        kwh = (watts * _HOURS_PER_MONTH * _CLOUD_PUE) / 1000.0
        kg_co2e = (kwh * intensity) / 1000.0  # gCO2e -> kgCO2e
        total_kg += kg_co2e

        breakdown.append(
            {
                "component_id": comp.id,
                "service": comp.service,
                "watts": round(watts, 1),
                "kwh_per_month": round(kwh, 2),
                "kg_co2e_per_month": round(kg_co2e, 3),
            }
        )

    return {
        "total_kg_co2e_per_month": round(total_kg, 3),
        "region": region,
        "grid_intensity_g_per_kwh": intensity,
        "breakdown": breakdown,
        "assumptions": {
            "pue": _CLOUD_PUE,
            "hours_per_month": _HOURS_PER_MONTH,
            "grid_intensity_source": "IEA Electricity Map regional averages 2023",
            "power_draw_source": "ACEEE cloud lifecycle assessments + AWS/GCP sustainability reports",
            "disclaimer": (
                "These are rough estimates. Actual emissions depend on server utilisation, "
                "renewable energy certificates, and provider-specific PPA mix."
            ),
        },
    }

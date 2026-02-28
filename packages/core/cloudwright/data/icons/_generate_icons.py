"""Generate minimal inline SVG icons for Cloudwright service catalog.

Run once to populate the icons directory:
    python3 packages/core/cloudwright/data/icons/_generate_icons.py

Each SVG is a 48x48 viewBox with a simple geometric shape representing
the service category in the provider's brand color. All shapes are
self-contained — no external refs, no fonts, no licensing concerns.
"""

from __future__ import annotations

from pathlib import Path

# Provider brand colors
_COLORS = {
    "aws": "#FF9900",
    "gcp": "#4285F4",
    "azure": "#0078D4",
    "generic": "#94a3b8",
}

_OUT = Path(__file__).parent


def _wrap(content: str, color: str) -> str:
    return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 48 48" width="48" height="48">{content}</svg>'


def _compute(color: str) -> str:
    # Rectangle body + right-pointing triangle (play button = "run")
    rect = f'<rect x="4" y="10" width="30" height="28" rx="3" fill="{color}" opacity="0.2" stroke="{color}" stroke-width="2"/>'
    tri = f'<polygon points="16,18 16,30 28,24" fill="{color}"/>'
    return _wrap(rect + tri, color)


def _database(color: str) -> str:
    # Cylinder: top ellipse + body rect + bottom ellipse
    body = (
        f'<rect x="10" y="16" width="28" height="20" fill="{color}" opacity="0.2" stroke="{color}" stroke-width="2"/>'
    )
    top = f'<ellipse cx="24" cy="16" rx="14" ry="5" fill="{color}" opacity="0.4" stroke="{color}" stroke-width="2"/>'
    bot = f'<ellipse cx="24" cy="36" rx="14" ry="5" fill="{color}" opacity="0.2" stroke="{color}" stroke-width="2"/>'
    return _wrap(body + top + bot, color)


def _storage(color: str) -> str:
    # Isometric box / cube outline
    # Front face, top face, right face
    front = f'<rect x="8" y="20" width="24" height="20" rx="2" fill="{color}" opacity="0.2" stroke="{color}" stroke-width="2"/>'
    top = f'<polygon points="8,20 20,10 44,10 32,20" fill="{color}" opacity="0.35" stroke="{color}" stroke-width="2"/>'
    right = (
        f'<polygon points="32,20 44,10 44,30 32,40" fill="{color}" opacity="0.15" stroke="{color}" stroke-width="2"/>'
    )
    return _wrap(front + top + right, color)


def _network(color: str) -> str:
    # Globe: circle + two horizontal arcs + vertical line
    circle = f'<circle cx="24" cy="24" r="18" fill="{color}" opacity="0.1" stroke="{color}" stroke-width="2"/>'
    h_line = f'<line x1="6" y1="24" x2="42" y2="24" stroke="{color}" stroke-width="1.5"/>'
    v_line = f'<line x1="24" y1="6" x2="24" y2="42" stroke="{color}" stroke-width="1.5"/>'
    arc1 = f'<ellipse cx="24" cy="24" rx="10" ry="18" fill="none" stroke="{color}" stroke-width="1.5"/>'
    return _wrap(circle + h_line + v_line + arc1, color)


def _security(color: str) -> str:
    # Shield shape
    shield = (
        f'<path d="M24 4 L42 12 L42 26 C42 35 34 42 24 46 C14 42 6 35 6 26 L6 12 Z" '
        f'fill="{color}" opacity="0.2" stroke="{color}" stroke-width="2"/>'
    )
    check = (
        f'<polyline points="16,24 21,30 32,18" fill="none" stroke="{color}" stroke-width="2.5" stroke-linecap="round"/>'
    )
    return _wrap(shield + check, color)


def _serverless(color: str) -> str:
    # Lightning bolt
    bolt = (
        f'<polygon points="28,4 14,26 24,26 20,44 34,22 24,22" '
        f'fill="{color}" opacity="0.9" stroke="{color}" stroke-width="1.5"/>'
    )
    return _wrap(bolt, color)


def _cache(color: str) -> str:
    # Diamond
    diamond = (
        f'<polygon points="24,4 44,24 24,44 4,24" fill="{color}" opacity="0.2" stroke="{color}" stroke-width="2"/>'
    )
    inner = (
        f'<polygon points="24,12 36,24 24,36 12,24" fill="{color}" opacity="0.3" stroke="{color}" stroke-width="1"/>'
    )
    return _wrap(diamond + inner, color)


def _queue(color: str) -> str:
    # Three stacked rectangles
    r1 = f'<rect x="6" y="8" width="36" height="9" rx="2" fill="{color}" opacity="0.5" stroke="{color}" stroke-width="1.5"/>'
    r2 = f'<rect x="6" y="20" width="36" height="9" rx="2" fill="{color}" opacity="0.35" stroke="{color}" stroke-width="1.5"/>'
    r3 = f'<rect x="6" y="32" width="36" height="9" rx="2" fill="{color}" opacity="0.2" stroke="{color}" stroke-width="1.5"/>'
    return _wrap(r1 + r2 + r3, color)


def _cdn(color: str) -> str:
    # Cloud shape
    cloud = (
        f'<path d="M38 30 A8 8 0 0 0 30 16 A12 12 0 0 0 10 26 A8 8 0 0 0 14 42 L38 42 A8 8 0 0 0 38 30 Z" '
        f'fill="{color}" opacity="0.2" stroke="{color}" stroke-width="2"/>'
    )
    return _wrap(cloud, color)


def _monitoring(color: str) -> str:
    # Simple line chart
    axes = (
        f'<line x1="8" y1="40" x2="8" y2="8" stroke="{color}" stroke-width="2"/>'
        f'<line x1="8" y1="40" x2="42" y2="40" stroke="{color}" stroke-width="2"/>'
    )
    line = (
        f'<polyline points="8,36 16,28 24,32 32,16 42,20" '
        f'fill="none" stroke="{color}" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/>'
    )
    return _wrap(axes + line, color)


def _ml(color: str) -> str:
    # Neural network: 3 circles connected by lines
    # Input layer: 2 nodes, output: 1
    nodes = (
        f'<circle cx="10" cy="16" r="5" fill="{color}" opacity="0.5" stroke="{color}" stroke-width="1.5"/>'
        f'<circle cx="10" cy="32" r="5" fill="{color}" opacity="0.5" stroke="{color}" stroke-width="1.5"/>'
        f'<circle cx="24" cy="24" r="5" fill="{color}" opacity="0.7" stroke="{color}" stroke-width="1.5"/>'
        f'<circle cx="38" cy="24" r="5" fill="{color}" opacity="0.9" stroke="{color}" stroke-width="1.5"/>'
    )
    edges = (
        f'<line x1="15" y1="18" x2="19" y2="22" stroke="{color}" stroke-width="1.5"/>'
        f'<line x1="15" y1="30" x2="19" y2="26" stroke="{color}" stroke-width="1.5"/>'
        f'<line x1="29" y1="24" x2="33" y2="24" stroke="{color}" stroke-width="1.5"/>'
    )
    return _wrap(edges + nodes, color)


def _analytics(color: str) -> str:
    # Bar chart
    axes = f'<line x1="8" y1="42" x2="42" y2="42" stroke="{color}" stroke-width="2"/>'
    bars = (
        f'<rect x="12" y="28" width="6" height="14" fill="{color}" opacity="0.6"/>'
        f'<rect x="22" y="16" width="6" height="26" fill="{color}" opacity="0.8"/>'
        f'<rect x="32" y="22" width="6" height="20" fill="{color}" opacity="0.5"/>'
    )
    return _wrap(axes + bars, color)


# Map category -> shape function
_SHAPES = {
    "compute": _compute,
    "database": _database,
    "storage": _storage,
    "network": _network,
    "security": _security,
    "serverless": _serverless,
    "cache": _cache,
    "queue": _queue,
    "cdn": _cdn,
    "monitoring": _monitoring,
    "ml": _ml,
    "analytics": _analytics,
}

# (provider, service) -> category
_ICONS: list[tuple[str, str, str]] = [
    # AWS
    ("aws", "ec2", "compute"),
    ("aws", "rds", "database"),
    ("aws", "s3", "storage"),
    ("aws", "lambda", "serverless"),
    ("aws", "alb", "network"),
    ("aws", "nlb", "network"),
    ("aws", "cloudfront", "cdn"),
    ("aws", "elasticache", "cache"),
    ("aws", "dynamodb", "database"),
    ("aws", "sqs", "queue"),
    ("aws", "sns", "queue"),
    ("aws", "waf", "security"),
    ("aws", "route53", "network"),
    ("aws", "api_gateway", "serverless"),
    ("aws", "ecs", "compute"),
    ("aws", "eks", "compute"),
    ("aws", "cognito", "security"),
    ("aws", "kms", "security"),
    ("aws", "cloudtrail", "security"),
    ("aws", "guardduty", "security"),
    ("aws", "kinesis", "queue"),
    ("aws", "ecr", "storage"),
    ("aws", "cloudwatch", "monitoring"),
    ("aws", "ebs", "storage"),
    ("aws", "sagemaker", "ml"),
    ("aws", "redshift", "analytics"),
    ("aws", "glue", "serverless"),
    ("aws", "step_functions", "serverless"),
    ("aws", "emr", "analytics"),
    # GCP
    ("gcp", "compute_engine", "compute"),
    ("gcp", "cloud_sql", "database"),
    ("gcp", "cloud_storage", "storage"),
    ("gcp", "gke", "compute"),
    ("gcp", "cloud_functions", "serverless"),
    ("gcp", "cloud_run", "serverless"),
    ("gcp", "pub_sub", "queue"),
    ("gcp", "memorystore", "cache"),
    ("gcp", "cloud_cdn", "cdn"),
    ("gcp", "cloud_load_balancing", "network"),
    ("gcp", "bigquery", "analytics"),
    # Azure
    ("azure", "virtual_machines", "compute"),
    ("azure", "azure_sql", "database"),
    ("azure", "blob_storage", "storage"),
    ("azure", "aks", "compute"),
    ("azure", "azure_functions", "serverless"),
    ("azure", "cosmos_db", "database"),
    ("azure", "azure_cache", "cache"),
    ("azure", "app_gateway", "network"),
    ("azure", "service_bus", "queue"),
    # Generic
    ("generic", "user", "network"),
    ("generic", "internet", "network"),
    ("generic", "firewall", "security"),
    ("generic", "load_balancer", "network"),
    ("generic", "database", "database"),
    ("generic", "cache", "cache"),
    ("generic", "queue", "queue"),
    ("generic", "storage", "storage"),
    ("generic", "compute", "compute"),
    ("generic", "cdn", "cdn"),
]


def generate_all() -> None:
    generated = 0
    for provider, service, category in _ICONS:
        color = _COLORS.get(provider, _COLORS["generic"])
        shape_fn = _SHAPES.get(category, _compute)
        svg = shape_fn(color)

        out_dir = _OUT / provider
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / f"{service}.svg").write_text(svg)
        generated += 1

    print(f"Generated {generated} SVG icons in {_OUT}")


if __name__ == "__main__":
    generate_all()

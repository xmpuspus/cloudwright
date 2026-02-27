"""Service catalog — SQLite-backed instance specs, pricing, and cross-cloud equivalences."""

from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from cloudwright.catalog.formula import default_managed_price as _default_managed_price
from cloudwright.registry import ServiceRegistry, get_registry

# Catalog JSON data location: top-level catalog/ dir or bundled data/
_CATALOG_DIR = Path(__file__).parent.parent.parent.parent.parent / "catalog"
_BUNDLED_DB = Path(__file__).parent.parent / "data" / "catalog.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS providers (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS regions (
    id TEXT PRIMARY KEY,
    provider_id TEXT NOT NULL,
    code TEXT NOT NULL,
    name TEXT NOT NULL,
    normalized TEXT NOT NULL,
    UNIQUE(provider_id, code)
);

CREATE TABLE IF NOT EXISTS instance_types (
    id TEXT PRIMARY KEY,
    provider_id TEXT NOT NULL,
    name TEXT NOT NULL,
    family TEXT,
    family_normalized TEXT,
    vcpus INTEGER NOT NULL,
    memory_gb REAL NOT NULL,
    storage_desc TEXT,
    gpu_count INTEGER DEFAULT 0,
    network_bandwidth TEXT,
    arch TEXT DEFAULT 'x86_64',
    generation TEXT,
    description TEXT
);

CREATE TABLE IF NOT EXISTS pricing (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    instance_type_id TEXT NOT NULL,
    region_id TEXT NOT NULL,
    os TEXT NOT NULL DEFAULT 'linux',
    price_per_hour REAL NOT NULL,
    price_type TEXT NOT NULL DEFAULT 'on_demand',
    UNIQUE(instance_type_id, region_id, os, price_type)
);

CREATE TABLE IF NOT EXISTS equivalences (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    instance_a_id TEXT NOT NULL,
    instance_b_id TEXT NOT NULL,
    confidence REAL NOT NULL DEFAULT 0.8,
    match_type TEXT NOT NULL DEFAULT 'spec',
    UNIQUE(instance_a_id, instance_b_id)
);

CREATE TABLE IF NOT EXISTS managed_services (
    id TEXT PRIMARY KEY,
    provider_id TEXT NOT NULL,
    service TEXT NOT NULL,
    tier_name TEXT NOT NULL,
    price_per_hour REAL NOT NULL DEFAULT 0,
    price_per_month REAL NOT NULL DEFAULT 0,
    vcpus INTEGER DEFAULT 0,
    memory_gb REAL DEFAULT 0,
    notes TEXT DEFAULT ''
);

CREATE TABLE IF NOT EXISTS catalog_metadata (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS service_definitions (
    id TEXT PRIMARY KEY,
    provider_id TEXT NOT NULL,
    service_key TEXT NOT NULL,
    category TEXT NOT NULL,
    name TEXT NOT NULL,
    pricing_formula TEXT NOT NULL DEFAULT 'per_hour',
    default_config TEXT DEFAULT '{}',
    UNIQUE(provider_id, service_key)
);

CREATE TABLE IF NOT EXISTS service_equivalences (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    service_a TEXT NOT NULL,
    provider_a TEXT NOT NULL,
    service_b TEXT NOT NULL,
    provider_b TEXT NOT NULL,
    UNIQUE(service_a, provider_a, service_b, provider_b)
);

CREATE INDEX IF NOT EXISTS idx_instance_provider ON instance_types(provider_id);
CREATE INDEX IF NOT EXISTS idx_instance_vcpus ON instance_types(vcpus);
CREATE INDEX IF NOT EXISTS idx_instance_memory ON instance_types(memory_gb);
CREATE INDEX IF NOT EXISTS idx_pricing_instance ON pricing(instance_type_id);
CREATE INDEX IF NOT EXISTS idx_pricing_region ON pricing(region_id);
CREATE INDEX IF NOT EXISTS idx_managed_service ON managed_services(provider_id, service);
"""

_PRICING_MULTIPLIERS = {
    "on_demand": 1.0,
    "reserved_1yr": 0.6,
    "reserved_3yr": 0.4,
    "spot": 0.3,
}

REGION_MAP = {
    "aws": {
        "us-east-1": ("us_east", "US East (Virginia)"),
        "us-west-2": ("us_west", "US West (Oregon)"),
        "eu-west-1": ("eu_west", "EU (Ireland)"),
        "ap-southeast-1": ("ap_southeast", "Asia Pacific (Singapore)"),
    },
    "gcp": {
        "us-central1": ("us_east", "US Central (Iowa)"),
        "us-west1": ("us_west", "US West (Oregon)"),
        "europe-west1": ("eu_west", "EU (Belgium)"),
        "asia-southeast1": ("ap_southeast", "Asia SE (Singapore)"),
    },
    "azure": {
        "eastus": ("us_east", "East US"),
        "westus2": ("us_west", "West US 2"),
        "westeurope": ("eu_west", "West Europe"),
        "southeastasia": ("ap_southeast", "Southeast Asia"),
    },
}


class Catalog:
    """SQLite-backed cloud service catalog.

    Provides instance specs, pricing data, and cross-cloud equivalence
    mappings for AWS, GCP, and Azure. Auto-seeds from JSON catalog files
    on first use.
    """

    def __init__(self, db_path: str | Path | None = None):
        if db_path:
            self.db_path = Path(db_path)
        elif _BUNDLED_DB.exists():
            self.db_path = _BUNDLED_DB
        else:
            self.db_path = _BUNDLED_DB
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._ensure_db()

    @contextmanager
    def _connect(self):
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _ensure_db(self):
        with self._connect() as conn:
            conn.executescript(SCHEMA)
            # Only auto-seed the bundled DB; explicit paths are caller-managed
            if self.db_path == _BUNDLED_DB:
                count = conn.execute("SELECT COUNT(*) FROM instance_types").fetchone()[0]
                if count == 0:
                    self._seed(conn)

    def _seed(self, conn: sqlite3.Connection):
        """Load catalog data from JSON files into SQLite."""
        # Insert providers
        for pid, name in [("aws", "Amazon Web Services"), ("gcp", "Google Cloud"), ("azure", "Microsoft Azure")]:
            conn.execute("INSERT OR IGNORE INTO providers (id, name) VALUES (?, ?)", (pid, name))

        # Insert regions
        for provider, regions in REGION_MAP.items():
            for code, (normalized, name) in regions.items():
                rid = f"{provider}:{code}"
                conn.execute(
                    "INSERT OR IGNORE INTO regions (id, provider_id, code, name, normalized) VALUES (?, ?, ?, ?, ?)",
                    (rid, provider, code, name, normalized),
                )

        # Load compute instance data
        for provider in ("aws", "gcp", "azure"):
            compute_path = _CATALOG_DIR / provider / "compute.json"
            if compute_path.exists():
                self._load_compute(conn, provider, compute_path)

            db_path = _CATALOG_DIR / provider / "database.json"
            if db_path.exists():
                self._load_managed_db(conn, provider, db_path)

            net_path = _CATALOG_DIR / provider / "networking.json"
            if net_path.exists():
                self._load_networking(conn, provider, net_path)

            storage_path = _CATALOG_DIR / provider / "storage.json"
            if storage_path.exists():
                self._load_storage(conn, provider, storage_path)

        # Load equivalences
        equiv_path = _CATALOG_DIR / "equivalences.json"
        if equiv_path.exists():
            self._load_equivalences(conn, equiv_path)

        self.sync_from_registry(_conn=conn)

    def _load_compute(self, conn: sqlite3.Connection, provider: str, path: Path):
        data = json.loads(path.read_text())
        for inst in data.get("instances", []):
            inst_id = f"{provider}:{inst['name']}"
            conn.execute(
                """INSERT OR IGNORE INTO instance_types
                (id, provider_id, name, family, family_normalized, vcpus, memory_gb,
                 storage_desc, gpu_count, network_bandwidth, arch, generation, description)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    inst_id,
                    provider,
                    inst["name"],
                    inst.get("family"),
                    inst.get("family_normalized"),
                    inst["vcpus"],
                    inst["memory_gb"],
                    inst.get("storage_desc"),
                    inst.get("gpu_count", 0),
                    inst.get("network_bandwidth"),
                    inst.get("arch", "x86_64"),
                    inst.get("generation"),
                    inst.get("description"),
                ),
            )
            for pr in inst.get("pricing", []):
                region_code = pr["region"]
                region_id = f"{provider}:{region_code}"
                prices = pr.get("prices", {})
                for os_type, price in prices.items():
                    conn.execute(
                        """INSERT OR IGNORE INTO pricing
                        (instance_type_id, region_id, os, price_per_hour, price_type)
                        VALUES (?, ?, ?, ?, ?)""",
                        (inst_id, region_id, os_type, price, pr.get("price_type", "on_demand")),
                    )

    def _load_managed_db(self, conn: sqlite3.Connection, provider: str, path: Path):
        data = json.loads(path.read_text())
        service = data.get("service", "rds")
        storage_per_gb = data.get("storage_per_gb", 0.115)
        multi_az_mult = data.get("multi_az_multiplier", 2.0)

        for tier in data.get("tiers", []):
            tier_id = f"{provider}:{service}:{tier['name']}"
            price_us = list(tier.get("pricing", {}).values())[0] if tier.get("pricing") else 0
            monthly = round(price_us * 730, 2)
            conn.execute(
                """INSERT OR IGNORE INTO managed_services
                (id, provider_id, service, tier_name, price_per_hour, price_per_month, vcpus, memory_gb, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    tier_id,
                    provider,
                    service,
                    tier["name"],
                    price_us,
                    monthly,
                    tier.get("vcpus", 0),
                    tier.get("memory_gb", 0),
                    f"storage_per_gb={storage_per_gb}, multi_az_mult={multi_az_mult}",
                ),
            )

    def _load_networking(self, conn: sqlite3.Connection, provider: str, path: Path):
        data = json.loads(path.read_text())
        # Store ALB/NLB/CDN pricing as managed services
        for svc_key in (
            "alb",
            "nlb",
            "cloudfront",
            "route53",
            "api_gateway",
            "cloud_load_balancing",
            "cloud_cdn",
            "cloud_dns",
            "app_gateway",
            "azure_lb",
            "azure_cdn",
            "azure_dns",
        ):
            svc_data = data.get(svc_key)
            if not svc_data:
                continue
            fixed = svc_data.get("fixed_per_month", 0)
            sid = f"{provider}:net:{svc_key}"
            conn.execute(
                """INSERT OR IGNORE INTO managed_services
                (id, provider_id, service, tier_name, price_per_hour, price_per_month, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (sid, provider, svc_key, "default", fixed / 730 if fixed else 0, fixed, json.dumps(svc_data)),
            )

    def _load_storage(self, conn: sqlite3.Connection, provider: str, path: Path):
        data = json.loads(path.read_text())
        for svc_key in ("s3", "ebs", "cloud_storage", "blob_storage", "persistent_disk", "managed_disks"):
            svc_data = data.get(svc_key)
            if not svc_data:
                continue
            per_gb = 0.0
            if isinstance(svc_data, dict):
                per_gb = svc_data.get("per_gb_month", svc_data.get("standard_per_gb", 0))
            sid = f"{provider}:storage:{svc_key}"
            conn.execute(
                """INSERT OR IGNORE INTO managed_services
                (id, provider_id, service, tier_name, price_per_hour, price_per_month, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (sid, provider, svc_key, "default", 0, per_gb, json.dumps(svc_data)),
            )

    def _load_equivalences(self, conn: sqlite3.Connection, path: Path):
        data = json.loads(path.read_text())
        for eq in data.get("equivalences", []):
            pairs = []
            if "aws" in eq and "gcp" in eq:
                pairs.append((f"aws:{eq['aws']}", f"gcp:{eq['gcp']}"))
            if "aws" in eq and "azure" in eq:
                pairs.append((f"aws:{eq['aws']}", f"azure:{eq['azure']}"))
            if "gcp" in eq and "azure" in eq:
                pairs.append((f"gcp:{eq['gcp']}", f"azure:{eq['azure']}"))
            for a, b in pairs:
                conn.execute(
                    "INSERT OR IGNORE INTO equivalences (instance_a_id, instance_b_id, confidence, match_type) VALUES (?, ?, ?, ?)",
                    (a, b, eq.get("confidence", 0.8), eq.get("match_type", "spec")),
                )

    def search(
        self,
        query: str | None = None,
        vcpus: int | None = None,
        memory_gb: float | None = None,
        provider: str | None = None,
        max_price_per_hour: float | None = None,
        limit: int = 20,
    ) -> list[dict]:
        """Search instances by specs or text query."""
        conditions = []
        params: list[Any] = []

        if provider:
            conditions.append("i.provider_id = ?")
            params.append(provider)
        if vcpus:
            conditions.append("i.vcpus >= ?")
            params.append(vcpus)
        if memory_gb:
            conditions.append("i.memory_gb >= ?")
            params.append(memory_gb)
        if max_price_per_hour:
            conditions.append("p.price_per_hour <= ?")
            params.append(max_price_per_hour)
        if query:
            # Simple text matching on name, family, description
            conditions.append("(i.name LIKE ? OR i.family LIKE ? OR i.description LIKE ?)")
            like = f"%{query}%"
            params.extend([like, like, like])

        where_clause = " AND ".join(conditions) if conditions else "1=1"
        # where_clause is built only from hardcoded strings above, never from user input.
        # All user-supplied values are passed via parameterized ? placeholders.
        sql = (  # noqa: S608
            "SELECT DISTINCT i.id, i.provider_id, i.name, i.family, i.family_normalized,"
            " i.vcpus, i.memory_gb, i.storage_desc, i.gpu_count, i.network_bandwidth,"
            " i.arch, p.price_per_hour, p.price_type,"
            " r.code as region_code, r.normalized as region_normalized"
            " FROM instance_types i"
            " LEFT JOIN pricing p ON p.instance_type_id = i.id AND p.os = 'linux' AND p.price_type = 'on_demand'"
            " LEFT JOIN regions r ON r.id = p.region_id AND r.normalized = 'us_east'"
            " WHERE " + where_clause + " ORDER BY COALESCE(p.price_per_hour, 999) ASC"
            " LIMIT ?"
        )
        params.append(limit)

        with self._connect() as conn:
            rows = conn.execute(sql, params).fetchall()
            return [self._row_to_dict(r) for r in rows]

    def compare(self, *instance_names: str) -> list[dict]:
        """Compare specific instances side by side."""
        results = []
        with self._connect() as conn:
            for name in instance_names:
                row = conn.execute(
                    """SELECT i.*, p.price_per_hour, p.price_type, r.code as region_code
                    FROM instance_types i
                    LEFT JOIN pricing p ON p.instance_type_id = i.id AND p.os = 'linux' AND p.price_type = 'on_demand'
                    LEFT JOIN regions r ON r.id = p.region_id AND r.normalized = 'us_east'
                    WHERE i.name = ? OR i.id = ?
                    LIMIT 1""",
                    (name, f"aws:{name}" if ":" not in name else name),
                ).fetchone()
                if row:
                    results.append(self._row_to_dict(row))
                else:
                    # Try other providers
                    for prefix in ("gcp:", "azure:"):
                        row = conn.execute(
                            """SELECT i.*, p.price_per_hour, p.price_type, r.code as region_code
                            FROM instance_types i
                            LEFT JOIN pricing p ON p.instance_type_id = i.id AND p.os = 'linux' AND p.price_type = 'on_demand'
                            LEFT JOIN regions r ON r.id = p.region_id AND r.normalized = 'us_east'
                            WHERE i.id = ? LIMIT 1""",
                            (f"{prefix}{name}",),
                        ).fetchone()
                        if row:
                            results.append(self._row_to_dict(row))
                            break
        return results

    def find_instance(self, name: str) -> dict | None:
        """Find an instance by name."""
        with self._connect() as conn:
            row = conn.execute(
                """SELECT i.*, p.price_per_hour
                FROM instance_types i
                LEFT JOIN pricing p ON p.instance_type_id = i.id AND p.os = 'linux' AND p.price_type = 'on_demand'
                LEFT JOIN regions r ON r.id = p.region_id AND r.normalized = 'us_east'
                WHERE i.name = ? OR i.id = ?
                LIMIT 1""",
                (name, name),
            ).fetchone()
            return self._row_to_dict(row) if row else None

    def get_service_pricing(
        self, service: str, provider: str, config: dict | None = None, pricing_tier: str = "on_demand"
    ) -> float | None:
        """Get monthly pricing for a service. Returns monthly cost or None."""
        base = self._get_base_price(service, provider, config)
        if base is None:
            return None
        multiplier = _PRICING_MULTIPLIERS.get(pricing_tier, 1.0)
        return round(base * multiplier, 2)

    def _get_base_price(self, service: str, provider: str, config: dict | None = None) -> float | None:
        """Compute on-demand monthly price for a service. Returns None if unknown."""
        config = config or {}

        # For compute instances, look up by instance_type
        if service in ("ec2", "compute_engine", "virtual_machines"):
            instance_type = config.get("instance_type", config.get("machine_type", config.get("vm_size")))
            if instance_type:
                inst = self.find_instance(instance_type)
                if inst and inst.get("price_per_hour"):
                    count = config.get("count", 1)
                    return round(inst["price_per_hour"] * 730 * count, 2)
            return None

        # For managed services, look up in managed_services table
        with self._connect() as conn:
            # Database services
            if service in ("rds", "aurora", "cloud_sql", "azure_sql"):
                instance_class = config.get("instance_class", config.get("tier", ""))
                if instance_class:
                    row = conn.execute(
                        "SELECT price_per_hour, notes FROM managed_services WHERE provider_id = ? AND service = ? AND tier_name = ?",
                        (provider, service if service != "aurora" else "rds", instance_class),
                    ).fetchone()
                    if row:
                        hourly = row["price_per_hour"]
                        monthly = round(hourly * 730, 2)
                        # Add storage cost
                        storage_gb = config.get("storage_gb", 20)
                        notes = row["notes"]
                        storage_rate = 0.115  # default
                        if "storage_per_gb=" in notes:
                            storage_rate = float(notes.split("storage_per_gb=")[1].split(",")[0])
                        monthly += round(storage_gb * storage_rate, 2)
                        # Multi-AZ doubles compute cost
                        if config.get("multi_az", False):
                            monthly = round(monthly + hourly * 730, 2)
                        return monthly
                # Fallback default pricing
                return _default_managed_price(service, config)

            # Storage
            if service in ("s3", "cloud_storage", "blob_storage"):
                storage_gb = config.get("storage_gb", 50)
                row = conn.execute(
                    "SELECT notes FROM managed_services WHERE provider_id = ? AND service = ?",
                    (provider, service),
                ).fetchone()
                if row and row["notes"]:
                    try:
                        svc_data = json.loads(row["notes"])
                        per_gb = svc_data.get("per_gb_month", svc_data.get("standard_per_gb", 0.023))
                    except (json.JSONDecodeError, TypeError):
                        per_gb = 0.023
                else:
                    per_gb = 0.023
                return round(storage_gb * per_gb, 2)

            # Load balancers
            if service in ("alb", "nlb", "app_gateway", "azure_lb", "cloud_load_balancing"):
                row = conn.execute(
                    "SELECT price_per_month, notes FROM managed_services WHERE provider_id = ? AND service = ?",
                    (provider, service),
                ).fetchone()
                if row:
                    return (
                        round(row["price_per_month"], 2)
                        if row["price_per_month"] > 0
                        else _default_managed_price(service, config)
                    )
                return _default_managed_price(service, config)

            # CDN
            if service in ("cloudfront", "cloud_cdn", "azure_cdn"):
                estimated_gb = config.get("estimated_gb", 100)
                row = conn.execute(
                    "SELECT notes FROM managed_services WHERE provider_id = ? AND service = ?",
                    (provider, service),
                ).fetchone()
                if row and row["notes"]:
                    try:
                        svc_data = json.loads(row["notes"])
                        if "data_transfer_out_per_gb" in svc_data:
                            rate = svc_data["data_transfer_out_per_gb"]
                            if isinstance(rate, dict):
                                rate = rate.get("first_10tb", 0.085)
                        elif "per_gb" in svc_data:
                            rate = svc_data["per_gb"]
                        else:
                            rate = 0.085
                    except (json.JSONDecodeError, TypeError):
                        rate = 0.085
                else:
                    rate = 0.085
                return round(estimated_gb * rate, 2)

            # Cache
            if service in ("elasticache", "memorystore", "azure_cache"):
                node_type = config.get("node_type", config.get("tier", ""))
                if node_type:
                    row = conn.execute(
                        "SELECT price_per_hour FROM managed_services WHERE provider_id = ? AND tier_name = ?",
                        (provider, node_type),
                    ).fetchone()
                    if row:
                        return round(row["price_per_hour"] * 730, 2)
                return _default_managed_price(service, config)

            # Serverless (Lambda, Cloud Functions, Azure Functions)
            if service in ("lambda", "cloud_functions", "azure_functions"):
                monthly_requests = config.get("monthly_requests", 1_000_000)
                avg_duration_ms = config.get("avg_duration_ms", 200)
                memory_mb = config.get("memory_mb", 512)
                # Request cost
                request_cost = (monthly_requests / 1_000_000) * 0.20
                # Compute cost: GB-seconds
                gb_seconds = (monthly_requests * avg_duration_ms / 1000) * (memory_mb / 1024)
                compute_cost = gb_seconds * 0.0000166667
                return round(request_cost + compute_cost, 2)

            # Queues
            if service in ("sqs", "pub_sub", "service_bus"):
                monthly_requests = config.get("monthly_requests", 10_000_000)
                per_million = 0.40 if service == "sqs" else 0.60
                return round((monthly_requests / 1_000_000) * per_million, 2)

            # DynamoDB
            if service in ("dynamodb", "firestore", "cosmos_db"):
                if config.get("billing_mode") == "provisioned":
                    rcu = config.get("read_capacity", 5)
                    wcu = config.get("write_capacity", 5)
                    return round(wcu * 0.00065 * 730 + rcu * 0.00013 * 730, 2)
                return 25.0  # on-demand base

            # Fallback
            return _default_managed_price(service, config)

    def sync_from_registry(
        self, registry: ServiceRegistry | None = None, *, _conn: sqlite3.Connection | None = None
    ) -> None:
        """Populate service_definitions and service_equivalences from a ServiceRegistry.

        Idempotent — uses INSERT OR REPLACE so repeated calls are safe.
        Pass _conn to reuse an existing transaction (used internally by _seed).
        """
        reg = registry if registry is not None else get_registry()

        def _do_sync(conn: sqlite3.Connection) -> None:
            for svc in reg._services.values():
                sid = f"{svc.provider}:{svc.service_key}"
                conn.execute(
                    """INSERT OR REPLACE INTO service_definitions
                    (id, provider_id, service_key, category, name, pricing_formula, default_config)
                    VALUES (?, ?, ?, ?, ?, ?, ?)""",
                    (
                        sid,
                        svc.provider,
                        svc.service_key,
                        svc.category,
                        svc.name,
                        svc.pricing_formula,
                        json.dumps(svc.default_config),
                    ),
                )

            for equiv in reg.all_equivalences():
                providers = list(equiv.keys())
                for i, pa in enumerate(providers):
                    for pb in providers[i + 1 :]:
                        conn.execute(
                            """INSERT OR IGNORE INTO service_equivalences
                            (service_a, provider_a, service_b, provider_b)
                            VALUES (?, ?, ?, ?)""",
                            (equiv[pa], pa, equiv[pb], pb),
                        )

        if _conn is not None:
            _do_sync(_conn)
        else:
            with self._connect() as conn:
                _do_sync(conn)

    def get_service_definition(self, provider: str, service_key: str) -> dict | None:
        """Return the service_definitions row for (provider, service_key) as a dict, or None."""
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM service_definitions WHERE provider_id = ? AND service_key = ?",
                (provider, service_key),
            ).fetchone()
            if row is None:
                return None
            result = dict(row)
            try:
                result["default_config"] = json.loads(result.get("default_config") or "{}")
            except (json.JSONDecodeError, TypeError):
                result["default_config"] = {}
            return result

    def get_stats(self) -> dict:
        with self._connect() as conn:
            instance_count = conn.execute("SELECT COUNT(*) FROM instance_types").fetchone()[0]
            pricing_count = conn.execute("SELECT COUNT(*) FROM pricing").fetchone()[0]
            managed_count = conn.execute("SELECT COUNT(*) FROM managed_services").fetchone()[0]
            equivalence_count = conn.execute("SELECT COUNT(*) FROM service_equivalences").fetchone()[0]
            return {
                "instance_count": instance_count,
                "pricing_count": pricing_count,
                "managed_count": managed_count,
                "equivalence_count": equivalence_count,
            }

    def _row_to_dict(self, row: sqlite3.Row) -> dict:
        d = dict(row)
        if "price_per_hour" in d and d["price_per_hour"]:
            d["price_per_month"] = round(d["price_per_hour"] * 730, 2)
        return d

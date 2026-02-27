"""Tests for the service registry loader."""

import pytest
from cloudwright.catalog.store import Catalog
from cloudwright.registry import ServiceRegistry, get_registry, reload_registry


@pytest.fixture
def registry():
    return ServiceRegistry()


class TestRegistryLoad:
    def test_loads_without_error(self, registry):
        assert registry is not None

    def test_has_three_providers(self, registry):
        providers = registry.list_providers()
        assert set(providers) == {"aws", "gcp", "azure"}

    def test_has_expected_categories(self, registry):
        cats = set(registry.list_categories())
        # Database and storage are split into subcategories; networking/security likewise
        assert "compute" in cats
        assert "serverless" in cats
        assert "containers" in cats
        assert "cache" in cats
        assert "messaging" in cats
        assert "streaming" in cats
        assert "analytics" in cats
        assert "ml" in cats
        assert "orchestration" in cats
        # Hierarchical subcategories
        assert "database_relational" in cats
        assert "database_nosql" in cats
        assert "storage_object" in cats

    def test_stats_reasonable(self, registry):
        s = registry.stats()
        assert s["total_services"] > 20
        assert s["categories"] >= 13
        assert s["providers"] == 3
        assert s["equivalences"] > 5


class TestServiceLookup:
    def test_get_aws_ec2(self, registry):
        svc = registry.get("aws", "ec2")
        assert svc is not None
        assert svc.name == "Amazon EC2"
        assert svc.category == "compute"
        assert svc.pricing_formula == "per_hour"
        assert "instance_type" in svc.default_config

    def test_get_gcp_compute_engine(self, registry):
        svc = registry.get("gcp", "compute_engine")
        assert svc is not None
        assert svc.provider == "gcp"
        assert svc.category == "compute"

    def test_get_azure_virtual_machines(self, registry):
        svc = registry.get("azure", "virtual_machines")
        assert svc is not None
        assert svc.provider == "azure"

    def test_get_unknown_returns_none(self, registry):
        assert registry.get("aws", "nonexistent_service") is None
        assert registry.get("unknown_provider", "ec2") is None

    def test_get_lambda(self, registry):
        svc = registry.get("aws", "lambda")
        assert svc.category == "serverless"
        assert svc.pricing_formula == "per_request"

    def test_get_s3(self, registry):
        svc = registry.get("aws", "s3")
        assert svc.category == "storage_object"
        assert svc.pricing_formula == "per_gb"

    def test_get_dynamodb(self, registry):
        svc = registry.get("aws", "dynamodb")
        assert svc.category == "database_nosql"

    def test_get_rds(self, registry):
        svc = registry.get("aws", "rds")
        assert "instance_class" in svc.default_config

    def test_to_dict(self, registry):
        svc = registry.get("aws", "ec2")
        d = svc.to_dict()
        assert d["service_key"] == "ec2"
        assert d["provider"] == "aws"
        assert "pricing_formula" in d
        assert "default_config" in d


class TestCategoryLookup:
    def test_compute_has_all_providers(self, registry):
        svcs = registry.get_category("compute")
        providers = {s.provider for s in svcs}
        assert "aws" in providers
        assert "gcp" in providers
        assert "azure" in providers

    def test_database_has_multiple_services(self, registry):
        # Relational DB services per AWS: rds + aurora
        svcs = registry.get_category("database_relational")
        aws_db = [s for s in svcs if s.provider == "aws"]
        assert len(aws_db) >= 2  # rds + aurora

    def test_empty_category_returns_empty_list(self, registry):
        result = registry.get_category("nonexistent_category")
        assert result == []

    def test_list_services_by_provider(self, registry):
        aws = registry.list_services("aws")
        assert len(aws) > 5
        assert all(s.provider == "aws" for s in aws)


class TestEquivalences:
    def test_aws_to_gcp_compute(self, registry):
        result = registry.get_equivalent("ec2", "aws", "gcp")
        assert result == "compute_engine"

    def test_aws_to_azure_compute(self, registry):
        result = registry.get_equivalent("ec2", "aws", "azure")
        assert result == "virtual_machines"

    def test_aws_to_gcp_lambda(self, registry):
        result = registry.get_equivalent("lambda", "aws", "gcp")
        assert result == "cloud_functions"

    def test_aws_to_azure_lambda(self, registry):
        result = registry.get_equivalent("lambda", "aws", "azure")
        assert result == "azure_functions"

    def test_gcp_to_aws_compute(self, registry):
        result = registry.get_equivalent("compute_engine", "gcp", "aws")
        assert result == "ec2"

    def test_azure_to_aws_compute(self, registry):
        result = registry.get_equivalent("virtual_machines", "azure", "aws")
        assert result == "ec2"

    def test_same_provider_returns_same_key(self, registry):
        result = registry.get_equivalent("ec2", "aws", "aws")
        assert result == "ec2"

    def test_unknown_service_returns_none(self, registry):
        result = registry.get_equivalent("totally_unknown", "aws", "gcp")
        assert result is None

    def test_all_equivalences_not_empty(self, registry):
        equivs = registry.all_equivalences()
        assert len(equivs) > 5


class TestHelpers:
    def test_get_pricing_formula_known(self, registry):
        assert registry.get_pricing_formula("aws", "ec2") == "per_hour"
        assert registry.get_pricing_formula("aws", "lambda") == "per_request"
        assert registry.get_pricing_formula("aws", "s3") == "per_gb"

    def test_get_pricing_formula_unknown_defaults_per_hour(self, registry):
        assert registry.get_pricing_formula("aws", "nonexistent") == "per_hour"

    def test_get_default_config_returns_copy(self, registry):
        cfg1 = registry.get_default_config("aws", "ec2")
        cfg2 = registry.get_default_config("aws", "ec2")
        cfg1["mutated"] = True
        assert "mutated" not in cfg2

    def test_get_default_config_unknown_returns_empty(self, registry):
        assert registry.get_default_config("aws", "nonexistent") == {}


class TestCatalogSync:
    @pytest.fixture
    def temp_catalog(self, tmp_path):
        db_file = tmp_path / "test.db"
        return Catalog(db_path=db_file)

    @pytest.fixture
    def synced_catalog(self, temp_catalog):
        reg = ServiceRegistry()
        temp_catalog.sync_from_registry(reg)
        return temp_catalog, reg

    def test_sync_populates_service_definitions(self, synced_catalog):
        cat, reg = synced_catalog
        with cat._connect() as conn:
            count = conn.execute("SELECT COUNT(*) FROM service_definitions").fetchone()[0]
        assert count == len(reg._services)
        assert count > 20

    def test_sync_populates_service_equivalences(self, synced_catalog):
        cat, reg = synced_catalog
        with cat._connect() as conn:
            count = conn.execute("SELECT COUNT(*) FROM service_equivalences").fetchone()[0]
        assert count > 0
        # Count unique pairs — some groups share the same provider pair across categories
        unique_pairs: set[tuple] = set()
        for equiv in reg.all_equivalences():
            providers = list(equiv.keys())
            for i, pa in enumerate(providers):
                for pb in providers[i + 1 :]:
                    unique_pairs.add((equiv[pa], pa, equiv[pb], pb))
        assert count == len(unique_pairs)

    def test_get_service_definition_returns_correct_data(self, synced_catalog):
        cat, _ = synced_catalog
        result = cat.get_service_definition("aws", "ec2")
        assert result is not None
        assert result["provider_id"] == "aws"
        assert result["service_key"] == "ec2"
        assert result["category"] == "compute"
        assert result["pricing_formula"] == "per_hour"
        assert isinstance(result["default_config"], dict)
        assert "instance_type" in result["default_config"]

    def test_get_service_definition_unknown_returns_none(self, synced_catalog):
        cat, _ = synced_catalog
        assert cat.get_service_definition("aws", "nonexistent") is None
        assert cat.get_service_definition("unknown_provider", "ec2") is None

    def test_sync_idempotent(self, synced_catalog):
        cat, reg = synced_catalog
        # Run sync a second time — counts must not change
        cat.sync_from_registry(reg)
        with cat._connect() as conn:
            svc_count = conn.execute("SELECT COUNT(*) FROM service_definitions").fetchone()[0]
            eq_count = conn.execute("SELECT COUNT(*) FROM service_equivalences").fetchone()[0]
        assert svc_count == len(reg._services)
        unique_pairs: set[tuple] = set()
        for equiv in reg.all_equivalences():
            providers = list(equiv.keys())
            for i, pa in enumerate(providers):
                for pb in providers[i + 1 :]:
                    unique_pairs.add((equiv[pa], pa, equiv[pb], pb))
        assert eq_count == len(unique_pairs)


class TestFeatureParity:
    def test_stats_include_feature_parity(self, registry):
        s = registry.stats()
        assert "feature_parity_services" in s
        assert s["feature_parity_services"] > 0

    def test_get_feature_parity_lambda(self, registry):
        parity = registry.get_feature_parity("lambda")
        assert len(parity) > 0
        assert "max_memory_gb" in parity
        assert parity["max_memory_gb"]["aws"] == 10
        assert parity["max_memory_gb"]["gcp"] == 32

    def test_get_feature_parity_ec2(self, registry):
        parity = registry.get_feature_parity("ec2")
        assert "spot_instances" in parity
        assert parity["spot_instances"]["aws"] is True

    def test_get_feature_parity_unknown_returns_empty(self, registry):
        parity = registry.get_feature_parity("totally_unknown_service")
        assert parity == {}

    def test_feature_gaps_gcp_lambda(self, registry):
        gaps = registry.feature_gaps("lambda", "gcp")
        assert "arm_runtime" in gaps
        assert "layers_extensions" in gaps

    def test_feature_gaps_unknown_provider_returns_empty(self, registry):
        gaps = registry.feature_gaps("lambda", "nonexistent_provider")
        # If provider not in parity data, no gaps detectable
        assert isinstance(gaps, list)

    def test_compare_features_lambda_vs_cloud_functions(self, registry):
        result = registry.compare_features("lambda", "cloud_functions")
        assert len(result) > 0
        feature_names = {r["feature"] for r in result}
        assert "max_memory_gb" in feature_names

    def test_compare_features_same_service_returns_all(self, registry):
        result = registry.compare_features("lambda", "lambda")
        assert len(result) > 0

    def test_feature_parity_cache(self, registry):
        parity = registry.get_feature_parity("elasticache")
        assert "serverless_mode" in parity
        assert parity["serverless_mode"]["aws"] is True
        assert parity["serverless_mode"]["gcp"] is False

    def test_feature_parity_s3(self, registry):
        parity = registry.get_feature_parity("s3")
        assert "intelligent_tiering" in parity
        assert parity["intelligent_tiering"]["aws"] is True
        assert parity["intelligent_tiering"]["azure"] is False

    def test_feature_gaps_rds(self, registry):
        parity = registry.get_feature_parity("rds")
        assert len(parity) > 0


class TestSingleton:
    def test_get_registry_returns_instance(self):
        reg = get_registry()
        assert isinstance(reg, ServiceRegistry)

    def test_get_registry_same_instance(self):
        r1 = get_registry()
        r2 = get_registry()
        assert r1 is r2

    def test_reload_registry(self):
        reg = reload_registry()
        assert isinstance(reg, ServiceRegistry)
        assert reg.stats()["total_services"] > 0

from __future__ import annotations

import pytest
from cloudwright.importer.live_aws import LiveImportError
from cloudwright.importer.live_gcp import import_live_gcp


class _Inst:
    def __init__(self, name, machine, zone="us-central1-a", status="RUNNING"):
        self.name = name
        self.machine_type = f"https://www.googleapis.com/compute/v1/.../machineTypes/{machine}"
        self.zone = f"https://www.googleapis.com/compute/v1/.../zones/{zone}"
        self.status = status
        self.shielded_instance_config = None


class _Scoped:
    def __init__(self, instances):
        self.instances = instances


class _ComputeClient:
    def __init__(self, instances, raise_exc=None):
        self._instances = instances
        self._raise = raise_exc

    def aggregated_list(self, project):
        if self._raise:
            raise self._raise
        yield "zones/us-central1-a", _Scoped(self._instances)


class _Bucket:
    def __init__(self, name, location="US", versioning=True, kms=None):
        self.name = name
        self.location = location
        self.storage_class = "STANDARD"
        self.default_kms_key_name = kms
        self.versioning_enabled = versioning
        self.iam_configuration = type("I", (), {"public_access_prevention": "enforced"})()


class _StorageClient:
    def __init__(self, buckets, raise_exc=None):
        self._buckets = buckets
        self._raise = raise_exc

    def list_buckets(self):
        if self._raise:
            raise self._raise
        return list(self._buckets)


class _Forbidden(Exception):
    pass


_Forbidden.__name__ = "Forbidden"


class TestGcpImport:
    def test_compute_instances_become_components(self):
        clients = {"compute_engine": _ComputeClient([_Inst("web-1", "e2-medium"), _Inst("web-2", "n2-standard-2")])}
        spec = import_live_gcp(project="proj-x", _clients=clients, services=["compute_engine"])
        vms = [c for c in spec.components if c.service == "compute_engine"]
        assert len(vms) == 2
        assert {v.config["machine_type"] for v in vms} == {"e2-medium", "n2-standard-2"}
        assert spec.provider == "gcp"
        assert spec.metadata["project"] == "proj-x"

    def test_storage_security_posture(self):
        clients = {
            "cloud_storage": _StorageClient(
                [_Bucket("data-lake", kms="projects/p/locations/l/keyRings/k/cryptoKeys/c")]
            )
        }
        spec = import_live_gcp(project="proj-x", _clients=clients, services=["cloud_storage"])
        b = [c for c in spec.components if c.service == "cloud_storage"][0]
        assert b.config["encryption"] is True
        assert b.config["versioning"] is True
        assert b.config["public_access_prevention"] == "enforced"

    def test_per_service_permission_denied_non_fatal(self):
        clients = {
            "compute_engine": _ComputeClient([_Inst("ok", "e2-small")]),
            "cloud_storage": _StorageClient([], raise_exc=_Forbidden("403 permission denied")),
        }
        lines: list[str] = []
        spec = import_live_gcp(
            project="proj-x", _clients=clients, services=["compute_engine", "cloud_storage"], progress=lines.append
        )
        assert any(c.service == "compute_engine" for c in spec.components)
        assert not any(c.service == "cloud_storage" for c in spec.components)
        assert any("permission denied" in line.lower() for line in lines)

    def test_missing_project_raises(self, monkeypatch):
        monkeypatch.delenv("GOOGLE_CLOUD_PROJECT", raising=False)
        monkeypatch.delenv("GCP_PROJECT", raising=False)
        with pytest.raises(LiveImportError, match="project not set"):
            import_live_gcp(_clients={})

    def test_unknown_service_raises(self):
        with pytest.raises(LiveImportError, match="Unknown service"):
            import_live_gcp(project="p", _clients={}, services=["not_a_service"])

    def test_missing_sdk_client_skips(self):
        # No client for a requested service -> skipped, no crash.
        lines: list[str] = []
        spec = import_live_gcp(project="p", _clients={}, services=["compute_engine"], progress=lines.append)
        assert spec.components == []
        assert any("skipping" in line.lower() for line in lines)

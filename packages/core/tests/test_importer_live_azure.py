from __future__ import annotations

import pytest
from cloudwright.importer.live_aws import LiveImportError
from cloudwright.importer.live_azure import import_live_azure


class _VM:
    def __init__(self, name, size, location="eastus"):
        self.name = name
        self.location = location
        self.hardware_profile = type("HW", (), {"vm_size": size})()
        self.storage_profile = type("SP", (), {"os_disk": type("OD", (), {"os_type": "Linux"})()})()


class _Acct:
    def __init__(self, name, public=False):
        self.name = name
        self.location = "eastus"
        self.sku = type("S", (), {"name": "Standard_LRS"})()
        self.encryption = object()
        self.enable_https_traffic_only = True
        self.allow_blob_public_access = public
        self.minimum_tls_version = "TLS1_2"


class _Coll:
    def __init__(self, items, raise_exc=None):
        self._items = items
        self._raise = raise_exc

    def list_all(self):
        return self._iter()

    def list(self):
        return self._iter()

    def _iter(self):
        if self._raise:
            raise self._raise
        yield from self._items


class _Compute:
    def __init__(self, vms, raise_exc=None):
        self.virtual_machines = _Coll(vms, raise_exc)


class _Storage:
    def __init__(self, accts, raise_exc=None):
        self.storage_accounts = _Coll(accts, raise_exc)


class _AuthFailed(Exception):
    pass


class TestAzureImport:
    def test_vms_become_components(self):
        clients = {"virtual_machines": _Compute([_VM("api-1", "Standard_D2s_v3"), _VM("api-2", "Standard_B2s")])}
        spec = import_live_azure(subscription="sub-1", _clients=clients, services=["virtual_machines"])
        vms = [c for c in spec.components if c.service == "virtual_machines"]
        assert len(vms) == 2
        assert {v.config["vm_size"] for v in vms} == {"Standard_D2s_v3", "Standard_B2s"}
        assert spec.provider == "azure"
        assert spec.metadata["subscription"] == "sub-1"

    def test_storage_security_posture(self):
        clients = {"blob_storage": _Storage([_Acct("logs", public=True)])}
        spec = import_live_azure(subscription="sub-1", _clients=clients, services=["blob_storage"])
        acct = [c for c in spec.components if c.service == "blob_storage"][0]
        assert acct.config["encryption"] is True
        assert acct.config["https_only"] is True
        assert acct.config["allow_public_blob"] is True
        assert acct.config["min_tls_version"] == "TLS1_2"

    def test_per_service_permission_denied_non_fatal(self):
        clients = {
            "virtual_machines": _Compute([_VM("ok", "Standard_B1s")]),
            "blob_storage": _Storage([], raise_exc=_AuthFailed("AuthorizationFailed: forbidden")),
        }
        lines: list[str] = []
        spec = import_live_azure(
            subscription="sub-1",
            _clients=clients,
            services=["virtual_machines", "blob_storage"],
            progress=lines.append,
        )
        assert any(c.service == "virtual_machines" for c in spec.components)
        assert not any(c.service == "blob_storage" for c in spec.components)
        assert any("permission denied" in line.lower() for line in lines)

    def test_missing_subscription_raises(self, monkeypatch):
        monkeypatch.delenv("AZURE_SUBSCRIPTION_ID", raising=False)
        with pytest.raises(LiveImportError, match="subscription not set"):
            import_live_azure(_clients={})

    def test_unknown_service_raises(self):
        with pytest.raises(LiveImportError, match="Unknown service"):
            import_live_azure(subscription="s", _clients={}, services=["nope"])

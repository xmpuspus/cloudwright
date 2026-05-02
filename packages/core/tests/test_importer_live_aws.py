"""Tests for the live AWS importer (cloudwright.importer.live_aws).

All tests hand-mock boto3 — no `moto` dependency, no live network calls.
"""

from __future__ import annotations

import pytest
from cloudwright.importer.live_aws import (
    SUPPORTED_SERVICES,
    LiveImportError,
    import_live_aws,
)

# Helpers
#
# A FakeClient supports just enough of the boto3 surface to mimic each service:
#  - get_paginator(name) -> object with .paginate(**kw) yielding pre-canned pages
#  - direct method calls returning pre-canned dicts
#  - selected methods can raise pre-set exceptions (for permission-denied tests)


class _FakePaginator:
    def __init__(self, pages):
        self._pages = list(pages)

    def paginate(self, **_kwargs):
        for page in self._pages:
            yield page


class _FakeClient:
    def __init__(self, paginators=None, methods=None, exceptions=None):
        self._paginators = paginators or {}
        self._methods = methods or {}
        self._exceptions = exceptions or {}

    def get_paginator(self, name):
        if name in self._exceptions:
            raise self._exceptions[name]
        if name not in self._paginators:
            raise AssertionError(f"No paginator stub for {name!r}")
        return _FakePaginator(self._paginators[name])

    def __getattr__(self, name):
        if name in self._exceptions:
            exc = self._exceptions[name]

            def _raise(**_kw):
                raise exc

            return _raise
        if name in self._methods:
            value = self._methods[name]

            def _call(**_kw):
                return value

            return _call
        raise AttributeError(f"FakeClient has no method {name!r}")


class _FakeSession:
    """Mimics ``boto3.Session`` enough for the importer."""

    def __init__(self, clients, has_credentials=True):
        self._clients = clients
        self._has_credentials = has_credentials
        # Tracks which services were asked for (for --services scoping tests).
        self.requested_clients: list[str] = []

    def client(self, name):
        self.requested_clients.append(name)
        if name not in self._clients:
            # Default: a fake client that raises AccessDenied for everything.
            return _AccessDeniedClient()
        return self._clients[name]

    def get_credentials(self):
        if not self._has_credentials:
            return None

        class _Creds:
            access_key = "AKIA-TEST"
            secret_key = "secret"

        return _Creds()


class _AccessDeniedException(Exception):
    pass


_AccessDeniedException.__name__ = "AccessDeniedException"


class _AccessDeniedClient:
    def get_paginator(self, _name):
        raise _AccessDeniedException("User: arn:aws:... is not authorized to perform: ...")

    def __getattr__(self, _name):
        def _raise(**_kw):
            raise _AccessDeniedException("not authorized")

        return _raise


def _patch_boto3(monkeypatch, fake_session):
    """Replace `boto3.Session` so import_live_aws sees the fake."""
    import sys
    import types

    # Build minimal boto3 + botocore.exceptions stand-ins.
    fake_boto3 = types.ModuleType("boto3")
    fake_boto3.Session = lambda **_kwargs: fake_session

    fake_botocore = types.ModuleType("botocore")
    fake_botocore_exceptions = types.ModuleType("botocore.exceptions")

    class _NoCredentialsError(Exception):
        pass

    class _PartialCredentialsError(Exception):
        pass

    fake_botocore_exceptions.NoCredentialsError = _NoCredentialsError
    fake_botocore_exceptions.PartialCredentialsError = _PartialCredentialsError
    fake_botocore.exceptions = fake_botocore_exceptions

    monkeypatch.setitem(sys.modules, "boto3", fake_boto3)
    monkeypatch.setitem(sys.modules, "botocore", fake_botocore)
    monkeypatch.setitem(sys.modules, "botocore.exceptions", fake_botocore_exceptions)
    return fake_botocore_exceptions


def _patch_boto3_no_creds(monkeypatch):
    import sys
    import types

    fake_boto3 = types.ModuleType("boto3")

    fake_botocore = types.ModuleType("botocore")
    fake_botocore_exceptions = types.ModuleType("botocore.exceptions")

    class _NoCredentialsError(Exception):
        pass

    class _PartialCredentialsError(Exception):
        pass

    fake_botocore_exceptions.NoCredentialsError = _NoCredentialsError
    fake_botocore_exceptions.PartialCredentialsError = _PartialCredentialsError
    fake_botocore.exceptions = fake_botocore_exceptions

    def _session(**_kw):
        raise _NoCredentialsError("Unable to locate credentials")

    fake_boto3.Session = _session

    monkeypatch.setitem(sys.modules, "boto3", fake_boto3)
    monkeypatch.setitem(sys.modules, "botocore", fake_botocore)
    monkeypatch.setitem(sys.modules, "botocore.exceptions", fake_botocore_exceptions)


# Per-scanner fake-client builders


def _ec2_client_with_instance(instance_type="m5.large", count=3):
    instances = [
        {
            "InstanceId": f"i-fake{i:04d}",
            "InstanceType": instance_type,
            "State": {"Name": "running"},
            "VpcId": "vpc-abc123",
            "SubnetId": "subnet-xyz",
            "Placement": {"AvailabilityZone": "us-east-1a"},
            "MetadataOptions": {"HttpTokens": "required"},
        }
        for i in range(count)
    ]
    return _FakeClient(
        paginators={
            "describe_instances": [{"Reservations": [{"Instances": instances}]}],
        },
        methods={
            "describe_vpcs": {"Vpcs": []},
            "describe_subnets": {"Subnets": []},
            "describe_security_groups": {"SecurityGroups": []},
        },
    )


def _s3_client(buckets):
    methods = {"list_buckets": {"Buckets": [{"Name": b["name"]} for b in buckets]}}

    enc_results: dict[str, dict] = {}
    ver_results: dict[str, dict] = {}
    pab_results: dict[str, dict] = {}
    for b in buckets:
        if b.get("encryption", False):
            enc_results[b["name"]] = {
                "ServerSideEncryptionConfiguration": {
                    "Rules": [{"ApplyServerSideEncryptionByDefault": {"SSEAlgorithm": "AES256"}}]
                }
            }
        else:
            enc_results[b["name"]] = {"ServerSideEncryptionConfiguration": {"Rules": []}}
        ver_results[b["name"]] = {"Status": "Enabled" if b.get("versioning", False) else "Suspended"}
        pab_results[b["name"]] = {
            "PublicAccessBlockConfiguration": {
                "BlockPublicAcls": b.get("public_block", False),
                "BlockPublicPolicy": b.get("public_block", False),
                "IgnorePublicAcls": b.get("public_block", False),
                "RestrictPublicBuckets": b.get("public_block", False),
            }
        }

    class _S3Client(_FakeClient):
        def get_bucket_encryption(self, *, Bucket):
            return enc_results[Bucket]

        def get_bucket_versioning(self, *, Bucket):
            return ver_results[Bucket]

        def get_public_access_block(self, *, Bucket):
            return pab_results[Bucket]

    return _S3Client(methods=methods)


def _rds_client():
    return _FakeClient(
        paginators={
            "describe_db_instances": [
                {
                    "DBInstances": [
                        {
                            "DBInstanceIdentifier": "prod-db",
                            "Engine": "postgres",
                            "EngineVersion": "16.1",
                            "DBInstanceClass": "db.t3.medium",
                            "MultiAZ": True,
                            "StorageEncrypted": True,
                            "BackupRetentionPeriod": 7,
                            "PubliclyAccessible": False,
                        }
                    ]
                }
            ]
        }
    )


# Tests


def test_ec2_instance_produces_component(monkeypatch):
    """An EC2 instance with InstanceType=m5.large surfaces in the spec."""
    session = _FakeSession({"ec2": _ec2_client_with_instance("m5.large", count=3)})
    _patch_boto3(monkeypatch, session)

    spec = import_live_aws(region="us-east-1", services=["ec2"])
    ec2 = [c for c in spec.components if c.service == "ec2"]
    assert len(ec2) == 3
    assert all(c.config.get("instance_type") == "m5.large" for c in ec2)
    assert all(c.config.get("count") == 1 for c in ec2)
    assert all(c.config.get("http_tokens") == "required" for c in ec2)
    assert spec.provider == "aws"
    assert spec.region == "us-east-1"


def test_unencrypted_s3_bucket_surfaces_encryption_false(monkeypatch):
    """An unencrypted S3 bucket produces config={encryption: false} so the gap is visible."""
    session = _FakeSession(
        {
            "s3": _s3_client(
                [
                    {"name": "secret-leak", "encryption": False, "versioning": False, "public_block": False},
                    {"name": "good-bucket", "encryption": True, "versioning": True, "public_block": True},
                ]
            )
        }
    )
    _patch_boto3(monkeypatch, session)

    spec = import_live_aws(region="us-east-1", services=["s3"])
    s3 = {c.label: c for c in spec.components if c.service == "s3"}
    assert s3["S3 secret-leak"].config["encryption"] is False
    assert s3["S3 secret-leak"].config["versioning"] is False
    assert s3["S3 secret-leak"].config["public_access_block"] is False
    assert s3["S3 good-bucket"].config["encryption"] is True
    assert s3["S3 good-bucket"].config["versioning"] is True
    assert s3["S3 good-bucket"].config["public_access_block"] is True


def test_no_credentials_raises_clean_error(monkeypatch):
    """Missing AWS credentials produce LiveImportError with a clear message."""
    _patch_boto3_no_creds(monkeypatch)

    with pytest.raises(LiveImportError) as exc_info:
        import_live_aws(region="us-east-1", services=["ec2"])

    msg = str(exc_info.value).lower()
    assert "credentials" in msg
    assert "aws configure" in msg or "aws_profile" in msg


def test_per_service_permission_denied_is_non_fatal(monkeypatch):
    """If one service permission-denies, other services still get scanned."""
    # ec2 returns a real instance, rds returns AccessDenied.
    rds_denied = _FakeClient(exceptions={"describe_db_instances": _AccessDeniedException("denied")})
    session = _FakeSession({"ec2": _ec2_client_with_instance("t3.small", 1), "rds": rds_denied})
    _patch_boto3(monkeypatch, session)

    progress_lines: list[str] = []
    spec = import_live_aws(region="us-east-1", services=["ec2", "rds"], progress=progress_lines.append)

    # EC2 still imported.
    assert any(c.service == "ec2" for c in spec.components)
    # RDS skipped, not crashed.
    assert not any(c.service == "rds" for c in spec.components)
    # Progress mentions permission-denied.
    assert any("permission denied" in line.lower() for line in progress_lines)


def test_services_filter_only_scans_listed(monkeypatch):
    """--services s3,rds only invokes those clients, not all 13."""
    s3 = _s3_client([{"name": "alpha", "encryption": True, "versioning": True, "public_block": True}])
    rds = _rds_client()
    session = _FakeSession({"s3": s3, "rds": rds})
    _patch_boto3(monkeypatch, session)

    spec = import_live_aws(region="us-west-2", services=["s3", "rds"])

    services_seen = {c.service for c in spec.components}
    assert services_seen == {"s3", "rds"}
    # No EC2/Lambda/CloudFront clients ever requested.
    assert "ec2" not in session.requested_clients
    assert "lambda" not in session.requested_clients
    assert "cloudfront" not in session.requested_clients
    # We did request s3 + rds.
    assert "s3" in session.requested_clients
    assert "rds" in session.requested_clients


def test_unknown_service_in_filter_raises(monkeypatch):
    session = _FakeSession({})
    _patch_boto3(monkeypatch, session)

    with pytest.raises(LiveImportError):
        import_live_aws(region="us-east-1", services=["ec2", "totally_made_up"])


def test_supported_services_list_is_stable():
    """Sanity: the public ordering is what the CLI advertises."""
    expected = (
        "ec2",
        "vpc",
        "rds",
        "s3",
        "lambda",
        "ecs",
        "eks",
        "dynamodb",
        "alb",
        "cloudfront",
        "sqs",
        "api_gateway",
        "cloudtrail",
    )
    assert SUPPORTED_SERVICES == expected


def test_rds_extracts_security_posture(monkeypatch):
    session = _FakeSession({"rds": _rds_client()})
    _patch_boto3(monkeypatch, session)

    spec = import_live_aws(region="us-east-1", services=["rds"])
    rds = [c for c in spec.components if c.service == "rds"]
    assert len(rds) == 1
    cfg = rds[0].config
    assert cfg["engine"] == "postgres"
    assert cfg["instance_class"] == "db.t3.medium"
    assert cfg["multi_az"] is True
    assert cfg["storage_encrypted"] is True
    assert cfg["backup_retention_period"] == 7
    assert cfg["publicly_accessible"] is False


def test_metadata_records_scan_context(monkeypatch):
    session = _FakeSession({"ec2": _ec2_client_with_instance("t3.small", 1)})
    _patch_boto3(monkeypatch, session)

    spec = import_live_aws(region="eu-west-1", profile="prod", services=["ec2"])
    assert spec.metadata["imported_from"] == "live_aws"
    assert spec.metadata["region"] == "eu-west-1"
    assert spec.metadata["profile"] == "prod"
    assert spec.metadata["services_scanned"] == ["ec2"]
    assert spec.name == "aws-live-eu-west-1"


def test_terminated_ec2_instances_are_skipped(monkeypatch):
    client = _FakeClient(
        paginators={
            "describe_instances": [
                {
                    "Reservations": [
                        {
                            "Instances": [
                                {
                                    "InstanceId": "i-running",
                                    "InstanceType": "t3.micro",
                                    "State": {"Name": "running"},
                                    "Placement": {},
                                },
                                {
                                    "InstanceId": "i-dead",
                                    "InstanceType": "t3.micro",
                                    "State": {"Name": "terminated"},
                                    "Placement": {},
                                },
                            ]
                        }
                    ]
                }
            ]
        }
    )
    session = _FakeSession({"ec2": client})
    _patch_boto3(monkeypatch, session)

    spec = import_live_aws(region="us-east-1", services=["ec2"])
    labels = {c.label for c in spec.components if c.service == "ec2"}
    assert "EC2 i-running" in labels
    assert "EC2 i-dead" not in labels

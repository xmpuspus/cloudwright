"""Cloud pricing adapters — fetch live pricing data from provider APIs."""

from __future__ import annotations

import ssl
import urllib.request
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Iterator


def _ssl_context() -> ssl.SSLContext:
    """Create an SSL context using certifi CA bundle (macOS workaround)."""
    try:
        import certifi

        return ssl.create_default_context(cafile=certifi.where())
    except ImportError:
        return ssl.create_default_context()


def urlopen_safe(req: urllib.request.Request, timeout: int = 30) -> bytes:
    """urlopen with certifi SSL — use this instead of raw urllib.request.urlopen."""
    ctx = _ssl_context()
    with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
        return resp.read()


@dataclass
class InstancePrice:
    """Pricing record for a compute instance type."""

    instance_type: str
    region: str
    vcpus: int
    memory_gb: float
    price_per_hour: float
    price_type: str = "on_demand"  # on_demand | reserved_1yr | reserved_3yr | spot
    os: str = "linux"
    storage_desc: str = ""
    network_bandwidth: str = ""


@dataclass
class ManagedServicePrice:
    """Pricing record for a managed service tier."""

    service: str
    tier_name: str
    price_per_hour: float
    price_per_month: float
    description: str = ""
    vcpus: int = 0
    memory_gb: float = 0.0


class PricingAdapter(ABC):
    """Abstract base for cloud pricing data adapters.

    Subclasses fetch live pricing from provider-specific APIs and return
    normalized InstancePrice / ManagedServicePrice records for catalog ingestion.
    """

    provider: str  # "aws" | "gcp" | "azure"

    @abstractmethod
    def fetch_instance_pricing(self, region: str) -> Iterator[InstancePrice]:
        """Yield compute instance prices for the given region."""

    @abstractmethod
    def fetch_managed_service_pricing(self, service: str, region: str) -> list[ManagedServicePrice]:
        """Return pricing tiers for a managed service in the given region."""

    @abstractmethod
    def supported_managed_services(self) -> list[str]:
        """List of managed service keys this adapter can fetch pricing for."""


__all__ = ["InstancePrice", "ManagedServicePrice", "PricingAdapter"]

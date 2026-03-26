"""POST /api/cost."""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import time

from cloudwright import ArchSpec
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

import cloudwright_web.singletons as _singletons
from cloudwright_web.middleware import check_api_key, check_rate_limit

log = logging.getLogger(__name__)
router = APIRouter()


class _SpecCache:
    """Simple TTL cache keyed by spec content hash."""

    def __init__(self, ttl_seconds: int = 3600):
        self._ttl = ttl_seconds
        self._cost_cache: dict[str, tuple[float, object]] = {}
        self._validate_cache: dict[str, tuple[float, object]] = {}

    def _hash(self, spec_dict: dict) -> str:
        key_data = {k: v for k, v in spec_dict.items() if k not in ("cost_estimate", "metadata")}
        return hashlib.sha256(json.dumps(key_data, sort_keys=True).encode()).hexdigest()[:16]

    def get_cost(self, spec_dict: dict):
        h = self._hash(spec_dict)
        if h in self._cost_cache:
            ts, result = self._cost_cache[h]
            if time.time() - ts < self._ttl:
                return result
            del self._cost_cache[h]
        return None

    def set_cost(self, spec_dict: dict, result):
        h = self._hash(spec_dict)
        self._cost_cache[h] = (time.time(), result)
        if len(self._cost_cache) > 100:
            oldest = min(self._cost_cache, key=lambda k: self._cost_cache[k][0])
            del self._cost_cache[oldest]

    def get_validation(self, spec_dict: dict, key_suffix: str = ""):
        h = self._hash(spec_dict) + key_suffix
        if h in self._validate_cache:
            ts, result = self._validate_cache[h]
            if time.time() - ts < self._ttl:
                return result
            del self._validate_cache[h]
        return None

    def set_validation(self, spec_dict: dict, result, key_suffix: str = ""):
        h = self._hash(spec_dict) + key_suffix
        self._validate_cache[h] = (time.time(), result)
        if len(self._validate_cache) > 100:
            oldest = min(self._validate_cache, key=lambda k: self._validate_cache[k][0])
            del self._validate_cache[oldest]


cache = _SpecCache()


class CostRequest(BaseModel):
    spec: dict
    compare_providers: list[str] = Field(default_factory=list)


@router.post("/cost")
async def cost(req: CostRequest, request: Request):
    check_api_key(request)
    if err := check_rate_limit(request):
        return err
    try:
        spec_dict = req.spec
        cached = cache.get_cost(spec_dict)
        if cached is not None:
            result: dict = {"estimate": cached}
            if req.compare_providers:
                spec = ArchSpec.model_validate(spec_dict)
                architect = _singletons.get_architect()
                alternatives = await asyncio.to_thread(architect.compare, spec, req.compare_providers)
                result["alternatives"] = [a.model_dump(exclude_none=True) for a in alternatives]
            return result

        engine = _singletons.get_cost_engine()
        spec = ArchSpec.model_validate(spec_dict)
        estimate = await asyncio.to_thread(engine.estimate, spec)
        cache.set_cost(spec_dict, estimate.model_dump())

        result = {"estimate": estimate.model_dump()}

        if req.compare_providers:
            architect = _singletons.get_architect()
            alternatives = await asyncio.to_thread(architect.compare, spec, req.compare_providers)
            result["alternatives"] = [a.model_dump(exclude_none=True) for a in alternatives]

        return result
    except Exception as e:
        log.exception("Cost endpoint failed")
        raise HTTPException(status_code=500, detail="Internal server error") from e

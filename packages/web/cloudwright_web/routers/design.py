"""POST /api/design, /api/design/stream, /api/modify, /api/modify/stream."""

from __future__ import annotations

import asyncio
import logging

from cloudwright import ArchSpec, Constraints
from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from cloudwright_web.middleware import check_api_key, check_rate_limit, error_response
from cloudwright_web.streaming import sse_event

log = logging.getLogger(__name__)
router = APIRouter()


def _get_architect():
    from cloudwright_web.singletons import get_architect

    return get_architect()


def _get_cost_engine():
    from cloudwright_web.singletons import get_cost_engine

    return get_cost_engine()


class DesignRequest(BaseModel):
    description: str = Field(..., min_length=5, max_length=2000)
    provider: str = "aws"
    region: str = "us-east-1"
    budget_monthly: float | None = None
    compliance: list[str] = Field(default_factory=list)


class ModifyRequest(BaseModel):
    spec: dict
    instruction: str = Field(..., min_length=3, max_length=2000)


@router.post("/design")
async def design(req: DesignRequest, request: Request):
    check_api_key(request)
    if err := check_rate_limit(request):
        return err
    try:
        architect = _get_architect()
        constraints = None
        if req.budget_monthly or req.compliance:
            constraints = Constraints(budget_monthly=req.budget_monthly, compliance=req.compliance)
        try:
            spec = await asyncio.wait_for(
                asyncio.to_thread(architect.design, req.description, constraints), timeout=120
            )
        except asyncio.TimeoutError:
            return error_response("llm_timeout", "Request timed out", "Try a simpler architecture description", 504)
        try:
            cost_estimate = await asyncio.to_thread(_get_cost_engine().estimate, spec)
            spec = spec.model_copy(update={"cost_estimate": cost_estimate})
        except Exception:
            log.warning("Cost estimation failed in design endpoint", exc_info=True)
        return {"spec": spec.model_dump(exclude_none=True), "yaml": spec.to_yaml()}
    except RuntimeError as e:
        if "No LLM provider" in str(e):
            return error_response("missing_api_key", str(e), "Set an LLM provider API key in your environment", 503)
        log.exception("Design endpoint failed")
        return error_response("internal_error", "Internal server error", "Check server logs for details", 500)
    except Exception:
        log.exception("Design endpoint failed")
        return error_response("internal_error", "Internal server error", "Check server logs for details", 500)


@router.post("/design/stream")
async def design_stream(req: DesignRequest, request: Request):
    check_api_key(request)
    if err := check_rate_limit(request):
        return err

    async def event_generator():
        architect = _get_architect()
        constraints = None
        if req.budget_monthly or req.compliance:
            constraints = Constraints(budget_monthly=req.budget_monthly, compliance=req.compliance)

        yield sse_event("generating", message="Generating architecture...")

        try:
            spec = await asyncio.to_thread(architect.design, req.description, constraints)
        except Exception as e:
            yield sse_event("error", message=str(e))
            return

        yield sse_event("generated", spec=spec.model_dump(exclude_none=True), yaml=spec.to_yaml())

        yield sse_event("costing", message="Estimating cost...")
        try:
            cost_estimate = await asyncio.to_thread(_get_cost_engine().estimate, spec)
            spec = spec.model_copy(update={"cost_estimate": cost_estimate})
            yield sse_event("costed", cost_estimate=cost_estimate.model_dump())
        except Exception:
            log.warning("Cost estimation failed in design stream", exc_info=True)
            yield sse_event("costed", cost_estimate=None)

        yield sse_event("validating", message="Running validation...")
        try:
            from cloudwright.validator import Validator

            validator = Validator()
            results = await asyncio.to_thread(validator.validate, spec, well_architected=True)
            checks = results[0].checks if results else []
            passed = sum(1 for c in checks if c.passed)
            yield sse_event("validated", passed=passed, total=len(checks))
        except Exception:
            log.warning("Validation failed in design stream", exc_info=True)
            yield sse_event("validated", passed=None, total=None)

        yield sse_event("done", spec=spec.model_dump(exclude_none=True), yaml=spec.to_yaml())

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.post("/modify")
async def modify(req: ModifyRequest, request: Request):
    check_api_key(request)
    if err := check_rate_limit(request):
        return err
    try:
        architect = _get_architect()
        spec = ArchSpec.model_validate(req.spec)
        try:
            updated = await asyncio.wait_for(asyncio.to_thread(architect.modify, spec, req.instruction), timeout=120)
        except asyncio.TimeoutError:
            return error_response("llm_timeout", "Request timed out", "Try a simpler architecture description", 504)
        return {"spec": updated.model_dump(exclude_none=True), "yaml": updated.to_yaml()}
    except Exception:
        log.exception("Modify endpoint failed")
        return error_response("internal_error", "Internal server error", "Check server logs for details", 500)


@router.post("/modify/stream")
async def modify_stream(req: ModifyRequest, request: Request):
    check_api_key(request)
    if err := check_rate_limit(request):
        return err

    async def event_generator():
        architect = _get_architect()
        spec = ArchSpec.model_validate(req.spec)

        yield sse_event("modifying", message="Applying modifications...")

        try:
            updated = await asyncio.to_thread(architect.modify, spec, req.instruction)
        except Exception as e:
            yield sse_event("error", message=str(e))
            return

        yield sse_event("modified", spec=updated.model_dump(exclude_none=True), yaml=updated.to_yaml())

        yield sse_event("costing", message="Estimating cost...")
        try:
            cost_estimate = await asyncio.to_thread(_get_cost_engine().estimate, updated)
            updated = updated.model_copy(update={"cost_estimate": cost_estimate})
            yield sse_event("costed", cost_estimate=cost_estimate.model_dump())
        except Exception:
            log.warning("Cost estimation failed in modify stream", exc_info=True)
            yield sse_event("costed", cost_estimate=None)

        yield sse_event("done", spec=updated.model_dump(exclude_none=True), yaml=updated.to_yaml())

    return StreamingResponse(event_generator(), media_type="text/event-stream")

"""Read-only migration planning and evidence HTTP endpoints."""

from __future__ import annotations

import logging

from cloudwright.migration import (
    EvidenceEvaluator,
    EvidenceInput,
    MigrationPlanner,
    MigrationProject,
)
from cloudwright.migration.demo import run_demo
from cloudwright.migration.packs import list_packs
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from cloudwright_web.middleware import check_api_key, check_migration_limit, check_rate_limit

log = logging.getLogger(__name__)
router = APIRouter()


class MigrationPlanRequest(BaseModel):
    """Portable project and optional pack override."""

    project: MigrationProject
    pack: str | None = None


class MigrationVerifyRequest(BaseModel):
    """Portable project and evidence used to recompute the acceptance contract."""

    project: MigrationProject
    evidence: EvidenceInput
    pack: str | None = None


@router.get("/migration/packs")
def migration_packs(request: Request):
    """List installed migration domain packs."""
    check_api_key(request)
    if error := check_rate_limit(request):
        return error
    return {"packs": [summary.as_dict() for summary in list_packs()]}


@router.post("/migration/plan")
def migration_plan(req: MigrationPlanRequest, request: Request):
    """Build dependency-ordered waves, economics, and acceptance gates."""
    check_api_key(request)
    if error := check_rate_limit(request):
        return error
    if error := check_migration_limit(req.project):
        return error
    try:
        assessment = MigrationPlanner().plan(req.project, pack_name=req.pack)
        return {"assessment": assessment.as_dict()}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        log.exception("Migration planning endpoint failed")
        raise HTTPException(status_code=500, detail="Internal server error") from exc


@router.post("/migration/verify")
def migration_verify(req: MigrationVerifyRequest, request: Request):
    """Evaluate evidence and return a visible closure decision."""
    check_api_key(request)
    if error := check_rate_limit(request):
        return error
    if error := check_migration_limit(req.project, req.evidence):
        return error
    try:
        assessment = MigrationPlanner().plan(req.project, pack_name=req.pack)
        evidence_pack = EvidenceEvaluator().evaluate(assessment, req.evidence)
        return {"evidence_pack": evidence_pack.as_dict()}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        log.exception("Migration evidence endpoint failed")
        raise HTTPException(status_code=500, detail="Internal server error") from exc


@router.get("/migration/demo")
def migration_demo(request: Request):
    """Run the installed PH telco proof project without external calls."""
    check_api_key(request)
    if error := check_rate_limit(request):
        return error
    try:
        return run_demo("ph_telco").as_dict()
    except Exception as exc:
        log.exception("Migration demo endpoint failed")
        raise HTTPException(status_code=500, detail="Internal server error") from exc

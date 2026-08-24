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
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from cloudwright_web.middleware import check_migration_limit

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
def migration_packs():
    """List installed migration domain packs."""
    return {"packs": [summary.as_dict() for summary in list_packs()]}


@router.post("/migration/plan")
def migration_plan(req: MigrationPlanRequest):
    """Build dependency-ordered waves, economics, and acceptance gates."""
    if error := check_migration_limit(req.project, pack=req.pack):
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
def migration_verify(req: MigrationVerifyRequest):
    """Evaluate evidence and return a visible closure decision."""
    if error := check_migration_limit(req.project, req.evidence, req.pack):
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
def migration_demo():
    """Run the installed PH telco proof project without external calls."""
    try:
        return run_demo("ph_telco").as_dict()
    except Exception as exc:
        log.exception("Migration demo endpoint failed")
        raise HTTPException(status_code=500, detail="Internal server error") from exc

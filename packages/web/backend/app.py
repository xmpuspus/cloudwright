"""FastAPI backend wrapping the Silmaril core package."""

from __future__ import annotations

import traceback
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from silmaril import ArchSpec, Constraints
from silmaril.architect import Architect
from silmaril.catalog import Catalog
from silmaril.cost import CostEngine
from silmaril.differ import Differ
from silmaril.exporter import FORMATS, export_spec
from silmaril.validator import Validator

app = FastAPI(title="Silmaril", version="0.1.0", description="Architecture intelligence for cloud engineers")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Lazy singletons
_architect: Architect | None = None
_catalog: Catalog | None = None
_cost_engine: CostEngine | None = None


def get_architect() -> Architect:
    global _architect
    if _architect is None:
        _architect = Architect()
    return _architect


def get_catalog() -> Catalog:
    global _catalog
    if _catalog is None:
        _catalog = Catalog()
    return _catalog


def get_cost_engine() -> CostEngine:
    global _cost_engine
    if _cost_engine is None:
        _cost_engine = CostEngine()
    return _cost_engine


# --- Request/Response models ---


class DesignRequest(BaseModel):
    description: str = Field(..., min_length=5, max_length=2000)
    provider: str = "aws"
    region: str = "us-east-1"
    budget_monthly: float | None = None
    compliance: list[str] = Field(default_factory=list)


class ModifyRequest(BaseModel):
    spec: dict
    instruction: str = Field(..., min_length=3, max_length=2000)


class ValidateRequest(BaseModel):
    spec: dict
    compliance: list[str] = Field(default_factory=list)
    well_architected: bool = False


class ExportRequest(BaseModel):
    spec: dict
    format: str


class DiffRequest(BaseModel):
    old_spec: dict
    new_spec: dict


class CostRequest(BaseModel):
    spec: dict
    compare_providers: list[str] = Field(default_factory=list)


class CatalogSearchRequest(BaseModel):
    query: str | None = None
    provider: str | None = None
    vcpus: int | None = None
    memory_gb: float | None = None
    max_price_per_hour: float | None = None
    limit: int = 20


class CatalogCompareRequest(BaseModel):
    instance_names: list[str] = Field(..., min_length=2)


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000)
    history: list[ChatMessage] = Field(default_factory=list)


# --- Endpoints ---


@app.get("/api/health")
def health():
    try:
        catalog = get_catalog()
        stats = catalog.get_stats()
        return {"status": "ok", **stats}
    except Exception:
        return {"status": "ok", "note": "catalog not initialized"}


@app.post("/api/design")
def design(req: DesignRequest):
    try:
        architect = get_architect()
        constraints = None
        if req.budget_monthly or req.compliance:
            constraints = Constraints(
                budget_monthly=req.budget_monthly,
                compliance=req.compliance,
            )
        spec = architect.design(req.description, constraints=constraints)
        return {"spec": spec.model_dump(exclude_none=True), "yaml": spec.to_yaml()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/modify")
def modify(req: ModifyRequest):
    try:
        architect = get_architect()
        spec = ArchSpec.model_validate(req.spec)
        updated = architect.modify(spec, req.instruction)
        return {"spec": updated.model_dump(exclude_none=True), "yaml": updated.to_yaml()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/cost")
def cost(req: CostRequest):
    try:
        engine = get_cost_engine()
        spec = ArchSpec.model_validate(req.spec)
        estimate = engine.estimate(spec)

        result = {"estimate": estimate.model_dump()}

        if req.compare_providers:
            architect = get_architect()
            alternatives = architect.compare(spec, req.compare_providers)
            result["alternatives"] = [a.model_dump(exclude_none=True) for a in alternatives]

        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/validate")
def validate(req: ValidateRequest):
    try:
        validator = Validator()
        spec = ArchSpec.model_validate(req.spec)
        frameworks = req.compliance if req.compliance else []
        results = validator.validate(spec, compliance=frameworks or None, well_architected=req.well_architected)
        return {"results": [r.model_dump() for r in results]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/export")
def export(req: ExportRequest):
    try:
        spec = ArchSpec.model_validate(req.spec)
        if req.format not in FORMATS:
            raise HTTPException(
                status_code=400, detail=f"Unknown format: {req.format}. Supported: {', '.join(FORMATS)}"
            )
        content = export_spec(spec, req.format)
        return {"content": content, "format": req.format}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/diff")
def diff(req: DiffRequest):
    try:
        differ = Differ()
        old = ArchSpec.model_validate(req.old_spec)
        new = ArchSpec.model_validate(req.new_spec)
        result = differ.diff(old, new)
        return {"diff": result.model_dump()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/catalog/search")
def catalog_search(req: CatalogSearchRequest):
    try:
        catalog = get_catalog()
        instances = catalog.search(
            query=req.query,
            vcpus=req.vcpus,
            memory_gb=req.memory_gb,
            provider=req.provider,
            max_price_per_hour=req.max_price_per_hour,
            limit=req.limit,
        )
        return {"instances": instances}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/catalog/compare")
def catalog_compare(req: CatalogCompareRequest):
    try:
        catalog = get_catalog()
        result = catalog.compare(*req.instance_names)
        return {"comparison": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/chat")
def chat(req: ChatRequest):
    try:
        architect = get_architect()
        spec = architect.design(req.message)
        return {
            "reply": f"Here's the architecture for: {spec.name}",
            "spec": spec.model_dump(exclude_none=True),
            "yaml": spec.to_yaml(),
        }
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


# Serve frontend static files if they exist
_frontend_dist = Path(__file__).parent.parent / "frontend" / "dist"
if _frontend_dist.exists():
    app.mount("/assets", StaticFiles(directory=str(_frontend_dist / "assets")), name="assets")

    @app.get("/{path:path}")
    def serve_frontend(path: str):
        file_path = _frontend_dist / path
        if file_path.exists() and file_path.is_file():
            return FileResponse(str(file_path))
        return FileResponse(str(_frontend_dist / "index.html"))


def serve(host: str = "0.0.0.0", port: int = 8000):
    """Start the Silmaril web server."""
    import uvicorn

    uvicorn.run(app, host=host, port=port)

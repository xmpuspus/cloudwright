"""FastAPI backend wrapping the Cloudwright core package."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Literal

from cloudwright import ArchSpec, Constraints
from cloudwright.architect import Architect
from cloudwright.catalog import Catalog
from cloudwright.cost import CostEngine
from cloudwright.differ import Differ
from cloudwright.exporter import FORMATS, export_spec
from cloudwright.validator import Validator
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

log = logging.getLogger(__name__)

app = FastAPI(title="Cloudwright", version="0.1.0", description="Architecture intelligence for cloud engineers")

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
    limit: int = Field(default=20, ge=1, le=100)


class CatalogCompareRequest(BaseModel):
    instance_names: list[str] = Field(..., min_length=2)


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000)
    history: list[ChatMessage] = Field(default_factory=list)


# --- Endpoints ---


@app.get("/api/health")
def health():
    try:
        catalog = get_catalog()
        # Quick check: can we search?
        results = catalog.search(query="m5", limit=1)
        return {"status": "ok", "catalog_loaded": True, "sample_count": len(results)}
    except Exception:
        return {"status": "ok", "catalog_loaded": False}


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
        try:
            cost_estimate = get_cost_engine().estimate(spec)
            spec = spec.model_copy(update={"cost_estimate": cost_estimate})
        except Exception:
            pass  # cost is best-effort
        return {"spec": spec.model_dump(exclude_none=True), "yaml": spec.to_yaml()}
    except Exception as e:
        log.exception("Design endpoint failed")
        raise HTTPException(status_code=500, detail="Internal server error") from e


@app.post("/api/modify")
def modify(req: ModifyRequest):
    try:
        architect = get_architect()
        spec = ArchSpec.model_validate(req.spec)
        updated = architect.modify(spec, req.instruction)
        return {"spec": updated.model_dump(exclude_none=True), "yaml": updated.to_yaml()}
    except Exception as e:
        log.exception("Modify endpoint failed")
        raise HTTPException(status_code=500, detail="Internal server error") from e


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
        log.exception("Cost endpoint failed")
        raise HTTPException(status_code=500, detail="Internal server error") from e


@app.post("/api/validate")
def validate(req: ValidateRequest):
    try:
        validator = Validator()
        spec = ArchSpec.model_validate(req.spec)
        frameworks = req.compliance if req.compliance else []
        results = validator.validate(spec, compliance=frameworks or None, well_architected=req.well_architected)
        return {"results": [r.model_dump() for r in results]}
    except Exception as e:
        log.exception("Validate endpoint failed")
        raise HTTPException(status_code=500, detail="Internal server error") from e


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
        log.exception("Export endpoint failed")
        raise HTTPException(status_code=500, detail="Internal server error") from e


@app.post("/api/download")
async def download(request: Request):
    try:
        data = await request.json()
        spec = ArchSpec.model_validate(data["spec"])
        fmt = data.get("format", "terraform")
        if fmt == "yaml":
            content = spec.to_yaml()
            filename = f"{spec.name.lower().replace(' ', '-')}.yaml"
        elif fmt not in FORMATS:
            raise HTTPException(status_code=400, detail=f"Unknown format: {fmt}. Supported: yaml, {', '.join(FORMATS)}")
        else:
            content = export_spec(spec, fmt)
            ext_map = {"terraform": "tf", "cloudformation": "yaml", "mermaid": "mmd", "d2": "d2"}
            ext = ext_map.get(fmt, "txt")
            filename = f"{spec.name.lower().replace(' ', '-')}.{ext}"
        return Response(
            content=content,
            media_type="text/plain",
            headers={"Content-Disposition": f"attachment; filename={filename}"},
        )
    except HTTPException:
        raise
    except Exception as e:
        log.exception("Download endpoint failed")
        raise HTTPException(status_code=500, detail="Internal server error") from e


@app.post("/api/diff")
def diff(req: DiffRequest):
    try:
        differ = Differ()
        old = ArchSpec.model_validate(req.old_spec)
        new = ArchSpec.model_validate(req.new_spec)
        result = differ.diff(old, new)
        return {"diff": result.model_dump()}
    except Exception as e:
        log.exception("Diff endpoint failed")
        raise HTTPException(status_code=500, detail="Internal server error") from e


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
        log.exception("Catalog search endpoint failed")
        raise HTTPException(status_code=500, detail="Internal server error") from e


@app.post("/api/catalog/compare")
def catalog_compare(req: CatalogCompareRequest):
    try:
        catalog = get_catalog()
        result = catalog.compare(*req.instance_names)
        return {"comparison": result}
    except Exception as e:
        log.exception("Catalog compare endpoint failed")
        raise HTTPException(status_code=500, detail="Internal server error") from e


@app.post("/api/diagram")
async def render_diagram(request: Request):
    data = await request.json()
    spec = ArchSpec.model_validate(data["spec"])
    fmt = data.get("format", "svg")
    from cloudwright.exporter.renderer import DiagramRenderer

    renderer = DiagramRenderer()
    if fmt == "png":
        png_data = renderer.render_png(spec)
        return Response(content=png_data, media_type="image/png")
    svg = renderer.render_svg(spec)
    return Response(content=svg, media_type="image/svg+xml")


@app.get("/api/icons/{provider}/{service}.svg")
def get_icon(provider: str, service: str):
    import cloudwright

    icons_dir = Path(cloudwright.__file__).parent / "data" / "icons"
    icon_path = icons_dir / provider / f"{service}.svg"
    if not icon_path.exists():
        raise HTTPException(status_code=404, detail=f"Icon not found: {provider}/{service}")
    # Security: ensure path doesn't escape icons dir
    if not icon_path.resolve().is_relative_to(icons_dir.resolve()):
        raise HTTPException(status_code=404, detail="Invalid path")
    return FileResponse(str(icon_path), media_type="image/svg+xml")


@app.post("/api/chat")
def chat(req: ChatRequest):
    try:
        from cloudwright.architect import ConversationSession

        architect = get_architect()
        session = ConversationSession(llm=architect.llm)

        # Replay history into the session
        for msg in req.history:
            session.history.append({"role": msg.role, "content": msg.content})

        text, spec = session.send(req.message)
        # Fallback: if session didn't extract a spec, try direct design
        if spec is None and not req.history:
            spec = architect.design(req.message)
            text = f"Architecture: {spec.name}"
        result: dict = {"reply": text, "history": session.history}
        if spec:
            result["spec"] = spec.model_dump(exclude_none=True)
            result["yaml"] = spec.to_yaml()
        return result
    except Exception as e:
        log.exception("Chat endpoint failed")
        raise HTTPException(status_code=500, detail="Internal server error") from e


# Serve frontend static files if they exist
_frontend_dist = Path(__file__).parent.parent / "frontend" / "dist"
if _frontend_dist.exists():
    app.mount("/assets", StaticFiles(directory=str(_frontend_dist / "assets")), name="assets")

    @app.get("/{path:path}")
    def serve_frontend(path: str):
        file_path = (_frontend_dist / path).resolve()
        if file_path.is_relative_to(_frontend_dist.resolve()) and file_path.is_file():
            return FileResponse(str(file_path))
        return FileResponse(str(_frontend_dist / "index.html"))


def serve(host: str = "127.0.0.1", port: int = 8000):
    """Start the Cloudwright web server."""
    import uvicorn

    uvicorn.run(app, host=host, port=port)

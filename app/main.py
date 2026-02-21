from __future__ import annotations

import logging
import time
import uuid

from fastapi import FastAPI, File, Header, HTTPException, Query, Request, UploadFile
from fastapi.responses import JSONResponse

from app.config import get_settings
from app.ingest import ingest_pdf, list_ingested_files
from app.logging_setup import RequestContextMiddleware, configure_logging
from app.models import AnalyzeRequest, AnalyzeResponse, HealthResponse
from app.prompts import DEEP_MODULES, MODULES
from app.retrieval import retrieve_context
from app.reviewers import run_module_review, run_triage
from app.scoring import compute_overall

settings = get_settings()
configure_logging(settings.log_level)
logger = logging.getLogger("app")

app = FastAPI(title="System Design Reviewer", version="1.0.0")
app.add_middleware(RequestContextMiddleware)


@app.middleware("http")
async def add_request_id(request: Request, call_next):
    request.state.request_id = str(uuid.uuid4())
    return await call_next(request)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.exception("unhandled_error", extra={"request_id": getattr(request.state, "request_id", "unknown")})
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})


def _ensure_openai_configured() -> None:
    if not settings.openai_api_key:
        raise HTTPException(status_code=400, detail="OPENAI_API_KEY is required for this operation")


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="ok")


@app.post("/ingest")
def ingest(
    request: Request,
    file: UploadFile = File(...),
    collection: str = Query(default="default"),
    x_ingest_token: str | None = Header(default=None),
):
    if x_ingest_token != settings.ingest_token:
        raise HTTPException(status_code=401, detail="Invalid ingest token")
    _ensure_openai_configured()

    start = time.perf_counter()
    result = ingest_pdf(file, collection)
    logger.info(
        "ingest_complete",
        extra={
            "request_id": request.state.request_id,
            "latency_ms": round((time.perf_counter() - start) * 1000, 2),
        },
    )
    return result


@app.get("/files")
def files(collection: str = Query(default="default")):
    return list_ingested_files(collection)


@app.post("/analyze", response_model=AnalyzeResponse)
def analyze(request: Request, payload: AnalyzeRequest):
    _ensure_openai_configured()
    start = time.perf_counter()

    top_k = payload.top_k or settings.default_top_k
    context_items, context_text = retrieve_context(
        collection=payload.collection,
        query=payload.query,
        top_k=top_k,
        file_filter=payload.file_filter,
    )
    if not context_items:
        raise HTTPException(status_code=404, detail="No context found in collection")

    triage = run_triage(context_text=context_text, user_query=payload.query)
    modules: dict = {}

    if payload.mode == "triage":
        modules = {}
    elif payload.mode == "targeted":
        budget = payload.budget_modules or settings.default_budget_modules
        recommended = triage.get("recommended_modules_to_run", [])
        selected = [m for m in recommended if m in MODULES][:budget]
        for module in selected:
            modules[module] = run_module_review(module_name=module, context_text=context_text, user_query=payload.query)
    else:
        for module in DEEP_MODULES[:6]:
            modules[module] = run_module_review(module_name=module, context_text=context_text, user_query=payload.query)

    overall = compute_overall(modules)
    logger.info(
        "analysis_complete",
        extra={
            "request_id": request.state.request_id,
            "latency_ms": round((time.perf_counter() - start) * 1000, 2),
        },
    )

    return AnalyzeResponse(overall=overall, triage=triage, modules=modules)

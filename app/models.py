from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class AnalyzeRequest(BaseModel):
    collection: str = "default"
    query: str = "Review this design for production readiness"
    mode: Literal["triage", "targeted", "deep"] = "triage"
    top_k: int = Field(default=6, ge=1, le=20)
    file_filter: str | None = None
    budget_modules: int = Field(default=3, ge=1, le=9)


class HealthResponse(BaseModel):
    status: str


class AnalyzeResponse(BaseModel):
    overall: dict
    triage: dict
    modules: dict

"""Pydantic schemas for MCP devdiag requests and responses."""

from __future__ import annotations
from typing import List, Optional, Literal, Dict, Any
from pydantic import BaseModel, Field

Severity = Literal["info", "warn", "error"]


class Problem(BaseModel):
    severity: Severity
    code: str
    message: str
    fix: List[str] = Field(default_factory=list)


class Context(BaseModel):
    frontend_origin: Optional[str] = None
    backend_origin: Optional[str] = None
    last_failed_url: Optional[str] = None
    last_error: Optional[str] = None
    env: Dict[str, Any] = Field(default_factory=dict)


class StatusResponse(BaseModel):
    ok: bool
    problems: List[Problem] = Field(default_factory=list)
    context: Context = Field(default_factory=Context)


class TailRequest(BaseModel):
    n: int = 300


class TailResponse(BaseModel):
    lines: List[str]


class EnvStateResponse(BaseModel):
    env: Dict[str, Any]

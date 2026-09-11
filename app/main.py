"""HTTP endpoints for the System Health & Service Monitoring API."""

from datetime import UTC, datetime
from platform import python_version
from time import monotonic

from fastapi import FastAPI
from pydantic import BaseModel

from app.config import settings

STARTED_AT = datetime.now(UTC)
STARTED_MONOTONIC = monotonic()


class ServiceSummary(BaseModel):
    """Common summary returned by the service endpoints."""

    name: str
    version: str
    status: str


class ReadinessResponse(BaseModel):
    """Response used by deployment systems before routing traffic."""

    status: str
    ready: bool
    service: str


class ServiceInfo(BaseModel):
    """Non-sensitive service metadata."""

    name: str
    version: str
    environment: str
    documentation: str


class RuntimeStatus(BaseModel):
    """Runtime data helpful when diagnosing a deployed service."""

    status: str
    service: str
    version: str
    environment: str
    started_at: datetime
    uptime_seconds: int
    python_version: str


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="A small API used as the workload for an AI-assisted CI/CD lab.",
)


@app.get("/", response_model=ServiceSummary, tags=["service"])
def root() -> ServiceSummary:
    """Return a short service summary."""
    return ServiceSummary(
        name=settings.app_name,
        version=settings.app_version,
        status="running",
    )


@app.get("/health", response_model=ServiceSummary, tags=["health"])
def health() -> ServiceSummary:
    """Liveness probe: confirms that this process can answer HTTP requests."""
    return ServiceSummary(
        name=settings.app_name,
        version=settings.app_version,
        status="healthy",
    )


@app.get("/ready", response_model=ReadinessResponse, tags=["health"])
def ready() -> ReadinessResponse:
    """Readiness probe: confirms that the service can receive traffic."""
    return ReadinessResponse(
        status="ready",
        ready=True,
        service=settings.app_name,
    )


@app.get("/info", response_model=ServiceInfo, tags=["service"])
def info() -> ServiceInfo:
    """Return basic non-sensitive application metadata."""
    return ServiceInfo(
        name=settings.app_name,
        version=settings.app_version,
        environment=settings.environment,
        documentation="/docs",
    )


@app.get("/api/v1/status", response_model=RuntimeStatus, tags=["status"])
def status() -> RuntimeStatus:
    """Return structured runtime information for operators and CI/CD checks."""
    return RuntimeStatus(
        status="operational",
        service=settings.app_name,
        version=settings.app_version,
        environment=settings.environment,
        started_at=STARTED_AT,
        uptime_seconds=int(monotonic() - STARTED_MONOTONIC),
        python_version=python_version(),
    )

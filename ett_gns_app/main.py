from __future__ import annotations

import json
import logging
import time
from collections.abc import Awaitable, Callable
from uuid import uuid4

from fastapi import Depends, FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from fastapi.responses import JSONResponse
from kombu import Connection
from opentelemetry import trace
from opentelemetry.trace import SpanKind
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest
from redis import Redis
from sqlalchemy import text
from sqlalchemy.orm import Session
from starlette.responses import Response

from ett_gns_app.api import router
from ett_gns_app.callbacks import router as callback_router
from ett_gns_app.database import engine, get_db
from ett_gns_app.in_app import router as in_app_router
from ett_gns_app.management_api import router as management_router
from ett_gns_app.observability import configure_observability
from ett_gns_app.operations_api import router as operations_router
from ett_gns_app.settings import get_settings

settings = get_settings()
logger = logging.getLogger("gns.api")
REQUESTS = Counter(
    "gns_http_requests_total",
    "HTTP requests",
    ["method", "route", "status"],
)
LATENCY = Histogram(
    "gns_http_request_duration_seconds",
    "HTTP request duration",
    ["method", "route"],
)

app = FastAPI(
    title="ETT Generic Notification Service",
    version="0.2.0",
    description="Multi-tenant notification management and durable runtime API.",
)


def custom_openapi() -> dict[str, object]:
    if app.openapi_schema:
        return app.openapi_schema
    schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )
    components = schema.setdefault("components", {})
    security_schemes = components.setdefault("securitySchemes", {})
    security_schemes["ApplicationBearer"] = {
        "type": "http",
        "scheme": "bearer",
        "bearerFormat": "gns_<prefix>.<secret>",
        "description": "Application credential shown once by the GNS Credentials screen.",
    }
    notifications = schema.get("paths", {}).get("/api/v1/notifications", {})
    if "post" in notifications:
        notifications["post"]["security"] = [{"ApplicationBearer": []}]
    app.openapi_schema = schema
    return app.openapi_schema


app.openapi = custom_openapi  # type: ignore[method-assign]
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=[
        "Authorization",
        "Content-Type",
        "Idempotency-Key",
        "X-Admin-User",
        "X-Admin-Roles",
        "X-Tenant-ID",
        "X-Request-ID",
    ],
)


@app.middleware("http")
async def request_context(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    request_id = request.headers.get("x-request-id") or f"req_{uuid4().hex}"
    request.state.request_id = request_id
    content_length = request.headers.get("content-length")
    if content_length and int(content_length) > settings.max_request_bytes:
        return JSONResponse(
            status_code=413,
            content={
                "error": {
                    "code": "payload_too_large",
                    "message": "Request body exceeds configured limit",
                    "request_id": request_id,
                }
            },
        )
    started = time.perf_counter()
    tracer = trace.get_tracer("gns.api")
    with tracer.start_as_current_span(
        f"{request.method} {request.url.path}",
        kind=SpanKind.SERVER,
        attributes={
            "http.request.method": request.method,
            "url.path": request.url.path,
            "gns.request_id": request_id,
        },
    ) as span:
        response = await call_next(request)
        span.set_attribute("http.response.status_code", response.status_code)
        trace_id = format(span.get_span_context().trace_id, "032x")
    duration = time.perf_counter() - started
    route = request.scope.get("route")
    route_path = getattr(route, "path", "unmatched")
    REQUESTS.labels(request.method, route_path, str(response.status_code)).inc()
    LATENCY.labels(request.method, route_path).observe(duration)
    response.headers["X-Request-ID"] = request_id
    logger.info(
        json.dumps(
            {
                "event": "http_request",
                "request_id": request_id,
                "method": request.method,
                "route": route_path,
                "status": response.status_code,
                "duration_ms": round(duration * 1000, 2),
                "trace_id": trace_id,
            }
        )
    )
    return response


@app.exception_handler(RequestValidationError)
async def validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
    return JSONResponse(
        status_code=422,
        content={
            "error": {
                "code": "validation_error",
                "message": "Request validation failed",
                "details": exc.errors(),
                "request_id": getattr(request.state, "request_id", None),
            }
        },
    )


@app.exception_handler(Exception)
async def unhandled_error(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled request error", extra={"request_id": request.state.request_id})
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": "internal_error",
                "message": "An unexpected error occurred",
                "request_id": request.state.request_id,
            }
        },
    )


@app.get("/health/live", tags=["health"])
def live() -> dict[str, str]:
    return {"status": "live"}


@app.get("/health/ready", tags=["health"])
def ready(db: Session = Depends(get_db)) -> dict[str, str]:
    db.execute(text("SELECT 1"))
    return {"status": "ready", "database": "up"}


@app.get("/health/dependencies", tags=["health"])
def dependencies(db: Session = Depends(get_db)) -> JSONResponse:
    result: dict[str, str] = {}
    try:
        db.execute(text("SELECT 1"))
        result["database"] = "up"
    except Exception:
        result["database"] = "down"
    try:
        result["redis"] = "up" if Redis.from_url(settings.result_backend_url).ping() else "down"
    except Exception:
        result["redis"] = "down"
    try:
        with Connection(settings.broker_url, connect_timeout=2) as connection:
            connection.ensure_connection(max_retries=0)
        result["broker"] = "up"
    except Exception:
        result["broker"] = "down"
    healthy = all(value == "up" for value in result.values())
    return JSONResponse(
        status_code=200 if healthy else 503,
        content={"status": "ready" if healthy else "degraded", **result},
    )


@app.get("/metrics", include_in_schema=False)
def metrics() -> Response:
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


app.include_router(router)
app.include_router(management_router)
app.include_router(callback_router)
app.include_router(operations_router)
app.include_router(in_app_router)
configure_observability(app, engine, settings.environment)

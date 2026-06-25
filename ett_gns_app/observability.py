from __future__ import annotations

from fastapi import FastAPI
from opentelemetry import trace
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.sampling import ParentBased, TraceIdRatioBased
from sqlalchemy.engine import Engine


def configure_observability(app: FastAPI, engine: Engine, environment: str) -> None:
    provider = TracerProvider(
        resource=Resource.create(
            {
                "service.name": "gns-api",
                "deployment.environment": environment,
            }
        ),
        sampler=ParentBased(TraceIdRatioBased(1.0 if environment != "production" else 0.1)),
    )
    if not isinstance(trace.get_tracer_provider(), TracerProvider):
        trace.set_tracer_provider(provider)
    SQLAlchemyInstrumentor().instrument(engine=engine)

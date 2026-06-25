from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from ett_gns_app.models import Application, UsageBucket


class QuotaExceeded(ValueError):
    def __init__(self, bucket_kind: str, limit: int):
        self.bucket_kind = bucket_kind
        self.limit = limit
        super().__init__(f"{bucket_kind} quota of {limit} notifications exceeded")


def bucket_start(now: datetime, kind: str) -> datetime:
    if kind == "minute":
        return now.replace(second=0, microsecond=0)
    return now.replace(hour=0, minute=0, second=0, microsecond=0)


def consume_quota(
    db: Session,
    app: Application,
    channel: str,
    *,
    now: datetime | None = None,
) -> None:
    now = now or datetime.now(UTC)
    limits = {"minute": app.quota_per_minute, "day": app.quota_per_day}
    buckets: list[UsageBucket] = []
    for kind, limit in limits.items():
        start = bucket_start(now, kind)
        usage = db.scalar(
            select(UsageBucket).where(
                UsageBucket.application_id == app.id,
                UsageBucket.bucket_kind == kind,
                UsageBucket.bucket_start == start,
            )
        )
        if usage is None:
            usage = UsageBucket(
                tenant_id=app.tenant_id,
                application_id=app.id,
                channel=channel,
                bucket_kind=kind,
                bucket_start=start,
                count=0,
            )
            db.add(usage)
            db.flush()
        if usage.count >= limit:
            raise QuotaExceeded(kind, limit)
        buckets.append(usage)
    for usage in buckets:
        usage.count += 1

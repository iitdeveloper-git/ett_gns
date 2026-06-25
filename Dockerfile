FROM python:3.12-slim AS builder

ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1
WORKDIR /build
COPY requirements.txt .
RUN python -m venv /opt/venv \
    && /opt/venv/bin/pip install --upgrade pip \
    && /opt/venv/bin/pip install -r requirements.txt

FROM python:3.12-slim AS runtime

ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1
RUN groupadd --system gns && useradd --system --gid gns --home /app gns
WORKDIR /app
COPY --from=builder /opt/venv /opt/venv
COPY --chown=gns:gns . .
USER gns
EXPOSE 5000
CMD ["uvicorn", "ett_gns_app.main:app", "--host", "0.0.0.0", "--port", "5000", "--proxy-headers"]

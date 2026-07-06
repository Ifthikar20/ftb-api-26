FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# curl is required by the compose healthcheck.
RUN apt-get update && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

COPY services/intelligence/requirements.txt /app/requirements.txt
RUN pip install -r requirements.txt

# Code lives under /app/services/... so import paths match the repo
# (services.intelligence.logic works identically in-container and
# in-process from Django).
COPY services/__init__.py /app/services/__init__.py
COPY services/intelligence/ /app/services/intelligence/

RUN addgroup --system appgroup && adduser --system --ingroup appgroup appuser
USER appuser

EXPOSE 8000

CMD ["uvicorn", "services.intelligence.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]

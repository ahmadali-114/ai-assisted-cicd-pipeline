# A small official Python runtime suitable for a containerized API.
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Copy dependency metadata first so Docker can reuse this cached layer when
# only application source code changes.
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Run the service as a dedicated non-root user.
RUN groupadd --system appgroup \
    && useradd --system --gid appgroup --create-home appuser

COPY app ./app
RUN chown -R appuser:appgroup /app

USER appuser

EXPOSE 8000

# Docker reports the container unhealthy if the HTTP health probe fails.
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health')" || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

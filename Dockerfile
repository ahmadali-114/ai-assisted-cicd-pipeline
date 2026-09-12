# Stage 1: install runtime dependencies outside the final application image.
FROM python:3.12-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /build

COPY requirements.txt .

# --prefix keeps dependencies in /install, ready to copy into the runtime image.
RUN python -m pip install --no-cache-dir --upgrade pip \
    && python -m pip install --no-cache-dir --prefix=/install -r requirements.txt


# Stage 2: small runtime image with no package-management tooling.
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Copy only FastAPI/Uvicorn runtime dependencies from the builder stage.
COPY --from=builder /install /usr/local

# pip is required while building an image but not to run this API. Removing it
# avoids shipping pip's vulnerable vendored packages in the runtime container.
RUN rm -rf \
    /usr/local/bin/pip \
    /usr/local/bin/pip3 \
    /usr/local/bin/pip3.12 \
    /usr/local/lib/python3.12/ensurepip \
    /usr/local/lib/python3.12/site-packages/pip \
    /usr/local/lib/python3.12/site-packages/pip-*.dist-info \
    /usr/local/lib/python3.12/site-packages/setuptools \
    /usr/local/lib/python3.12/site-packages/setuptools-*.dist-info

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

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001"]

# System Health & Service Monitoring API

A small FastAPI service used as the application workload for the **AI-Assisted CI/CD Pipeline** portfolio project. The application is intentionally simple: the learning focus is Docker, testing, CI/CD, secure deployments, health checks, rollback, and later AI-assisted incident analysis.

## Features

- Liveness endpoint: `GET /health`
- Readiness endpoint: `GET /ready`
- Service metadata and runtime status endpoints
- Automated endpoint tests with pytest
- Environment-based configuration
- Production-minded Docker image that runs as a non-root user

## Technology stack

- Python 3.11+ (Docker uses Python 3.12)
- FastAPI and Uvicorn
- Pydantic response models
- pytest and httpx
- Docker and Docker Compose

## Project structure

```text
app/
├── __init__.py
├── config.py          # Environment-based settings
└── main.py            # FastAPI endpoints
tests/
├── __init__.py
└── test_health.py     # Endpoint tests
.dockerignore
.env.example
.gitignore
compose.yaml
Dockerfile
requirements.txt
requirements-dev.txt
```

## Local installation

Windows PowerShell:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements-dev.txt
```

Ubuntu:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements-dev.txt
```

Copy `.env.example` to `.env` only if you need to override the default local configuration. Never commit `.env`.

## Run locally

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Open Swagger documentation at [http://localhost:8000/docs](http://localhost:8000/docs).

## Run tests

```bash
pytest
```

## Run with Docker

Build the image:

```bash
docker build -t system-monitor-api:local .
```

Run a container:

```bash
docker run --rm -p 8000:8000 --name system-monitor-api system-monitor-api:local
```

Or use Docker Compose:

```bash
docker compose up --build
```

Stop the Compose stack:

```bash
docker compose down
```

## API endpoints

| Method | Endpoint | Purpose |
| --- | --- | --- |
| GET | `/` | Application summary |
| GET | `/health` | Liveness health check |
| GET | `/ready` | Readiness health check |
| GET | `/info` | Non-sensitive service information |
| GET | `/api/v1/status` | Runtime status information |

## Example requests

```bash
curl http://localhost:8000/
curl http://localhost:8000/health
curl http://localhost:8000/ready
curl http://localhost:8000/info
curl http://localhost:8000/api/v1/status
```

Example health response:

```json
{
  "name": "System Health & Service Monitoring API",
  "version": "1.0.0",
  "status": "healthy"
}
```

## Future DevOps integration

This application will later be connected to GitHub Actions. The planned pipeline will run tests, SonarQube/SonarCloud analysis, Trivy image scanning, Docker image builds, image-registry publishing, and staging deployment to VM1. A later VM2 component will use a local AI model with restricted MCP tools to analyze sanitized CI/CD and application logs. It will not receive unrestricted server access.

# AI-Assisted CI/CD Pipeline for a FastAPI Service

A production-minded DevSecOps lab that builds, scans, publishes, deploys, verifies, and troubleshoots a small FastAPI service. The application is deliberately simple; the project focus is the delivery and operations workflow around it.

## What problem does this solve?

A deployment is not complete merely because a container starts. A reliable delivery system must verify code quality, image security, deployment health, and recovery behaviour. When an incident happens, an AI assistant must receive only approved diagnostic evidence—not unrestricted server access.

This project demonstrates that workflow from commit to verified staging recovery.

## Architecture

```text
Windows development host
        |
        | git push
        v
GitHub repository
        |
        | Jenkins polls main every five minutes
        v
VM1: Ubuntu staging and CI/CD server (private host-only network)
  Jenkins -> pytest -> SonarQube Quality Gate -> Docker build -> Trivy
          -> Docker Hub -> health-checked staging deployment / rollback
        ^
        | restricted SSH snapshot only
        |
VM2: CentOS AI operations server
  local Ollama + localhost-only MCP service -> evidence-based AI advisory report
```

The application, Jenkins, SonarQube, and AI operations service are all lab services on isolated VirtualBox VMs. The local AI API and MCP endpoint are not exposed to the network.

## CI/CD flow

```text
Commit to main
  -> Jenkins checkout
  -> pytest + JUnit + coverage artifact
  -> SonarQube analysis
  -> SonarQube Quality Gate webhook
  -> hardened Docker image build
  -> Trivy HIGH/CRITICAL vulnerability gate
  -> versioned image push to Docker Hub
  -> staging deployment
  -> HTTP health-check retries
  -> persist last healthy release or roll back on failure
```

The pipeline definition is in [Jenkinsfile](Jenkinsfile). The deployment and rollback logic is in [scripts/deploy-staging.sh](scripts/deploy-staging.sh).

## Application workload

The workload is a FastAPI **System Health & Service Monitoring API** with:

| Endpoint | Purpose |
| --- | --- |
| `GET /health` | Liveness health check |
| `GET /ready` | Readiness health check |
| `GET /info` | Non-sensitive service information |
| `GET /api/v1/status` | Runtime status information |

The production Docker image uses a multi-stage build, runs as a non-root user, includes a container health check, and removes build-time package tooling from the runtime image.

## DevSecOps controls

| Control | Implementation |
| --- | --- |
| Automated tests | `pytest`, JUnit XML, and coverage artifact in Jenkins |
| Code quality | Local SonarQube analysis and blocking Quality Gate |
| Image security | Trivy fails the pipeline on fixable HIGH or CRITICAL findings |
| Immutable release identity | Docker image tag is `build-<Jenkins build number>` |
| Registry verification | Staging pulls the Docker Hub image, rather than using the locally built image |
| Safe deployment | Health checks retry before the release is accepted |
| Rollback | The last healthy image repository and tag are persisted for rollback |
| Concurrency protection | Jenkins disables concurrent deployments |
| Secrets | Docker Hub and SonarQube credentials remain in Jenkins, not Git |

## AI-assisted operations design

AI is used for **read-only incident explanation and troubleshooting suggestions**, not for autonomous production changes.

```text
Ollama incident analyzer
  -> MCP client
  -> MCP service bound to 127.0.0.1:8001 only
  -> dedicated VM1 SSH key
  -> aiops-reader account
  -> one root-owned, argument-free diagnostic snapshot command
```

The MCP service exposes one tool: `get_vm1_diagnostic_snapshot`.

The VM1 `aiops-reader` account is intentionally not a member of `sudo` or `docker` groups. Its only allowed privileged action is a fixed, no-argument diagnostic command that returns bounded service status and recent, redacted logs. The corresponding source is in [infra/aiops](infra/aiops).

The analyzer has two outputs:

1. **Automated current-state verdict** — deterministic health signals decide `ACTIVE INCIDENT`, `NO ACTIVE INCIDENT`, or `INSUFFICIENT EVIDENCE`.
2. **AI advisory analysis** — local Ollama summarizes the approved evidence and proposes safe, read-only follow-up commands.

This separation is deliberate: small local models can over-focus on historical warnings. The AI report is never treated as the source of truth.

## Lab validation evidence

The following scenarios were completed in the lab:

- `pytest -q` passed all five API tests.
- Jenkins completed tests, SonarQube Quality Gate, Trivy scan, Docker Hub push, and staging deployment successfully.
- A SonarQube webhook connectivity timeout was diagnosed from logs and corrected using a localhost Docker host-gateway mapping plus a restricted firewall rule.
- A Trivy finding from a pip-vendored dependency was eliminated by changing the Dockerfile to a smaller multi-stage runtime image.
- A deliberately unhealthy deployment triggered the deployment script's rollback to the last healthy image.
- A controlled `docker stop system-monitor-api` incident produced `ACTIVE INCIDENT`; after recovery, the deterministic result returned `NO ACTIVE INCIDENT`.
- A real MCP smoke test successfully called the local MCP server and retrieved the approved VM1 diagnostic snapshot.
- SELinux denied a systemd service running Python from a user home directory; the service was corrected to run from `/opt/aiops` with SELinux still enforcing.

## Repository layout

```text
app/                         FastAPI application
tests/                       pytest tests
Dockerfile                   Hardened multi-stage container image
compose.yaml                 Application deployment definition
Jenkinsfile                  Jenkins declarative pipeline
scripts/deploy-staging.sh    Deploy, health-check, and rollback logic
infra/sonarqube/             Local SonarQube and PostgreSQL stack
infra/aiops/                 Restricted diagnostics, MCP server, and AI analyzer
```

## Run the application locally

```bash
python3 -m venv .venv
source .venv/bin/activate              # Windows: .venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements-dev.txt
pytest -q
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Open Swagger UI at [http://localhost:8000/docs](http://localhost:8000/docs).

To run with Docker:

```bash
docker compose up --build
curl http://127.0.0.1:8000/health
```

## Important security notes

- Do not commit `.env` files, Docker Hub tokens, SonarQube tokens, SSH private keys, or generated service state.
- Keep Ollama (`11434`) and MCP (`8001`) bound to loopback only.
- Do not add the AI operations account to the `docker` or `sudo` group.
- Validate AI recommendations against deterministic health checks and logs before making a change.

## Resume-ready summary

Built an AI-assisted DevSecOps CI/CD pipeline for a containerized FastAPI service using Jenkins, Docker, Docker Hub, SonarQube, Trivy, and local Ollama. Implemented health-checked deployments with rollback, a blocking security and quality gate, and a least-privilege MCP diagnostic service that provides evidence-based incident analysis without granting AI unrestricted server access.

## Future improvements

- Add Prometheus and Grafana metrics and dashboards.
- Add alert routing for failed deployment and health-check events.
- Add a separate production environment with manual approval gates.
- Add integration tests and dependency update automation.

# AI-Assisted CI/CD Pipeline: Complete Project Documentation

This document records the complete implementation of the **AI-Assisted CI/CD Pipeline for a FastAPI Service**. It is written as a portfolio case study and an operational runbook for rebuilding the lab.

For architecture diagrams, component responsibilities, data flows, trust boundaries, and failure handling, see [System Design](SYSTEM_DESIGN.md).

## 1. Project goal

The goal is not only to deploy a web application. The goal is to build a delivery workflow that answers real DevOps questions:

- Does the code pass automated tests?
- Does it meet a code-quality gate?
- Does the container image contain serious known vulnerabilities?
- Is the exact image published to a registry and deployed successfully?
- Does the running service become healthy after deployment?
- Can the previous known-good release be restored automatically?
- Can a local AI assistant inspect approved evidence without receiving unrestricted server access?

The workload is intentionally small: a FastAPI **System Health & Service Monitoring API**. The CI/CD, security, deployment, and operations design is the main project.

## 2. Final architecture

```text
Developer workstation (Windows)
  C:\Project\AI-Assisted CICD Pipeline
       |
       | git commit / git push
       v
GitHub: ahmadali-114/ai-assisted-cicd-pipeline
       |
       | Jenkins polls main every 5 minutes
       v
VM1: Ubuntu Server - Project-CICD - 192.168.1.6
  Jenkins + Docker + Trivy + SonarQube + staging FastAPI service
       |
       | dedicated SSH key, fixed read-only diagnostic command
       v
VM2: CentOS 9 - ai-ops-assistant - 192.168.1.7
  Ollama + qwen2.5:3b + local MCP service + incident analyzer
```

Both VMs use:

- **NAT** adapter for package downloads and GitHub/Docker Hub access.
- **Host-only** adapter for isolated lab communication.
- No service in this lab is intentionally exposed to the public internet.

## 3. Technology stack

| Area | Technology |
| --- | --- |
| Application | Python, FastAPI, Uvicorn, Pydantic |
| Tests | pytest, pytest-cov, httpx |
| Container platform | Docker and Docker Compose |
| CI/CD | Jenkins declarative pipeline |
| Static analysis | SonarQube Community Edition + SonarScanner |
| Image security | Trivy |
| Container registry | Docker Hub |
| AI operations | Ollama with `qwen2.5:3b` |
| AI tool protocol | Model Context Protocol (MCP), Python SDK |
| VM1 OS | Ubuntu Server |
| VM2 OS | CentOS Stream 9 with SELinux enforcing |

## 4. Repository structure

```text
app/                         FastAPI application code
tests/                       API tests
Dockerfile                   Hardened multi-stage image
compose.yaml                 Application deployment definition
Jenkinsfile                  CI/CD pipeline
scripts/deploy-staging.sh    Health-checked deployment and rollback
sonar-project.properties     SonarQube project configuration
infra/sonarqube/             Local SonarQube + PostgreSQL Compose stack
infra/aiops/                 VM1 diagnostics and VM2 MCP/AI components
docs/README.md               This implementation guide
```

## 5. Application design

The FastAPI service provides these routes:

| Route | Purpose |
| --- | --- |
| `GET /` | Application summary |
| `GET /health` | Liveness health check |
| `GET /ready` | Readiness health check |
| `GET /info` | Non-sensitive service metadata |
| `GET /api/v1/status` | Runtime status |

The `/health` endpoint is used by Docker, Jenkins deployment verification, and the AI operations diagnostic snapshot.

Run tests locally:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
pytest -q
```

Expected result:

```text
5 passed
```

## 6. Docker image design

The `Dockerfile` uses a multi-stage build:

1. Builder stage installs Python runtime dependencies into an isolated location.
2. Final image copies only runtime dependencies and application code.
3. Final image runs as a non-root `appuser`.
4. Build-time package tooling is removed from the runtime image.
5. Docker health check calls `http://127.0.0.1:8000/health`.

This design was improved after Trivy identified a HIGH vulnerability in a `pip`-vendored package. The root cause was not application code; it was unnecessary build tooling present in the runtime image. Moving to a minimal runtime stage removed that attack surface.

Build and verify locally:

```bash
docker build -t system-monitor-api:local .
docker run --rm -p 8000:8000 --name system-monitor-api system-monitor-api:local
curl http://127.0.0.1:8000/health
```

## 7. VM1 setup: Ubuntu CI/CD and staging server

VM1 hostname:

```text
Project-CICD
```

Host-only interface is configured through NetworkManager/Netplan and receives:

```text
192.168.1.6
```

Core components installed on VM1:

- Docker Engine and Docker Compose
- Jenkins LTS
- Java runtime required by Jenkins/SonarScanner
- Trivy
- Git, curl, Python virtual environment tools
- SonarQube Community Edition and PostgreSQL through Compose

The application source is cloned on VM1 under:

```text
~/projects/ai-assisted-cicd-pipeline
```

Jenkins runs pipeline jobs and has Docker access through membership in the `docker` group. Docker Hub and SonarQube credentials are configured in Jenkins credentials storage, never committed to Git.

## 8. Jenkins pipeline stages

The pipeline is defined in [`../Jenkinsfile`](../Jenkinsfile).

```text
Checkout
  -> Test
  -> SonarQube Analysis
  -> Quality Gate
  -> Build Docker Image
  -> Scan Docker Image
  -> Push Image to Docker Hub
  -> Deploy to Staging
```

### Checkout

Jenkins uses Pipeline from SCM on the `main` branch. VM1 is private, so GitHub cannot send a public webhook directly to it. Jenkins instead uses:

```text
H/5 * * * *
```

This checks for SCM changes approximately every five minutes.

### Test

The pipeline creates a temporary Python virtual environment, installs development dependencies, runs pytest, publishes JUnit results, and archives `coverage.xml`.

### SonarQube Analysis and Quality Gate

SonarScanner uploads code analysis to the local SonarQube instance. Jenkins then waits for the Quality Gate.

Important lesson: `waitForQualityGate` does not repeatedly poll forever; it expects a webhook from SonarQube. A successful scanner execution does not mean the Jenkins stage will continue unless the webhook can reach Jenkins.

The working SonarQube webhook URL is:

```text
http://host.docker.internal:8080/sonarqube-webhook/
```

Why this is needed:

- SonarQube runs inside Docker on VM1.
- Jenkins runs directly on VM1.
- Calling VM1's host-only address from the SonarQube container timed out.
- `host.docker.internal:host-gateway` was added to the SonarQube service.
- UFW allows the SonarQube Docker subnet to reach Jenkins TCP port `8080`.

### Trivy security gate

Trivy scans each built image for fixable HIGH and CRITICAL vulnerabilities:

```bash
trivy image --scanners vuln --severity HIGH,CRITICAL --ignore-unfixed \
  --exit-code 1 system-monitor-api:build-N
```

Exit code `1` deliberately fails the pipeline. The human must update the dependency or harden the image before a vulnerable image is published.

### Publish and deploy

Jenkins tags each release with the build number:

```text
ahmadalimalik/system-monitor-api:build-N
```

It pushes that image to Docker Hub. Staging then pulls the registry image, rather than deploying the local image that Jenkins built. This verifies the actual distributed artifact.

## 9. Staging deployment and rollback

Deployment logic lives in [`../scripts/deploy-staging.sh`](../scripts/deploy-staging.sh).

The script:

1. Reads the last known-good repository and image tag.
2. Pulls and deploys the requested image.
3. Retries `/health` up to 10 times with a 3-second delay.
4. Writes the release to `last-successful.env` only after health succeeds.
5. Restores the prior image if the new deployment does not become healthy.
6. Exits non-zero after a failed release even if rollback succeeds, so Jenkins marks the release failed.

State location:

```text
/opt/ai-assisted-cicd/state/last-successful.env
```

This file is intentionally owned by Jenkins and not readable by general users. It contains deployment state and should not be manually sourced by an ordinary user.

Check deployed service health:

```bash
curl http://127.0.0.1:8000/health
docker inspect --format='{{.State.Health.Status}}' system-monitor-api
docker compose ps
```

## 10. VM2 setup: local AI operations server

VM2 hostname:

```text
ai-ops-assistant
```

Host-only IP:

```text
192.168.1.7
```

VM2 was converted from GUI mode to CLI-only mode using:

```bash
sudo systemctl set-default multi-user.target
sudo systemctl disable gdm
```

This preserves RAM and CPU for local inference. VM2 was later increased to approximately 7.5 GiB RAM and 5 CPUs for better `qwen2.5:3b` performance.

Ollama is installed as a service and bound to loopback only:

```text
127.0.0.1:11434
```

The selected model is:

```text
qwen2.5:3b
```

This is CPU-only inference; no passthrough GPU is available in the VM.

## 11. Least-privilege AI and MCP design

The project does **not** allow an LLM to execute arbitrary commands on VM1.

### VM1 account boundary

On VM1, a dedicated account is created:

```text
aiops-reader
```

It has:

- an SSH public key from VM2;
- no interactive password access;
- no Docker group membership;
- no general sudo access;
- exactly one passwordless sudo command.

The only allowed command is:

```text
/usr/local/sbin/aiops-diagnostics
```

The script is root-owned, accepts no arguments, limits log output, and redacts common sensitive values. It collects a bounded snapshot of:

- timestamp and hostname;
- CPU/memory/disk state;
- Jenkins and Docker service status;
- running containers;
- application `/health` response;
- recent application logs;
- recent Jenkins logs.

### VM2 MCP server

The local MCP service exposes exactly one tool:

```text
get_vm1_diagnostic_snapshot
```

It runs through the `aiops-mcp.service` systemd unit and binds to:

```text
127.0.0.1:8001/mcp
```

It retrieves the snapshot via the fixed SSH command. It cannot run arbitrary VM1 commands.

The incident analyzer calls the MCP endpoint, not SSH directly:

```text
Ollama analyzer -> MCP client -> localhost MCP service -> restricted SSH -> VM1 snapshot
```

### SELinux lesson

CentOS SELinux initially blocked systemd from launching a Python virtual environment under `/home/test`, producing status `203/EXEC`. The correct fix was not disabling SELinux.

The service runtime was moved to:

```text
/opt/aiops
```

The SSH key and `known_hosts` file were stored under:

```text
/etc/aiops
```

The systemd unit uses `ProtectHome=true`, `NoNewPrivileges=true`, and `ProtectSystem=full`. SELinux remains enforcing.

## 12. Deterministic verdict versus AI advisory

The local model can summarize logs, but it can over-emphasize historical warnings. For example, it repeatedly mentioned old SonarQube timeout messages even when the current application was healthy.

The analyzer therefore produces two separate outputs:

```text
AUTOMATED CURRENT-STATE VERDICT
AI ADVISORY ANALYSIS (validate before making changes)
```

The automated verdict uses direct current evidence:

- Jenkins active/inactive state;
- Docker active/inactive state;
- container health state;
- current API health check result.

Possible verdicts:

```text
ACTIVE INCIDENT
NO ACTIVE INCIDENT
INSUFFICIENT EVIDENCE
```

The AI section is advisory only. It must never be used as authorization to modify infrastructure.

Run an analysis on VM2:

```bash
source ~/projects/ai-assisted-cicd-pipeline/.venv/bin/activate
cd ~/projects/ai-assisted-cicd-pipeline/infra/aiops/vm2

AIOPS_OLLAMA_MODEL=qwen2.5:3b \
AIOPS_OLLAMA_TIMEOUT_SECONDS=420 \
python incident_analyzer.py
```

The response budget is bounded because CPU-only local inference is slower than cloud inference. Ollama is configured to keep the model loaded briefly between requests.

## 13. Controlled incident validation

A controlled incident was performed to prove the workflow.

### Create the incident on VM1

```bash
docker stop system-monitor-api
curl --fail http://127.0.0.1:8000/health || echo 'Expected: staging API is unavailable'
```

Expected condition:

```text
curl: (7) Failed to connect
```

### Detect from VM2

Run the incident analyzer. It returned:

```text
AUTOMATED CURRENT-STATE VERDICT: ACTIVE INCIDENT
```

### Recover on VM1

Because the stopped container was the last healthy release, the immediate recovery was:

```bash
docker start system-monitor-api
curl http://127.0.0.1:8000/health
docker inspect --format='{{.State.Health.Status}}' system-monitor-api
```

### Verify after recovery

Run the analyzer again on VM2. Expected result:

```text
AUTOMATED CURRENT-STATE VERDICT: NO ACTIVE INCIDENT
```

## 14. Important troubleshooting lessons

| Symptom | Root cause | Correct response |
| --- | --- | --- |
| Jenkins Quality Gate timed out | SonarQube webhook could not reach Jenkins from Docker | Configure Docker host gateway and restricted firewall access; do not merely increase timeout |
| Trivy reported `msgpack`/`pip` vulnerability | Build tooling existed in runtime image | Use a multi-stage Docker build and remove unused runtime tooling |
| `docker compose up` name conflict during manual recovery | Deployment state file was protected; Compose used default image/tag | Do not bypass protected state casually; start the known stopped container or use Jenkins deployment workflow |
| `sudo source ...` failed | `source` is a shell built-in, not a program | Use an appropriate root shell only when authorized; do not expose protected deployment state |
| MCP systemd status `203/EXEC` | SELinux denied systemd reading executable under user home | Move service files to `/opt`, use `/etc` for secrets, keep SELinux enforcing |
| Ollama request timed out | 3B model generated slowly on CPU with long logs | Bound generated tokens and raise the client timeout reasonably |
| AI discussed old SonarQube warnings | Small local model treated historical logs as current evidence | Keep deterministic health verdict separate from advisory LLM output |

## 15. Daily operating commands

### VM1 service checks

```bash
systemctl status jenkins --no-pager
docker compose ps
curl http://127.0.0.1:8000/health
cd ~/projects/ai-assisted-cicd-pipeline/infra/sonarqube && docker compose ps
```

### VM2 service checks

```bash
systemctl status ollama --no-pager
sudo systemctl status aiops-mcp --no-pager
ollama ps
sudo ss -ltnp | grep -E ':11434|:8001'
```

Expected local-only listeners:

```text
127.0.0.1:11434  Ollama
127.0.0.1:8001   MCP service
```

### MCP smoke test

```bash
source ~/projects/ai-assisted-cicd-pipeline/.venv/bin/activate
cd ~/projects/ai-assisted-cicd-pipeline/infra/aiops/vm2
python mcp_smoke_test.py
```

Expected first line:

```text
MCP tool call: SUCCESS
```

## 16. Security rules

- Never commit `.env` files, tokens, passwords, private SSH keys, or Docker Hub credentials.
- Do not expose Jenkins, SonarQube, Ollama, or MCP directly to the public internet in this lab.
- Keep Ollama and MCP on loopback addresses only.
- Do not give `aiops-reader` Docker membership or broad `sudo` access.
- Treat local model output as recommendations, not as an authority.
- Validate every suggested change using current health checks, Jenkins output, and logs.

## 17. Resume and LinkedIn summary

> Built an AI-assisted DevSecOps CI/CD pipeline for a containerized FastAPI service using Jenkins, Docker, Docker Hub, SonarQube, Trivy, and local Ollama. Implemented automated tests, quality and vulnerability gates, immutable image releases, health-checked staging deployment with rollback, and a least-privilege MCP diagnostic service for evidence-based incident analysis without unrestricted server access.

## 18. Future improvements

- Add Prometheus metrics and Grafana dashboards.
- Add Alertmanager notifications for failed deployments and unhealthy services.
- Add a separate production environment with manual approval gates.
- Add integration tests and dependency automation.
- Add signed container images and SBOM generation.
- Replace SCM polling with a secure reachable webhook/reverse-proxy design in a real hosted environment.

# Ticketing Application

A Flask ticketing application for browsing events, selecting seats, placing
temporary holds, checking out, and receiving digital tickets.

## Project status

This repository is currently a project scaffold. The folders and placeholder
files are ready for the team, while the Flask application, database models,
API routes, and deployment files still need to be implemented.

## Repository structure

```text
ticketing-app/
|-- app/                         # Application code and frontend assets
|   |-- jobs/                    # Background tasks
|   |-- models/                  # Database models
|   |-- routes/                  # Page and API routes
|   |-- services/                # Booking and payment business logic
|   |-- static/                  # CSS, JavaScript, and images
|   |   |-- css/
|   |   |-- images/
|   |   `-- js/
|   `-- templates/               # Server-rendered HTML
|       `-- index-prototype.html # Current UI prototype
|
|-- tests/                       # Automated tests
|   |-- unit/                    # Individual functions and services
|   |-- integration/             # API and database interactions
|   |-- load/                    # Performance tests
|   `-- smoke/                   # Basic deployment checks
|
|-- infrastructure/              # Docker, Compose, and Terraform files
|   |-- docker/
|   |-- compose/
|   `-- terraform/
|
|-- scripts/                     # Deployment and pipeline helper scripts
|   |-- infrastructure/
|   `-- pipeline/
|
|-- ci/                          # Jenkins or other CI configuration
|-- monitoring/                  # Prometheus and Grafana configuration
|-- migrations/                  # Database migration history
|-- docs/                        # Architecture, API, deployment, and security docs
|   `-- incidents/               # Incident notes
|-- .github/                     # GitHub collaboration files
|
|-- .env.example                 # Safe environment variable template
|-- .gitignore                   # Files Git must ignore
|-- .dockerignore                # Files Docker must ignore
|-- requirements.txt             # Runtime dependencies
|-- requirements-dev.txt         # Development and test dependencies
`-- README.md                    # This guide
```

### Why are there `.gitkeep` files?

Git does not track empty directories. Each currently empty folder contains a
`.gitkeep` placeholder so the planned structure can appear on GitHub. Replace
the placeholder with a real file when work begins; the `.gitkeep` can then be
removed.

## What belongs where?

| Location | Responsibility |
| --- | --- |
| `app/models/` | Database tables and relationships for users, events, seats, holds, orders, and tickets. |
| `app/routes/` | HTTP endpoints. Routes should validate requests and call services. |
| `app/services/` | Business rules such as seat locking, hold expiration, payments, and ticket generation. |
| `app/jobs/` | Scheduled work, such as releasing expired holds. |
| `app/templates/` | HTML pages rendered by Flask. |
| `app/static/` | Browser assets: CSS, JavaScript, and images. |
| `tests/` | Unit, integration, load, and smoke tests. |
| `infrastructure/` | Container and AWS deployment configuration. |
| `scripts/` | Repeatable deployment, rollback, and verification commands. |
| `monitoring/` | Metrics, dashboards, and alert rules. |
| `docs/` | Shared project decisions and technical documentation. |

## Application flow

```text
Browser or API client
        |
        v
     routes
        |
        v
    services  --->  models  --->  database
        |
        v
 templates and static assets
```

Keep routes thin: receive the request, call a service, and return a response.
Put reusable business logic in services and database definitions in models.

## Local setup

Run these commands from the repository root.

### Windows PowerShell

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
pip install -r requirements-dev.txt
Copy-Item .env.example .env
```

### macOS or Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
pip install -r requirements-dev.txt
cp .env.example .env
```

The application entry point and tests will be runnable after the scaffold is
implemented. The intended commands are:

```bash
python run.py
pytest
```

### Local monitoring stack

The Compose file also includes a local monitoring stack. Start it with:

```bash
docker compose up -d
```

The local UIs are bound to localhost:

| Service | Address | Purpose |
| --- | --- | --- |
| Grafana | http://localhost:3001 | Dashboards for health probes and logs |
| Prometheus | http://localhost:9091 | Scraped probe metrics and alert rules |
| Alertmanager | http://localhost:9093 | Receives and groups Prometheus alerts |

The default Grafana login is `admin` / `change-me-before-sharing`; set
`GRAFANA_ADMIN_USER` and `GRAFANA_ADMIN_PASSWORD` in `.env` first. If these
ports are available, you can set `PROMETHEUS_PORT=9090` and
`GRAFANA_PORT=3000` instead.

At this stage the app does not expose a Prometheus `/metrics` endpoint. The
stack therefore measures the current availability signals:

- Blackbox Exporter probes `/healthz` and records whether the process responds,
  the HTTP status code, and probe duration.
- Blackbox Exporter probes `/readyz` and records whether the app and database
  readiness check returns successfully, the HTTP status code, and probe
  duration.
- Prometheus evaluates alerts for failed probes, slow probes, and down scrape
  targets.
- Grafana queries Prometheus for availability and latency, and Loki for Docker
  container logs. Grafana Alloy forwards the Compose container logs to Loki.

When Person 1 adds `/metrics`, add the app scrape target and application
dashboards for request rate, errors, latency, tickets, and booking metrics.

Do not commit `.env`, passwords, API keys, cloud credentials, Terraform state,
or generated build files. Commit `.env.example` only.

## Team ownership

| Owner | Main responsibility |
| --- | --- |
| Person 1 | `app/`, `migrations/`, runtime dependencies, and application tests |
| Person 2 | `infrastructure/` and infrastructure scripts |
| Person 3 | `tests/`, `ci/`, `monitoring/`, and pipeline scripts |
| Shared | `docs/`, `.github/`, `README.md`, `.gitignore`, `.env.example`, and development dependencies |

## Git workflow

Create a branch for each task and open pull requests against `develop`:

```bash
git switch develop
git pull origin develop
git switch -c feature/short-description

# Make changes, then review them
git status
git add .
git commit -m "Describe the change"
git push -u origin feature/short-description
```

Before merging, run the relevant tests and include the results in the pull
request. Do not commit directly to `develop`.

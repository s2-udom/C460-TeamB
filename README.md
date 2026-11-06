# Ticketing Application

A Flask-based ticketing application for browsing events, selecting seats,
holding seats temporarily, completing checkout, and receiving tickets.

This project uses a small number of top-level folders so the repository stays
easy to navigate while the application is being built. New folders should only
be added when they contain a clear, separate responsibility.

## Simple repository structure

```text
ticketing-app/
├── app/                          # Person 1: Flask application
│   ├── __init__.py               # Creates the Flask application
│   ├── config.py                 # Application configuration
│   ├── extensions.py             # Database and Flask extensions
│   ├── models.py                 # Database models
│   ├── routes.py                 # Page and API routes
│   ├── services.py               # Booking, payment, and ticket logic
│   ├── templates/                # Server-rendered HTML pages
│   └── static/                   # CSS, JavaScript, and images
│
├── tests/                        # Person 3: all automated tests
│   ├── test_app.py               # Basic application tests
│   ├── test_api.py               # API and integration tests
│   ├── test_booking.py           # Seat, hold, and checkout tests
│   └── test_smoke.py             # Basic deployment checks
│
├── infrastructure/               # Person 2: deployment and operations
│   ├── Dockerfile                # Container image definition
│   ├── docker-compose.yml        # Local services
│   ├── terraform/                # AWS infrastructure as code
│   └── monitoring/               # Prometheus and Grafana configuration
│
├── scripts/                      # Small deployment and test helper scripts
├── docs/                         # Architecture, API, deployment, and security docs
├── .github/                      # Pull request templates and CI workflows
│
├── .env.example                  # Safe environment variable template
├── .gitignore                    # Files Git must not track
├── .dockerignore                 # Files excluded from Docker builds
├── requirements.txt              # Runtime Python dependencies
├── requirements-dev.txt          # Development and testing dependencies
├── pytest.ini                    # Pytest configuration
├── run.py                        # Local application entry point
└── README.md                     # Project guide
```

## How the main folders work

| Folder | What belongs there |
| --- | --- |
| `app/` | All Flask application code and frontend assets. Keep request handling in `routes.py`, database definitions in `models.py`, and reusable business rules in `services.py`. |
| `tests/` | Every automated test. Use clear filenames instead of creating a new folder for every test type. |
| `infrastructure/` | Docker, Compose, Terraform, monitoring, and deployment configuration. |
| `scripts/` | Commands that help developers deploy, test, or maintain the project. |
| `docs/` | Shared technical documentation and incident notes. |
| `.github/` | Pull request templates, code ownership, and GitHub Actions workflows. |

If a file becomes very large, it can later be split into a focused module. For
example, `models.py` can become an `app/models/` package when the number of
models justifies it. Starting flat keeps the initial project easier to learn.

## Application flow

```text
Browser or API client
        |
        v
     routes.py  --->  services.py  --->  models.py  --->  database
        |
        v
 templates/ and static/
```

- `routes.py` receives requests and returns HTML pages or API responses.
- `services.py` contains booking, seat-hold, payment, and ticket rules.
- `models.py` describes the database tables and relationships.
- `templates/` contains HTML; `static/` contains CSS, JavaScript, and images.

## Local setup

From the repository root:

```bash
python -m venv .venv

# Windows PowerShell
.venv\Scripts\Activate.ps1

# macOS/Linux
# source .venv/bin/activate

pip install -r requirements.txt
pip install -r requirements-dev.txt
```

Create local configuration from the safe template:

```bash
copy .env.example .env        # Windows
# cp .env.example .env        # macOS/Linux
```

Start the application and run tests:

```bash
python run.py
pytest
```

Do not commit `.env`, passwords, API keys, cloud credentials, Terraform state,
or generated build files. `.env.example` is safe to commit; `.env` is not.

## Team ownership

| Owner | Areas |
| --- | --- |
| Person 1 | `app/`, `requirements.txt`, `run.py`, and database work |
| Person 2 | `infrastructure/` and deployment scripts |
| Person 3 | `tests/`, CI workflows, and monitoring |
| Shared | `docs/`, `.github/`, `README.md`, `.gitignore`, `.env.example`, and `requirements-dev.txt` |

Use a feature branch, keep pull requests focused, and run the relevant tests
before merging into `develop`.


"""App settings, read from environment variables (and a local .env file)."""
import os

from dotenv import load_dotenv

# Load .env before reading any settings. Real environment variables win.
load_dotenv()


def _database_url():
    """Return DATABASE_URL with the psycopg (v3) driver name added.

    Teammates and Docker Compose use plain postgresql:// URLs. SQLAlchemy
    would then look for psycopg2, which we don't install, so swap in the
    driver here instead of making everyone change their URLs.
    """
    url = os.environ.get("DATABASE_URL", "")
    for prefix in ("postgresql://", "postgres://"):
        if url.startswith(prefix):
            return "postgresql+psycopg://" + url[len(prefix):]
    return url


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-only-change-me")
    ENVIRONMENT = os.environ.get("ENVIRONMENT", "local")
    SQLALCHEMY_DATABASE_URI = _database_url()
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    # Fail fast instead of hanging when the database is unreachable,
    # and check pooled connections still work before reusing them.
    SQLALCHEMY_ENGINE_OPTIONS = {
        "connect_args": {"connect_timeout": 3},
        "pool_pre_ping": True,
    }
    HOLD_DURATION_MINUTES = int(os.environ.get("HOLD_DURATION_MINUTES", "10"))
    METRICS_ENABLED = os.environ.get("METRICS_ENABLED", "true").lower() == "true"

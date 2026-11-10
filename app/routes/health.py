"""Health endpoints used by Docker, Jenkins smoke tests and monitoring."""
from flask import Blueprint, jsonify
from sqlalchemy import text

from app.extensions import db

health_bp = Blueprint("health", __name__)


@health_bp.get("/healthz")
def healthz():
    """The app process is up. Does not touch the database."""
    return jsonify(status="ok"), 200


@health_bp.route("/readyz", methods=["GET"])
def ready():
    """The app can reach the database. 503 tells Docker/monitoring it isn't ready."""
    try:
        db.session.execute(text("SELECT 1"))
        return jsonify({"status": "ready"}), 200
    except Exception:
        db.session.rollback()
        return jsonify({"status": "unavailable"}), 503

"""Health endpoints used by Docker, Jenkins smoke tests and monitoring."""
from flask import Blueprint, jsonify

health_bp = Blueprint("health", __name__)


@health_bp.get("/healthz")
def healthz():
    """The app process is up. Does not touch the database."""
    return jsonify(status="ok"), 200

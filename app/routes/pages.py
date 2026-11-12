"""Serves the frontend prototype at the site root."""
import os

from flask import Blueprint, current_app, send_from_directory

pages_bp = Blueprint("pages", __name__)


@pages_bp.get("/")
def index():
    # Sent as a plain file, not rendered as a Jinja template, so any {{ or {% in the page's inline JS is left alone.
    return send_from_directory(os.path.join(current_app.root_path, "templates"), "index-prototype.html")
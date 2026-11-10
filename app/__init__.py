"""Application factory: create_app() builds and returns the Flask app."""
from flask import Flask

from app.config import Config


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    from app.routes.health import health_bp

    app.register_blueprint(health_bp)

    return app

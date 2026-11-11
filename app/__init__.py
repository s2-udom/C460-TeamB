"""Application factory: create_app() builds and returns the Flask app."""
from flask import Flask

from app.config import Config
from app.extensions import db, migrate
from app.metrics import init_metrics


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    db.init_app(app)
    migrate.init_app(app, db)
    init_metrics(app)

    from app import models  # noqa: F401  (registers models with Flask-Migrate)
    from app.routes.events import events_bp
    from app.routes.health import health_bp
    from app.routes.holds import holds_bp

    app.register_blueprint(health_bp)
    app.register_blueprint(events_bp)
    app.register_blueprint(holds_bp)

    from app.cli import seed

    app.cli.add_command(seed)

    return app

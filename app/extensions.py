"""Shared Flask extensions. Created here without an app, then attached in create_app()."""
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()
migrate = Migrate()

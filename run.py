"""Entry point for `flask run` (FLASK_APP=run.py) and `python run.py`.

Gunicorn uses the factory directly: gunicorn "app:create_app()"
"""
from app import create_app

app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)

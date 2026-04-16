"""
run.py — Ponto de entrada principal da aplicação.
Execute: python run.py
"""
import os
from app.app import create_app

env = os.getenv("FLASK_ENV", "development")
app = create_app(env=env)

if __name__ == "__main__":
    app.run(
        host="127.0.0.1",
        port=5000,
        debug=app.config.get("DEBUG", False),
    )

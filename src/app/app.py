"""
app/app.py — Factory da Aplicação Flask.
Princípio SOLID: DIP — Monta o grafo de dependências e injeta nos controllers.
"""
from flask import Flask
from config import config_map, BaseConfig
from app.repositories.sqlite_divida_repository import SQLiteDividaRepository
from app.repositories.migrations import aplicar_migracoes
from app.services.divida_service import DividaService
from app.controllers.divida_controller import divida_bp, init_controller
from app.security.csrf import init_csrf
from app.logger import get_logger

logger = get_logger(__name__)


def create_app(env: str = "development") -> Flask:
    """
    Factory function que cria e configura a aplicação Flask.

    Args:
        env: Ambiente de execução ('development', 'testing', 'production').

    Returns:
        Instância configurada de Flask.
    """
    app = Flask(
        __name__,
        template_folder="views/templates",
        static_folder="static",
    )

    # --- Configuração por Ambiente ---
    config_class: type[BaseConfig] = config_map.get(env, config_map["development"])
    app.config.from_object(config_class)

    logger.info("Aplicação iniciada.", extra={"environment": env})

    # --- Migrações de Schema ---
    db_path = app.config["DB_PATH"]
    database_url = app.config.get("DATABASE_URL", "")
    is_postgres = app.config.get("is_postgres", False)

    if is_postgres:
        from app.repositories.postgresql_divida_repository import PostgreSQLDividaRepository
        repository = PostgreSQLDividaRepository(db_url=database_url)
        aplicar_migracoes(db_url=database_url, is_postgres=True)
    else:
        if db_path != ":memory:":
            aplicar_migracoes(db_path=db_path)
        repository = SQLiteDividaRepository(db_path=db_path)

    # --- Montagem do Grafo de Dependências (DIP) ---
    service = DividaService(repository=repository)

    # --- Injeção nos Controllers ---
    init_controller(service=service)

    # --- Segurança: CSRF ---
    init_csrf(app)

    # --- Registro de Blueprints ---
    app.register_blueprint(divida_bp)

    return app

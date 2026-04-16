"""
config.py — Configurações da Aplicação por Ambiente.
Princípio SOLID aplicado: Open/Closed — novas configs herdam sem alterar a base.
"""
import os
from dotenv import load_dotenv

load_dotenv()

# Diretório raiz do projeto (onde este arquivo vive — src/)
_BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def _resolve_db(env_value: str) -> str:
    """
    Garante que DB_PATH seja sempre um caminho absoluto.
    Aceita ':memory:' como caso especial para testes.
    Se o valor de ambiente for relativo, ancora-o em _BASE_DIR.
    """
    if not env_value or env_value == ":memory:":
        return env_value
    if os.path.isabs(env_value):
        return env_value
    return os.path.join(_BASE_DIR, env_value)


class BaseConfig:
    """Configuração base compartilhada por todos os ambientes."""
    SECRET_KEY: str = os.getenv("SECRET_KEY", "dev-secret-key-change-in-production")
    DB_PATH: str = _resolve_db(os.getenv("DB_PATH", "controle_dividas.db"))
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    TESTING: bool = False
    DEBUG: bool = False


class DevelopmentConfig(BaseConfig):
    """Configuração para ambiente de desenvolvimento."""
    DEBUG: bool = True
    LOG_LEVEL: str = "DEBUG"


class TestingConfig(BaseConfig):
    """Configuração para testes automatizados. Usa banco em memória."""
    TESTING: bool = True
    DB_PATH: str = ":memory:"
    LOG_LEVEL: str = "WARNING"
    CSRF_DISABLED: bool = True   # Desativa validação CSRF nos testes


class ProductionConfig(BaseConfig):
    """Configuração para produção. SECRET_KEY obrigatória via variável de ambiente."""
    DEBUG: bool = False
    LOG_LEVEL: str = "WARNING"


# Mapa de ambientes para uso no factory
config_map: dict = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
}

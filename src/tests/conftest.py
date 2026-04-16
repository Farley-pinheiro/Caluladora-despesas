"""
tests/conftest.py — Fixtures compartilhadas para todos os testes.
Usa banco em memória para garantir isolamento e velocidade.
"""
import sys
import os
import pytest

# Garante que o diretório src está no path para imports absolutos
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.app import create_app
from app.repositories.sqlite_divida_repository import SQLiteDividaRepository
from app.services.divida_service import DividaService
from app.models.divida import Divida, CategoriaDivida


@pytest.fixture(scope="function")
def repository():
    """Repositório SQLite em memória — isolado por teste."""
    return SQLiteDividaRepository(db_path=":memory:")


@pytest.fixture(scope="function")
def service(repository):
    """Service com repository em memória injetado."""
    return DividaService(repository=repository)


@pytest.fixture(scope="function")
def divida_exemplo():
    """Instância de Dívida válida para reuso nos testes."""
    return Divida(
        nome="Cartão Nubank",
        valor_total=1200.00,
        valor_parcela=100.00,
        total_parcelas=12,
        categoria=CategoriaDivida.CARTAO,
        parcelas_pagas=3,
    )


@pytest.fixture(scope="function")
def flask_client():
    """Cliente de teste Flask com ambiente de testing."""
    app = create_app(env="testing")
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client

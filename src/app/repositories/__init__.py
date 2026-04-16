"""app/repositories/__init__.py — Exporta implementações de repositório."""
from app.repositories.base_repository import BaseRepository
from app.repositories.sqlite_divida_repository import SQLiteDividaRepository

__all__ = ["BaseRepository", "SQLiteDividaRepository"]

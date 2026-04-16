"""
app/repositories/base_repository.py — Interface Abstrata de Repositório.
Princípio SOLID: DIP — Controllers e Services dependem desta abstração,
não de implementações concretas (SQLite, PostgreSQL, etc.).
"""
from abc import ABC, abstractmethod
from typing import Optional
from app.models.divida import Divida


class BaseRepository(ABC):
    """Contrato que toda implementação de repositório deve cumprir."""

    @abstractmethod
    def save(self, divida: Divida) -> Divida:
        """Persiste uma nova dívida e retorna o objeto com ID preenchido."""
        ...

    @abstractmethod
    def find_by_id(self, divida_id: int) -> Optional[Divida]:
        """Busca uma dívida pelo ID. Retorna None se não encontrada."""
        ...

    @abstractmethod
    def find_all(self) -> list[Divida]:
        """Retorna todas as dívidas persistidas."""
        ...

    @abstractmethod
    def update(self, divida: Divida) -> Divida:
        """Atualiza uma dívida existente. Levanta ValueError se não existir."""
        ...

    @abstractmethod
    def delete(self, divida_id: int) -> bool:
        """Remove uma dívida pelo ID. Retorna True se removida, False se não encontrada."""
        ...

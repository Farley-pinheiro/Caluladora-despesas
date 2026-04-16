"""
app/repositories/sqlite_divida_repository.py — Implementação SQLite.
Princípio SOLID: LSP — substitui BaseRepository sem alterar comportamento esperado.
Logs estruturados em toda operação de escrita/leitura.
"""
import sqlite3
import sys
import os
from typing import Optional

from app.repositories.base_repository import BaseRepository
from app.models.divida import Divida, CategoriaDivida
from app.logger import get_logger

logger = get_logger(__name__)


def _resolve_db_path(db_path: str) -> str:
    """
    Resolve o caminho final do banco de dados.
    - ':memory:' é mantido como está (para testes).
    - Caminhos absolutos são usados diretamente (passados via config.py).
    - Caminhos relativos são resolvidos a partir do diretório do executável
      (compatibilidade com PyInstaller).
    """
    if db_path == ":memory:":
        return db_path
    if os.path.isabs(db_path):
        return db_path
    # Fallback para executável PyInstaller (caminho relativo)
    if getattr(sys, "frozen", False):
        base_dir = os.path.dirname(sys.executable)
        return os.path.join(base_dir, db_path)
    # Em desenvolvimento, se ainda recebemos um caminho relativo,
    # ancora ao diretório de trabalho atual (cwd = src/)
    return os.path.join(os.getcwd(), db_path)


class SQLiteDividaRepository(BaseRepository):
    """
    Repositório concreto para persistência de Dívidas em SQLite.
    Utiliza parâmetros parametrizados (?) em todas as queries para prevenir SQL Injection.
    """

    _CREATE_TABLE_SQL = """
        CREATE TABLE IF NOT EXISTS dividas (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            nome            TEXT    NOT NULL,
            valor_total     REAL    NOT NULL,
            valor_parcela   REAL    NOT NULL,
            total_parcelas  INTEGER NOT NULL,
            parcelas_pagas  INTEGER NOT NULL DEFAULT 0,
            categoria       TEXT    NOT NULL DEFAULT 'Outro',
            dia_vencimento  INTEGER
        )
    """

    def __init__(self, db_path: str = "controle_dividas.db") -> None:
        self._db_path = _resolve_db_path(db_path)
        # Para bancos em memória (testes), mantemos uma conexão persistente
        # pois cada sqlite3.connect(":memory:") abre um banco isolado diferente.
        self._in_memory_conn: sqlite3.Connection | None = None
        if self._db_path == ":memory:":
            self._in_memory_conn = sqlite3.connect(":memory:", check_same_thread=False)
            self._in_memory_conn.row_factory = sqlite3.Row
            self._in_memory_conn.execute("PRAGMA foreign_keys = ON")
        self._inicializar_schema()

    # ------------------------------------------------------------------
    # Infraestrutura de Conexão
    # ------------------------------------------------------------------

    def _conectar(self) -> sqlite3.Connection:
        """Retorna a conexão ativa. Em modo memória, reutiliza a conexão persistente."""
        if self._in_memory_conn is not None:
            return self._in_memory_conn
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def _inicializar_schema(self) -> None:
        """Cria a tabela se ainda não existir (migração implícita inicial)."""
        try:
            conn = self._conectar()
            conn.execute(self._CREATE_TABLE_SQL)
            conn.commit()
            # Não fecha a conexão em memória — ela deve ser persistente
            if self._in_memory_conn is None:
                conn.close()
            logger.info("Schema do banco de dados inicializado com sucesso.")
        except sqlite3.Error as exc:
            logger.error("Falha ao inicializar schema.", extra={"error": str(exc)})
            raise

    # ------------------------------------------------------------------
    # Mapeamento Row → Entidade
    # ------------------------------------------------------------------

    @staticmethod
    def _row_to_divida(row: sqlite3.Row) -> Divida:
        """Converte uma linha do banco em uma entidade Divida."""
        try:
            categoria = CategoriaDivida(row["categoria"])
        except ValueError:
            categoria = CategoriaDivida.OUTRO

        return Divida(
            id=row["id"],
            nome=row["nome"],
            valor_total=row["valor_total"],
            valor_parcela=row["valor_parcela"],
            total_parcelas=row["total_parcelas"],
            parcelas_pagas=row["parcelas_pagas"],
            categoria=categoria,
            dia_vencimento=row["dia_vencimento"] if "dia_vencimento" in row.keys() else None,
        )

    def _usar_conn(self):
        """
        Context manager seguro: não fecha a conexão em memória ao sair.
        Para conexões em arquivo, abre, usa e fecha normalmente.
        """
        from contextlib import contextmanager

        @contextmanager
        def _cm():
            if self._in_memory_conn is not None:
                yield self._in_memory_conn
            else:
                conn = self._conectar()
                try:
                    yield conn
                finally:
                    conn.close()
        return _cm()

    # ------------------------------------------------------------------
    # Implementação da Interface BaseRepository
    # ------------------------------------------------------------------

    def save(self, divida: Divida) -> Divida:
        """Insere uma nova dívida e retorna o objeto com ID gerado."""
        sql = """
            INSERT INTO dividas (nome, valor_total, valor_parcela, total_parcelas, parcelas_pagas, categoria, dia_vencimento)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """
        params = (
            divida.nome,
            divida.valor_total,
            divida.valor_parcela,
            divida.total_parcelas,
            divida.parcelas_pagas,
            divida.categoria.value,
            divida.dia_vencimento,
        )
        try:
            with self._usar_conn() as conn:
                cursor = conn.execute(sql, params)
                conn.commit()
                divida.id = cursor.lastrowid
            logger.info("Dívida salva com sucesso.", extra={"divida_id": divida.id, "nome": divida.nome})
            return divida
        except sqlite3.Error as exc:
            logger.error("Erro ao salvar dívida.", extra={"nome": divida.nome, "error": str(exc)})
            raise

    def find_by_id(self, divida_id: int) -> Optional[Divida]:
        """Busca dívida por ID. Retorna None se não encontrada."""
        sql = "SELECT * FROM dividas WHERE id = ?"
        try:
            with self._usar_conn() as conn:
                row = conn.execute(sql, (divida_id,)).fetchone()
            if row is None:
                logger.warning("Dívida não encontrada.", extra={"divida_id": divida_id})
                return None
            return self._row_to_divida(row)
        except sqlite3.Error as exc:
            logger.error("Erro ao buscar dívida.", extra={"divida_id": divida_id, "error": str(exc)})
            raise

    def find_all(self) -> list[Divida]:
        """Retorna todas as dívidas ordenadas pelo ID."""
        sql = "SELECT * FROM dividas ORDER BY id ASC"
        try:
            with self._conectar() as conn:
                rows = conn.execute(sql).fetchall()
            dividas = [self._row_to_divida(r) for r in rows]
            logger.info("Dívidas listadas.", extra={"quantidade": len(dividas)})
            return dividas
        except sqlite3.Error as exc:
            logger.error("Erro ao listar dívidas.", extra={"error": str(exc)})
            raise

    def update(self, divida: Divida) -> Divida:
        """Atualiza todos os campos de uma dívida existente."""
        if divida.id is None:
            raise ValueError("Dívida sem ID não pode ser atualizada.")
        sql = """
            UPDATE dividas
            SET nome = ?, valor_total = ?, valor_parcela = ?,
                total_parcelas = ?, parcelas_pagas = ?, categoria = ?, dia_vencimento = ?
            WHERE id = ?
        """
        params = (
            divida.nome,
            divida.valor_total,
            divida.valor_parcela,
            divida.total_parcelas,
            divida.parcelas_pagas,
            divida.categoria.value,
            divida.dia_vencimento,
            divida.id,
        )
        try:
            with self._conectar() as conn:
                cursor = conn.execute(sql, params)
                conn.commit()
                if cursor.rowcount == 0:
                    raise ValueError(f"Dívida com id={divida.id} não encontrada.")
            logger.info("Dívida atualizada.", extra={"divida_id": divida.id})
            return divida
        except sqlite3.Error as exc:
            logger.error("Erro ao atualizar dívida.", extra={"divida_id": divida.id, "error": str(exc)})
            raise

    def delete(self, divida_id: int) -> bool:
        """Remove uma dívida. Retorna True se excluída, False se não existia."""
        sql = "DELETE FROM dividas WHERE id = ?"
        try:
            with self._conectar() as conn:
                cursor = conn.execute(sql, (divida_id,))
                conn.commit()
                removed = cursor.rowcount > 0
            if removed:
                logger.info("Dívida excluída.", extra={"divida_id": divida_id})
            else:
                logger.warning("Tentativa de excluir dívida inexistente.", extra={"divida_id": divida_id})
            return removed
        except sqlite3.Error as exc:
            logger.error("Erro ao excluir dívida.", extra={"divida_id": divida_id, "error": str(exc)})
            raise

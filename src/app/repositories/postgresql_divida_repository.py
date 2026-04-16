"""
app/repositories/postgresql_divida_repository.py — Implementação PostgreSQL.
Princípio SOLID: LSP — substitui BaseRepository sem alterar comportamento esperado.
"""
import os
from typing import Optional
import psycopg2
from psycopg2.extras import DictCursor

from app.repositories.base_repository import BaseRepository
from app.models.divida import Divida, CategoriaDivida
from app.logger import get_logger

logger = get_logger(__name__)


class PostgreSQLDividaRepository(BaseRepository):
    """
    Repositório concreto para persistência de Dívidas em PostgreSQL.
    """

    def __init__(self, db_url: str) -> None:
        self._db_url = db_url

    def _conectar(self):
        """Retorna uma nova conexão ativa com o banco."""
        return psycopg2.connect(self._db_url, cursor_factory=DictCursor)

    @staticmethod
    def _row_to_divida(row: dict) -> Divida:
        """Converte uma linha do banco em uma entidade Divida."""
        try:
            categoria = CategoriaDivida(row["categoria"])
        except ValueError:
            categoria = CategoriaDivida.OUTRO

        return Divida(
            id=row["id"],
            nome=row["nome"],
            valor_total=float(row["valor_total"]),
            valor_parcela=float(row["valor_parcela"]),
            total_parcelas=row["total_parcelas"],
            parcelas_pagas=row["parcelas_pagas"],
            categoria=categoria,
            dia_vencimento=row.get("dia_vencimento"),
        )

    def save(self, divida: Divida) -> Divida:
        sql = """
            INSERT INTO dividas (nome, valor_total, valor_parcela, total_parcelas, parcelas_pagas, categoria, dia_vencimento)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING id
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
            with self._conectar() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(sql, params)
                    result = cursor.fetchone()
                    if result:
                        divida.id = result["id"]
                conn.commit()
            logger.info("Dívida salva com sucesso.", extra={"divida_id": divida.id, "nome": divida.nome})
            return divida
        except psycopg2.Error as exc:
            logger.error("Erro ao salvar dívida.", extra={"nome": divida.nome, "error": str(exc)})
            raise

    def find_by_id(self, divida_id: int) -> Optional[Divida]:
        sql = "SELECT * FROM dividas WHERE id = %s"
        try:
            with self._conectar() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(sql, (divida_id,))
                    row = cursor.fetchone()
            if row is None:
                logger.warning("Dívida não encontrada.", extra={"divida_id": divida_id})
                return None
            return self._row_to_divida(row)
        except psycopg2.Error as exc:
            logger.error("Erro ao buscar dívida.", extra={"divida_id": divida_id, "error": str(exc)})
            raise

    def find_all(self) -> list[Divida]:
        sql = "SELECT * FROM dividas ORDER BY id ASC"
        try:
            with self._conectar() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(sql)
                    rows = cursor.fetchall()
            dividas = [self._row_to_divida(r) for r in rows]
            logger.info("Dívidas listadas.", extra={"quantidade": len(dividas)})
            return dividas
        except psycopg2.Error as exc:
            logger.error("Erro ao listar dívidas.", extra={"error": str(exc)})
            raise

    def update(self, divida: Divida) -> Divida:
        if divida.id is None:
            raise ValueError("Dívida sem ID não pode ser atualizada.")
        sql = """
            UPDATE dividas
            SET nome = %s, valor_total = %s, valor_parcela = %s,
                total_parcelas = %s, parcelas_pagas = %s, categoria = %s, dia_vencimento = %s
            WHERE id = %s
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
                with conn.cursor() as cursor:
                    cursor.execute(sql, params)
                    rowcount = cursor.rowcount
                conn.commit()
                if rowcount == 0:
                    raise ValueError(f"Dívida com id={divida.id} não encontrada.")
            logger.info("Dívida atualizada.", extra={"divida_id": divida.id})
            return divida
        except psycopg2.Error as exc:
            logger.error("Erro ao atualizar dívida.", extra={"divida_id": divida.id, "error": str(exc)})
            raise

    def delete(self, divida_id: int) -> bool:
        sql = "DELETE FROM dividas WHERE id = %s"
        try:
            with self._conectar() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(sql, (divida_id,))
                    rowcount = cursor.rowcount
                conn.commit()
                removed = rowcount > 0
            if removed:
                logger.info("Dívida excluída.", extra={"divida_id": divida_id})
            else:
                logger.warning("Tentativa de excluir dívida inexistente.", extra={"divida_id": divida_id})
            return removed
        except psycopg2.Error as exc:
            logger.error("Erro ao excluir dívida.", extra={"divida_id": divida_id, "error": str(exc)})
            raise

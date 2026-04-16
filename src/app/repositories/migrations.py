"""
app/repositories/migrations.py — Sistema de Migração de Schema SQLite.
Permite evoluir o banco de dados sem perder dados existentes.
Princípio SOLID: OCP — novas migrações são adicionadas sem alterar as existentes.
"""
import sqlite3
from typing import Callable
from app.logger import get_logger

logger = get_logger(__name__)

# Tipo de uma função de migração: recebe um cursor e executa as alterações
MigrationFn = Callable[[sqlite3.Cursor], None]


# ---------------------------------------------------------------------------
# Registro de Migrações — adicione novas entradas APENAS ao final da lista
# ---------------------------------------------------------------------------

def _m001_criar_tabela_dividas(cursor: sqlite3.Cursor) -> None:
    """Migração inicial: cria a tabela dividas."""
    cursor.execute("""
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
    """)


def _m002_criar_tabela_migrations(cursor: sqlite3.Cursor) -> None:
    """Garante que a tabela de controle de versão exista."""
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS _migrations (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            versao      INTEGER NOT NULL UNIQUE,
            aplicada_em TEXT    NOT NULL DEFAULT (datetime('now'))
        )
    """)


def _m003_adicionar_dia_vencimento(cursor: sqlite3.Cursor) -> None:
    """Migração 3: adiciona coluna dia_vencimento (dia do mês, 1-31)."""
    try:
        cursor.execute("ALTER TABLE dividas ADD COLUMN dia_vencimento INTEGER")
    except Exception:
        pass  # Coluna já existe em bancos recém-criados


# Lista ordenada de migrações. A posição (índice + 1) é a versão.
MIGRATIONS: list[tuple[str, MigrationFn]] = [
    ("m001_criar_tabela_dividas",      _m001_criar_tabela_dividas),
    ("m002_criar_tabela_migrations",   _m002_criar_tabela_migrations),
    ("m003_adicionar_dia_vencimento",  _m003_adicionar_dia_vencimento),
]


# ---------------------------------------------------------------------------
# Engine de Migração
# ---------------------------------------------------------------------------

def _get_versao_atual(cursor: sqlite3.Cursor) -> int:
    """Retorna a versão atual do schema. Retorna 0 se não houver migrações."""
    try:
        cursor.execute("SELECT MAX(versao) FROM _migrations")
        row = cursor.fetchone()
        return row[0] if row and row[0] is not None else 0
    except sqlite3.OperationalError:
        # A tabela _migrations ainda não existe
        return 0


def aplicar_migracoes(db_path: str) -> None:
    """
    Aplica todas as migrações pendentes no banco de dados.
    É idempotente — pode ser chamada múltiplas vezes com segurança.

    Args:
        db_path: Caminho para o arquivo SQLite (ou ':memory:' para testes).
    """
    conn = sqlite3.connect(db_path)
    try:
        cursor = conn.cursor()

        # Garante a tabela de controle antes de qualquer coisa
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS _migrations (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                versao      INTEGER NOT NULL UNIQUE,
                aplicada_em TEXT    NOT NULL DEFAULT (datetime('now'))
            )
        """)
        conn.commit()

        versao_atual = _get_versao_atual(cursor)
        migracoes_pendentes = MIGRATIONS[versao_atual:]

        if not migracoes_pendentes:
            logger.info("Schema atualizado. Nenhuma migração pendente.", extra={"versao": versao_atual})
            return

        for i, (nome, fn) in enumerate(migracoes_pendentes, start=versao_atual + 1):
            logger.info("Aplicando migração.", extra={"versao": i, "nome": nome})
            fn(cursor)
            cursor.execute(
                "INSERT INTO _migrations (versao) VALUES (?)", (i,)
            )
            conn.commit()
            logger.info("Migração aplicada com sucesso.", extra={"versao": i})

        logger.info(
            "Migrações concluídas.",
            extra={"versao_anterior": versao_atual, "versao_atual": versao_atual + len(migracoes_pendentes)},
        )
    except sqlite3.Error as exc:
        conn.rollback()
        logger.error("Falha ao aplicar migrações. Rollback executado.", extra={"error": str(exc)})
        raise
    finally:
        conn.close()

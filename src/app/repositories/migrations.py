"""
app/repositories/migrations.py — Sistema de Migração de Schema SQLite.
Permite evoluir o banco de dados sem perder dados existentes.
Princípio SOLID: OCP — novas migrações são adicionadas sem alterar as existentes.
"""
import sqlite3
from typing import Callable, Any
from app.logger import get_logger

logger = get_logger(__name__)

# Tipo de uma função de migração: recebe um cursor e is_postgres
MigrationFn = Callable[[Any, bool], None]


# ---------------------------------------------------------------------------
# Registro de Migrações — adicione novas entradas APENAS ao final da lista
# ---------------------------------------------------------------------------

def _m001_criar_tabela_dividas(cursor: Any, is_postgres: bool) -> None:
    """Migração inicial: cria a tabela dividas."""
    if is_postgres:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS dividas (
                id              SERIAL PRIMARY KEY,
                nome            TEXT             NOT NULL,
                valor_total     DOUBLE PRECISION NOT NULL,
                valor_parcela   DOUBLE PRECISION NOT NULL,
                total_parcelas  INTEGER          NOT NULL,
                parcelas_pagas  INTEGER          NOT NULL DEFAULT 0,
                categoria       TEXT             NOT NULL DEFAULT 'Outro',
                dia_vencimento  INTEGER
            )
        """)
    else:
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


def _m002_criar_tabela_migrations(cursor: Any, is_postgres: bool) -> None:
    """Garante que a tabela de controle de versão exista."""
    if is_postgres:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS _migrations (
                id          SERIAL PRIMARY KEY,
                versao      INTEGER NOT NULL UNIQUE,
                aplicada_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)
    else:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS _migrations (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                versao      INTEGER NOT NULL UNIQUE,
                aplicada_em TEXT    NOT NULL DEFAULT (datetime('now'))
            )
        """)


def _m003_adicionar_dia_vencimento(cursor: Any, is_postgres: bool) -> None:
    """Migração 3: adiciona coluna dia_vencimento (dia do mês, 1-31)."""
    try:
        cursor.execute("ALTER TABLE dividas ADD COLUMN dia_vencimento INTEGER")
    except Exception:
        pass  # Coluna já existe


# Lista ordenada de migrações. A posição (índice + 1) é a versão.
MIGRATIONS: list[tuple[str, MigrationFn]] = [
    ("m001_criar_tabela_dividas",      _m001_criar_tabela_dividas),
    ("m002_criar_tabela_migrations",   _m002_criar_tabela_migrations),
    ("m003_adicionar_dia_vencimento",  _m003_adicionar_dia_vencimento),
]


# ---------------------------------------------------------------------------
# Engine de Migração
# ---------------------------------------------------------------------------

def _get_versao_atual(cursor: Any, is_postgres: bool) -> int:
    """Retorna a versão atual do schema. Retorna 0 se não houver migrações."""
    try:
        cursor.execute("SELECT MAX(versao) FROM _migrations")
        row = cursor.fetchone()
        if is_postgres:
            # Em psycopg2 DictCursor fetchone retorna uma lista/dicionario ou None
            return row[0] if row and row[0] is not None else 0
        return row[0] if row and row[0] is not None else 0
    except Exception:
        if is_postgres:
            # psycopg2 aborta a transação em caso de erro, logo precisa fazer rollback aqui
            # mas vamos preferir que o chamador faça, ou podemos usar conexões auto-commit para o check
            pass
        return 0


def aplicar_migracoes(db_path: str = None, db_url: str = None, is_postgres: bool = False) -> None:
    """
    Aplica todas as migrações pendentes no banco de dados.
    """
    if is_postgres:
        import psycopg2
        conn = psycopg2.connect(db_url)
    else:
        conn = sqlite3.connect(db_path)
    
    try:
        cursor = conn.cursor()

        if is_postgres:
            # Em PostgreSQL, um erro na consulta de get_versao aborta a transacao.
            # Vamos garantir a tabela antes de consultar e sempre comitar
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS _migrations (
                    id          SERIAL PRIMARY KEY,
                    versao      INTEGER NOT NULL UNIQUE,
                    aplicada_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.commit()
        else:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS _migrations (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    versao      INTEGER NOT NULL UNIQUE,
                    aplicada_em TEXT    NOT NULL DEFAULT (datetime('now'))
                )
            """)
            conn.commit()

        versao_atual = _get_versao_atual(cursor, is_postgres)
        migracoes_pendentes = MIGRATIONS[versao_atual:]

        if not migracoes_pendentes:
            logger.info("Schema atualizado. Nenhuma migração pendente.", extra={"versao": versao_atual})
            return

        for i, (nome, fn) in enumerate(migracoes_pendentes, start=versao_atual + 1):
            logger.info("Aplicando migração.", extra={"versao": i, "nome": nome})
            fn(cursor, is_postgres)
            if is_postgres:
                cursor.execute("INSERT INTO _migrations (versao) VALUES (%s)", (i,))
            else:
                cursor.execute("INSERT INTO _migrations (versao) VALUES (?)", (i,))
            conn.commit()
            logger.info("Migração aplicada com sucesso.", extra={"versao": i})

        logger.info(
            "Migrações concluídas.",
            extra={"versao_anterior": versao_atual, "versao_atual": versao_atual + len(migracoes_pendentes)},
        )
    except Exception as exc:
        conn.rollback()
        logger.error("Falha ao aplicar migrações. Rollback executado.", extra={"error": str(exc)})
        raise
    finally:
        conn.close()

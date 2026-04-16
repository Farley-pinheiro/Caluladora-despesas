"""
logger.py — Logger Estruturado Global da Aplicação.
Emite logs em formato JSON para facilitar ingestão por ferramentas de observabilidade.
"""
import logging
import json
import os
from datetime import datetime, timezone


class JSONFormatter(logging.Formatter):
    """Formata registros de log como JSON estruturado."""

    def format(self, record: logging.LogRecord) -> str:
        log_record = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
            "message": record.getMessage(),
        }
        if record.exc_info:
            log_record["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_record, ensure_ascii=False)


def get_logger(name: str) -> logging.Logger:
    """
    Retorna um logger configurado com o nome do módulo chamador.
    Uso: logger = get_logger(__name__)
    """
    log_level_str: str = os.getenv("LOG_LEVEL", "INFO").upper()
    log_level: int = getattr(logging, log_level_str, logging.INFO)

    logger = logging.getLogger(name)

    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(JSONFormatter())
        logger.addHandler(handler)

    logger.setLevel(log_level)
    logger.propagate = False
    return logger

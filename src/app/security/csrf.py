"""
app/security/csrf.py — Proteção CSRF via Token de Sessão.
Implementação manual sem dependências externas.

Estratégia:
  - Token gerado por `secrets.token_hex` e armazenado na sessão Flask.
  - Exposto via meta tag no HTML (base.html).
  - Incluído pelo JS como header `X-CSRF-Token` em cada mutação.
  - Validado em `before_request` para métodos POST, PUT, DELETE.

Princípio SOLID: SRP — toda lógica de CSRF isolada neste módulo.
"""
import secrets
from flask import Flask, session, request, jsonify
from app.logger import get_logger

logger = get_logger(__name__)

_CSRF_SESSION_KEY = "_csrf_token"
_CSRF_HEADER      = "X-CSRF-Token"
_SAFE_METHODS     = frozenset(["GET", "HEAD", "OPTIONS"])


def _generate_token() -> str:
    """Gera um token CSRF criptograficamente seguro."""
    return secrets.token_hex(32)


def get_csrf_token() -> str:
    """
    Retorna o token CSRF da sessão atual, criando um novo se necessário.
    Deve ser chamado nos templates via `{{ csrf_token() }}`.
    """
    if _CSRF_SESSION_KEY not in session:
        session[_CSRF_SESSION_KEY] = _generate_token()
    return session[_CSRF_SESSION_KEY]


def _validate_csrf() -> None:
    """
    Hook `before_request`: valida o CSRF token para métodos de mutação.
    Ignota métodos seguros (GET, HEAD, OPTIONS) e rotas de assets estáticos.
    Pode ser desabilitado via config CSRF_DISABLED=True (útil em testes).
    """
    from flask import current_app
    if current_app.config.get("CSRF_DISABLED", False):
        return

    if request.method in _SAFE_METHODS:
        return

    # Ignora arquivos estáticos
    if request.endpoint and request.endpoint.startswith("static"):
        return

    token_sessao = session.get(_CSRF_SESSION_KEY)
    token_header = request.headers.get(_CSRF_HEADER)

    if not token_sessao or not token_header:
        logger.warning(
            "CSRF token ausente.",
            extra={"endpoint": request.endpoint, "method": request.method},
        )
        return jsonify({"erro": "CSRF token ausente."}), 403

    # Comparação segura contra timing attacks
    if not secrets.compare_digest(token_sessao, token_header):
        logger.warning(
            "CSRF token inválido.",
            extra={"endpoint": request.endpoint, "method": request.method},
        )
        return jsonify({"erro": "CSRF token inválido."}), 403


def init_csrf(app: Flask) -> None:
    """
    Registra o middleware CSRF na aplicação Flask.
    Também injeta `csrf_token` como função global nos templates Jinja2.

    Args:
        app: Instância Flask a ser configurada.
    """
    app.before_request(_validate_csrf)

    # Torna csrf_token() disponível em todos os templates
    app.jinja_env.globals["csrf_token"] = get_csrf_token

    logger.info("Proteção CSRF inicializada.")

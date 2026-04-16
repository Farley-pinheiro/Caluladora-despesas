"""
app/controllers/divida_controller.py — Blueprint Flask com rotas da aplicação.
Princípio SOLID: SRP — Apenas trata HTTP requests/responses, delega ao Service.
Segurança: Validação de inputs, tratamento de erros padronizado.
"""
from flask import Blueprint, render_template, request, redirect, url_for, jsonify, abort
from app.services.divida_service import DividaService
from app.models.divida import CategoriaDivida
from app.logger import get_logger

logger = get_logger(__name__)

divida_bp = Blueprint("dividas", __name__)

# O service será injetado via app factory (ver app.py)
_service: DividaService | None = None


def init_controller(service: DividaService) -> None:
    """Injeta a dependência do service no controller."""
    global _service
    _service = service


def _get_service() -> DividaService:
    """Garante que o service foi injetado antes do uso."""
    if _service is None:
        raise RuntimeError("DividaService não foi inicializado no controller.")
    return _service


# ---------------------------------------------------------------------------
# Rotas — Views (HTML)
# ---------------------------------------------------------------------------

@divida_bp.route("/", methods=["GET"])
def index():
    """Dashboard principal com resumo geral."""
    logger.info("Requisição para Dashboard.", extra={"method": "GET", "path": "/"})
    service = _get_service()
    resumo = service.obter_resumo_geral()
    categorias = [c.value for c in CategoriaDivida]

    # Dados para o gráfico de rosca (agrega valor restante por categoria)
    from collections import defaultdict
    cat_totals: dict = defaultdict(float)
    for d in resumo["dividas"]:
        if not d["esta_quitada"] and d["valor_restante"] > 0:
            cat_totals[d["categoria"]] += d["valor_restante"]
    chart_data = [{"label": k, "value": round(v, 2)} for k, v in cat_totals.items()]

    # Percentual global de parcelas quitadas
    total_p = sum(d["total_parcelas"] for d in resumo["dividas"])
    pagas_p = sum(d["parcelas_pagas"] for d in resumo["dividas"])
    pct_quitado = round((pagas_p / total_p * 100) if total_p > 0 else 0, 1)

    return render_template(
        "index.html",
        resumo=resumo,
        categorias=categorias,
        chart_data=chart_data,
        pct_quitado=pct_quitado,
    )


@divida_bp.route("/nova", methods=["GET"])
def nova_divida_form():
    """Exibe o formulário de cadastro de nova dívida."""
    categorias = [c.value for c in CategoriaDivida]
    return render_template("nova_divida.html", categorias=categorias)


# ---------------------------------------------------------------------------
# Rotas — API (JSON)
# ---------------------------------------------------------------------------

@divida_bp.route("/api/dividas", methods=["POST"])
def criar_divida():
    """Recebe JSON e cria uma nova dívida."""
    data = request.get_json(silent=True)
    if not data:
        logger.warning("Payload inválido na criação de dívida.")
        return jsonify({"erro": "Payload JSON inválido ou ausente."}), 400

    campos_obrigatorios = ["nome", "valor_total", "total_parcelas"]
    faltando = [c for c in campos_obrigatorios if c not in data]
    if faltando:
        return jsonify({"erro": f"Campos obrigatórios ausentes: {faltando}"}), 400

    try:
        divida = _get_service().criar_divida(
            nome=str(data["nome"]),
            valor_total=float(data["valor_total"]),
            total_parcelas=int(data["total_parcelas"]),
            categoria=data.get("categoria", "Outro"),
            dia_vencimento=int(data["dia_vencimento"]) if data.get("dia_vencimento") else None,
        )
        logger.info("Dívida criada via API.", extra={"divida_id": divida.id})
        return jsonify(divida.to_dict()), 201
    except (ValueError, TypeError) as exc:
        logger.warning("Dados inválidos na criação.", extra={"error": str(exc)})
        return jsonify({"erro": str(exc)}), 400
    except Exception as exc:
        logger.error("Erro interno ao criar dívida.", extra={"error": str(exc)})
        return jsonify({"erro": "Erro interno do servidor."}), 500


@divida_bp.route("/api/dividas", methods=["GET"])
def listar_dividas():
    """Retorna todas as dívidas em JSON."""
    try:
        dividas = _get_service().listar_dividas()
        return jsonify([d.to_dict() for d in dividas]), 200
    except Exception as exc:
        logger.error("Erro ao listar dívidas.", extra={"error": str(exc)})
        return jsonify({"erro": "Erro interno do servidor."}), 500


@divida_bp.route("/api/dividas/<int:divida_id>", methods=["GET"])
def detalhar_divida(divida_id: int):
    """Retorna detalhes de uma dívida específica."""
    try:
        divida = _get_service().buscar_divida(divida_id)
        return jsonify(divida.to_dict()), 200
    except ValueError as exc:
        return jsonify({"erro": str(exc)}), 404
    except Exception as exc:
        logger.error("Erro ao detalhar dívida.", extra={"divida_id": divida_id, "error": str(exc)})
        return jsonify({"erro": "Erro interno do servidor."}), 500


@divida_bp.route("/api/dividas/<int:divida_id>/pagar", methods=["PUT"])
def pagar_parcela(divida_id: int):
    """Registra o pagamento de uma parcela."""
    data = request.get_json(silent=True) or {}
    quantidade = int(data.get("quantidade", 1))
    try:
        divida = _get_service().registrar_pagamento(divida_id, quantidade)
        return jsonify(divida.to_dict()), 200
    except ValueError as exc:
        return jsonify({"erro": str(exc)}), 400
    except Exception as exc:
        logger.error("Erro ao registrar pagamento.", extra={"divida_id": divida_id, "error": str(exc)})
        return jsonify({"erro": "Erro interno do servidor."}), 500


@divida_bp.route("/api/dividas/<int:divida_id>", methods=["DELETE"])
def excluir_divida(divida_id: int):
    """Remove uma dívida pelo ID."""
    try:
        _get_service().excluir_divida(divida_id)
        return jsonify({"mensagem": f"Dívida {divida_id} excluída com sucesso."}), 200
    except ValueError as exc:
        return jsonify({"erro": str(exc)}), 404
    except Exception as exc:
        logger.error("Erro ao excluir dívida.", extra={"divida_id": divida_id, "error": str(exc)})
        return jsonify({"erro": "Erro interno do servidor."}), 500

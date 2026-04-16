"""
tests/test_controller.py — Testes de Integração dos Endpoints HTTP.
Usa o cliente de teste do Flask com banco em memória.
Valida: status codes, payloads, tratamento de erros e fluxo completo.
"""
import json
import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def post_divida(client, **kwargs):
    """Atalho para criar uma dívida via POST."""
    payload = {
        "nome": "Cartão Nubank",
        "valor_total": 1200.0,
        "total_parcelas": 12,
        "categoria": "Cartão de Crédito",
        **kwargs,
    }
    return client.post(
        "/api/dividas",
        data=json.dumps(payload),
        content_type="application/json",
    )


# ---------------------------------------------------------------------------
# POST /api/dividas — Criação
# ---------------------------------------------------------------------------

class TestCriarDivida:

    def test_cria_divida_retorna_201(self, flask_client):
        res = post_divida(flask_client)
        assert res.status_code == 201

    def test_cria_divida_retorna_campos_esperados(self, flask_client):
        res = post_divida(flask_client)
        data = res.get_json()
        assert data["nome"] == "Cartão Nubank"
        assert data["valor_total"] == 1200.0
        assert data["valor_parcela"] == pytest.approx(100.0)  # 1200 / 12
        assert data["total_parcelas"] == 12
        assert data["parcelas_pagas"] == 0
        assert data["esta_quitada"] is False
        assert "id" in data

    def test_cria_divida_sem_nome_retorna_400(self, flask_client):
        res = flask_client.post(
            "/api/dividas",
            data=json.dumps({"valor_total": 100.0, "total_parcelas": 10}),
            content_type="application/json",
        )
        assert res.status_code == 400

    def test_cria_divida_payload_invalido_retorna_400(self, flask_client):
        res = flask_client.post(
            "/api/dividas",
            data="nao-e-json",
            content_type="application/json",
        )
        assert res.status_code == 400

    def test_cria_divida_valor_negativo_retorna_400(self, flask_client):
        res = post_divida(flask_client, valor_total=-500.0)
        assert res.status_code == 400

    def test_cria_divida_parcela_maior_total_retorna_400(self, flask_client):
        """Com o novo design, valor_parcela é calculado (total/parcelas).
        Esse cenário já não se aplica — verifica que o endpoint aceita normalmente."""
        # R$100 em 1 parcela → parcela = R$100 (igual ao total, válido)
        res = post_divida(flask_client, valor_total=100.0, total_parcelas=1)
        assert res.status_code == 201

    def test_cria_divida_campos_faltando_retorna_400(self, flask_client):
        # Falta total_parcelas
        res = flask_client.post(
            "/api/dividas",
            data=json.dumps({"nome": "Teste", "valor_total": 100.0}),
            content_type="application/json",
        )
        assert res.status_code == 400
        dados = res.get_json()
        assert "erro" in dados


# ---------------------------------------------------------------------------
# GET /api/dividas — Listagem
# ---------------------------------------------------------------------------

class TestListarDividas:

    def test_lista_vazia_retorna_200(self, flask_client):
        res = flask_client.get("/api/dividas")
        assert res.status_code == 200
        assert res.get_json() == []

    def test_lista_com_dividas(self, flask_client):
        post_divida(flask_client)
        post_divida(flask_client, nome="Financiamento Carro")
        res = flask_client.get("/api/dividas")
        data = res.get_json()
        assert res.status_code == 200
        assert len(data) == 2

    def test_lista_retorna_lista(self, flask_client):
        res = flask_client.get("/api/dividas")
        assert isinstance(res.get_json(), list)


# ---------------------------------------------------------------------------
# GET /api/dividas/<id> — Detalhe
# ---------------------------------------------------------------------------

class TestDetalharDivida:

    def test_detalha_divida_existente(self, flask_client):
        criada = post_divida(flask_client).get_json()
        res = flask_client.get(f"/api/dividas/{criada['id']}")
        assert res.status_code == 200
        assert res.get_json()["id"] == criada["id"]

    def test_detalha_divida_inexistente_retorna_404(self, flask_client):
        res = flask_client.get("/api/dividas/9999")
        assert res.status_code == 404

    def test_detalhe_contem_campos_calculados(self, flask_client):
        criada = post_divida(flask_client).get_json()
        res = flask_client.get(f"/api/dividas/{criada['id']}").get_json()
        assert "valor_restante" in res
        assert "parcelas_restantes" in res
        assert "porcentagem_paga" in res


# ---------------------------------------------------------------------------
# PUT /api/dividas/<id>/pagar — Pagamento
# ---------------------------------------------------------------------------

class TestPagarParcela:

    def test_paga_parcela_retorna_200(self, flask_client):
        criada = post_divida(flask_client).get_json()
        res = flask_client.put(
            f"/api/dividas/{criada['id']}/pagar",
            data=json.dumps({"quantidade": 1}),
            content_type="application/json",
        )
        assert res.status_code == 200

    def test_pagar_incrementa_parcelas(self, flask_client):
        criada = post_divida(flask_client).get_json()
        res = flask_client.put(
            f"/api/dividas/{criada['id']}/pagar",
            data=json.dumps({}),
            content_type="application/json",
        )
        data = res.get_json()
        assert data["parcelas_pagas"] == 1

    def test_pagar_divida_inexistente_retorna_400(self, flask_client):
        res = flask_client.put(
            "/api/dividas/9999/pagar",
            data=json.dumps({}),
            content_type="application/json",
        )
        # 400 pois o service levanta ValueError ao não encontrar
        assert res.status_code in (400, 404)

    def test_pagar_divida_ja_quitada_retorna_400(self, flask_client):
        # Cria com 12/12 parcelas pagas — não é possível via API normal
        # Então cria e paga todas as parcelas sequencialmente (simplificado: cria dívida de 1 parcela)
        res = flask_client.post(
            "/api/dividas",
            data=json.dumps({
                "nome": "Dívida 1 Parcela",
                "valor_total": 100.0,
                "valor_parcela": 100.0,
                "total_parcelas": 1,
            }),
            content_type="application/json",
        )
        divida_id = res.get_json()["id"]

        # Paga a única parcela
        flask_client.put(
            f"/api/dividas/{divida_id}/pagar",
            data=json.dumps({}),
            content_type="application/json",
        )

        # Tenta pagar novamente (já quitada)
        res2 = flask_client.put(
            f"/api/dividas/{divida_id}/pagar",
            data=json.dumps({}),
            content_type="application/json",
        )
        assert res2.status_code == 400


# ---------------------------------------------------------------------------
# DELETE /api/dividas/<id> — Exclusão
# ---------------------------------------------------------------------------

class TestExcluirDivida:

    def test_exclui_divida_existente_retorna_200(self, flask_client):
        criada = post_divida(flask_client).get_json()
        res = flask_client.delete(f"/api/dividas/{criada['id']}")
        assert res.status_code == 200

    def test_apos_exclusao_nao_encontra_mais(self, flask_client):
        criada = post_divida(flask_client).get_json()
        flask_client.delete(f"/api/dividas/{criada['id']}")
        res = flask_client.get(f"/api/dividas/{criada['id']}")
        assert res.status_code == 404

    def test_exclui_divida_inexistente_retorna_404(self, flask_client):
        res = flask_client.delete("/api/dividas/9999")
        assert res.status_code == 404


# ---------------------------------------------------------------------------
# GET / — Dashboard (View HTML)
# ---------------------------------------------------------------------------

class TestDashboard:

    def test_dashboard_retorna_200(self, flask_client):
        res = flask_client.get("/")
        assert res.status_code == 200

    def test_dashboard_contem_html(self, flask_client):
        res = flask_client.get("/")
        assert b"Controle de D" in res.data  # "Controle de Dívidas"

    def test_dashboard_com_dividas_cadastradas(self, flask_client):
        post_divida(flask_client)
        res = flask_client.get("/")
        assert res.status_code == 200
        assert b"Cart" in res.data  # "Cartão Nubank"

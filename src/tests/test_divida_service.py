"""
tests/test_divida_service.py — Testes Unitários do DividaService.
O repositório é mockado para isolar a lógica de negócio da persistência.
Demonstra o princípio DIP em ação nos testes.
"""
import pytest
from unittest.mock import MagicMock
from app.services.divida_service import DividaService
from app.models.divida import Divida, CategoriaDivida


@pytest.fixture
def repo_mock():
    """Mock do repositório — isolamento total da camada de persistência."""
    return MagicMock()


@pytest.fixture
def svc(repo_mock):
    return DividaService(repository=repo_mock)


class TestCriarDivida:

    def test_cria_divida_com_dados_validos(self, svc, repo_mock):
        divida_persistida = Divida("Cartão", 1200.0, 100.0, 12, CategoriaDivida.CARTAO)
        divida_persistida.id = 1
        repo_mock.save.return_value = divida_persistida

        resultado = svc.criar_divida("Cartão", 1200.0, 12, "Cartão de Crédito")

        repo_mock.save.assert_called_once()
        assert resultado.id == 1
        assert resultado.nome == "Cartão"

    def test_categoria_invalida_usa_outro(self, svc, repo_mock):
        repo_mock.save.return_value = Divida("Teste", 500.0, 50.0, 10, parcelas_pagas=0)
        svc.criar_divida("Teste", 500.0, 10, categoria="CategoriaInexistente")
        chamada = repo_mock.save.call_args[0][0]
        assert chamada.categoria == CategoriaDivida.OUTRO

    def test_valor_negativo_levanta_erro(self, svc, repo_mock):
        with pytest.raises(ValueError):
            svc.criar_divida("Teste", -100.0, 10)
        repo_mock.save.assert_not_called()


class TestListarDividas:

    def test_retorna_lista_vazia(self, svc, repo_mock):
        repo_mock.find_all.return_value = []
        resultado = svc.listar_dividas()
        assert resultado == []

    def test_retorna_dividas_do_repositorio(self, svc, repo_mock):
        d1 = Divida("D1", 100.0, 10.0, 10)
        d2 = Divida("D2", 200.0, 20.0, 10)
        repo_mock.find_all.return_value = [d1, d2]
        resultado = svc.listar_dividas()
        assert len(resultado) == 2


class TestBuscarDivida:

    def test_busca_divida_existente(self, svc, repo_mock):
        d = Divida("Teste", 500.0, 50.0, 10)
        d.id = 5
        repo_mock.find_by_id.return_value = d
        resultado = svc.buscar_divida(5)
        assert resultado.id == 5

    def test_divida_inexistente_levanta_erro(self, svc, repo_mock):
        repo_mock.find_by_id.return_value = None
        with pytest.raises(ValueError, match="não encontrada"):
            svc.buscar_divida(99)


class TestRegistrarPagamento:

    def test_pagamento_registrado_com_sucesso(self, svc, repo_mock):
        d = Divida("Teste", 500.0, 50.0, 10, parcelas_pagas=3)
        d.id = 1
        repo_mock.find_by_id.return_value = d
        repo_mock.update.return_value = d

        resultado = svc.registrar_pagamento(1)
        assert resultado.parcelas_pagas == 4
        repo_mock.update.assert_called_once()

    def test_divida_ja_quitada_levanta_erro(self, svc, repo_mock):
        d = Divida("Teste", 500.0, 50.0, 10, parcelas_pagas=10)
        d.id = 2
        repo_mock.find_by_id.return_value = d
        with pytest.raises(ValueError, match="quitada"):
            svc.registrar_pagamento(2)


class TestCalculosAgregados:

    def test_total_geral_restante(self, svc, repo_mock):
        dividas = [
            Divida("D1", 1000.0, 100.0, 10, parcelas_pagas=5),   # restante: 500
            Divida("D2", 600.0, 100.0, 6, parcelas_pagas=2),     # restante: 400
        ]
        repo_mock.find_all.return_value = dividas
        total = svc.calcular_total_geral_restante()
        assert total == pytest.approx(900.0)

    def test_gasto_mensal_ignora_quitadas(self, svc, repo_mock):
        dividas = [
            Divida("Ativa",   1200.0, 100.0, 12, parcelas_pagas=3),
            Divida("Quitada", 600.0, 100.0, 6, parcelas_pagas=6),
        ]
        repo_mock.find_all.return_value = dividas
        mensal = svc.calcular_gasto_mensal_total()
        assert mensal == pytest.approx(100.0)

    def test_resumo_geral_estrutura(self, svc, repo_mock):
        repo_mock.find_all.return_value = []
        resumo = svc.obter_resumo_geral()
        assert "total_dividas" in resumo
        assert "dividas_ativas" in resumo
        assert "total_restante" in resumo
        assert "gasto_mensal" in resumo
        assert "dividas" in resumo

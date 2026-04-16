"""
tests/test_model_divida.py — Testes Unitários da Entidade Divida.
Valida regras de domínio, validações e cálculos financeiros.
"""
import pytest
from app.models.divida import Divida, CategoriaDivida


class TestDividaInstanciacao:
    """Testes de criação e validação da entidade."""

    def test_cria_divida_valida(self):
        d = Divida("Empréstimo CEF", 5000.0, 500.0, 10, CategoriaDivida.EMPRESTIMO)
        assert d.nome == "Empréstimo CEF"
        assert d.valor_total == 5000.0
        assert d.valor_parcela == 500.0
        assert d.total_parcelas == 10
        assert d.parcelas_pagas == 0

    def test_nome_vazio_levanta_erro(self):
        with pytest.raises(ValueError, match="nome"):
            Divida("", 1000.0, 100.0, 10)

    def test_nome_apenas_espacos_levanta_erro(self):
        with pytest.raises(ValueError, match="nome"):
            Divida("   ", 1000.0, 100.0, 10)

    def test_valor_total_negativo_levanta_erro(self):
        with pytest.raises(ValueError, match="valor total"):
            Divida("Teste", -100.0, 10.0, 10)

    def test_valor_total_zero_levanta_erro(self):
        with pytest.raises(ValueError, match="valor total"):
            Divida("Teste", 0.0, 10.0, 10)

    def test_valor_parcela_negativo_levanta_erro(self):
        with pytest.raises(ValueError, match="parcela"):
            Divida("Teste", 1000.0, -50.0, 10)

    def test_parcela_calculada_automaticamente(self):
        """valor_parcela agora é derivado pelo service (total / n_parcelas).
        No model, qualquer valor positivo é aceito — a validação de consistência
        é responsabilidade do DividaService, não do domínio."""
        d = Divida("Empréstimo", 1000.0, 142.86, 7)  # 1000/7 ≈ 142.86
        assert d.valor_parcela == pytest.approx(142.86)

    def test_total_parcelas_zero_levanta_erro(self):
        with pytest.raises(ValueError, match="total de parcelas"):
            Divida("Teste", 1000.0, 100.0, 0)

    def test_parcelas_pagas_negativas_levanta_erro(self):
        with pytest.raises(ValueError, match="negativas"):
            Divida("Teste", 1000.0, 100.0, 10, parcelas_pagas=-1)

    def test_parcelas_pagas_maior_que_total_levanta_erro(self):
        with pytest.raises(ValueError, match="exceder"):
            Divida("Teste", 1000.0, 100.0, 5, parcelas_pagas=6)


class TestDividaCalculos:
    """Testes dos cálculos financeiros de domínio."""

    def test_valor_restante_inicial(self):
        d = Divida("Teste", 1200.0, 100.0, 12)
        assert d.calcular_valor_restante() == 1200.0

    def test_valor_restante_com_parcelas_pagas(self):
        d = Divida("Teste", 1200.0, 100.0, 12, parcelas_pagas=3)
        assert d.calcular_valor_restante() == pytest.approx(900.0)

    def test_valor_restante_nao_negativo(self):
        d = Divida("Teste", 1200.0, 100.0, 12, parcelas_pagas=12)
        assert d.calcular_valor_restante() == 0.0

    def test_valor_restante_zero_quando_quitada_com_total_diferente(self):
        """
        Regressão: quando valor_total ≠ valor_parcela × total_parcelas e
        todas as parcelas estão pagas, o restante deve ser exatamente 0.0.
        Ex: Itaú — R$1000 total / R$100 parcela / 6 parcelas → R$400 'sobrando'
        """
        d = Divida("Itaú", 1000.0, 100.0, 6, parcelas_pagas=6)
        assert d.esta_quitada() is True
        assert d.calcular_valor_restante() == 0.0

    def test_parcelas_restantes(self):
        d = Divida("Teste", 1200.0, 100.0, 12, parcelas_pagas=4)
        assert d.calcular_parcelas_restantes() == 8

    def test_porcentagem_paga_zero(self):
        d = Divida("Teste", 1200.0, 100.0, 12)
        assert d.calcular_porcentagem_paga() == pytest.approx(0.0)

    def test_porcentagem_paga_metade(self):
        d = Divida("Teste", 1200.0, 100.0, 12, parcelas_pagas=6)
        assert d.calcular_porcentagem_paga() == pytest.approx(0.5)

    def test_porcentagem_paga_completa(self):
        d = Divida("Teste", 1200.0, 100.0, 12, parcelas_pagas=12)
        assert d.calcular_porcentagem_paga() == pytest.approx(1.0)

    def test_esta_quitada_false(self):
        d = Divida("Teste", 1200.0, 100.0, 12, parcelas_pagas=11)
        assert d.esta_quitada() is False

    def test_esta_quitada_true(self):
        d = Divida("Teste", 1200.0, 100.0, 12, parcelas_pagas=12)
        assert d.esta_quitada() is True


class TestDividaRegistrarPagamento:
    """Testes da mutação de estado via registrar_pagamento."""

    def test_registrar_um_pagamento(self):
        d = Divida("Teste", 1200.0, 100.0, 12, parcelas_pagas=0)
        d.registrar_pagamento(1)
        assert d.parcelas_pagas == 1

    def test_registrar_multiplos_pagamentos(self):
        d = Divida("Teste", 1200.0, 100.0, 12, parcelas_pagas=0)
        d.registrar_pagamento(3)
        assert d.parcelas_pagas == 3

    def test_exceder_limite_levanta_erro(self):
        d = Divida("Teste", 1200.0, 100.0, 12, parcelas_pagas=11)
        with pytest.raises(ValueError, match="exceder"):
            d.registrar_pagamento(2)

    def test_quantidade_zero_levanta_erro(self):
        d = Divida("Teste", 1200.0, 100.0, 12)
        with pytest.raises(ValueError, match="positiva"):
            d.registrar_pagamento(0)


class TestDividaSerializacao:
    """Testa a serialização da entidade para dicionário."""

    def test_to_dict_contem_campos_esperados(self):
        d = Divida("Nubank", 1200.0, 100.0, 12, CategoriaDivida.CARTAO, parcelas_pagas=6)
        d.id = 1
        resultado = d.to_dict()
        assert resultado["id"] == 1
        assert resultado["nome"] == "Nubank"
        assert resultado["valor_restante"] == pytest.approx(600.0)
        assert resultado["parcelas_restantes"] == 6
        assert resultado["porcentagem_paga"] == pytest.approx(50.0)
        assert resultado["esta_quitada"] is False
        assert resultado["categoria"] == CategoriaDivida.CARTAO.value

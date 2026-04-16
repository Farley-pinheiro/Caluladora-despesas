"""
app/models/divida.py — Entidade de Domínio: Dívida.
Contém apenas lógica de negócio pura, sem dependência de infraestrutura.
Princípio SOLID: SRP — Responsabilidade única de representar e calcular sobre uma dívida.
"""
from dataclasses import dataclass, field
from datetime import date
from enum import Enum
import calendar
from typing import Optional


class CategoriaDivida(str, Enum):
    """Categorias válidas de dívida — evita strings mágicas no sistema."""
    CARTAO = "Cartão de Crédito"
    EMPRESTIMO = "Empréstimo"
    FINANCIAMENTO = "Financiamento"
    ALUGUEL = "Aluguel"
    SAUDE = "Saúde"
    EDUCACAO = "Educação"
    OUTRO = "Outro"


@dataclass
class Divida:
    """
    Entidade de domínio que representa uma dívida parcelada.

    Atributos:
        nome: Nome ou descrição da dívida (ex: 'Cartão Nubank').
        valor_total: Valor total da dívida em reais.
        valor_parcela: Valor fixo de cada parcela mensal.
        total_parcelas: Número total de parcelas do contrato.
        categoria: Categoria da dívida (enum CategoriaDivida).
        parcelas_pagas: Quantidade de parcelas já quitadas.
        id: Identificador único (preenchido pelo repositório após persistência).
    """
    nome: str
    valor_total: float
    valor_parcela: float
    total_parcelas: int
    categoria: CategoriaDivida = CategoriaDivida.OUTRO
    parcelas_pagas: int = 0
    dia_vencimento: Optional[int] = None   # Dia do mês do vencimento (1–31)
    id: Optional[int] = field(default=None, compare=False)

    def __post_init__(self) -> None:
        """Validações de domínio executadas após a inicialização."""
        self._validar()

    def _validar(self) -> None:
        """Aplica as regras de negócio da entidade."""
        if not self.nome or not self.nome.strip():
            raise ValueError("O nome da dívida não pode ser vazio.")
        if self.valor_total <= 0:
            raise ValueError("O valor total deve ser maior que zero.")
        if self.valor_parcela <= 0:
            raise ValueError("O valor da parcela deve ser maior que zero.")
        if self.total_parcelas <= 0:
            raise ValueError("O total de parcelas deve ser maior que zero.")
        if self.parcelas_pagas < 0:
            raise ValueError("As parcelas pagas não podem ser negativas.")
        if self.parcelas_pagas > self.total_parcelas:
            raise ValueError("Parcelas pagas não podem exceder o total de parcelas.")
        if self.dia_vencimento is not None and not (1 <= self.dia_vencimento <= 31):
            raise ValueError("O dia de vencimento deve estar entre 1 e 31.")

    # -------------------------------------------------------------------------
    # Lógica de Domínio
    # -------------------------------------------------------------------------

    def calcular_valor_restante(self) -> float:
        """
        Retorna o valor ainda a ser pago.
        Quando todas as parcelas estão pagas, retorna 0.0 independentemente
        de eventuais diferenças entre valor_total e (valor_parcela × total_parcelas).
        """
        if self.esta_quitada():
            return 0.0
        return max(0.0, self.valor_total - (self.valor_parcela * self.parcelas_pagas))

    def calcular_parcelas_restantes(self) -> int:
        """Retorna a quantidade de parcelas ainda a vencer."""
        return max(0, self.total_parcelas - self.parcelas_pagas)

    def calcular_porcentagem_paga(self) -> float:
        """Retorna o percentual já pago (0.0 a 1.0)."""
        if self.total_parcelas <= 0:
            return 0.0
        return min(1.0, self.parcelas_pagas / self.total_parcelas)

    def esta_quitada(self) -> bool:
        """Retorna True se a dívida estiver totalmente paga."""
        return self.parcelas_pagas >= self.total_parcelas

    def dias_para_vencimento(self) -> Optional[int]:
        """
        Calcula quantos dias faltam para o próximo vencimento.
        Retorna None se `dia_vencimento` não estiver definido ou a dívida estiver quitada.
        """
        if self.dia_vencimento is None or self.esta_quitada():
            return None
        hoje = date.today()
        ultimo_dia_mes = calendar.monthrange(hoje.year, hoje.month)[1]
        dia = min(self.dia_vencimento, ultimo_dia_mes)
        vencimento_este_mes = date(hoje.year, hoje.month, dia)
        if vencimento_este_mes >= hoje:
            return (vencimento_este_mes - hoje).days
        # Já passou: calcula para o próximo mês
        proximo = hoje.month + 1
        ano = hoje.year + (1 if proximo > 12 else 0)
        proximo = proximo if proximo <= 12 else 1
        ultimo_dia_prox = calendar.monthrange(ano, proximo)[1]
        dia_prox = min(self.dia_vencimento, ultimo_dia_prox)
        return (date(ano, proximo, dia_prox) - hoje).days

    def registrar_pagamento(self, quantidade: int = 1) -> None:
        """Registra o pagamento de uma ou mais parcelas."""
        if quantidade <= 0:
            raise ValueError("A quantidade de parcelas a pagar deve ser positiva.")
        novo_total = self.parcelas_pagas + quantidade
        if novo_total > self.total_parcelas:
            raise ValueError("Não é possível exceder o número total de parcelas.")
        self.parcelas_pagas = novo_total

    def to_dict(self) -> dict:
        """Serializa a entidade para dicionário (useful para JSON responses)."""
        dias = self.dias_para_vencimento()
        return {
            "id": self.id,
            "nome": self.nome,
            "valor_total": self.valor_total,
            "valor_parcela": self.valor_parcela,
            "total_parcelas": self.total_parcelas,
            "categoria": self.categoria.value,
            "parcelas_pagas": self.parcelas_pagas,
            "dia_vencimento": self.dia_vencimento,
            "dias_para_vencimento": dias,
            "valor_restante": self.calcular_valor_restante(),
            "parcelas_restantes": self.calcular_parcelas_restantes(),
            "porcentagem_paga": round(self.calcular_porcentagem_paga() * 100, 1),
            "esta_quitada": self.esta_quitada(),
        }

    def __repr__(self) -> str:
        return (
            f"Divida(id={self.id}, nome='{self.nome}', "
            f"categoria={self.categoria.value}, "
            f"valor_total={self.valor_total:.2f}, "
            f"parcelas={self.parcelas_pagas}/{self.total_parcelas})"
        )

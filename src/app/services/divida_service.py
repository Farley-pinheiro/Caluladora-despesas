"""
app/services/divida_service.py — Lógica de Negócio e Cálculos Financeiros.
Princípio SOLID:
  - SRP: Única responsabilidade de orquestrar operações sobre Dívidas.
  - DIP: Depende da abstração BaseRepository, não do SQLite diretamente.
  - OCP: Novos cálculos podem ser adicionados sem modificar os existentes.
"""
from app.repositories.base_repository import BaseRepository
from app.models.divida import Divida, CategoriaDivida
from app.logger import get_logger

logger = get_logger(__name__)


class DividaService:
    """
    Orquestra casos de uso relacionados a dívidas.
    Recebe o repositório via injeção de dependência no construtor.
    """

    def __init__(self, repository: BaseRepository) -> None:
        self._repo = repository

    # ------------------------------------------------------------------
    # Casos de Uso — CRUD
    # ------------------------------------------------------------------

    def criar_divida(
        self,
        nome: str,
        valor_total: float,
        total_parcelas: int,
        categoria: str = "Outro",
        dia_vencimento: int | None = None,
    ) -> Divida:
        """
        Cria e persiste uma nova dívida após validação.
        O valor da parcela é calculado automaticamente: valor_total / total_parcelas.
        Levanta ValueError em caso de dados inválidos.
        """
        logger.info("Criando nova dívida.", extra={"nome": nome, "categoria": categoria})
        try:
            cat_enum = CategoriaDivida(categoria)
        except ValueError:
            cat_enum = CategoriaDivida.OUTRO

        valor_total_f = float(valor_total)
        total_parcelas_i = int(total_parcelas)
        valor_parcela = round(valor_total_f / total_parcelas_i, 2)

        divida = Divida(
            nome=nome.strip(),
            valor_total=valor_total_f,
            valor_parcela=valor_parcela,
            total_parcelas=total_parcelas_i,
            categoria=cat_enum,
            dia_vencimento=int(dia_vencimento) if dia_vencimento is not None else None,
        )
        salva = self._repo.save(divida)
        logger.info("Dívida criada com sucesso.", extra={"divida_id": salva.id, "valor_parcela": valor_parcela})
        return salva

    def listar_dividas(self) -> list[Divida]:
        """Retorna todas as dívidas cadastradas."""
        dividas = self._repo.find_all()
        logger.info("Listagem de dívidas concluída.", extra={"total": len(dividas)})
        return dividas

    def buscar_divida(self, divida_id: int) -> Divida:
        """
        Busca uma dívida pelo ID.
        Levanta ValueError se não encontrada.
        """
        divida = self._repo.find_by_id(divida_id)
        if divida is None:
            logger.warning("Dívida não encontrada.", extra={"divida_id": divida_id})
            raise ValueError(f"Dívida com id={divida_id} não encontrada.")
        return divida

    def excluir_divida(self, divida_id: int) -> bool:
        """
        Remove uma dívida pelo ID.
        Levanta ValueError se não existir.
        """
        removida = self._repo.delete(divida_id)
        if not removida:
            raise ValueError(f"Dívida com id={divida_id} não encontrada para exclusão.")
        logger.info("Dívida excluída.", extra={"divida_id": divida_id})
        return True

    # ------------------------------------------------------------------
    # Casos de Uso — Pagamento
    # ------------------------------------------------------------------

    def registrar_pagamento(self, divida_id: int, quantidade: int = 1) -> Divida:
        """
        Registra o pagamento de uma ou mais parcelas de uma dívida.
        Levanta ValueError se a dívida não existir ou estado inválido.
        """
        logger.info("Registrando pagamento.", extra={"divida_id": divida_id, "quantidade": quantidade})
        divida = self.buscar_divida(divida_id)

        if divida.esta_quitada():
            raise ValueError("Esta dívida já está completamente quitada.")

        divida.registrar_pagamento(quantidade)
        self._repo.update(divida)
        logger.info(
            "Pagamento registrado.",
            extra={
                "divida_id": divida_id,
                "parcelas_pagas": divida.parcelas_pagas,
                "parcelas_restantes": divida.calcular_parcelas_restantes(),
            },
        )
        return divida

    # ------------------------------------------------------------------
    # Casos de Uso — Cálculos Financeiros Agregados
    # ------------------------------------------------------------------

    def calcular_total_geral_restante(self, dividas: list[Divida] | None = None) -> float:
        """
        Soma o valor restante de todas as dívidas (ou da lista fornecida).
        Considera apenas dívidas não quitadas.
        """
        if dividas is None:
            dividas = self._repo.find_all()
        total = sum(d.calcular_valor_restante() for d in dividas if not d.esta_quitada())
        logger.info("Total geral calculado.", extra={"total_restante": total})
        return round(total, 2)

    def calcular_gasto_mensal_total(self, dividas: list[Divida] | None = None) -> float:
        """
        Soma o valor mensal (valor_parcela) de todas as dívidas ativas.
        Representa o compromisso financeiro mensal do usuário.
        """
        if dividas is None:
            dividas = self._repo.find_all()
        total_mensal = sum(d.valor_parcela for d in dividas if not d.esta_quitada())
        logger.info("Gasto mensal calculado.", extra={"total_mensal": total_mensal})
        return round(total_mensal, 2)

    def obter_resumo_geral(self) -> dict:
        """
        Retorna um dicionário com métricas gerais para o Dashboard.
        """
        dividas = self._repo.find_all()
        ativas = [d for d in dividas if not d.esta_quitada()]
        quitadas = [d for d in dividas if d.esta_quitada()]

        resumo = {
            "total_dividas": len(dividas),
            "dividas_ativas": len(ativas),
            "dividas_quitadas": len(quitadas),
            "total_restante": self.calcular_total_geral_restante(dividas),
            "gasto_mensal": self.calcular_gasto_mensal_total(ativas),
            "dividas": [d.to_dict() for d in dividas],
        }
        logger.info("Resumo geral gerado.", extra={"total_dividas": resumo["total_dividas"]})
        return resumo

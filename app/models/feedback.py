from pydantic import BaseModel, Field
from typing import Optional


class FeedbackRequest(BaseModel):
    tipologia_chave: str = Field(..., description="Chave canônica da tipologia (ex: janela_correr_2_folhas)")
    peca_classificacao: str = Field(..., description="Classificação da peça (ex: correr, movel, fixa)")
    ferragem_nome: str = Field(..., description="Nome da ferragem com erro (ex: Roldana)")
    campo_corrigido: str = Field(..., description="Campo corrigido: 'y_formula' ou 'x_formula'")
    valor_correto: str = Field(..., description="Fórmula correta (ex: 'altura - 20')")
    observacao: Optional[str] = Field(None, description="Observação livre do vidraceiro")


class FeedbackResponse(BaseModel):
    aceito: bool
    mensagem: str
    tipologia_chave: str
    ferragem_nome: str
    campo_corrigido: str
    valor_anterior: Optional[str] = None
    valor_novo: str

"""Schemas Pydantic para o endpoint de feedback do vidraceiro."""
from pydantic import BaseModel, Field
from typing import Optional


class FeedbackRequest(BaseModel):
    """Correção de fórmula de posicionamento enviada pelo vidraceiro."""

    tipologia_chave: str = Field(..., description="Chave canônica da tipologia (ex: janela_correr_2_folhas)")
    peca_classificacao: str = Field(..., description="Classificação da peça (ex: correr, movel, fixa)")
    ferragem_nome: str = Field(..., description="Nome da ferragem com erro (ex: Roldana)")
    campo_corrigido: str = Field(..., description="Campo corrigido: 'y_formula' ou 'x_formula'")
    valor_correto: str = Field(..., description="Fórmula correta (ex: 'altura - 20')")
    observacao: Optional[str] = Field(None, description="Observação livre do vidraceiro")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "tipologia_chave": "janela_correr_2_folhas",
                    "peca_classificacao": "correr",
                    "ferragem_nome": "Roldana",
                    "campo_corrigido": "y_formula",
                    "valor_correto": "altura - 20",
                    "observacao": "Roldana deve ficar 20mm da borda inferior",
                }
            ]
        }
    }


class FeedbackResponse(BaseModel):
    """Resultado do processamento da correção na Constitution."""

    aceito: bool
    mensagem: str
    tipologia_chave: str
    ferragem_nome: str
    campo_corrigido: str
    valor_anterior: Optional[str] = None
    valor_novo: str

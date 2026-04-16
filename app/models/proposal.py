"""Models Pydantic para geração de proposta comercial em PDF."""
from typing import Optional
from pydantic import BaseModel, Field
from app.models._limits import DIMENSAO_MIN_MM, DIMENSAO_MAX_MM, ESPESSURA_MIN_MM, ESPESSURA_MAX_MM, QUANTIDADE_MAX_ITEM


class ClienteInfo(BaseModel):
    """Dados do cliente destinatário da proposta."""

    nome: str
    telefone: Optional[str] = None
    email: Optional[str] = None
    endereco: Optional[str] = None
    cpf_cnpj: Optional[str] = None


class EmpresaInfo(BaseModel):
    """Dados da empresa de vidraçaria — white-label."""

    nome: str
    telefone: Optional[str] = None
    email: Optional[str] = None
    endereco: Optional[str] = None
    cnpj: Optional[str] = None
    logo_base64: Optional[str] = None   # PNG/JPG em base64 (sem prefixo data:...)
    cor_primaria: str = "#1a5276"       # cor da marca (hex)
    cor_secundaria: str = "#2c3e50"     # cor de destaque (hex)


class ItemProposta(BaseModel):
    """Item individual do orçamento."""

    descricao: str = Field(..., min_length=1, max_length=500)
    tipologia: str = Field(..., min_length=1, max_length=200)
    largura: float = Field(
        ...,
        ge=DIMENSAO_MIN_MM,
        le=DIMENSAO_MAX_MM,
        description=f"Largura em mm ({DIMENSAO_MIN_MM}–{DIMENSAO_MAX_MM})",
    )
    altura: float = Field(
        ...,
        ge=DIMENSAO_MIN_MM,
        le=DIMENSAO_MAX_MM,
        description=f"Altura em mm ({DIMENSAO_MIN_MM}–{DIMENSAO_MAX_MM})",
    )
    quantidade: int = Field(1, ge=1, le=QUANTIDADE_MAX_ITEM)
    espessura: Optional[int] = Field(8, ge=ESPESSURA_MIN_MM, le=ESPESSURA_MAX_MM)
    cor_vidro: Optional[str] = "incolor"
    fabricante: Optional[str] = None        # "HE", "AL", "SM"
    valor_unitario: Optional[float] = Field(None, ge=0)
    valor_total: Optional[float] = Field(None, ge=0)
    observacoes: Optional[str] = None


class CondicoesPagamento(BaseModel):
    """Condições de pagamento da proposta."""

    forma: str = "À vista"
    desconto_percentual: Optional[float] = None
    parcelas: Optional[int] = None
    observacoes: Optional[str] = None


class ProposalRequest(BaseModel):
    """Request para gerar proposta comercial em PDF."""

    empresa: EmpresaInfo
    cliente: ClienteInfo
    itens: list[ItemProposta]
    condicoes: Optional[CondicoesPagamento] = None
    validade_dias: int = 15
    observacoes_gerais: Optional[str] = None
    numero_proposta: Optional[str] = None   # gerado automaticamente se não informado
    incluir_desenho: bool = True            # incluir PNG do desenho técnico por item
    incluir_ferragens: bool = True          # listar ferragens de cada peça

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "empresa": {
                        "nome": "Vidraçaria São José",
                        "telefone": "(85) 99999-9999",
                        "cnpj": "12.345.678/0001-99",
                        "cor_primaria": "#1a5276",
                    },
                    "cliente": {
                        "nome": "João da Silva",
                        "telefone": "(85) 98888-8888",
                        "endereco": "Rua das Flores, 123 — Fortaleza/CE",
                    },
                    "itens": [
                        {
                            "descricao": "Porta Pivotante Simples",
                            "tipologia": "porta_pivotante_simples",
                            "largura": 900,
                            "altura": 2100,
                            "quantidade": 1,
                            "espessura": 8,
                            "fabricante": "HE",
                            "valor_unitario": 1250.00,
                            "valor_total": 1250.00,
                        },
                        {
                            "descricao": "Box de Banheiro Frontal",
                            "tipologia": "box_banheiro",
                            "largura": 800,
                            "altura": 1900,
                            "quantidade": 2,
                            "valor_unitario": 980.00,
                            "valor_total": 1960.00,
                        },
                    ],
                    "condicoes": {"forma": "2x no cartão", "parcelas": 2},
                    "validade_dias": 15,
                    "incluir_desenho": True,
                    "incluir_ferragens": True,
                }
            ]
        }
    }


class ProposalResponse(BaseModel):
    """Metadados da proposta gerada (sem o conteúdo binário do PDF)."""

    numero_proposta: str
    total_itens: int
    valor_total: Optional[float] = None
    pdf_bytes: int                  # tamanho do PDF em bytes (0 no preview)
    validade_ate: Optional[str] = None  # ISO date YYYY-MM-DD

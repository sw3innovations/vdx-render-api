from __future__ import annotations
from typing import Literal, Optional
from pydantic import BaseModel, Field


class PendentePost(BaseModel):
    descricao: str = Field(..., min_length=3, max_length=500)
    contexto: Optional[dict] = Field(None)
    fonte: str = Field(..., min_length=1, max_length=50)


class AliasPost(BaseModel):
    alias: str = Field(..., min_length=1, max_length=100)
    canonical_id: str = Field(..., min_length=1, max_length=50)
    tipo: Literal["truncamento", "apelido_comercial", "fonetico", "abreviacao", "outro"]
    fonte: str = Field(..., min_length=1, max_length=50)
    confidence: Literal["alto", "medio", "baixo"] = "medio"


class AlternativaPost(BaseModel):
    funcao_id: str = Field(..., min_length=1, max_length=50)
    canonical_id: str = Field(..., min_length=1, max_length=50)
    ordem_default: int = Field(99, ge=1, le=999)
    indicacao_uso: Optional[str] = Field(None, max_length=500)


class EntryPost(BaseModel):
    nicho: str = Field("vidros", max_length=50)
    tipo: str = Field(..., min_length=1, max_length=50)
    chave: str = Field(..., min_length=1, max_length=200)
    dados: dict = Field(...)
    origem: str = Field(..., min_length=1, max_length=100)
    confianca: float = Field(0.7, ge=0.0, le=1.0)


class PendenteResolver(BaseModel):
    resolucao: Literal["aprovado", "descartado", "duplicado"]
    nota: Optional[str] = Field(None, max_length=500)
    validado_por: str = Field(..., min_length=1, max_length=50)
    promover_para: Literal["alias", "alternativa", "entry", "nenhum"] = "nenhum"
    dados_promocao: Optional[dict] = Field(None)

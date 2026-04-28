from __future__ import annotations
from typing import Literal, Optional
from pydantic import BaseModel, Field


class FerragemPosicaoSchema(BaseModel):
    codigo: str = Field(..., min_length=1, max_length=50)
    fabricante_id: Optional[str] = Field(None, max_length=50)
    tipo: str = Field(..., min_length=1, max_length=50)
    x_mm: float = Field(..., ge=0)
    y_mm: float = Field(..., ge=0)


class PainelSchema(BaseModel):
    nome: str = Field(..., min_length=1, max_length=100)
    largura_mm: float = Field(..., ge=100, le=6000)
    altura_mm: float = Field(..., ge=100, le=6000)
    classificacao: Literal["movel", "fixo", "correr", "bandeira"] = "movel"
    ferragens: list[FerragemPosicaoSchema] = []


class OpcoesRenderSchema(BaseModel):
    cor: Literal["incolor", "verde", "fume", "bronze", "azul", "espelho"] = "incolor"
    acabamento: Literal["cromado", "inox", "preto", "dourado"] = "cromado"
    incluir_png: bool = True


class TipologiaImportadaSchema(BaseModel):
    nome: str = Field(..., min_length=1, max_length=200)
    paineis: list[PainelSchema] = Field(..., min_length=1)
    opcoes: OpcoesRenderSchema = OpcoesRenderSchema()

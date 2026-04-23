"""Schemas Smart Vision — foto/croqui → projeto completo."""
from __future__ import annotations

from typing import List, Optional
from pydantic import BaseModel, Field


class PhotoToProjectRequest(BaseModel):
    """Foto real do vão + contexto textual opcional."""

    image_base64: str = Field(..., description="Imagem em base64 (com ou sem prefix data:)")
    contexto: str = Field("", max_length=500, description="Contexto do cliente (ex: cozinha aberta)")
    cor_vidro: Optional[str] = Field(None, description="Sobrescreve cor sugerida pela IA")
    espessura_vidro_mm: Optional[float] = Field(None, ge=3, le=25)

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "image_base64": "/9j/4AAQSkZJRg...",
                    "contexto": "Porta da varanda, cliente quer vidro fume",
                }
            ]
        }
    }


class SketchToProjectRequest(BaseModel):
    """Croqui/desenho a mão + notas textuais do projetista."""

    image_base64: str = Field(..., description="Croqui em base64 (com ou sem prefix data:)")
    notas: str = Field("", max_length=500, description="Notas do projetista")
    cor_vidro: Optional[str] = Field(None)
    espessura_vidro_mm: Optional[float] = Field(None, ge=3, le=25)


class VisionAnalysis(BaseModel):
    """Resultado estruturado da análise Claude Vision."""

    tipologia_sugerida: str
    largura_mm: int
    altura_mm: int
    tipo_abertura: str
    num_folhas: int
    espessura_vidro_mm: int
    cor_vidro: str
    observacoes: str
    confianca: float


class SmartProjectResponse(BaseModel):
    """Resposta completa — análise + SVG + scene 3D + ferragens + viewer URL."""

    analise: VisionAnalysis
    tipologia_chave: str
    svg: str
    scene: dict
    pecas: List[dict] = []
    ferragens: List[dict] = []
    kit: Optional[dict] = None
    viewer_url: Optional[str] = None
    viewer_token: Optional[str] = None
    viewer_expires_in: Optional[int] = None
    engine: str = ""
    versao_api: str = "1.0.0"

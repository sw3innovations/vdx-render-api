from pydantic import BaseModel, Field
from typing import Optional, List
from enum import Enum


class Formato(str, Enum):
    svg = "svg"
    # png e pdf = fase 2


class Layout(str, Enum):
    auto = "auto"
    paralelas = "paralelas"
    bandeira_topo = "bandeira_topo"
    canto_l = "canto_l"
    fixo_movel_fixo = "fixo_movel_fixo"
    basculante = "basculante"
    cobertura = "cobertura"
    paineis_lineares = "paineis_lineares"


class Tema(str, Enum):
    tecnico = "tecnico"   # azul técnico VDX
    clean = "clean"       # preto e branco


class TipoVisual(str, Enum):
    linha_h = "linha_h"       # linha horizontal (bate-fecha, trinco)
    circulo = "circulo"       # círculo com crosshair (puxador)
    retangulo = "retangulo"   # pequeno retângulo (dobradiça, fechadura)


class FerragemInput(BaseModel):
    tipo: str                              # "bate_fecha"|"puxador"|"dobradica"|"trinco"|"fechadura"
    nome: Optional[str] = None
    posicao_y_mm: Optional[float] = None  # None → Claude infere
    distancia_borda_mm: Optional[float] = None
    tipo_visual: Optional[TipoVisual] = None


class FerragemEnriquecida(BaseModel):
    tipo: str
    nome: Optional[str] = None
    posicao_y_mm: float
    distancia_borda_mm: float
    tipo_visual: TipoVisual
    inferida_por_ia: bool = False


class PecaInput(BaseModel):
    nome: str
    largura_mm: float
    altura_mm: float
    ferragens: List[FerragemInput] = []


class PecaEnriquecida(BaseModel):
    nome: str
    largura_mm: float
    altura_mm: float
    ferragens: List[FerragemEnriquecida] = []


class Opcoes(BaseModel):
    tema: Tema = Tema.tecnico
    mostrar_cotas: bool = True
    mostrar_nome_peca: bool = True
    mostrar_ferragens: bool = True
    largura_px: int = 480
    altura_px: int = 360


class RenderRequest(BaseModel):
    formato: Formato = Formato.svg
    tipologia_nome: str = ""
    layout: Layout = Layout.auto
    pecas: List[PecaInput]
    opcoes: Opcoes = Opcoes()


class RenderResponse(BaseModel):
    svg: str
    largura_px: int
    altura_px: int
    layout_usado: str
    ferragens_inferidas: bool
    claude_usado: bool
    versao_api: str = "1.0.0"

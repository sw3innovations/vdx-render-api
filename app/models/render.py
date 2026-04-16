"""Schemas Pydantic do pipeline de render — request e response do VDX Glass Engine."""
from pydantic import BaseModel, Field
from typing import Optional, List
from enum import Enum
from app.models._limits import DIMENSAO_MIN_MM, DIMENSAO_MAX_MM, ESPESSURA_MIN_MM, ESPESSURA_MAX_MM


class Formato(str, Enum):
    """Formato de saída do render."""

    svg = "svg"
    png = "png"
    pdf = "pdf"


class Layout(str, Enum):
    """Algoritmo de layout para posicionamento das peças no canvas."""

    auto = "auto"
    paralelas = "paralelas"
    bandeira_topo = "bandeira_topo"
    canto_l = "canto_l"
    fixo_movel_fixo = "fixo_movel_fixo"
    basculante = "basculante"
    cobertura = "cobertura"
    paineis_lineares = "paineis_lineares"


class Tema(str, Enum):
    """Tema visual do SVG gerado."""

    tecnico = "tecnico"   # azul técnico VDX
    clean = "clean"       # preto e branco


class TipoVisual(str, Enum):
    """Representação gráfica da ferragem no desenho técnico."""

    linha_h = "linha_h"       # linha horizontal (bate-fecha, trinco)
    circulo = "circulo"       # círculo com crosshair (puxador)
    retangulo = "retangulo"   # pequeno retângulo (dobradiça, fechadura)


class FerragemInput(BaseModel):
    """Ferragem informada pelo cliente na request — posicionamento pode ser inferido pela IA."""

    tipo: str                              # "bate_fecha"|"puxador"|"dobradica"|"trinco"|"fechadura"
    nome: Optional[str] = None
    posicao_y_mm: Optional[float] = None  # None → Claude infere
    distancia_borda_mm: Optional[float] = None
    tipo_visual: Optional[TipoVisual] = None


class FerragemEnriquecida(BaseModel):
    """Ferragem após enriquecimento com posição calculada e tipo visual resolvido."""

    tipo: str
    nome: Optional[str] = None
    posicao_y_mm: float
    distancia_borda_mm: float
    tipo_visual: TipoVisual
    inferida_por_ia: bool = False


class PuxadorInput(BaseModel):
    """Especificação explícita do puxador enviada pelo frontend."""

    tipo_furacao: str           # "EIXO_600", "EIXO_300", "PUXADOR_UM_FURO"
    eixo_mm: Optional[float] = None  # distância entre furos (ex: 600, 300)


class PecaInput(BaseModel):
    """Peça de vidro com dimensões e ferragens a renderizar."""

    nome: str
    largura_mm: float = Field(
        ...,
        ge=DIMENSAO_MIN_MM,
        le=DIMENSAO_MAX_MM,
        description=f"Largura em mm ({DIMENSAO_MIN_MM}–{DIMENSAO_MAX_MM})",
    )
    altura_mm: float = Field(
        ...,
        ge=DIMENSAO_MIN_MM,
        le=DIMENSAO_MAX_MM,
        description=f"Altura em mm ({DIMENSAO_MIN_MM}–{DIMENSAO_MAX_MM})",
    )
    ferragens: List[FerragemInput] = []
    puxador: Optional[PuxadorInput] = None  # puxador explícito do frontend


class PecaEnriquecida(BaseModel):
    """Peça após resolução de ferragens pela Constitution ou pela IA."""

    nome: str
    largura_mm: float
    altura_mm: float
    ferragens: List[FerragemEnriquecida] = []


class Opcoes(BaseModel):
    """Opções visuais do SVG gerado."""

    tema: Tema = Tema.tecnico
    mostrar_cotas: bool = True
    mostrar_nome_peca: bool = True
    mostrar_ferragens: bool = True
    largura_px: int = 480
    altura_px: int = 360


class RenderRequest(BaseModel):
    """Body da request POST /render — peças + opções de saída."""

    formato: Formato = Formato.svg
    tipologia_nome: str = ""
    layout: Layout = Layout.auto
    pecas: List[PecaInput]
    opcoes: Opcoes = Opcoes()
    espessura_vidro_mm: Optional[float] = Field(
        None,
        ge=ESPESSURA_MIN_MM,
        le=ESPESSURA_MAX_MM,
        description=f"Espessura do vidro em mm ({ESPESSURA_MIN_MM}–{ESPESSURA_MAX_MM})",
    )  # ex: 8.0, 10.0
    tipo_vidro: Optional[str] = None             # "temperado"|"laminado"|"aramado"|"comum"

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "tipologia_nome": "porta_pivotante_simples",
                    "layout": "auto",
                    "pecas": [
                        {"nome": "Porta", "largura_mm": 900, "altura_mm": 2100}
                    ],
                    "espessura_vidro_mm": 8.0,
                    "tipo_vidro": "temperado",
                }
            ]
        }
    }


class FerragemPosicionada(BaseModel):
    """Ferragem com coordenadas absolutas no desenho técnico (mm)."""

    codigo: Optional[str] = None
    nome: str
    tipo: str
    x_mm: float
    y_mm: float
    lado: str                          # "esquerdo", "direito", "centro"
    visual: str                        # "retangulo", "circulo", "linha_h"
    recorte: str = "padrao_sm"         # "padrao_sm", "furo_passante", "nenhum"


class PecaRenderizada(BaseModel):
    """Peça após render completo — classificação e ferragens posicionadas."""

    nome: str
    largura_mm: float
    altura_mm: float
    classificacao: str                 # "fixa" ou "movel"
    ferragens: List[FerragemPosicionada] = []


class KitFerragem(BaseModel):
    """Kit de ferragens recomendado para a tipologia renderizada."""

    codigo: str
    nome: str
    itens: List[dict] = []
    puxador_separado: bool = True


class RegrasInterativas(BaseModel):
    """Parâmetros para o componente interativo de ajuste de puxador no frontend."""

    puxador_centro_y_mm: Optional[float] = None
    puxador_centro_x_mm: Optional[float] = None
    formula_puxador: str = "centro_y ± eixo_mm / 2"
    eixos_disponiveis: List[int] = [100, 200, 300, 400, 500, 600, 800]
    nomes_pecas_fixas: List[str] = [
        "FIXO", "Bandeira", "Painel", "Lateral fixa",
        "Vidro fixo", "Lateral", "Fixo 1", "Fixo 2", "Folha fixa"
    ]


class RenderResponse(BaseModel):
    """Resposta do pipeline de render — SVG + metadados + kit de ferragens."""

    svg: str
    pecas: List[PecaRenderizada] = []
    kit: Optional[KitFerragem] = None
    regras_interativas: Optional[RegrasInterativas] = None
    alertas_norma: List[dict] = []
    metadata: dict = {}
    # manter campos legados para compatibilidade
    largura_px: int = 800
    altura_px: int = 600
    layout_usado: str = ""
    ferragens_inferidas: bool = False
    claude_usado: bool = False
    versao_api: str = "1.0.0"

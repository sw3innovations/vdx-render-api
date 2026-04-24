"""
Scene Builder — converte RenderResponse em Scene JSON para o Three.js Viewer.

Input : RenderResponse (pecas posicionadas + metadata do ConstitutionEngine)
Output: Scene JSON versionado, consumido pelo viewer HTML e pelo frontend Next.js

Convenções de coordenadas:
  - y_mm do ConstitutionEngine já é medido da BASE para CIMA (0 = piso)
  - Direto em Three.js: y_3d = y_mm (sem inversão)
  - Centering em x: toda a montagem é centrada em x=0
  - z = 0 é o plano do vidro; ferragens ficam em z=±(esp/2 + prof_ferr/2)
  - Unidades: milímetros (1 unit Three.js = 1mm)
"""
from __future__ import annotations
from typing import Optional
from app.models.render import RenderResponse, PecaRenderizada, FerragemPosicionada


# ─── Materiais PBR fotorrealistas ─────────────────────────────────────────────

MATERIAIS_PBR: dict[str, dict] = {
    "cromado": {
        "cor": "#E8E8E8",
        "roughness": 0.05,
        "metalness": 1.0,
        "clearcoat": 0.8,
        "clearcoatRoughness": 0.1,
        "envMapIntensity": 1.5,
    },
    "inox_escovado": {
        "cor": "#D0D0D0",
        "roughness": 0.30,
        "metalness": 0.95,
        "clearcoat": 0.2,
        "clearcoatRoughness": 0.3,
        "envMapIntensity": 0.8,
    },
    "inox": {
        "cor": "#D4D4D4",
        "roughness": 0.20,
        "metalness": 0.90,
        "clearcoat": 0.3,
        "clearcoatRoughness": 0.2,
        "envMapIntensity": 1.0,
    },
    "preto_fosco": {
        "cor": "#1A1A1A",
        "roughness": 0.70,
        "metalness": 0.10,
        "clearcoat": 0.0,
        "envMapIntensity": 0.3,
    },
    "preto_brilhante": {
        "cor": "#0A0A0A",
        "roughness": 0.10,
        "metalness": 0.30,
        "clearcoat": 1.0,
        "clearcoatRoughness": 0.05,
        "envMapIntensity": 1.2,
    },
    "preto": {
        "cor": "#1A1A1A",
        "roughness": 0.40,
        "metalness": 0.30,
        "clearcoat": 0.2,
        "envMapIntensity": 0.5,
    },
    "branco": {
        "cor": "#F5F5F0",
        "roughness": 0.60,
        "metalness": 0.0,
        "clearcoat": 0.3,
        "clearcoatRoughness": 0.2,
        "envMapIntensity": 0.4,
    },
    "bronze": {
        "cor": "#8B6914",
        "roughness": 0.25,
        "metalness": 0.85,
        "clearcoat": 0.5,
        "clearcoatRoughness": 0.1,
        "envMapIntensity": 1.0,
    },
    "dourado": {
        "cor": "#D4AF37",
        "roughness": 0.15,
        "metalness": 0.95,
        "clearcoat": 0.7,
        "clearcoatRoughness": 0.1,
        "envMapIntensity": 1.3,
    },
    "fosco": {
        "cor": "#A0A0A0",
        "roughness": 0.70,
        "metalness": 0.50,
        "clearcoat": 0.0,
        "envMapIntensity": 0.3,
    },
    "default": {
        "cor": "#808080",
        "roughness": 0.40,
        "metalness": 0.50,
        "clearcoat": 0.1,
        "envMapIntensity": 0.5,
    },
}

# tipo_ferragem → acabamento padrão
_TIPO_ACABAMENTO: dict[str, str] = {
    "dobradica":       "cromado",
    "pivo":            "cromado",
    "fechadura":       "cromado",
    "puxador":         "cromado",
    "trinco":          "cromado",
    "bate_fecha":      "preto",
    "roldana":         "fosco",
    "suporte":         "inox",
}

GEOMETRIAS: dict[str, dict] = {
    "dobradica":        {"tipo": "box",      "largura": 30,  "altura": 50,  "profundidade": 15},
    "pivo":             {"tipo": "cylinder", "raio":    8,   "altura": 40,  "profundidade": 16},
    "fechadura":        {"tipo": "box",      "largura": 73,  "altura": 45,  "profundidade": 20},
    "contra_fechadura": {"tipo": "box",      "largura": 40,  "altura": 45,  "profundidade": 15},
    "puxador":          {"tipo": "cylinder", "raio":    12,  "altura": 200, "profundidade": 24},
    "trinco":           {"tipo": "box",      "largura": 30,  "altura": 20,  "profundidade": 10},
    "roldana":          {"tipo": "cylinder", "raio":    15,  "altura": 10,  "profundidade": 30},
    "bate_fecha":       {"tipo": "box",      "largura": 20,  "altura": 60,  "profundidade": 12},
    "suporte":          {"tipo": "box",      "largura": 30,  "altura": 30,  "profundidade": 20},
    "default":          {"tipo": "box",      "largura": 25,  "altura": 25,  "profundidade": 10},
}

# Cores e propriedades PBR físicas do vidro
CORES_VIDRO: dict[str, dict] = {
    "incolor": {
        "cor": "#FFFFFF",
        "opacidade": 0.08,
        "transmission": 0.96,
        "ior": 1.52,
        "thickness": 8,
        "roughness": 0.0,
        "metalness": 0.0,
        "attenuationColor": "#FFFFFF",
        "attenuationDistance": 200,
        "clearcoat": 1.0,
        "clearcoatRoughness": 0.03,
        "envMapIntensity": 0.3,
    },
    "verde": {
        "cor": "#4A7A5B",
        "opacidade": 0.12,
        "transmission": 0.88,
        "ior": 1.52,
        "thickness": 8,
        "roughness": 0.0,
        "metalness": 0.0,
        "attenuationColor": "#2D5A3D",
        "attenuationDistance": 60,
        "clearcoat": 1.0,
        "clearcoatRoughness": 0.03,
        "envMapIntensity": 0.6,
    },
    "fume": {
        "cor": "#3A3A3A",
        "opacidade": 0.25,
        "transmission": 0.72,
        "ior": 1.52,
        "thickness": 8,
        "roughness": 0.0,
        "metalness": 0.0,
        "attenuationColor": "#1A1A1A",
        "attenuationDistance": 20,
        "clearcoat": 1.0,
        "clearcoatRoughness": 0.03,
        "envMapIntensity": 0.7,
    },
    "bronze": {
        "cor": "#6B5B3A",
        "opacidade": 0.18,
        "transmission": 0.78,
        "ior": 1.52,
        "thickness": 8,
        "roughness": 0.0,
        "metalness": 0.0,
        "attenuationColor": "#4A3A1A",
        "attenuationDistance": 35,
        "clearcoat": 1.0,
        "clearcoatRoughness": 0.03,
        "envMapIntensity": 0.6,
    },
    "espelho": {
        "cor": "#E0E0E0",
        "opacidade": 0.05,
        "transmission": 0.05,
        "ior": 1.52,
        "thickness": 8,
        "roughness": 0.05,
        "metalness": 0.95,
        "attenuationColor": "#C0C0C0",
        "attenuationDistance": 5,
        "clearcoat": 1.0,
        "clearcoatRoughness": 0.03,
        "envMapIntensity": 2.0,
    },
    "default": {
        "cor": "#B8D4E3",
        "opacidade": 0.10,
        "transmission": 0.92,
        "ior": 1.52,
        "thickness": 8,
        "roughness": 0.0,
        "metalness": 0.0,
        "attenuationColor": "#FFFFFF",
        "attenuationDistance": 150,
        "clearcoat": 1.0,
        "clearcoatRoughness": 0.03,
        "envMapIntensity": 0.3,
    },
}


# ─── Family detection ─────────────────────────────────────────────────────────

# Order matters: more specific patterns first
_FAMILIA_KEYWORDS: list[tuple[str, list[str]]] = [
    ("box_canto",    ["box_canto"]),
    ("cobertura",    ["cobertura"]),
    ("sacada",       ["sacada"]),
    ("guarda_corpo", ["guarda_corpo"]),
    ("balcao",       ["balcao", "balcão", "pia"]),
    ("divisoria",    ["divisoria", "divisória", "painel"]),
    ("vitrine",      ["vitrine"]),
    ("janela",       ["janela", "maxim"]),
    ("especial",     ["diâmetro", "diametro"]),
]

# Families that appear embedded in a wall (show vao frame)
_FAMILIA_VAO_PRESENTE: frozenset[str] = frozenset({"porta", "janela"})

# mm from floor: default cobertura installation height
_COBERTURA_INSTALL_H = 2200


def _detectar_familia(tipologia: str) -> str:
    t = tipologia.lower()
    for familia, keywords in _FAMILIA_KEYWORDS:
        if any(k in t for k in keywords):
            return familia
    return "porta"


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _r(v: float) -> float:
    return round(v, 1)


def _pbr_material(tipo_ferragem: str) -> dict:
    finish = _TIPO_ACABAMENTO.get(tipo_ferragem, "default")
    m = MATERIAIS_PBR.get(finish, MATERIAIS_PBR["default"])
    result = {"tipo": finish, "cor": m["cor"], "roughness": m["roughness"], "metalness": m["metalness"]}
    for key in ("clearcoat", "clearcoatRoughness", "envMapIntensity"):
        if key in m:
            result[key] = m[key]
    return result


def _geom(tipo_ferragem: str) -> dict:
    return dict(GEOMETRIAS.get(tipo_ferragem, GEOMETRIAS["default"]))


def _profundidade(geom: dict) -> float:
    """Profundidade efetiva da geometria para cálculo de z."""
    return geom.get("profundidade", geom.get("raio", 10) * 2)


# ─── SceneBuilder ─────────────────────────────────────────────────────────────

class SceneBuilder:
    """Converte RenderResponse → Scene JSON para o Three.js Viewer."""

    def build(
        self,
        resp: RenderResponse,
        espessura_vidro: float = 8.0,
        cor_vidro: str = "default",
    ) -> dict:
        """
        Parâmetros:
            resp            : RenderResponse do render_orchestrator.executar()
            espessura_vidro : espessura do vidro em mm (default 8)
            cor_vidro       : chave de cor ('incolor','verde','fume','bronze','espelho','default')
        """
        tipologia = resp.metadata.get("tipologia_chave", "")
        layout    = resp.metadata.get("layout_usado", "paralelas")
        familia   = _detectar_familia(tipologia)

        pecas = list(resp.pecas)
        offsets, total_largura, total_altura = self._compute_layout(pecas, layout)
        ferragens = self._build_ferragens(pecas, offsets, espessura_vidro, total_largura)

        vao_presente = familia in _FAMILIA_VAO_PRESENTE

        if familia == "box_canto":
            vidros = self._build_vidros_box_canto(pecas, tipologia, espessura_vidro, cor_vidro)
        elif familia == "cobertura":
            vidros = self._build_vidros_cobertura(pecas, tipologia, espessura_vidro, cor_vidro)
        else:
            vidros = self._build_vidros(pecas, offsets, tipologia, espessura_vidro, cor_vidro, total_largura)

        return {
            "version":   "2.0",
            "tipologia":  tipologia,
            "layout":     layout,
            "dimensoes": {
                "largura":         _r(total_largura),
                "altura":          _r(total_altura),
                "espessura_vidro": espessura_vidro,
            },
            "unidade":   "mm",
            "vidros":    vidros,
            "ferragens": ferragens,
            "vao":       self._build_vao(total_largura, total_altura, presente=vao_presente),
            "ambiente":  self._build_ambiente(total_largura, total_altura),
        }

    # ── Layout ────────────────────────────────────────────────────────────────

    def _compute_layout(
        self, pecas: list[PecaRenderizada], layout: str
    ) -> tuple[list[dict], float, float]:
        """Retorna (offsets_por_peca, total_largura, total_altura)."""
        if not pecas:
            return [], 900.0, 2100.0

        offsets: list[dict] = []

        if layout == "basculante":
            y = 0.0
            max_w = max(p.largura_mm for p in pecas)
            for p in pecas:
                offsets.append({"x": 0.0, "y": y})
                y += p.altura_mm
            return offsets, max_w, y

        elif layout == "bandeira_topo":
            bandeira_idx = next(
                (i for i, p in enumerate(pecas) if "bandeira" in p.nome.lower()),
                min(range(len(pecas)), key=lambda i: pecas[i].altura_mm),
            )
            bandeira = pecas[bandeira_idx]
            max_other_h = max(
                (p.altura_mm for i, p in enumerate(pecas) if i != bandeira_idx),
                default=0.0,
            )
            x = 0.0
            for i, p in enumerate(pecas):
                if i == bandeira_idx:
                    offsets.append({"x": 0.0, "y": max_other_h})
                else:
                    offsets.append({"x": x, "y": 0.0})
                    x += p.largura_mm
            total_w = max(x, bandeira.largura_mm)
            total_h = max_other_h + bandeira.altura_mm
            return offsets, total_w, total_h

        else:
            x = 0.0
            max_h = max(p.altura_mm for p in pecas)
            for p in pecas:
                offsets.append({"x": x, "y": 0.0})
                x += p.largura_mm
            return offsets, x, max_h

    # ── Material helper ───────────────────────────────────────────────────────

    def _mat_vidro(self, base: dict, espessura: float) -> dict:
        return {
            "tipo":               "vidro_temperado",
            "cor":                base["cor"],
            "opacidade":          base["opacidade"],
            "transmission":       base.get("transmission", 0.92),
            "ior":                base.get("ior", 1.52),
            "thickness":          base.get("thickness", espessura),
            "roughness":          base.get("roughness", 0.0),
            "metalness":          base.get("metalness", 0.0),
            "clearcoat":          base.get("clearcoat", 1.0),
            "clearcoatRoughness": base.get("clearcoatRoughness", 0.03),
            "envMapIntensity":    base.get("envMapIntensity", 0.3),
            "attenuationColor":   base.get("attenuationColor", "#FFFFFF"),
            "attenuationDistance":base.get("attenuationDistance", 150),
        }

    # ── Vidros — generic (vertical XY plane) ─────────────────────────────────

    def _build_vidros(
        self,
        pecas: list[PecaRenderizada],
        offsets: list[dict],
        tipologia: str,
        espessura: float,
        cor_vidro: str,
        total_largura: float,
    ) -> list[dict]:
        vidro_mat_base = CORES_VIDRO.get(cor_vidro, CORES_VIDRO["default"])
        animacao_base  = self._animacao_para_tipologia(tipologia)
        center_x       = total_largura / 2

        vidros = []
        for i, (peca, offset) in enumerate(zip(pecas, offsets)):
            x_3d = _r(offset["x"] + peca.largura_mm / 2 - center_x)
            y_3d = _r(offset["y"] + peca.altura_mm / 2)

            mat = self._mat_vidro(vidro_mat_base, espessura)

            vidro: dict = {
                "id":            f"vidro_{i+1}",
                "nome":          peca.nome,
                "classificacao": peca.classificacao,
                "largura":       peca.largura_mm,
                "altura":        peca.altura_mm,
                "espessura":     espessura,
                "posicao":       {"x": x_3d, "y": y_3d, "z": 0.0},
                "rotacao":       {"x": 0.0, "y": 0.0, "z": 0.0},
                "material":      mat,
            }

            if peca.classificacao in ("movel", "correr") and animacao_base:
                vidro["animacao"] = self._animacao_vidro(
                    animacao_base, peca, offset, center_x
                )

            vidros.append(vidro)
        return vidros

    # ── Vidros — box_canto (L-shape) ──────────────────────────────────────────

    def _build_vidros_box_canto(
        self,
        pecas: list[PecaRenderizada],
        tipologia: str,
        espessura: float,
        cor_vidro: str,
    ) -> list[dict]:
        base = CORES_VIDRO.get(cor_vidro, CORES_VIDRO["default"])

        if len(pecas) < 2:
            offsets = [{"x": p.largura_mm * i, "y": 0.0} for i, p in enumerate(pecas)]
            total_w = sum(p.largura_mm for p in pecas) or 900.0
            return self._build_vidros(pecas, offsets, tipologia, espessura, cor_vidro, total_w)

        p1, p2 = pecas[0], pecas[1]
        # Panel 1: frontal, centered in X, z=0
        # Panel 2: lateral, rotated 90° around Y, positioned at corner
        specs = [
            (p1, 0.0,              _r(p1.altura_mm / 2), 0.0,                 0.0),
            (p2, _r(p1.largura_mm / 2), _r(p2.altura_mm / 2), _r(-p2.largura_mm / 2), 90.0),
        ]

        vidros = []
        for i, (peca, x3d, y3d, z3d, rot_y) in enumerate(specs):
            mat = self._mat_vidro(base, espessura)
            vidro: dict = {
                "id":            f"vidro_{i+1}",
                "nome":          peca.nome,
                "classificacao": peca.classificacao,
                "largura":       peca.largura_mm,
                "altura":        peca.altura_mm,
                "espessura":     espessura,
                "posicao":       {"x": x3d, "y": y3d, "z": z3d},
                "rotacao":       {"x": 0.0, "y": rot_y, "z": 0.0},
                "material":      mat,
            }
            if peca.classificacao in ("movel", "correr"):
                vidro["animacao"] = {"tipo": "deslizante", "eixo": "x", "distancia_max": peca.largura_mm}
            vidros.append(vidro)

        # Extra panels (>2) placed as generic XY panels
        if len(pecas) > 2:
            extra = pecas[2:]
            x_start = p1.largura_mm + p2.largura_mm
            for j, peca in enumerate(extra):
                mat = self._mat_vidro(base, espessura)
                total_extra = sum(p.largura_mm for p in extra)
                cx = x_start + total_extra / 2
                x3d = _r(x_start + peca.largura_mm * j + peca.largura_mm / 2 - cx)
                vidros.append({
                    "id":            f"vidro_{len(specs)+j+1}",
                    "nome":          peca.nome,
                    "classificacao": peca.classificacao,
                    "largura":       peca.largura_mm,
                    "altura":        peca.altura_mm,
                    "espessura":     espessura,
                    "posicao":       {"x": x3d, "y": _r(peca.altura_mm / 2), "z": 0.0},
                    "rotacao":       {"x": 0.0, "y": 0.0, "z": 0.0},
                    "material":      mat,
                })

        return vidros

    # ── Vidros — cobertura (horizontal) ───────────────────────────────────────

    def _build_vidros_cobertura(
        self,
        pecas: list[PecaRenderizada],
        tipologia: str,
        espessura: float,
        cor_vidro: str,
    ) -> list[dict]:
        base = CORES_VIDRO.get(cor_vidro, CORES_VIDRO["default"])
        vidros = []
        for i, peca in enumerate(pecas):
            mat = self._mat_vidro(base, espessura)
            vidros.append({
                "id":            f"vidro_{i+1}",
                "nome":          peca.nome,
                "classificacao": peca.classificacao,
                "largura":       peca.largura_mm,
                "altura":        peca.altura_mm,
                "espessura":     espessura,
                # Rotated -90° around X → panel lies flat at install height
                "posicao":       {"x": 0.0, "y": _r(_COBERTURA_INSTALL_H), "z": _r(-peca.altura_mm / 2)},
                "rotacao":       {"x": -90.0, "y": 0.0, "z": 0.0},
                "material":      mat,
            })
        return vidros

    # ── Animação ──────────────────────────────────────────────────────────────

    def _animacao_para_tipologia(self, tipologia: str) -> Optional[dict]:
        t = tipologia.lower()
        if "pivotante" in t:
            vai_vem = "vai_vem" in t or "vaivem" in t
            return {
                "tipo": "pivotante",
                "eixo": "y",
                "angulo_max": 90,
                "angulo_min": -90 if vai_vem else 0,
                "_pivot_offset": 15,
            }
        elif "abrir" in t:
            return {
                "tipo": "pivotante",
                "eixo": "y",
                "angulo_max": 90,
                "angulo_min": 0,
                "_pivot_offset": 0,
            }
        if any(k in t for k in ("correr", "box", "sacada", "quatro_folhas")):
            return {"tipo": "deslizante", "eixo": "x"}
        if "basculante" in t:
            return {"tipo": "basculante", "eixo": "x", "angulo_max": 45}
        if "maxim" in t:
            return {"tipo": "basculante", "eixo": "x", "angulo_max": 60}
        return None

    def _animacao_vidro(
        self,
        base: dict,
        peca: PecaRenderizada,
        offset: dict,
        center_x: float,
    ) -> dict:
        anim = {k: v for k, v in base.items() if not k.startswith("_")}
        if base["tipo"] == "pivotante":
            pivot_offset = base.get("_pivot_offset", 0)
            left_edge_x = _r(offset["x"] - center_x)
            pivo_x = _r(left_edge_x + pivot_offset)
            anim["ponto_pivo"] = {"x": pivo_x, "y": 0.0, "z": 0.0}
        elif base["tipo"] == "deslizante":
            anim["distancia_max"] = peca.largura_mm
        return anim

    # ── Ferragens ─────────────────────────────────────────────────────────────

    def _build_ferragens(
        self,
        pecas: list[PecaRenderizada],
        offsets: list[dict],
        espessura: float,
        total_largura: float,
    ) -> list[dict]:
        center_x = total_largura / 2
        result = []
        seen_ids: dict[str, int] = {}

        for peca, offset in zip(pecas, offsets):
            for f in peca.ferragens:
                geom = _geom(f.tipo)
                pbr  = _pbr_material(f.tipo)
                prof = _profundidade(geom)

                x_3d = _r(offset["x"] + f.x_mm - center_x)
                y_3d = _r(f.y_mm)
                z_sign = -1 if f.lado == "esquerdo" else 1
                z_3d = _r((espessura / 2 + prof / 2) * z_sign)

                base_id = (
                    f"{f.tipo}_{f.nome.lower()}"
                    .replace(" ", "_")
                    .replace("ç", "c")
                    .replace("ã", "a")
                    .replace("á", "a")
                    .replace("â", "a")
                    .replace("é", "e")
                    .replace("ê", "e")
                    .replace("í", "i")
                    .replace("ó", "o")
                    .replace("ô", "o")
                    .replace("ú", "u")
                )
                n = seen_ids.get(base_id, 0)
                fid = base_id if n == 0 else f"{base_id}_{n}"
                seen_ids[base_id] = n + 1

                result.append({
                    "id":        fid,
                    "nome":      f.nome,
                    "codigo":    f.codigo or "",
                    "tipo":      f.tipo,
                    "peca_nome": peca.nome,
                    "posicao":   {"x": x_3d, "y": y_3d, "z": z_3d},
                    "rotacao":   {"x": 0.0, "y": 0.0, "z": 0.0},
                    "geometria": geom,
                    "material":  pbr,
                    "recorte":   f.recorte,
                })
        return result

    # ── Vão e ambiente ────────────────────────────────────────────────────────

    def _build_vao(self, largura: float, altura: float, presente: bool = True) -> dict:
        # Folgas NBR / Glasspeças: movel_alvenaria=5mm (lateral/topo), movel_piso=8mm (base).
        folga_lat  = 5.0
        folga_topo = 5.0
        folga_base = 8.0
        return {
            "presente":     presente,
            "largura":      _r(largura + 2 * folga_lat),
            "altura":       _r(altura + folga_topo + folga_base),
            "profundidade": 150,
            "material": {
                "tipo":      "alvenaria",
                "cor":       "#E8E0D8",
                "roughness": 0.90,
                "metalness": 0.0,
                "bumpScale": 0.02,
            },
        }

    def _build_ambiente(self, largura: float, altura: float) -> dict:
        diag = (largura ** 2 + altura ** 2) ** 0.5
        cam_z = _r(diag * 1.2)
        cam_y = _r(altura * 0.5)
        return {
            "iluminacao":         "studio_hdr",
            "toneMapping":        "ACESFilmic",
            "toneMappingExposure": 1.2,
            "shadowMap":          "PCFSoft",
            "antialias":          True,
            "piso": {
                "cor":              "#F0EDE8",
                "roughness":        0.40,
                "metalness":        0.0,
                "envMapIntensity":  0.3,
            },
            "parede": {
                "cor":      "#E8E0D8",
                "roughness": 0.90,
                "metalness": 0.0,
            },
            "camera_inicial": {
                "posicao": {"x": 0.0, "y": cam_y, "z": cam_z},
                "target":  {"x": 0.0, "y": cam_y, "z": 0.0},
            },
        }

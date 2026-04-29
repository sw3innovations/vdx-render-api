"""Normalizer: raw variável strings → canonical codigo."""
from __future__ import annotations

# (alias_lower, fonte) → canonical codigo
# fonte: 'dump_altura', 'dump_largura', 'render'
_VARIAVEL_MAP: dict[str, str] = {
    # ── altura ───────────────────────────────────────────────────────────────
    "altura": "ALTURA_VAO",
    "altura do vão": "ALTURA_VAO",
    "altura do vao": "ALTURA_VAO",
    "alt": "ALTURA_VAO",
    "altura total": "ALTURA_TOTAL",
    "altura folha": "ALTURA_FOLHA",
    "altura bandeira": "ALTURA_BANDEIRA",
    "altura sacada": "ALTURA_SACADA",
    "sacada": "ALTURA_SACADA",
    "peitoril": "PEITORIL",
    "altura peitoril": "PEITORIL",
    "folga": "FOLGA_ALTURA",
    "folga altura": "FOLGA_ALTURA",
    # ── largura ───────────────────────────────────────────────────────────────
    "largura": "LARGURA_VAO",
    "largura do vão": "LARGURA_VAO",
    "largura do vao": "LARGURA_VAO",
    "larg": "LARGURA_VAO",
    "largura total": "LARGURA_TOTAL",
    "largura folha": "LARGURA_FOLHA",
    "folga largura": "FOLGA_LARGURA",
}

# eixo inference from codigo prefix
def _eixo_from_codigo(codigo: str) -> str:
    c = codigo.upper()
    if any(c.startswith(p) for p in ("ALTURA", "PEITORIL", "SACADA", "FOLGA_ALT")):
        return "altura"
    if any(c.startswith(p) for p in ("LARGURA", "FOLGA_LARG")):
        return "largura"
    return "neutro"


SEED_VARIAVEIS: list[tuple[str, str, str]] = [
    # (codigo, nome_apresentacao, eixo)
    ("ALTURA_VAO",      "Altura do Vão",       "altura"),
    ("ALTURA_TOTAL",    "Altura Total",         "altura"),
    ("ALTURA_FOLHA",    "Altura da Folha",      "altura"),
    ("ALTURA_BANDEIRA", "Altura da Bandeira",   "altura"),
    ("ALTURA_SACADA",   "Altura da Sacada",     "altura"),
    ("PEITORIL",        "Peitoril",             "altura"),
    ("FOLGA_ALTURA",    "Folga de Altura",      "altura"),
    ("LARGURA_VAO",     "Largura do Vão",       "largura"),
    ("LARGURA_TOTAL",   "Largura Total",        "largura"),
    ("LARGURA_FOLHA",   "Largura da Folha",     "largura"),
    ("FOLGA_LARGURA",   "Folga de Largura",     "largura"),
]


def normalizar_variavel(raw: str | None) -> str:
    """Return canonical codigo for a raw variável string, or raw uppercased."""
    if not raw:
        return "DESCONHECIDA"
    key = raw.strip().lower()
    return _VARIAVEL_MAP.get(key, raw.strip().upper().replace(" ", "_"))

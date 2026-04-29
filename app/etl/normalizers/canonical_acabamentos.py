"""Normalizer: raw acabamento strings → canonical codigo."""
from __future__ import annotations

_ACABAMENTO_MAP: dict[str, str] = {
    # polido / espelhado
    "polido": "POLIDO",
    "polished": "POLIDO",
    "espelhado": "POLIDO",
    "brilhante": "POLIDO",
    # escovado / acetinado
    "escovado": "ESCOVADO",
    "brushed": "ESCOVADO",
    "acetinado": "ESCOVADO",
    "fosco escovado": "ESCOVADO",
    "hairline": "ESCOVADO",
    # fosco / matte
    "fosco": "FOSCO",
    "matte": "FOSCO",
    "opaco": "FOSCO",
    # preto / black
    "preto": "PRETO",
    "black": "PRETO",
    "preto fosco": "PRETO",
    "preto brilhante": "PRETO",
    "negro": "PRETO",
    "gunmetal": "PRETO",
    # cromado
    "cromado": "CROMADO",
    "cromo": "CROMADO",
    "chrome": "CROMADO",
    # dourado / ouro
    "dourado": "DOURADO",
    "ouro": "DOURADO",
    "gold": "DOURADO",
    "champagne": "DOURADO",
    "champanhe": "DOURADO",
    # bronze / cobre
    "bronze": "BRONZE",
    "cobre": "BRONZE",
    "copper": "BRONZE",
    "antiqued": "BRONZE",
    # anodizado
    "anodizado": "ANODIZADO",
    "anodized": "ANODIZADO",
    # pintado / lacado
    "pintado": "PINTADO",
    "lacado": "PINTADO",
    "powder coat": "PINTADO",
    "epoxy": "PINTADO",
    # natural / sem acabamento
    "natural": "NATURAL",
    "sem acabamento": "NATURAL",
    "bruto": "NATURAL",
    "raw": "NATURAL",
}

SEED_ACABAMENTOS: list[tuple[str, str]] = [
    ("POLIDO",    "Polido / Espelhado"),
    ("ESCOVADO",  "Escovado / Acetinado"),
    ("FOSCO",     "Fosco / Matte"),
    ("PRETO",     "Preto"),
    ("CROMADO",   "Cromado"),
    ("DOURADO",   "Dourado / Ouro"),
    ("BRONZE",    "Bronze / Cobre"),
    ("ANODIZADO", "Anodizado"),
    ("PINTADO",   "Pintado / Lacado"),
    ("NATURAL",   "Natural / Bruto"),
    ("OUTRO",     "Outro"),
]


def normalizar_acabamento(raw: str | None) -> str:
    """Return canonical codigo for a raw acabamento string, or 'OUTRO'."""
    if not raw:
        return "OUTRO"
    key = raw.strip().lower()
    return _ACABAMENTO_MAP.get(key, "OUTRO")

"""Normalizer: raw material strings → canonical codigo."""
from __future__ import annotations

# Maps raw alias (lower, stripped) → canonical codigo
_MATERIAL_MAP: dict[str, str] = {
    # alumínio
    "aluminio": "ALUMINIO",
    "alumínio": "ALUMINIO",
    "al": "ALUMINIO",
    "liga de aluminio": "ALUMINIO",
    "liga de alumínio": "ALUMINIO",
    # aço inox
    "aco inox": "ACO_INOX",
    "aço inox": "ACO_INOX",
    "inox": "ACO_INOX",
    "acero inox": "ACO_INOX",
    "stainless steel": "ACO_INOX",
    "inox 304": "ACO_INOX",
    "inox 316": "ACO_INOX",
    # aço carbono
    "aco carbono": "ACO_CARBONO",
    "aço carbono": "ACO_CARBONO",
    "aco": "ACO_CARBONO",
    "aço": "ACO_CARBONO",
    "steel": "ACO_CARBONO",
    # zamak / zinco
    "zamak": "ZAMAK",
    "zinc": "ZAMAK",
    "zinco": "ZAMAK",
    "zama": "ZAMAK",
    # latão / bronze
    "latao": "LATAO",
    "latão": "LATAO",
    "bronze": "LATAO",
    "brass": "LATAO",
    # policarbonato / plástico
    "policarbonato": "POLIMERO",
    "plastico": "POLIMERO",
    "plástico": "POLIMERO",
    "nylon": "POLIMERO",
    "abs": "POLIMERO",
    "pvc": "POLIMERO",
    # vidro
    "vidro": "VIDRO",
    "glass": "VIDRO",
    # madeira
    "madeira": "MADEIRA",
    "wood": "MADEIRA",
    "mdf": "MADEIRA",
}

# Canonical records to seed: (codigo, nome_apresentacao, densidade_kg_m3)
SEED_MATERIAIS: list[tuple[str, str, float | None]] = [
    ("ALUMINIO",    "Alumínio",       2700.0),
    ("ACO_INOX",    "Aço Inoxidável", 7900.0),
    ("ACO_CARBONO", "Aço Carbono",    7850.0),
    ("ZAMAK",       "Zamak / Zinco",  6600.0),
    ("LATAO",       "Latão / Bronze", 8500.0),
    ("POLIMERO",    "Polímero",       None),
    ("VIDRO",       "Vidro",          2500.0),
    ("MADEIRA",     "Madeira / MDF",  None),
    ("OUTRO",       "Outro",          None),
]


def normalizar_material(raw: str | None) -> str:
    """Return canonical codigo for a raw material string, or 'OUTRO'."""
    if not raw:
        return "OUTRO"
    key = raw.strip().lower()
    return _MATERIAL_MAP.get(key, "OUTRO")

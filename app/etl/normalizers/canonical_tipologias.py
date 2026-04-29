"""Normalizer: tipologia names → canonical codigo."""
from __future__ import annotations
import re

# Common category prefixes from dump DS_TMD values
_CATEGORY_PATTERNS: list[tuple[re.Pattern, str]] = [
    (re.compile(r"janela", re.I),        "JANELA"),
    (re.compile(r"porta", re.I),         "PORTA"),
    (re.compile(r"correr", re.I),        "CORRER"),
    (re.compile(r"de abrir", re.I),      "ABRIR"),
    (re.compile(r"abrir", re.I),         "ABRIR"),
    (re.compile(r"basculante", re.I),    "BASCULANTE"),
    (re.compile(r"maximar", re.I),       "MAXIMAR"),
    (re.compile(r"pivotante", re.I),     "PIVOTANTE"),
    (re.compile(r"bandeira", re.I),      "BANDEIRA"),
    (re.compile(r"sacada", re.I),        "SACADA"),
    (re.compile(r"fixa", re.I),          "FIXA"),
    (re.compile(r"fachada", re.I),       "FACHADA"),
    (re.compile(r"veneziana", re.I),     "VENEZIANA"),
    (re.compile(r"guilhotina", re.I),    "GUILHOTINA"),
    (re.compile(r"vitro", re.I),         "VITRO"),
]


def inferir_categoria(ds_tmd: str | None) -> str | None:
    """Infer a category string from a DS_TMD description."""
    if not ds_tmd:
        return None
    for pattern, cat in _CATEGORY_PATTERNS:
        if pattern.search(ds_tmd):
            return cat
    return None


def ds_tmd_to_codigo(nu_tip: int, ds_tmd: str | None) -> str:
    """Generate a canonical codigo from nu_tip + DS_TMD."""
    if not ds_tmd:
        return f"TIP_{nu_tip:04d}"
    slug = re.sub(r"[^a-z0-9]+", "_", ds_tmd.strip().lower())
    slug = slug.strip("_")[:40]
    return f"TIP_{nu_tip:04d}_{slug}".upper()

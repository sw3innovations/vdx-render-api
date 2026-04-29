"""Deduplication helpers — no rapidfuzz dependency."""
from __future__ import annotations
import re


def normalizar_codigo_ferragem(codigo: str | None) -> str | None:
    """Normalize a hardware code: remove spaces, hyphens, slashes → uppercase."""
    if not codigo:
        return None
    return re.sub(r"[\s\-/]", "", codigo).upper()


def _char_bigrams(s: str) -> set[str]:
    return {s[i:i+2] for i in range(len(s) - 1)}


def similaridade_bigram(a: str, b: str) -> float:
    """Return bigram similarity [0,1] between two strings."""
    a, b = a.upper(), b.upper()
    if not a or not b:
        return 0.0
    bg_a = _char_bigrams(a)
    bg_b = _char_bigrams(b)
    if not bg_a or not bg_b:
        return 1.0 if a == b else 0.0
    intersection = len(bg_a & bg_b)
    return 2 * intersection / (len(bg_a) + len(bg_b))


def sao_duplicatas(
    nome_a: str,
    nome_b: str,
    codigo_a: str | None = None,
    codigo_b: str | None = None,
    threshold: float = 0.85,
) -> bool:
    """Return True if two ferragem records appear to be duplicates."""
    if codigo_a and codigo_b:
        if normalizar_codigo_ferragem(codigo_a) == normalizar_codigo_ferragem(codigo_b):
            return True
    return similaridade_bigram(nome_a, nome_b) >= threshold


def agrupar_por_codigo(
    registros: list[dict],
    campo_codigo: str = "codigo",
) -> dict[str, list[dict]]:
    """Group records by normalized codigo, merging near-duplicates."""
    grupos: dict[str, list[dict]] = {}
    for rec in registros:
        norm = normalizar_codigo_ferragem(rec.get(campo_codigo)) or "SEM_CODIGO"
        grupos.setdefault(norm, []).append(rec)
    return grupos

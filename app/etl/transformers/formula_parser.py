"""Normalize formula variable tokens to canonical codes.

Formulas in dump_geometria_pecas use raw variable names like 'ALTURA-10',
'LARGURA/2', or 'ALTURA DO VÃO * 0.5'. This module replaces those tokens
with canonical variable codes.
"""
from __future__ import annotations
import re

# Token → canonical replacement (longest match wins via pre-sorting)
_TOKEN_MAP: dict[str, str] = {
    "ALTURA DO VAO": "ALTURA_VAO",
    "ALTURA DO VÃO": "ALTURA_VAO",
    "LARGURA DO VAO": "LARGURA_VAO",
    "LARGURA DO VÃO": "LARGURA_VAO",
    "ALTURA TOTAL": "ALTURA_TOTAL",
    "LARGURA TOTAL": "LARGURA_TOTAL",
    "ALTURA FOLHA": "ALTURA_FOLHA",
    "LARGURA FOLHA": "LARGURA_FOLHA",
    "ALTURA BANDEIRA": "ALTURA_BANDEIRA",
    "ALTURA SACADA": "ALTURA_SACADA",
    "SACADA": "ALTURA_SACADA",
    "PEITORIL": "PEITORIL",
    "FOLGA ALTURA": "FOLGA_ALTURA",
    "FOLGA LARGURA": "FOLGA_LARGURA",
    "ALTURA": "ALTURA_VAO",
    "LARGURA": "LARGURA_VAO",
}

# Pre-sort by length descending so longer tokens match first in single pass
_SORTED_TOKENS = sorted(_TOKEN_MAP.keys(), key=len, reverse=True)

# Single combined pattern for one-pass replacement.
# Negative lookahead/lookbehind on [A-Za-z0-9_] prevents matching tokens
# that are already part of canonical codes (e.g. "ALTURA" inside "ALTURA_VAO").
_COMBINED_PATTERN = re.compile(
    r"(?<![A-Za-z0-9_])(?:" + "|".join(re.escape(t) for t in _SORTED_TOKENS) + r")(?![A-Za-z0-9_])",
    re.IGNORECASE,
)


def normalizar_formula(formula: str | None) -> str | None:
    """Replace raw variable names in formula with canonical codes (single pass)."""
    if formula is None:
        return None
    stripped = formula.strip()
    if not stripped:
        return stripped

    def _replace(m: re.Match) -> str:
        return _TOKEN_MAP[m.group(0).upper()]

    return _COMBINED_PATTERN.sub(_replace, stripped)


def extrair_variaveis(formula: str | None) -> list[str]:
    """Extract all canonical variable codes referenced in a formula."""
    if not formula:
        return []
    normalizada = normalizar_formula(formula) or ""
    canonical_set = set(_TOKEN_MAP.values())
    tokens = re.findall(r"[A-Z][A-Z0-9_]+", normalizada)
    return [t for t in tokens if t in canonical_set]

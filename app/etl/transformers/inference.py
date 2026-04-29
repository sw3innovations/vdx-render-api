"""Infer missing or placeholder values for canonical records."""
from __future__ import annotations
import re

_ROMAN = {
    "I": 1, "II": 2, "III": 3, "IV": 4, "V": 5,
    "VI": 6, "VII": 7, "VIII": 8, "IX": 9, "X": 10,
}

_FOLHA_PATTERNS = [
    (re.compile(r"(\d+)\s*FOLHA", re.I), lambda m: int(m.group(1))),
    (re.compile(r"(\d+)\s*FL\b", re.I), lambda m: int(m.group(1))),
]

_ROMANO_PATTERN = re.compile(
    r"\b(" + "|".join(sorted(_ROMAN.keys(), key=len, reverse=True)) + r")\b"
)


def inferir_nome_modelo(nu_mod: int, ds_tmd: str | None, div_largura: int, div_altura: int) -> str:
    """Build a human-readable model name when DS_MOD is '?' or empty."""
    base = ds_tmd.strip() if ds_tmd and ds_tmd != "?" else f"Tipologia {nu_mod}"
    folhas = div_largura * div_altura
    return f"{base} — {folhas}F ({div_largura}L×{div_altura}A)"


def inferir_nome_valido(nome: str | None) -> bool:
    """Return True if a name is a real name (not '?' or empty)."""
    if not nome:
        return False
    return nome.strip() not in ("?", "", "-", "N/A", "NA")


def inferir_tipo_peca(ds_tipo: str | None, ds_peca: str | None) -> str | None:
    """Normalize piece type from DS_TIPO / DS_PECA."""
    candidates = [ds_tipo, ds_peca]
    for c in candidates:
        if c and c.strip():
            return c.strip().upper()
    return None

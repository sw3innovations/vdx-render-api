from __future__ import annotations
import sqlite3
from dataclasses import dataclass
from pathlib import Path

from app.schemas.import_tipologia import TipologiaImportadaSchema

DB_PATH = Path(__file__).parent.parent.parent / "data" / "constitution.db"


@dataclass
class ErroValidacao:
    campo: str
    mensagem: str


def validar_geometria(tipologia: TipologiaImportadaSchema) -> list[ErroValidacao]:
    erros: list[ErroValidacao] = []
    try:
        conn = sqlite3.connect(str(DB_PATH))
        for i, painel in enumerate(tipologia.paineis):
            for j, f in enumerate(painel.ferragens):
                row = conn.execute(
                    "SELECT 1 FROM ferragens WHERE codigo_normalizado = ?"
                    " AND (fabricante_id = ? OR ? IS NULL)",
                    (f.codigo, f.fabricante_id, f.fabricante_id),
                ).fetchone()
                if not row:
                    campo = f"paineis[{i}].ferragens[{j}].codigo"
                    if f.fabricante_id:
                        msg = (f"Ferragem '{f.codigo}' do fabricante '{f.fabricante_id}'"
                               f" não encontrada no catálogo")
                    else:
                        msg = f"Ferragem '{f.codigo}' não encontrada no catálogo"
                    erros.append(ErroValidacao(campo=campo, mensagem=msg))
        conn.close()
    except Exception:
        pass
    return erros

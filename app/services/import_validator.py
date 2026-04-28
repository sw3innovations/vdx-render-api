from __future__ import annotations
import sqlite3
from dataclasses import dataclass, field
from pathlib import Path

from app.schemas.import_tipologia import TipologiaImportadaSchema

DB_PATH = Path(__file__).parent.parent.parent / "data" / "constitution.db"


@dataclass
class ErroValidacao:
    campo: str
    mensagem: str
    is_warning: bool = False


def validar_geometria(tipologia: TipologiaImportadaSchema) -> list[ErroValidacao]:
    issues: list[ErroValidacao] = []
    try:
        conn = sqlite3.connect(str(DB_PATH))

        for i, painel in enumerate(tipologia.paineis):
            # Posição explícita: validar bounding box 0..6000
            if painel.posicao_x_mm is not None:
                if painel.posicao_x_mm < 0 or (painel.posicao_x_mm + painel.largura_mm) > 6000:
                    issues.append(ErroValidacao(
                        campo=f"paineis[{i}].posicao_x_mm",
                        mensagem=(
                            f"posicao_x_mm={painel.posicao_x_mm:.0f} + largura={painel.largura_mm:.0f}"
                            f" ultrapassa o bounding box (0..6000)"
                        ),
                    ))
            if painel.posicao_y_mm is not None:
                if painel.posicao_y_mm < 0 or (painel.posicao_y_mm + painel.altura_mm) > 6000:
                    issues.append(ErroValidacao(
                        campo=f"paineis[{i}].posicao_y_mm",
                        mensagem=(
                            f"posicao_y_mm={painel.posicao_y_mm:.0f} + altura={painel.altura_mm:.0f}"
                            f" ultrapassa o bounding box (0..6000)"
                        ),
                    ))

            # Abertura sem lado_dobradica → aviso (não erro)
            if (painel.abertura and
                    painel.abertura.modo == "abrir" and
                    painel.abertura.lado_dobradica is None):
                issues.append(ErroValidacao(
                    campo=f"paineis[{i}].abertura.lado_dobradica",
                    mensagem="Lado da dobradiça não especificado, usando padrão 'esquerda'",
                    is_warning=True,
                ))

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
                    issues.append(ErroValidacao(campo=campo, mensagem=msg))

        conn.close()

        # Categoria "porta" sem painel móvel → aviso
        if tipologia.categoria == "porta":
            has_movel = any(p.classificacao in ("movel", "correr") for p in tipologia.paineis)
            if not has_movel:
                issues.append(ErroValidacao(
                    campo="categoria",
                    mensagem="Porta sem painel móvel — revisar classificação dos painéis",
                    is_warning=True,
                ))

    except Exception:
        pass
    return issues


def resolver_ferragens(tipologia: TipologiaImportadaSchema) -> list[dict]:
    """Retorna detalhes resolvidos do catálogo para cada ferragem do payload."""
    result: list[dict] = []
    try:
        conn = sqlite3.connect(str(DB_PATH))
        for painel in tipologia.paineis:
            for f in painel.ferragens:
                row = conn.execute(
                    "SELECT nome, fabricante_id FROM ferragens"
                    " WHERE codigo_normalizado = ? AND (fabricante_id = ? OR ? IS NULL)"
                    " LIMIT 1",
                    (f.codigo, f.fabricante_id, f.fabricante_id),
                ).fetchone()
                result.append({
                    "codigo": f.codigo,
                    "fabricante_id": f.fabricante_id or (row[1] if row else None),
                    "nome": row[0] if row else None,
                    "tipo": f.tipo,
                    "posicao_aplicada": {"x_mm": f.x_mm, "y_mm": f.y_mm},
                    "painel": painel.nome,
                })
        conn.close()
    except Exception:
        pass
    return result

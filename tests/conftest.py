"""Fixtures compartilhadas para os testes do VDX Glass Engine."""
import asyncio
import pytest

from app.core.constitution import init_db
from app.core.constitution_seed import seed
from app.models.render import PecaInput, RenderRequest
from app.services.render_orchestrator import executar


# ── Ambiente de teste ─────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def _force_test_env(monkeypatch):
    """Força modo dev em runtime: master_key vazia aceita qualquer X-VDX-Key.

    Evita que o .env de produção (VDX_API_MASTER_KEY=vdx-render-prod-2026)
    invalide os headers hardcoded test-key nos testes de proposal e view_token.
    Também garante view_token_secret estável para testes de encode/decode.
    """
    from app.config import settings
    monkeypatch.setattr(settings, "vdx_api_master_key", "", raising=False)
    monkeypatch.setattr(
        settings,
        "view_token_secret",
        "test-secret-32chars-xxxxxxxxxx",
        raising=False,
    )


# ── DB ────────────────────────────────────────────────────────────────────────

@pytest.fixture(scope="session", autouse=True)
def db_ready():
    """Inicializa o banco e popula com o seed antes de qualquer teste."""
    import json
    import sqlite3
    from pathlib import Path

    init_db()
    seed()

    db_path = Path(__file__).parent.parent / "data" / "constitution.db"
    conn = sqlite3.connect(str(db_path))

    # ── fabricantes (for ferragens FK) ────────────────────────────────────────
    for fab_id, nome, prefixo in [
        ("SM", "Glasspeças/Santa Marina", "SM"),
        ("HE", "Fechaduras Hela", "HE"),
        ("AL", "AL Indústria", "AL"),
    ]:
        conn.execute(
            "INSERT OR IGNORE INTO fabricantes (id, nome, prefixo) VALUES (?,?,?)",
            (fab_id, nome, prefixo),
        )

    # ── catalogo_fabricantes (for catalogo_puxadores FK) ─────────────────────
    for codigo, nome in [("SM", "Santa Marina"), ("HE", "Hela"), ("AL", "AL Indústria")]:
        conn.execute(
            "INSERT OR IGNORE INTO catalogo_fabricantes (codigo, nome) VALUES (?,?)",
            (codigo, nome),
        )

    # ── catalogo_puxadores ────────────────────────────────────────────────────
    # FUSE-001 normalizes to FUSE001, matching the ferragens seed below (fusion test)
    for row_id, codigo, nome, tipo, material, acabamento, comp_mm, diam_mm, fab in [
        (9001, "FUSE-001", "Puxador Fusão CI", "puxador", "Aluminio", "polido", 300.0, None, "SM"),
        (9002, "PUXADOR 400", "Puxador Barra 400mm", "puxador", None, None, 400.0, None, "SM"),
        (9003, "PUXADOR 300", "Puxador Barra 300mm", "puxador", None, None, 300.0, None, "HE"),
        (9004, "BARRA-CI-001", "Puxador Barra Inox CI 300mm", "barra", "Inox", "escovado", 300.0, None, "AL"),
        (9005, "DOBRADICA-CI-001", "Dobradiça Box CI", "dobradica", None, None, None, None, "SM"),
        (9006, "FECHADURA-CI-001", "Fechadura CI Basic", "fechadura", None, None, None, None, "SM"),
        (9007, "SUPORTE-CI-001", "Suporte Barra CI", "suporte", None, None, None, None, "SM"),
    ]:
        conn.execute(
            """INSERT OR IGNORE INTO catalogo_puxadores
               (id, codigo, nome, tipo_visual, material, acabamento, comp_mm, diametro_mm, fabricante_id)
               VALUES (?,?,?,?,?,?,?,?,?)""",
            (row_id, codigo, nome, tipo, material, acabamento, comp_mm, diam_mm, fab),
        )

    # ── ferragens (render staging) ────────────────────────────────────────────
    # 'PUXADOR 400'/'PUXADOR 300' feed buscar_dimensoes_puxador() tests
    # 'FUSE001' has same codigo_normalizado as catalog FUSE-001 → triggers fusion
    # 'NEWCI001' is a truly new canonical from render
    for codigo, norm, fab_id, nome, tipo, material, dims in [
        ("PUXADOR 400", "PUXADOR 400", "SM", "Puxador Barra 400mm", "puxador", "Aluminio",
         json.dumps({"comprimento": 400})),
        ("PUXADOR 300", "PUXADOR 300", "HE", "Puxador Barra 300mm", "puxador", "Inox",
         json.dumps({"comprimento": 300})),
        ("FUSE001", "FUSE001", "SM", "Ferragem para Fusão CI", "puxador", "Aluminio", None),
        ("NEWCI001", "NEWCI001", "SM", "Ferragem Nova CI", "dobradica", "Zamac", None),
    ]:
        conn.execute(
            """INSERT OR IGNORE INTO ferragens
               (codigo, codigo_normalizado, fabricante_id, nome, tipo, material, dimensoes_json, confianca, fonte)
               VALUES (?,?,?,?,?,?,?,0.9,'ci_seed')""",
            (codigo, norm, fab_id, nome, tipo, material, dims),
        )

    # ── dump_tipologias ───────────────────────────────────────────────────────
    conn.execute(
        """INSERT OR IGNORE INTO dump_tipologias (nu_tip, ds_tmd, id_ativo)
           VALUES (100, 'JANELA DE CORRER 2 FOLHAS', 1)"""
    )
    conn.execute(
        """INSERT OR IGNORE INTO dump_tipologias (nu_tip, ds_tmd, id_ativo)
           VALUES (15, 'SANFONADO', 1)"""
    )
    conn.execute(
        """INSERT OR IGNORE INTO dump_tipologias (nu_tip, ds_tmd, id_ativo)
           VALUES (5, 'PIVOTANTE', 1)"""
    )

    # ── dump_modelos ──────────────────────────────────────────────────────────
    conn.execute(
        """INSERT OR IGNORE INTO dump_modelos (nu_mod, nu_tip, ds_mod, div_largura, div_altura)
           VALUES (9001, NULL, 'Modelo CI Teste', 1, 1)"""
    )

    # ── dump_geometria_pecas ──────────────────────────────────────────────────
    conn.execute(
        """INSERT OR IGNORE INTO dump_geometria_pecas
           (nu_mod, nu_peca, ds_peca, ds_tipo, eixo_x_alt, eixo_y_alt, eixo_x_lar, eixo_y_lar)
           VALUES (9001, 1, 'Folha CI', 'folha', 0.0, 1.0, 0.0, 1.0)"""
    )

    # ── equivalencias ─────────────────────────────────────────────────────────
    conn.execute(
        """INSERT OR IGNORE INTO equivalencias (codigo_normalizado, fabricante_id, codigo_fabricante)
           VALUES ('NEWCI001', 'SM', 'NEWCI001SG')"""
    )

    conn.commit()
    conn.close()


# ── Request helpers ───────────────────────────────────────────────────────────

@pytest.fixture
def porta_simples_request() -> RenderRequest:
    """RenderRequest mínimo para porta_pivotante_simples 900×2100."""
    return RenderRequest(
        tipologia_nome="porta_pivotante_simples",
        pecas=[PecaInput(nome="Porta", largura_mm=900, altura_mm=2100)],
    )


@pytest.fixture
def box_banheiro_request() -> RenderRequest:
    """RenderRequest para box_banheiro com fixo + porta."""
    return RenderRequest(
        tipologia_nome="box_banheiro",
        pecas=[
            PecaInput(nome="Fixo", largura_mm=300, altura_mm=1900),
            PecaInput(nome="Porta", largura_mm=700, altura_mm=1900),
        ],
    )


# ── Render helpers ────────────────────────────────────────────────────────────

@pytest.fixture
def render_porta_simples(porta_simples_request):
    """RenderResponse pronto para porta_pivotante_simples."""
    return asyncio.run(executar(porta_simples_request))

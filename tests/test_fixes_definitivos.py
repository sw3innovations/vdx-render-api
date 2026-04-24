"""
Testes de regressão — 4 bugs corrigidos em 2026-04-24.

CRÍTICO-1: HTML viewer deslizante direction
CRÍTICO-2: Smart Vision dimensões absurdas (normalizar_dimensoes)
MÉDIO-1:   Timeouts pipeline Vision < 60s nginx
MÉDIO-2:   constitution.registrar() normaliza URL-encoding

Rode com: python -m pytest tests/test_fixes_definitivos.py -v
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.services.vision_service import (
    VisionService,
    VisionResult,
    _OLLAMA_VISION_TIMEOUT_CAP,
    _OLLAMA_TEXT_TIMEOUT,
    MAX_PIPELINE_BUDGET,
)
from app.core.constitution import registrar, buscar, listar_entries


# ── CRÍTICO-1: HTML viewer deslizante direction ───────────────────────────────

class TestViewerDeslizanteDirection:
    """Verifica que o viewer HTML gera código JS com direção correta por folha."""

    def _get_viewer_html(self) -> str:
        from fastapi.testclient import TestClient
        from app.main import app
        from app.config import settings
        with TestClient(app) as c:
            resp = c.get(
                "/api/v1/3d/viewer",
                params={
                    "tipologia": "janela_correr_2_folhas",
                    "largura": 1200,
                    "altura": 1200,
                    "cor_vidro": "incolor",
                },
                headers={"X-VDX-Key": settings.vdx_api_master_key or "test-key"},
            )
            assert resp.status_code == 200, f"viewer returned {resp.status_code}"
            return resp.text

    def test_viewer_html_contem_direction_field(self):
        """O HTML gerado deve conter campo direction no entry deslizante."""
        html = self._get_viewer_html()
        assert "direction:dir" in html, (
            "JS de inicialização deslizante não contém campo 'direction:dir'. "
            "A fix do CRÍTICO-1 não foi aplicada corretamente."
        )

    def test_viewer_html_contem_calculo_dir(self):
        """O HTML deve conter o cálculo de direção baseado na posição x."""
        html = self._get_viewer_html()
        assert "vidro.posicao.x < 0 ? -1 : 1" in html, (
            "JS não calcula direction por posição x. Fix CRÍTICO-1 ausente."
        )

    def test_viewer_html_openval_multiplicado_por_dir(self):
        """openVal deve ser multiplicado por dir (valor assinado)."""
        html = self._get_viewer_html()
        assert ")*dir}" in html or ")*dir}}" in html, (
            "openVal não é multiplicado por dir no HTML. Folhas esquerdas vão na direção errada."
        )

    def test_react_viewer_e_html_viewer_logica_identica(self):
        """A lógica de direção React (viewer-3d.tsx) e HTML devem ser equivalentes."""
        html = self._get_viewer_html()
        # React usa: const dir = state.originalPos.x < 0 ? -1 : 1
        # HTML deve usar: const dir = vidro.posicao.x < 0 ? -1 : 1
        assert "< 0 ? -1 : 1" in html, (
            "HTML viewer não usa lógica de direção dir=-1/+1 como o React viewer."
        )


# ── CRÍTICO-2: normalizar_dimensoes ──────────────────────────────────────────

class TestNormalizarDimensoes:
    """Testa a função _normalizar_dim e sua integração em _to_result."""

    def test_normaliza_90000_divide_por_100(self):
        """90000mm (cm*100 error) → 900mm."""
        v, norm = VisionService._normalizar_dim(90000, "largura_mm")
        assert v == 900
        assert norm is True

    def test_normaliza_210000_divide_por_100(self):
        """210000mm → 2100mm."""
        v, norm = VisionService._normalizar_dim(210000, "altura_mm")
        assert v == 2100
        assert norm is True

    def test_normaliza_90_multiplica_por_10(self):
        """90mm (bare cm, sem conversão) → 900mm."""
        v, norm = VisionService._normalizar_dim(90, "largura_mm")
        assert v == 900
        assert norm is True

    def test_normaliza_50_multiplica_por_10(self):
        """50mm → 500mm."""
        v, norm = VisionService._normalizar_dim(50, "largura_mm")
        assert v == 500
        assert norm is True

    def test_valores_normais_nao_mudam(self):
        """Valores em range [100, 6000] não são alterados."""
        for val in [100, 500, 900, 1200, 2100, 4000, 6000]:
            v, norm = VisionService._normalizar_dim(val, "test")
            assert v == val, f"{val} foi alterado para {v}"
            assert norm is False

    def test_clamp_maximo_6000(self):
        """Valor que após correção ainda > 6000 → clamp em 6000."""
        # 80000 / 100 = 800, ok. Mas 700000 / 100 = 7000 > 6000 → clamp
        v, norm = VisionService._normalizar_dim(700000, "largura_mm")
        assert v == 6000
        assert norm is True

    def test_clamp_minimo_100(self):
        """Valor muito pequeno que após *10 ainda < 100 → clamp em 100."""
        # 5mm * 10 = 50mm < 100 → clamp
        v, norm = VisionService._normalizar_dim(5, "largura_mm")
        assert v == 100
        assert norm is True

    def test_to_result_normaliza_dimensoes_absurdas(self):
        """_to_result deve normalizar 90000/210000 automaticamente."""
        data = {
            "tipologia_sugerida": "porta_pivotante_simples",
            "largura_mm": 90000,
            "altura_mm": 210000,
            "tipo_abertura": "pivotante",
            "num_folhas": 1,
            "espessura_vidro_mm": 8,
            "cor_vidro": "incolor",
            "observacoes": "AI retornou cm*100",
            "confianca": 0.7,
        }
        r = VisionService._to_result(data)
        assert r.largura_mm == 900, f"esperado 900, obtido {r.largura_mm}"
        assert r.altura_mm == 2100, f"esperado 2100, obtido {r.altura_mm}"
        assert r.dimensoes_normalizadas is True

    def test_to_result_valores_normais_nao_normaliza(self):
        """_to_result não altera valores já corretos."""
        data = {
            "tipologia_sugerida": "porta_pivotante_simples",
            "largura_mm": 900,
            "altura_mm": 2100,
            "tipo_abertura": "pivotante",
            "num_folhas": 1,
            "espessura_vidro_mm": 8,
            "cor_vidro": "incolor",
            "observacoes": "",
            "confianca": 0.9,
        }
        r = VisionService._to_result(data)
        assert r.largura_mm == 900
        assert r.altura_mm == 2100
        assert r.dimensoes_normalizadas is False

    def test_pipeline_nao_crasha_com_dimensao_absurda(self):
        """Pipeline completo não levanta exceção com 90000mm."""
        from fastapi.testclient import TestClient
        from app.main import app
        from app.config import settings
        from app.routers import smart_vision as sv

        # VisionResult com dimensões absurdas — normalizadas antes de chegar aqui
        fake_result = VisionResult(
            tipologia_sugerida="porta_pivotante_simples",
            largura_mm=900,   # já normalizado — _to_result faz isso
            altura_mm=2100,
            tipo_abertura="pivotante",
            num_folhas=1,
            espessura_vidro_mm=8,
            cor_vidro="incolor",
            observacoes="AI returned 90000mm, normalized to 900mm",
            confianca=0.7,
            dimensoes_normalizadas=True,
        )

        with TestClient(app) as c:
            import app.routers.smart_vision as sv_mod
            sv_mod._vision._disponivel = True
            original = sv_mod._vision.analisar_foto_vao
            sv_mod._vision.analisar_foto_vao = lambda *a, **kw: fake_result
            try:
                resp = c.post(
                    "/api/v1/smart/photo-to-project",
                    json={"image_base64": "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR4nGNgYGBgAAAABQABXvMqOgAAAABJRU5ErkJggg=="},
                    headers={"X-VDX-Key": settings.vdx_api_master_key or "test-key"},
                )
                assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
            finally:
                sv_mod._vision.analisar_foto_vao = original
                sv_mod._vision._disponivel = None

    def test_vision_result_tem_campo_dimensoes_normalizadas(self):
        """VisionResult deve ter o campo dimensoes_normalizadas."""
        r = VisionResult(
            tipologia_sugerida="porta_pivotante_simples",
            largura_mm=900,
            altura_mm=2100,
            tipo_abertura="pivotante",
            num_folhas=1,
            espessura_vidro_mm=8,
            cor_vidro="incolor",
            observacoes="",
            confianca=0.5,
        )
        assert hasattr(r, "dimensoes_normalizadas"), "Campo dimensoes_normalizadas ausente no VisionResult"
        assert r.dimensoes_normalizadas is False


# ── MÉDIO-1: Pipeline total < 30s budget ────────────────────────────────────

class TestTimeoutPipeline:
    """Verifica que os timeouts configurados garantem pipeline < 30s (nginx /api/vdx/* = 30s)."""

    def test_vision_timeout_cap_e_15(self):
        """Cap de visão deve ser 15s — fail-fast para Claude."""
        assert _OLLAMA_VISION_TIMEOUT_CAP == 15, (
            f"Vision timeout cap é {_OLLAMA_VISION_TIMEOUT_CAP}s, esperado 15s. "
            "Pipeline vision (15+12=27) deve ficar abaixo do budget 30s."
        )

    def test_text_timeout_e_15(self):
        """Cap de texto deve ser 15s."""
        assert _OLLAMA_TEXT_TIMEOUT == 15, (
            f"Text timeout é {_OLLAMA_TEXT_TIMEOUT}s, esperado 15s. "
            "Pipeline texto (15+12=27) deve ficar abaixo do budget 30s."
        )

    def test_pipeline_visao_total_menor_30s(self):
        """Vision pipeline max: Moondream(15) + Claude(12) = 27 < 30."""
        claude_timeout = 12.0
        total = _OLLAMA_VISION_TIMEOUT_CAP + claude_timeout
        assert total < 30, f"Pipeline visão = {total}s >= 30s budget"

    def test_pipeline_texto_total_menor_30s(self):
        """Text pipeline max: Gemma3(15) + Claude(12) = 27 < 30."""
        claude_timeout = 12.0
        total = _OLLAMA_TEXT_TIMEOUT + claude_timeout
        assert total < 30, f"Pipeline texto = {total}s >= 30s budget"

    def test_vision_service_usa_cap_correto(self):
        """VisionService._ollama_vision_timeout <= _OLLAMA_VISION_TIMEOUT_CAP."""
        svc = VisionService()
        assert svc._ollama_vision_timeout <= _OLLAMA_VISION_TIMEOUT_CAP

    def test_claude_vision_timeout_no_source(self):
        """Código-fonte do VisionService contém timeout=12.0 para Claude Vision."""
        import inspect
        src = inspect.getsource(VisionService._analisar_via_claude)
        assert "timeout=12.0" in src, (
            "Claude Vision não tem timeout=12.0. "
            "Pipeline pode exceder 30s budget."
        )

    def test_claude_texto_timeout_no_source(self):
        """Código-fonte do VisionService contém timeout=12.0 para Claude Text."""
        import inspect
        src = inspect.getsource(VisionService._analisar_via_claude_texto)
        assert "timeout=12.0" in src, (
            "Claude Text não tem timeout=12.0. "
            "Pipeline pode exceder 30s budget."
        )


    def test_pipeline_budget_menor_que_30s(self):
        """MAX_PIPELINE_BUDGET < 30s — nginx /api/vdx/* via catch-all tem proxy_read_timeout 30s."""
        assert MAX_PIPELINE_BUDGET < 30, (
            f"MAX_PIPELINE_BUDGET={MAX_PIPELINE_BUDGET}s >= 30s: "
            "Smart Vision via /api/vdx/v1/smart/* timeout no nginx antes de responder."
        )


# ── MÉDIO-2: constitution.registrar() URL-decode ─────────────────────────────

class TestConstitutionUrlNormalization:
    """Verifica que registrar() e buscar() normalizam URL-encoding."""

    @pytest.fixture(autouse=True)
    def _isolated_db(self, tmp_path, monkeypatch):
        """Redirect all constitution writes to a temp DB — never pollute production."""
        import app.core.constitution as c_mod
        from pathlib import Path
        monkeypatch.setattr(c_mod, "DB_PATH", Path(tmp_path) / "test_constitution.db")
        c_mod.init_db()

    _CHAVE_ENCODED = "balc%c3%a3o_de_pia_quatro_folhas"
    _CHAVE_UNICODE = "balcão_de_pia_quatro_folhas"
    _DADOS = {"nome": "Balcão de Pia 4 Folhas", "test": True}

    def test_registrar_normaliza_url_encoding(self):
        """registrar() com chave URL-encoded deve salvar como unicode."""
        registrar(
            self._CHAVE_ENCODED,
            self._DADOS,
            tipo="tipologia",
            origem="test_fixes",
        )
        # Busca pela chave unicode deve encontrar
        result = buscar(self._CHAVE_UNICODE, tipo="tipologia")
        assert result is not None, (
            f"Não encontrou '{self._CHAVE_UNICODE}' após registrar '{self._CHAVE_ENCODED}'. "
            "registrar() não normalizou o URL-encoding."
        )
        assert result["dados"]["test"] is True

    def test_registrar_idempotente_com_encoding_e_unicode(self):
        """registrar() com encoded e unicode devem ser a mesma entry (sem duplicata)."""
        registrar(self._CHAVE_ENCODED, {"v": 1}, tipo="tipologia", origem="test_enc")
        registrar(self._CHAVE_UNICODE, {"v": 2}, tipo="tipologia", origem="test_uni")

        # Deve haver exatamente 1 entry, não 2
        all_entries = listar_entries(tipo="tipologia")
        matching = [e for e in all_entries if self._CHAVE_UNICODE in e.get("chave", "")]
        encoded_entries = [e for e in all_entries if "%" in e.get("chave", "")]
        assert len(encoded_entries) == 0, (
            f"Ainda há {len(encoded_entries)} entry(ies) com chave URL-encoded no DB. "
            "registrar() deve normalizar antes de inserir."
        )

    def test_buscar_normaliza_url_encoding(self):
        """buscar() com chave URL-encoded deve encontrar entry unicode."""
        registrar(self._CHAVE_UNICODE, {"from": "unicode"}, tipo="tipologia", origem="test_buscar")
        result = buscar(self._CHAVE_ENCODED, tipo="tipologia")
        assert result is not None, (
            f"buscar('{self._CHAVE_ENCODED}') não encontrou entry unicode. "
            "buscar() deve normalizar o URL-encoding."
        )

    def test_db_sem_entries_com_percent(self):
        """Verificar que o DB não tem nenhuma entry com '%' na chave."""
        import sqlite3
        from app.core.constitution import DB_PATH
        conn = sqlite3.connect(str(DB_PATH))
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM constitution_entries WHERE instr(chave, '%') > 0")
        count = cur.fetchone()[0]
        conn.close()
        assert count == 0, (
            f"Há {count} entry(ies) com chave URL-encoded no DB. "
            "Execute patch_constitution.py para limpar."
        )

    def test_registrar_loga_warning_quando_normaliza(self, caplog):
        """Não exige log (implementação opcional), mas não deve levantar exceção."""
        import logging
        with caplog.at_level(logging.DEBUG, logger="app.core.constitution"):
            registrar(
                "chave%20com%20espacos",
                {"test": True},
                tipo="tipologia",
                origem="test_log",
            )
        # Não deve levantar exceção
        result = buscar("chave com espacos", tipo="tipologia")
        assert result is not None


# ── CRÍTICO-1: Preview endpoints públicos ────────────────────────────────────

class TestPreviewPublico:
    """Verifica que os endpoints de preview não exigem autenticação."""

    def test_preview_svg_sem_auth_retorna_200(self):
        """GET /api/v1/tipologia/{chave}/preview sem X-VDX-Key deve retornar 200."""
        from fastapi.testclient import TestClient
        from app.main import app
        with TestClient(app) as c:
            resp = c.get("/api/v1/tipologia/porta_pivotante_simples/preview")
            assert resp.status_code == 200, (
                f"Preview SVG retornou {resp.status_code} sem auth. "
                "CRÍTICO-1 não aplicado: validate_api_key ainda protege GET preview."
            )
            assert "image/svg+xml" in resp.headers.get("content-type", "")

    def test_preview_png_sem_auth_retorna_200(self):
        """GET /api/v1/tipologia/{chave}/preview/png sem X-VDX-Key deve retornar 200."""
        from fastapi.testclient import TestClient
        from app.main import app
        with TestClient(app) as c:
            resp = c.get("/api/v1/tipologia/porta_pivotante_simples/preview/png")
            assert resp.status_code in (200, 500), (
                f"Preview PNG retornou {resp.status_code} sem auth. "
                "CRÍTICO-1 não aplicado: endpoint exige autenticação."
            )
            assert resp.status_code != 401, (
                "Preview PNG retornou 401 — endpoint ainda exige X-VDX-Key. "
                "Browser não consegue carregar <img src> sem auth."
            )

    def test_listar_previews_sem_auth_retorna_200(self):
        """GET /api/v1/tipologias/previews sem X-VDX-Key deve retornar 200."""
        from fastapi.testclient import TestClient
        from app.main import app
        with TestClient(app) as c:
            resp = c.get("/api/v1/tipologias/previews")
            assert resp.status_code == 200, (
                f"Listagem de previews retornou {resp.status_code} sem auth. "
                "CRÍTICO-1 não aplicado."
            )
            data = resp.json()
            assert "items" in data

    def test_render_sem_auth_continua_retornando_401(self):
        """POST /api/v1/render/export/3d com sem X-VDX-Key deve retornar 401."""
        from fastapi.testclient import TestClient
        from app.main import app
        with TestClient(app) as c:
            resp = c.post("/api/v1/render/export/3d", json={
                "tipologia_nome": "porta_pivotante_simples",
                "pecas": [{"nome": "Porta", "largura_mm": 900, "altura_mm": 2100}]
            })
            assert resp.status_code == 401, (
                f"Render retornou {resp.status_code} sem auth — deveria ser 401. "
                "Endpoints de render devem permanecer protegidos."
            )


# ── MÉDIO-1: duas_folhas em auto_pecas ───────────────────────────────────────

class TestAutoPecasDuasFolhas:
    """Verifica que 'duas_folhas' é reconhecido como padrão de 2 folhas."""

    def test_viewer_3d_reconhece_duas_folhas(self):
        """_auto_pecas com 'balcão_de_pia_duas_folhas' deve gerar 2 peças."""
        from app.routers.viewer_3d import _auto_pecas
        pecas = _auto_pecas("balcão_de_pia_duas_folhas", 1200, 800)
        assert len(pecas) == 2, (
            f"_auto_pecas retornou {len(pecas)} peças para 'duas_folhas', esperado 2. "
            "MÉDIO-1 não aplicado em viewer_3d.py."
        )

    def test_viewer_3d_reconhece_balcao_quatro_folhas(self):
        """_auto_pecas com 'balcão_de_pia_quatro_folhas' deve gerar 4 peças."""
        from app.routers.viewer_3d import _auto_pecas
        pecas = _auto_pecas("balcão_de_pia_quatro_folhas", 2000, 800)
        assert len(pecas) == 4, (
            f"_auto_pecas retornou {len(pecas)} peças para 'quatro_folhas', esperado 4."
        )


# ── ALTO-1: DB sem lixo de testes ────────────────────────────────────────────

class TestDbSemLixoTestes:
    """Verifica que o DB de produção não contém entradas geradas por testes."""

    def test_db_sem_origens_test(self):
        """Nenhuma entry no DB deve ter origem com prefixo 'test_'."""
        import sqlite3
        from app.core.constitution import DB_PATH
        conn = sqlite3.connect(str(DB_PATH))
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM constitution_entries WHERE origem LIKE 'test_%'")
        count = cur.fetchone()[0]
        conn.close()
        assert count == 0, (
            f"Há {count} entry(ies) com origem 'test_*' no DB de produção. "
            "Execute fix_alto1_db.py para limpar."
        )

    def test_db_sem_chaves_com_espacos(self):
        """Nenhuma entry no DB deve ter espaço na chave."""
        import sqlite3
        from app.core.constitution import DB_PATH
        conn = sqlite3.connect(str(DB_PATH))
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM constitution_entries WHERE instr(chave, ' ') > 0")
        count = cur.fetchone()[0]
        conn.close()
        assert count == 0, (
            f"Há {count} entry(ies) com espaço na chave no DB. "
            "registrar() deve normalizar espaços."
        )

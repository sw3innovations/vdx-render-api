"""
Testes para app/services/photorealistic_pipeline.py

Dependências externas (cv2, cairosvg, gradio_client, urllib) são mockadas
para que os testes rodem sem GPU/rede.
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

_DUMMY_SVG = '<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100"><rect width="100" height="100"/></svg>'
_DUMMY_PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 100
_DUMMY_JPEG = b"\xff\xd8\xff" + b"\x00" * 100


# ---------------------------------------------------------------------------
# _cache_path — lógica pura, sem mock
# ---------------------------------------------------------------------------

def test_cache_path_creates_subdir(tmp_path):
    from app.services.photorealistic_pipeline import _cache_path
    p = _cache_path(str(tmp_path), "porta_pivotante_simples", 900.0, 2100.0)
    assert p.parent.name == "fotorrealistas"
    assert p.parent.exists()


def test_cache_path_filename(tmp_path):
    from app.services.photorealistic_pipeline import _cache_path
    p = _cache_path(str(tmp_path), "porta_pivotante_simples", 900.0, 2100.0)
    assert p.name == "porta_pivotante_simples_900x2100.jpg"


def test_cache_path_rounds_float_dimensions(tmp_path):
    from app.services.photorealistic_pipeline import _cache_path
    p = _cache_path(str(tmp_path), "box", 700.5, 1900.9)
    assert p.name == "box_700x1900.jpg"


# ---------------------------------------------------------------------------
# _prompt_para_chave — lógica pura
# ---------------------------------------------------------------------------

def test_prompt_para_chave_porta():
    from app.services.photorealistic_pipeline import _prompt_para_chave
    p = _prompt_para_chave("porta_pivotante_simples")
    assert "pivot" in p
    assert "glass door" in p


def test_prompt_para_chave_box():
    from app.services.photorealistic_pipeline import _prompt_para_chave
    p = _prompt_para_chave("box_banheiro")
    assert "shower" in p


def test_prompt_para_chave_desconhecido():
    from app.services.photorealistic_pipeline import _prompt_para_chave
    p = _prompt_para_chave("tipologia_desconhecida")
    assert "glass door" in p


# ---------------------------------------------------------------------------
# gerar_fotorrealista — cache hit (sem rede)
# ---------------------------------------------------------------------------

def test_gerar_fotorrealista_cache_hit(tmp_path):
    from app.services.photorealistic_pipeline import gerar_fotorrealista

    cache_dir = tmp_path / "fotorrealistas"
    cache_dir.mkdir()
    (cache_dir / "porta_pivotante_simples_900x2100.jpg").write_bytes(_DUMMY_JPEG)

    result_bytes, mime = asyncio.run(gerar_fotorrealista(
        svg=_DUMMY_SVG,
        chave="porta_pivotante_simples",
        largura_mm=900.0,
        altura_mm=2100.0,
        upload_dir=str(tmp_path),
    ))

    assert result_bytes == _DUMMY_JPEG
    assert mime == "image/jpeg"


# ---------------------------------------------------------------------------
# gerar_fotorrealista — Pollinations sucesso → salva cache
# ---------------------------------------------------------------------------

def test_gerar_fotorrealista_pollinations_success_saves_cache(tmp_path):
    from app.services import photorealistic_pipeline as foto

    with patch.object(foto, "_run_pollinations", return_value=_DUMMY_JPEG):
        result_bytes, mime = asyncio.run(foto.gerar_fotorrealista(
            svg=_DUMMY_SVG,
            chave="janela_correr",
            largura_mm=1200.0,
            altura_mm=1000.0,
            upload_dir=str(tmp_path),
        ))

    assert result_bytes == _DUMMY_JPEG
    assert mime == "image/jpeg"
    cache_file = tmp_path / "fotorrealistas" / "janela_correr_1200x1000.jpg"
    assert cache_file.exists()
    assert cache_file.read_bytes() == _DUMMY_JPEG


# ---------------------------------------------------------------------------
# gerar_fotorrealista — Pollinations falha → HF Canny → sucesso
# ---------------------------------------------------------------------------

def test_gerar_fotorrealista_falls_through_to_hf_canny(tmp_path):
    from app.services import photorealistic_pipeline as foto

    with patch.object(foto, "_run_pollinations", side_effect=RuntimeError("net err")):
        with patch.object(foto, "_run_hf_canny", return_value=_DUMMY_JPEG):
            result_bytes, mime = asyncio.run(foto.gerar_fotorrealista(
                svg=_DUMMY_SVG,
                chave="box_banheiro",
                largura_mm=700.0,
                altura_mm=1900.0,
                upload_dir=str(tmp_path),
            ))

    assert result_bytes == _DUMMY_JPEG
    assert mime == "image/jpeg"


# ---------------------------------------------------------------------------
# gerar_fotorrealista — tudo falha → fallback PNG
# ---------------------------------------------------------------------------

def test_gerar_fotorrealista_fallback_on_all_errors(tmp_path):
    from app.services import photorealistic_pipeline as foto

    with patch.object(foto, "_run_pollinations", side_effect=RuntimeError("net")):
        with patch.object(foto, "_run_hf_canny", side_effect=RuntimeError("hf")):
            with patch.object(foto, "_fallback_png", return_value=_DUMMY_PNG):
                result_bytes, mime = asyncio.run(foto.gerar_fotorrealista(
                    svg=_DUMMY_SVG,
                    chave="test",
                    largura_mm=500.0,
                    altura_mm=500.0,
                    upload_dir=str(tmp_path),
                ))

    assert result_bytes == _DUMMY_PNG
    assert mime == "image/png"


# ---------------------------------------------------------------------------
# _run_pollinations — verifica URL e parâmetros
# ---------------------------------------------------------------------------

def test_run_pollinations_builds_correct_url(tmp_path):
    from app.services import photorealistic_pipeline as foto
    import io
    from PIL import Image

    # Simula resposta HTTP com JPEG válido
    fake_img = Image.new("RGB", (512, 512), color=(100, 150, 200))
    buf = io.BytesIO()
    fake_img.save(buf, format="JPEG")
    fake_jpeg = buf.getvalue()

    class FakeResp:
        def read(self): return fake_jpeg
        def __enter__(self): return self
        def __exit__(self, *a): pass

    captured_url = []

    def fake_urlopen(req, timeout=None):
        captured_url.append(req.full_url if hasattr(req, "full_url") else str(req))
        return FakeResp()

    with patch("urllib.request.urlopen", side_effect=fake_urlopen):
        result = foto._run_pollinations("porta_pivotante_simples", 900.0, 2100.0)

    assert isinstance(result, bytes)
    assert len(captured_url) == 1
    url = captured_url[0]
    assert "pollinations.ai" in url
    assert "flux" in url
    assert "porta" in url.lower() or "pivot" in url.lower() or "glass" in url.lower()


# ---------------------------------------------------------------------------
# _run_hf_canny — verifica que client.predict é chamado corretamente
# ---------------------------------------------------------------------------

def test_run_hf_canny_calls_predict_with_correct_params(tmp_path):
    import numpy as np

    fake_after = str(tmp_path / "after.jpg")
    Path(fake_after).write_bytes(_DUMMY_JPEG)

    mock_client = MagicMock()
    mock_client.predict.return_value = ("before.jpg", fake_after)
    mock_gradio = MagicMock()
    mock_gradio.Client.return_value = mock_client

    mock_cv2 = MagicMock()
    mock_cv2.IMREAD_GRAYSCALE = 0
    mock_cv2.imdecode.return_value = np.zeros((10, 10), dtype=np.uint8)
    mock_cv2.GaussianBlur.return_value = np.zeros((10, 10), dtype=np.uint8)
    mock_cv2.Canny.return_value = np.zeros((10, 10), dtype=np.uint8)
    mock_cv2.imencode.return_value = (True, MagicMock(tobytes=lambda: b"canny"))

    mock_cairo = MagicMock()
    mock_cairo.svg2png.return_value = _DUMMY_PNG

    fake_img = MagicMock()
    fake_img.convert.return_value = fake_img
    fake_img.save = lambda buf, **kw: buf.write(_DUMMY_JPEG)
    mock_pil_image = MagicMock()
    mock_pil_image.open.return_value = fake_img

    with patch.dict(sys.modules, {
        "gradio_client": mock_gradio,
        "cv2": mock_cv2,
        "cairosvg": mock_cairo,
        "PIL": MagicMock(Image=mock_pil_image),
        "PIL.Image": mock_pil_image,
    }):
        if "app.services.photorealistic_pipeline" in sys.modules:
            del sys.modules["app.services.photorealistic_pipeline"]
        from app.services.photorealistic_pipeline import _run_hf_canny
        result = _run_hf_canny(_DUMMY_SVG)

    mock_client.predict.assert_called_once()
    kwargs = mock_client.predict.call_args.kwargs
    assert kwargs["api_name"] == "/generate_image"
    assert kwargs["seed"] == 42
    assert isinstance(result, bytes)

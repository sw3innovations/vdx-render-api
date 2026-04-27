"""
Router 3D — Viewer interativo e endpoint de Scene JSON.

POST /api/v1/3d/viewer/token → emite view token JWT (requer X-VDX-Key)
GET  /api/v1/3d/viewer       → HTML Three.js — aceita X-VDX-Key header OU ?t=<token>
POST /api/v1/render/export/3d → Scene JSON para consumo externo
"""
import json
import logging
from typing import Optional

from fastapi import APIRouter, Depends, Header, Query, Request
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel, Field

from app.config import settings
from app.core import view_token as vt
from app.core.limiter import limiter
from app.core.auth import validate_api_key
from app.models._limits import DIMENSAO_MIN_MM, DIMENSAO_MAX_MM, ESPESSURA_MIN_MM, ESPESSURA_MAX_MM
from app.models.render import PecaInput, RenderRequest
from app.renderers.scene_builder import SceneBuilder, CORES_VIDRO
from app.services.render_orchestrator import executar

log = logging.getLogger(__name__)
router = APIRouter(tags=["3d"])

_sb = SceneBuilder()


# ─── Modelos ──────────────────────────────────────────────────────────────────

class Render3DRequest(RenderRequest):
    """RenderRequest estendido com parâmetros do viewer 3D."""
    cor_vidro: str = "default"
    espessura_vidro_mm: Optional[float] = 8.0


class ViewTokenRequest(BaseModel):
    """Parâmetros para emissão de um view token."""
    tipologia: str = Field(..., min_length=1, max_length=200)
    largura: float = Field(..., ge=DIMENSAO_MIN_MM, le=DIMENSAO_MAX_MM)
    altura: float = Field(..., ge=DIMENSAO_MIN_MM, le=DIMENSAO_MAX_MM)
    cor_vidro: str = Field("default", max_length=50)
    fabricante: Optional[str] = Field(None, max_length=100)
    espessura: float = Field(8.0, ge=ESPESSURA_MIN_MM, le=ESPESSURA_MAX_MM)
    ttl_seconds: Optional[int] = Field(None, ge=60, le=86400)


class ViewTokenResponse(BaseModel):
    """Resposta com token JWT e URL compartilhável."""
    token: str
    url: str
    expires_in: int
    expires_at: int


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _html_error(status: int, title: str, message: str) -> HTMLResponse:
    """Retorna página HTML amigável para erros de autenticação do viewer."""
    html = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>VDX 3D — {title}</title>
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{background:#F5F2EE;font-family:'Segoe UI',system-ui,sans-serif;
     display:flex;align-items:center;justify-content:center;min-height:100vh;color:#222}}
.card{{background:#fff;border-radius:16px;padding:40px 48px;max-width:420px;width:90%;
       box-shadow:0 4px 24px rgba(0,0,0,.10);text-align:center}}
.icon{{font-size:48px;margin-bottom:16px}}
h1{{font-size:20px;font-weight:700;color:#1a5276;margin-bottom:8px}}
p{{font-size:14px;color:#666;line-height:1.6}}
.code{{display:inline-block;background:#f0f0f0;border-radius:6px;
       padding:2px 8px;font-family:monospace;font-size:13px;color:#333;margin-top:12px}}
</style>
</head>
<body>
<div class="card">
  <div class="icon">&#x1F512;</div>
  <h1>{title}</h1>
  <p>{message}</p>
  <div class="code">HTTP {status}</div>
</div>
</body>
</html>"""
    return HTMLResponse(content=html, status_code=status)


def _auto_pecas(tipologia: str, largura: float, altura: float) -> list[PecaInput]:
    """Auto-gera peças baseado na tipologia para o viewer GET."""
    t = tipologia.lower()
    if any(k in t for k in ("6_folhas", "6folhas")):
        w = largura / 6
        return [PecaInput(nome=f"Folha {i+1}", largura_mm=w, altura_mm=altura) for i in range(6)]
    if any(k in t for k in ("3_folhas", "3folhas")):
        w = largura / 3
        return [PecaInput(nome=f"Folha {i+1}", largura_mm=w, altura_mm=altura) for i in range(3)]
    if any(k in t for k in ("2_folhas", "2folhas", "box")):
        w = largura / 2
        return [
            PecaInput(nome="Folha 1", largura_mm=w, altura_mm=altura),
            PecaInput(nome="Folha 2", largura_mm=w, altura_mm=altura),
        ]
    if "dupla_bandeira" in t:
        return [
            PecaInput(nome="Bandeira", largura_mm=largura, altura_mm=min(400.0, altura * 0.16)),
            PecaInput(nome="Porta",    largura_mm=largura, altura_mm=altura),
        ]
    return [PecaInput(nome="Porta", largura_mm=largura, altura_mm=altura)]


# ─── Endpoints ────────────────────────────────────────────────────────────────

@router.post("/api/v1/render/export/3d")
@limiter.limit("5/second")
async def export_3d(
    request: Request,
    body: Render3DRequest,
    _auth: None = Depends(validate_api_key),
) -> JSONResponse:
    """Gera Scene JSON 3D para consumo do viewer ou SDK externo."""
    resp = await executar(body)
    scene = _sb.build(
        resp,
        espessura_vidro=body.espessura_vidro_mm or 8.0,
        cor_vidro=body.cor_vidro or "default",
    )
    return JSONResponse(content=scene)


@router.post("/api/v1/3d/viewer/token")
@limiter.limit("30/minute")
async def create_viewer_token(
    request: Request,
    body: ViewTokenRequest,
    _auth: None = Depends(validate_api_key),
) -> ViewTokenResponse:
    """Emite um view token JWT de curta duração para o viewer 3D.

    Permite compartilhar o viewer via link (WhatsApp, e-mail, iframe)
    sem expor a API key. O token carrega dimensões e tipologia assinados —
    o receptor não pode alterar os parâmetros.
    """
    ttl = body.ttl_seconds or settings.view_token_ttl_seconds
    ttl = min(ttl, settings.view_token_max_ttl_seconds)

    claims = vt.new_claims(
        tip=body.tipologia,
        w=body.largura,
        h=body.altura,
        cv=body.cor_vidro,
        fab=body.fabricante,
        esp=body.espessura,
        ttl_seconds=ttl,
    )
    token = vt.encode(claims, settings.view_token_secret)

    # Monta base URL a partir do request (funciona atrás de proxy reverso)
    base = str(request.base_url).rstrip("/")
    url = f"{base}/api/v1/3d/viewer?t={token}"

    return ViewTokenResponse(token=token, url=url, expires_in=ttl, expires_at=claims.exp)


@router.get("/api/v1/3d/viewer")
@limiter.limit("60/minute")
async def viewer_3d(
    request: Request,
    # Modo 1: view token via query param (browser / link compartilhado)
    t: Optional[str] = Query(None, description="View token JWT emitido por POST /token"),
    # Modo 2: API key via header (SDK / fetch autenticado) — parâmetros manuais
    x_vdx_key: Optional[str] = Header(None, alias="X-VDX-Key"),
    tipologia: str = Query("porta_pivotante_simples"),
    largura: float = Query(900.0, ge=100, le=10000),
    altura: float  = Query(2100.0, ge=100, le=10000),
    cor_vidro: str = Query("default"),
    espessura: float = Query(8.0, ge=3, le=25),
) -> HTMLResponse:
    """Serve o viewer 3D HTML com scene JSON embutido.

    Aceita autenticação em dois modos:
    - **?t=<token>**: view token de curta duração (browser, WhatsApp, iframe)
    - **X-VDX-Key header**: API key completa (SDK, fetch autenticado)
    """
    if t:
        # ── Modo token ────────────────────────────────────────────────────────
        try:
            claims = vt.decode(t, settings.view_token_secret)
        except vt.ViewTokenExpiredError:
            return _html_error(
                401,
                "Link expirado",
                "Este link de visualização expirou. Solicite um novo link ao responsável.",
            )
        except vt.ViewTokenInvalidError:
            return _html_error(
                401,
                "Link inválido",
                "Este link de visualização é inválido ou foi adulterado.",
            )
        # Dimensões vêm da assinatura — não usar query params para evitar forja
        tipologia  = claims.tip
        largura    = claims.w
        altura     = claims.h
        cor_vidro  = claims.cv
        espessura  = claims.esp

    else:
        # ── Modo header ───────────────────────────────────────────────────────
        if not x_vdx_key:
            return _html_error(
                401,
                "Autenticação necessária",
                "Acesse o viewer através de um link compartilhável ou com a API key no header X-VDX-Key.",
            )
        master = settings.vdx_api_master_key
        import hmac as _hmac
        if master and not _hmac.compare_digest(x_vdx_key, master):
            log.warning("Viewer: API key inválida (primeiros 4 chars: %s...)", x_vdx_key[:4])
            return _html_error(
                401,
                "API key inválida",
                "A chave de API fornecida é inválida.",
            )

    pecas = _auto_pecas(tipologia, largura, altura)
    req = RenderRequest(tipologia_nome=tipologia, pecas=pecas)
    resp = await executar(req)
    scene = _sb.build(resp, espessura_vidro=espessura, cor_vidro=cor_vidro)

    html = _gerar_viewer_html(scene)
    return HTMLResponse(content=html)


# ─── Fotorrealista ─────────────────────────────────────────────────────────────

_CORES_VALIDAS = {"incolor", "verde", "fumê", "fume", "bronze", "azul"}
_ACABAMENTOS_VALIDOS = {"cromado", "inox", "dourado", "preto"}


@router.get("/api/v1/tipologia/{chave}/fotorrealista")
@limiter.limit("10/minute")
async def tipologia_fotorrealista(
    request: Request,
    chave: str,
    largura: float = Query(900.0, ge=DIMENSAO_MIN_MM, le=DIMENSAO_MAX_MM, description="Largura em mm"),
    altura: float = Query(2100.0, ge=DIMENSAO_MIN_MM, le=DIMENSAO_MAX_MM, description="Altura em mm"),
    cor: str = Query("incolor", description="Cor do vidro: incolor, verde, fumê, bronze, azul"),
    acabamento: str = Query("cromado", description="Acabamento: cromado, inox, dourado, preto"),
):
    """Retorna imagem PNG da tipologia gerada pelo SVG Renderer v2.

    PNG renderizado via CairoSVG, sem dependências externas.
    Sem autenticação — endpoint público.
    """
    import cairosvg
    from fastapi.responses import Response as FastAPIResponse
    from app.renderers.svg_renderer_v2 import render as render_v2

    cor_norm = cor.lower().strip()
    acab_norm = acabamento.lower().strip()
    if cor_norm not in _CORES_VALIDAS:
        cor_norm = "incolor"
    if acab_norm not in _ACABAMENTOS_VALIDOS:
        acab_norm = "cromado"

    svg = render_v2(chave, largura, altura, cor=cor_norm, acabamento=acab_norm)
    png_bytes = cairosvg.svg2png(bytestring=svg.encode())

    return FastAPIResponse(
        content=png_bytes,
        media_type="image/png",
        headers={
            "Content-Disposition": f'inline; filename="{chave}_{int(largura)}x{int(altura)}_{cor_norm}_{acab_norm}.png"',
            "Cache-Control": "no-store",
        },
    )


# ─── HTML Generator ───────────────────────────────────────────────────────────

def _gerar_viewer_html(scene: dict) -> str:
    scene_json = json.dumps(scene, ensure_ascii=False, separators=(",", ":"))
    tipologia   = scene.get("tipologia", "")
    dim         = scene.get("dimensoes", {})
    n_vidros    = len(scene.get("vidros", []))
    n_ferr      = len(scene.get("ferragens", []))

    return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0">
<title>VDX 3D — {tipologia}</title>
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{background:#F5F2EE;overflow:hidden;font-family:'Segoe UI',system-ui,sans-serif;color:#222}}
#c{{display:block;width:100vw;height:100vh}}
#ui{{
  position:fixed;top:16px;right:16px;
  background:rgba(255,255,255,.88);
  border:1px solid rgba(0,0,0,.08);border-radius:16px;
  padding:16px 18px;min-width:210px;max-width:240px;
  backdrop-filter:blur(16px);-webkit-backdrop-filter:blur(16px);
  box-shadow:0 4px 24px rgba(0,0,0,.12);z-index:10;user-select:none
}}
#ui h3{{font-size:12px;font-weight:700;color:#1a5276;letter-spacing:.8px;text-transform:uppercase;margin-bottom:3px}}
#ui .sub{{font-size:11px;color:#666;margin-bottom:10px}}
#ui hr{{border:none;border-top:1px solid rgba(0,0,0,.07);margin:9px 0}}
.btn{{
  display:block;width:100%;padding:8px 12px;border:none;border-radius:8px;
  font-size:12px;font-weight:500;cursor:pointer;transition:all .15s;margin-bottom:6px
}}
.btn-primary{{background:rgba(26,82,118,.12);color:#1a5276;border:1px solid rgba(26,82,118,.25)}}
.btn-primary:hover{{background:rgba(26,82,118,.2)}}
.btn-primary.active{{background:rgba(26,82,118,.35);color:#fff}}
.btn-action{{background:rgba(0,0,0,.04);color:#555;border:1px solid rgba(0,0,0,.08)}}
.btn-action:hover{{background:rgba(0,0,0,.08);color:#222}}
.color-grid{{display:grid;grid-template-columns:repeat(3,1fr);gap:5px;margin:8px 0}}
.color-swatch{{
  height:32px;border-radius:8px;cursor:pointer;border:2px solid transparent;
  transition:all .15s;position:relative
}}
.color-swatch.active{{border-color:#1a5276;transform:scale(1.08)}}
.color-swatch:hover{{transform:scale(1.05)}}
.label{{font-size:10px;font-weight:600;color:#888;text-transform:uppercase;letter-spacing:.5px;margin-bottom:5px}}
.info-row{{font-size:11px;color:#999;display:flex;justify-content:space-between;margin-bottom:2px}}
.info-val{{color:#333;font-weight:600}}
#hint{{
  position:fixed;bottom:16px;left:50%;transform:translateX(-50%);
  background:rgba(0,0,0,.45);padding:6px 18px;border-radius:20px;
  font-size:11px;color:#ddd;pointer-events:none;
  animation:fadeout 4s 2.5s forwards
}}
@keyframes fadeout{{to{{opacity:0}}}}
#loading{{
  position:fixed;inset:0;background:#F5F2EE;display:flex;
  align-items:center;justify-content:center;flex-direction:column;gap:14px;z-index:999
}}
#loading p{{font-size:14px;color:#1a5276;font-weight:500}}
.spinner{{
  width:40px;height:40px;border:3px solid rgba(26,82,118,.15);
  border-top-color:#1a5276;border-radius:50%;animation:spin .75s linear infinite
}}
@keyframes spin{{to{{transform:rotate(360deg)}}}}
</style>
</head>
<body>
<div id="loading"><div class="spinner"></div><p>Carregando viewer 3D…</p></div>
<canvas id="c"></canvas>

<div id="ui">
  <h3>VDX 3D Viewer</h3>
  <div class="sub">{tipologia.replace("_"," ").title()}</div>

  <div class="info-row"><span>Largura</span><span class="info-val">{dim.get("largura","?")}mm</span></div>
  <div class="info-row"><span>Altura</span><span class="info-val">{dim.get("altura","?")}mm</span></div>
  <div class="info-row"><span>Vidros</span><span class="info-val">{n_vidros}</span></div>
  <div class="info-row"><span>Ferragens</span><span class="info-val">{n_ferr}</span></div>

  <hr>
  <button id="btn-door" class="btn btn-primary" onclick="toggleDoor()">&#x1F6AA; Abrir porta</button>

  <hr>
  <div class="label">Cor do vidro</div>
  <div class="color-grid">
    <div class="color-swatch active" style="background:linear-gradient(135deg,rgba(200,220,235,.6),rgba(230,245,255,.8))" title="Incolor" onclick="setGlassColor('incolor',this)"></div>
    <div class="color-swatch" style="background:linear-gradient(135deg,rgba(74,122,91,.55),rgba(100,160,120,.7))" title="Verde" onclick="setGlassColor('verde',this)"></div>
    <div class="color-swatch" style="background:linear-gradient(135deg,rgba(40,40,40,.75),rgba(70,70,70,.85))" title="Fume" onclick="setGlassColor('fume',this)"></div>
    <div class="color-swatch" style="background:linear-gradient(135deg,rgba(107,91,58,.65),rgba(150,125,85,.75))" title="Bronze" onclick="setGlassColor('bronze',this)"></div>
    <div class="color-swatch" style="background:linear-gradient(135deg,#C8D8E8,#f0f0f0,#C8D8E8)" title="Espelho" onclick="setGlassColor('espelho',this)"></div>
    <div class="color-swatch" style="background:linear-gradient(135deg,rgba(200,215,225,.4),rgba(220,235,245,.6))" title="Default" onclick="setGlassColor('default',this)"></div>
  </div>

  <hr>
  <button class="btn btn-action" onclick="resetCamera()">&#x1F3A5; Reset camera</button>
  <button class="btn btn-action" onclick="screenshot()">&#x1F4F7; Screenshot PNG</button>
</div>

<div id="hint">Arrastar: orbitar &nbsp;|&nbsp; Scroll: zoom &nbsp;|&nbsp; Shift+drag: pan</div>

<script type="importmap">
{{"imports":{{"three":"https://cdn.jsdelivr.net/npm/three@0.165.0/build/three.module.min.js","three/addons/":"https://cdn.jsdelivr.net/npm/three@0.165.0/examples/jsm/"}}}}
</script>
<script type="module">
import * as THREE from 'three';
import {{ OrbitControls }} from 'three/addons/controls/OrbitControls.js';

// ── Dados da cena (embutidos pelo Python) ─────────────────────────────────
const SCENE = {scene_json};

// Tabela de materiais de vidro para troca interativa
const VIDRO_MATS = {{
  incolor: {{cor:"#FFFFFF",   op:0.08, tr:0.96, att:"#FFFFFF", attD:200}},
  verde:   {{cor:"#4A7A5B",   op:0.12, tr:0.88, att:"#2D5A3D", attD:60}},
  fume:    {{cor:"#3A3A3A",   op:0.25, tr:0.72, att:"#1A1A1A", attD:20}},
  bronze:  {{cor:"#6B5B3A",   op:0.18, tr:0.78, att:"#4A3A1A", attD:35}},
  espelho: {{cor:"#E0E0E0",   op:0.05, tr:0.05, att:"#C0C0C0", attD:5, metal:0.95}},
  default: {{cor:"#B8D4E3",   op:0.10, tr:0.92, att:"#FFFFFF", attD:150}},
}};

// ── Estado global ─────────────────────────────────────────────────────────
let renderer, camera, controls, threeScene;
const glassMeshes = [];
const animatables = [];
let isDoorOpen = false;

// ── Bootstrap ─────────────────────────────────────────────────────────────
window.addEventListener("load", () => {{
  init();
  loadScene(SCENE);
  animate();
  document.getElementById("loading").style.display = "none";
  if (animatables.length === 0) document.getElementById("btn-door").style.display = "none";
}});

// ── Three.js setup ────────────────────────────────────────────────────────
function init() {{
  const canvas = document.getElementById("c");
  const W = window.innerWidth, H = window.innerHeight;

  // Renderer fotorrealista
  renderer = new THREE.WebGLRenderer({{canvas, antialias:true, preserveDrawingBuffer:true}});
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
  renderer.setSize(W, H);
  renderer.toneMapping = THREE.ACESFilmicToneMapping;
  renderer.toneMappingExposure = 1.2;
  renderer.shadowMap.enabled = true;
  renderer.shadowMap.type = THREE.PCFSoftShadowMap;
  renderer.outputColorSpace = THREE.SRGBColorSpace;

  threeScene = new THREE.Scene();
  threeScene.background = new THREE.Color("#F5F2EE");

  camera = new THREE.PerspectiveCamera(40, W/H, 1, 50000);

  controls = new OrbitControls(camera, renderer.domElement);
  controls.enableDamping = true;
  controls.dampingFactor = 0.05;
  controls.minDistance = 300;
  controls.maxDistance = 15000;
  controls.maxPolarAngle = Math.PI * 0.87;
  controls.screenSpacePanning = true;

  // Environment map procedural (gera reflexos reais sem HDR externo)
  const pmrem = new THREE.PMREMGenerator(renderer);
  pmrem.compileEquirectangularShader();
  // Cena de luz estúdio como fonte do env map
  const envScene = new THREE.RoomEnvironment(0.5);
  const envMap = pmrem.fromScene(envScene, 0.04).texture;
  threeScene.environment = envMap;
  pmrem.dispose();

  // Iluminação 3-point fotorrealista
  // Key: quente, forte, com sombras
  const key = new THREE.DirectionalLight(0xFFF8F0, 2.5);
  key.position.set(2000, 3000, 2000);
  key.castShadow = true;
  key.shadow.mapSize.set(2048, 2048);
  key.shadow.camera.near = 10;
  key.shadow.camera.far = 12000;
  key.shadow.camera.left = -2500;
  key.shadow.camera.right = 2500;
  key.shadow.camera.top = 3500;
  key.shadow.camera.bottom = -500;
  key.shadow.bias = -0.0005;
  key.shadow.normalBias = 0.02;
  threeScene.add(key);

  // Fill: frio, suave, sem sombra
  const fill = new THREE.DirectionalLight(0xD4E4FF, 0.8);
  fill.position.set(-1500, 2000, 1000);
  threeScene.add(fill);

  // Rim: contorno quente
  const rim = new THREE.DirectionalLight(0xFFE0C0, 0.6);
  rim.position.set(0, 500, -2500);
  threeScene.add(rim);

  // Ambient
  threeScene.add(new THREE.AmbientLight(0xF0EDE8, 0.4));

  // Piso MeshStandardMaterial (reflexivo sutil)
  const pisoGeo = new THREE.PlaneGeometry(12000, 12000);
  const pisoMat = new THREE.MeshStandardMaterial({{
    color: new THREE.Color("#F0EDE8"),
    roughness: 0.4,
    metalness: 0.0,
    envMapIntensity: 0.25,
  }});
  const piso = new THREE.Mesh(pisoGeo, pisoMat);
  piso.rotation.x = -Math.PI/2;
  piso.position.y = -1;
  piso.receiveShadow = true;
  threeScene.add(piso);

  window.addEventListener("resize", () => {{
    const W = window.innerWidth, H = window.innerHeight;
    camera.aspect = W/H;
    camera.updateProjectionMatrix();
    renderer.setSize(W, H);
  }});
}}

// ── Carregamento da cena ──────────────────────────────────────────────────
function loadScene(s) {{
  const cam = s.ambiente.camera_inicial;
  camera.position.set(cam.posicao.x, cam.posicao.y, cam.posicao.z);
  camera.lookAt(cam.target.x, cam.target.y, cam.target.z);
  controls.target.set(cam.target.x, cam.target.y, cam.target.z);
  controls.update();

  // Parede / vão
  threeScene.add(createWall(s.vao));

  // Vidros
  s.vidros.forEach(v => {{
    const obj = addGlass(v);
    if (obj) glassMeshes.push(obj.mesh || obj);
  }});

  // Ferragens
  s.ferragens.forEach(f => threeScene.add(createHardware(f)));
}}

// ── Vidro fotorrealista — MeshPhysicalMaterial completo ───────────────────
function makeGlassMaterial(m) {{
  const mat = new THREE.MeshPhysicalMaterial({{
    color:               new THREE.Color(m.cor),
    transparent:         true,
    opacity:             m.opacidade,
    transmission:        m.transmission ?? 0.92,
    ior:                 m.ior ?? 1.52,
    thickness:           (m.thickness ?? 8) * 0.5,
    roughness:           m.roughness ?? 0.0,
    metalness:           m.metalness ?? 0.0,
    clearcoat:           m.clearcoat ?? 1.0,
    clearcoatRoughness:  m.clearcoatRoughness ?? 0.03,
    envMapIntensity:     m.envMapIntensity ?? 0.5,
    side:                THREE.DoubleSide,
    depthWrite:          false,
  }});
  if (m.attenuationColor) {{
    mat.attenuationColor = new THREE.Color(m.attenuationColor);
    mat.attenuationDistance = m.attenuationDistance ?? 150;
  }}
  return mat;
}}

function addGlass(vidro) {{
  const geom = new THREE.BoxGeometry(vidro.largura, vidro.altura, vidro.espessura);
  const mat  = makeGlassMaterial(vidro.material);
  const mesh = new THREE.Mesh(geom, mat);
  mesh.castShadow = true;
  mesh.receiveShadow = false;  // vidro não recebe sombra pra manter translucidez

  if (!vidro.animacao) {{
    mesh.position.set(vidro.posicao.x, vidro.posicao.y, vidro.posicao.z);
    threeScene.add(mesh);
    return {{mesh, type:"static"}};
  }}

  const anim = vidro.animacao;

  if (anim.tipo === "pivotante") {{
    const pivo = anim.ponto_pivo || {{x: vidro.posicao.x - vidro.largura/2, y:0, z:0}};
    const grp = new THREE.Group();
    grp.position.set(pivo.x, vidro.posicao.y, 0);
    mesh.position.set(vidro.largura/2, 0, 0);
    grp.add(mesh);
    threeScene.add(grp);
    const entry = {{type:"pivotante", group:grp, mesh, current:0, target:0, openVal:(anim.angulo_max||90)*Math.PI/180}};
    animatables.push(entry);
    return entry;

  }} else if (anim.tipo === "deslizante") {{
    mesh.position.set(vidro.posicao.x, vidro.posicao.y, vidro.posicao.z);
    threeScene.add(mesh);
    const entry = {{type:"deslizante", mesh, current:0, target:0, originX:vidro.posicao.x, openVal:anim.distancia_max||vidro.largura}};
    animatables.push(entry);
    return entry;

  }} else if (anim.tipo === "basculante") {{
    const grp = new THREE.Group();
    grp.position.set(vidro.posicao.x, vidro.posicao.y + vidro.altura/2, 0);
    mesh.position.set(0, -vidro.altura/2, 0);
    grp.add(mesh);
    threeScene.add(grp);
    const entry = {{type:"basculante", group:grp, mesh, current:0, target:0, openVal:-(anim.angulo_max||45)*Math.PI/180}};
    animatables.push(entry);
    return entry;
  }}

  mesh.position.set(vidro.posicao.x, vidro.posicao.y, vidro.posicao.z);
  threeScene.add(mesh);
  return {{mesh, type:"static"}};
}}

// ── Ferragem PBR — MeshPhysicalMaterial para cromados ────────────────────
function createHardware(f) {{
  const g = f.geometria;
  const m = f.material;
  let geom;
  if (g.tipo === "cylinder") {{
    geom = new THREE.CylinderGeometry(g.raio, g.raio, g.altura, 20);
  }} else {{
    geom = new THREE.BoxGeometry(g.largura, g.altura, g.profundidade);
  }}

  // Se tem clearcoat (cromados), usa MeshPhysicalMaterial
  const mat = (m.clearcoat && m.clearcoat > 0)
    ? new THREE.MeshPhysicalMaterial({{
        color:              new THREE.Color(m.cor),
        roughness:          m.roughness,
        metalness:          m.metalness,
        clearcoat:          m.clearcoat,
        clearcoatRoughness: m.clearcoatRoughness ?? 0.1,
        envMapIntensity:    m.envMapIntensity ?? 1.5,
      }})
    : new THREE.MeshStandardMaterial({{
        color:           new THREE.Color(m.cor),
        roughness:       m.roughness,
        metalness:       m.metalness,
        envMapIntensity: m.envMapIntensity ?? 0.5,
      }});

  const mesh = new THREE.Mesh(geom, mat);
  mesh.position.set(f.posicao.x, f.posicao.y, f.posicao.z);
  mesh.castShadow = true;
  mesh.receiveShadow = true;
  return mesh;
}}

// ── Parede / Vão ──────────────────────────────────────────────────────────
function createWall(vao) {{
  const wallMat = new THREE.MeshStandardMaterial({{
    color:    new THREE.Color(vao.material.cor || "#E8E0D8"),
    roughness: vao.material.roughness ?? 0.9,
    metalness: 0.0,
    envMapIntensity: 0.05,
  }});
  const d        = vao.profundidade || 150;
  const wallThick = 240;
  const wallH     = vao.altura + 600;
  const halfVW    = vao.largura / 2;

  function box(w, h, x, y) {{
    const m = new THREE.Mesh(new THREE.BoxGeometry(w, h, d), wallMat);
    m.position.set(x, y, -d/2);
    m.receiveShadow = true;
    return m;
  }}

  const sillH = 25;
  const grp = new THREE.Group();
  grp.add(box(wallThick, wallH, -(halfVW + wallThick/2), wallH/2));
  grp.add(box(wallThick, wallH,  (halfVW + wallThick/2), wallH/2));
  const lintelH = Math.max(80, wallH - vao.altura);
  grp.add(box(vao.largura + wallThick*2, lintelH, 0, vao.altura + lintelH/2));
  grp.add(box(vao.largura, sillH, 0, -sillH/2));
  return grp;
}}

// ── Loop de animação ──────────────────────────────────────────────────────
function lerp(a, b, t) {{ return a + (b-a)*t; }}

function animate() {{
  requestAnimationFrame(animate);
  controls.update();
  const SPEED = 0.045;
  for (const a of animatables) {{
    if (Math.abs(a.current - a.target) < 0.0001) continue;
    a.current = lerp(a.current, a.target, SPEED);
    if (a.type === "pivotante")   a.group.rotation.y = a.current;
    else if (a.type === "deslizante") a.mesh.position.x = a.originX + a.current;
    else if (a.type === "basculante") a.group.rotation.x = a.current;
  }}
  renderer.render(threeScene, camera);
}}

// ── Controles UI ──────────────────────────────────────────────────────────
window.toggleDoor = function() {{
  isDoorOpen = !isDoorOpen;
  const btn = document.getElementById("btn-door");
  animatables.forEach(a => {{ a.target = isDoorOpen ? a.openVal : 0; }});
  btn.textContent = isDoorOpen ? "🚪 Fechar" : "🚪 Abrir porta";
  btn.classList.toggle("active", isDoorOpen);
}};

window.setGlassColor = function(key, el) {{
  const c = VIDRO_MATS[key] || VIDRO_MATS.default;
  glassMeshes.forEach(m => {{
    if (!m || !m.material) return;
    m.material.color.set(c.cor);
    m.material.opacity = c.op;
    m.material.transmission = c.tr ?? 0.9;
    m.material.metalness = c.metal ?? 0;
    if (m.material.attenuationColor) m.material.attenuationColor.set(c.att || "#FFFFFF");
    if (m.material.attenuationDistance !== undefined) m.material.attenuationDistance = c.attD ?? 100;
    m.material.needsUpdate = true;
  }});
  document.querySelectorAll(".color-swatch").forEach(s => s.classList.remove("active"));
  if (el) el.classList.add("active");
}};

window.resetCamera = function() {{
  const cam = SCENE.ambiente.camera_inicial;
  camera.position.set(cam.posicao.x, cam.posicao.y, cam.posicao.z);
  controls.target.set(cam.target.x, cam.target.y, cam.target.z);
  controls.update();
}};

window.screenshot = function() {{
  renderer.render(threeScene, camera);
  const tip = (SCENE.tipologia || "render").replace(/[^a-z0-9]/gi,"_");
  renderer.domElement.toBlob(blob => {{
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url; a.download = `vdx_${{tip}}.png`;
    document.body.appendChild(a); a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  }}, "image/png");
}};
</script>
</body>
</html>"""

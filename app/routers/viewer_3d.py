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
    if any(k in t for k in ("duas_folhas", "2_folhas", "2folhas", "box")):
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
    if any(k in t for k in ("quatro_folhas", "4_folhas", "4folhas")):
        w = largura / 4
        return [PecaInput(nome=f"Folha {i+1}", largura_mm=w, altura_mm=altura) for i in range(4)]
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
  <button id="toggleBtn" class="btn btn-primary" onclick="toggleDoor()">&#x1F6AA; Abrir porta</button>
  <div id="angleWrap" style="margin-top:6px">
    <div style="display:flex;justify-content:space-between;align-items:center">
      <span class="label" style="margin:0">&#194;ngulo</span>
      <span id="angleLabel" style="font-size:11px;color:#333;font-weight:600">0&deg;</span>
    </div>
    <input type="range" id="angleSlider" min="0" max="90" value="0" step="1"
      style="width:100%;margin-top:4px;accent-color:#1a5276">
  </div>

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

<script src="https://cdn.babylonjs.com/babylon.js"></script>
<script>
const SCENE = {scene_json};

const VIDRO_MATS = {{
  incolor: {{cor:"#FFFFFF", alpha:0.12, ior:1.52}},
  verde:   {{cor:"#4A7A5B", alpha:0.20, ior:1.52}},
  fume:    {{cor:"#3A3A3A", alpha:0.40, ior:1.52}},
  bronze:  {{cor:"#6B5B3A", alpha:0.30, ior:1.52}},
  espelho: {{cor:"#E0E0E0", alpha:0.05, ior:1.52, metal:0.95, refracao:false}},
  default: {{cor:"#B8D4E3", alpha:0.10, ior:1.52}},
}};

let engine, bScene, camera;
const glassMeshes = [];
const animatables = [];
let isDoorOpen = false;

window.addEventListener("load", () => {{
  const canvas = document.getElementById("c");

  engine = new BABYLON.Engine(canvas, true, {{
    preserveDrawingBuffer: true, stencil: true, antialias: true,
  }});
  bScene = new BABYLON.Scene(engine);
  bScene.useRightHandedSystem = true;
  bScene.clearColor = new BABYLON.Color4(0.961, 0.949, 0.933, 1);

  const cam = SCENE.ambiente.camera_inicial;
  const target = new BABYLON.Vector3(cam.target.x, cam.target.y, cam.target.z);
  camera = new BABYLON.ArcRotateCamera("cam", 0, Math.PI/2, 3, target, bScene);
  camera.setPosition(new BABYLON.Vector3(cam.posicao.x, cam.posicao.y, cam.posicao.z));
  camera.lowerRadiusLimit = 200;
  camera.upperRadiusLimit = 15000;
  camera.wheelPrecision = 0.05;
  camera.panningSensibility = 5;
  camera.minZ = 1;
  camera.maxZ = 50000;
  camera.attachControl(canvas, true);

  const hemi = new BABYLON.HemisphericLight("hemi", new BABYLON.Vector3(0,1,0), bScene);
  hemi.intensity = 0.6;
  hemi.groundColor = new BABYLON.Color3(0.4, 0.4, 0.4);

  const key = new BABYLON.DirectionalLight("key", new BABYLON.Vector3(-1,-2,-1.5).normalize(), bScene);
  key.intensity = 2.5;
  key.diffuse = new BABYLON.Color3(1, 0.97, 0.9);

  const fill = new BABYLON.DirectionalLight("fill", new BABYLON.Vector3(1.5,-0.5,0.5).normalize(), bScene);
  fill.intensity = 1.0;
  fill.diffuse = new BABYLON.Color3(0.8, 0.88, 1.0);

  const rim = new BABYLON.DirectionalLight("rim", new BABYLON.Vector3(0,-1,2).normalize(), bScene);
  rim.intensity = 0.6;
  rim.diffuse = new BABYLON.Color3(1, 0.9, 0.7);

  (function() {{
    const sz = 512, grid = 64;
    const cv = document.createElement("canvas");
    cv.width = sz; cv.height = sz;
    const ctx = cv.getContext("2d");
    ctx.fillStyle = "#F5F0EB";
    ctx.fillRect(0, 0, sz, sz);
    ctx.strokeStyle = "rgba(180,160,140,0.25)";
    ctx.lineWidth = 1;
    for (let i = 0; i <= sz; i += grid) {{
      ctx.beginPath(); ctx.moveTo(i,0); ctx.lineTo(i,sz); ctx.stroke();
      ctx.beginPath(); ctx.moveTo(0,i); ctx.lineTo(sz,i); ctx.stroke();
    }}
    const floorTex = new BABYLON.Texture(cv.toDataURL(), bScene);
    floorTex.uScale = 20; floorTex.vScale = 20;
    const floorMat = new BABYLON.StandardMaterial("floorMat", bScene);
    floorMat.diffuseTexture = floorTex;
    floorMat.specularColor = BABYLON.Color3.Black();
    const floor = BABYLON.MeshBuilder.CreateGround("floor", {{width:12000, height:12000}}, bScene);
    floor.position.y = -1;
    floor.material = floorMat;
  }})();

  loadScene(SCENE);

  const LERP = 0.045;
  bScene.registerBeforeRender(() => {{
    for (const a of animatables) {{
      if (Math.abs(a.current - a.target) < 0.0001) continue;
      a.current += (a.target - a.current) * LERP;
      if (a.type === "pivotante")       a.pivotNode.rotation.y = a.current;
      else if (a.type === "deslizante") a.mesh.position.x = a.originX + a.current;
      else if (a.type === "basculante") a.pivotNode.rotation.x = a.current;
    }}
  }});

  engine.runRenderLoop(() => bScene.render());
  window.addEventListener("resize", () => engine.resize());

  document.getElementById("loading").style.display = "none";

  if (animatables.length === 0) {{
    document.getElementById("toggleBtn").style.display = "none";
    document.getElementById("angleWrap").style.display = "none";
  }} else {{
    const slider = document.getElementById("angleSlider");
    const label  = document.getElementById("angleLabel");
    slider.addEventListener("input", () => {{
      const deg = Number(slider.value);
      label.textContent = deg + "°";
      const frac = deg / 90;
      animatables.forEach(a => {{ a.target = a.openVal * frac; }});
      isDoorOpen = deg > 0;
      const btn = document.getElementById("toggleBtn");
      btn.textContent = isDoorOpen ? "🚧 Fechar" : "🚧 Abrir porta";
      btn.classList.toggle("active", isDoorOpen);
    }});
  }}
}});

function loadScene(s) {{
  if (s.vao && s.vao.presente !== false) createWall(s.vao);
  const pivotGroupMap = {{}};
  s.vidros.forEach(v => {{
    const result = addGlass(v);
    if (result) {{
      glassMeshes.push(result.mesh);
      if (result.pivotNode) pivotGroupMap[v.nome] = {{pivotNode: result.pivotNode, pivoX: result.pivoX || 0}};
    }}
  }});
  s.ferragens.forEach(f => {{
    const hw = createHardware(f);
    if (!hw) return;
    const pm = pivotGroupMap[f.peca_nome];
    if (pm) {{
      hw.position.x = f.posicao.x - pm.pivoX;
      hw.position.y = f.posicao.y;
      hw.position.z = f.posicao.z;
      hw.parent = pm.pivotNode;
    }}
  }});
}}

function makeGlassMat(m, id) {{
  const mat = new BABYLON.PBRMaterial("glass_" + id, bScene);
  mat.albedoColor = BABYLON.Color3.FromHexString(m.cor);
  mat.metallic = m.metalness || 0;
  mat.roughness = m.roughness || 0;
  mat.alpha = m.opacidade || 0.10;
  mat.needDepthPrePass = true;
  mat.environmentIntensity = 0.3;
  mat.clearCoat.isEnabled = true;
  mat.clearCoat.intensity = (m.clearcoat > 0) ? m.clearcoat : 1.0;
  mat.clearCoat.roughness = m.clearcoatRoughness || 0.03;
}}

function addGlass(vidro) {{
  const glassMesh = BABYLON.MeshBuilder.CreateBox("vidro_" + vidro.id, {{
    width: vidro.largura, height: vidro.altura, depth: vidro.espessura,
  }}, bScene);
  glassMesh.material = makeGlassMat(vidro.material, vidro.id);

  if (!vidro.animacao || vidro.animacao.tipo === "fixo") {{
    glassMesh.position.set(vidro.posicao.x, vidro.posicao.y, vidro.posicao.z);
    return {{mesh: glassMesh}};
  }}

  const anim = vidro.animacao;

  if (anim.tipo === "pivotante") {{
    const pivo = anim.ponto_pivo || {{x: vidro.posicao.x - vidro.largura/2, y:0, z:0}};
    const pivotNode = new BABYLON.TransformNode("pivot_" + vidro.nome, bScene);
    pivotNode.position.set(pivo.x, pivo.y, pivo.z);
    glassMesh.position.set(vidro.posicao.x - pivo.x, vidro.posicao.y, vidro.posicao.z);
    glassMesh.parent = pivotNode;
    const openVal = (anim.angulo_max || 90) * Math.PI / 180;
    animatables.push({{type:"pivotante", pivotNode, mesh:glassMesh, pivoX:pivo.x, current:0, target:0, openVal}});
    return {{mesh:glassMesh, pivotNode, pivoX:pivo.x}};
  }}

  if (anim.tipo === "deslizante") {{
    glassMesh.position.set(vidro.posicao.x, vidro.posicao.y, vidro.posicao.z);
    const dir = vidro.posicao.x < 0 ? -1 : 1;
    const openVal = (anim.distancia_max || vidro.largura) * dir;
    animatables.push({{type:"deslizante", mesh:glassMesh, current:0, target:0, originX:vidro.posicao.x, openVal}});
    return {{mesh:glassMesh}};
  }}

  if (anim.tipo === "basculante") {{
    const pivotNode = new BABYLON.TransformNode("pivot_" + vidro.nome, bScene);
    pivotNode.position.set(vidro.posicao.x, vidro.posicao.y + vidro.altura/2, 0);
    glassMesh.position.set(0, -vidro.altura/2, 0);
    glassMesh.parent = pivotNode;
    const openVal = -(anim.angulo_max || 45) * Math.PI / 180;
    animatables.push({{type:"basculante", pivotNode, mesh:glassMesh, current:0, target:0, openVal}});
    return {{mesh:glassMesh, pivotNode, pivoX:0}};
  }}

  glassMesh.position.set(vidro.posicao.x, vidro.posicao.y, vidro.posicao.z);
  return {{mesh:glassMesh}};
}}

function createHinge(f) {{
  const hingeRoot = new BABYLON.TransformNode("hinge_" + f.id, bScene);
  const g = f.geometria; const m = f.material;
  const w = g.largura || 30, h = g.altura || 50, d = g.profundidade || 8;

  const bodyMat = new BABYLON.PBRMaterial("hinge_body_mat_" + f.id, bScene);
  bodyMat.albedoColor = BABYLON.Color3.FromHexString(m.cor);
  bodyMat.metallic = m.metalness; bodyMat.roughness = m.roughness;
  if ((m.clearcoat||0) > 0) {{ bodyMat.clearCoat.isEnabled = true; bodyMat.clearCoat.intensity = m.clearcoat; }}
  bodyMat.environmentIntensity = m.envMapIntensity || 1.5;
  const body = BABYLON.MeshBuilder.CreateBox("hinge_body_" + f.id, {{width:w,height:h,depth:d}}, bScene);
  body.material = bodyMat; body.parent = hingeRoot;

  const pinMat = new BABYLON.PBRMaterial("hinge_pin_mat_" + f.id, bScene);
  pinMat.albedoColor = new BABYLON.Color3(0.831, 0.686, 0.216);
  pinMat.metallic = 1.0; pinMat.roughness = 0.1;
  pinMat.clearCoat.isEnabled = true; pinMat.clearCoat.intensity = 0.5;
  const pin = BABYLON.MeshBuilder.CreateCylinder("hinge_pin_" + f.id, {{diameter:5,height:h+4,tessellation:16}}, bScene);
  pin.material = pinMat; pin.parent = hingeRoot;

  const screwMat = new BABYLON.PBRMaterial("hinge_screw_mat_" + f.id, bScene);
  screwMat.albedoColor = new BABYLON.Color3(0.667, 0.667, 0.667);
  screwMat.metallic = 1.0; screwMat.roughness = 0.2;
  screwMat.clearCoat.isEnabled = true; screwMat.clearCoat.intensity = 0.3;
  [[-w*0.28,h*0.3],[w*0.28,h*0.3],[-w*0.28,-h*0.3],[w*0.28,-h*0.3]].forEach(([sx,sy],i) => {{
    const sc = BABYLON.MeshBuilder.CreateCylinder("hinge_sc_" + f.id + "_" + i, {{diameter:3.6,height:d+1,tessellation:8}}, bScene);
    sc.rotation.x = Math.PI/2; sc.position.set(sx,sy,0);
    sc.material = screwMat; sc.parent = hingeRoot;
  }});

  hingeRoot.position.set(f.posicao.x, f.posicao.y, f.posicao.z);
  return hingeRoot;
}}

function createHardware(f) {{
  if (f.tipo === "dobradica") return createHinge(f);
  const g = f.geometria; const m = f.material;
  const hwMat = new BABYLON.PBRMaterial("ferr_mat_" + f.id, bScene);
  hwMat.albedoColor = BABYLON.Color3.FromHexString(m.cor);
  hwMat.metallic = m.metalness; hwMat.roughness = m.roughness;
  if ((m.clearcoat||0) > 0) {{
    hwMat.clearCoat.isEnabled = true; hwMat.clearCoat.intensity = m.clearcoat;
    hwMat.clearCoat.roughness = m.clearcoatRoughness || 0.1;
  }}
  hwMat.environmentIntensity = m.envMapIntensity || 1.5;
  let mesh;
  if (g.tipo === "cylinder") {{
    mesh = BABYLON.MeshBuilder.CreateCylinder("ferr_" + f.id, {{diameter:(g.raio||5)*2,height:g.altura||30,tessellation:20}}, bScene);
  }} else {{
    mesh = BABYLON.MeshBuilder.CreateBox("ferr_" + f.id, {{width:g.largura||10,height:g.altura||10,depth:g.profundidade||10}}, bScene);
  }}
  mesh.material = hwMat;
  mesh.position.set(f.posicao.x, f.posicao.y, f.posicao.z);
  return mesh;
}}

function createWall(vao) {{
  const wallMat = new BABYLON.StandardMaterial("wallMat", bScene);
  wallMat.diffuseColor = BABYLON.Color3.FromHexString(vao.material.cor || "#E8E0D8");
  wallMat.specularColor = new BABYLON.Color3(0.03, 0.03, 0.03);
  wallMat.backFaceCulling = false;
  const d = vao.profundidade || 150;
  const wallThick = 240, wallH = vao.altura + 600;
  const halfVW = vao.largura / 2;
  const lintelH = Math.max(80, wallH - vao.altura), sillH = 25;
  function box(w, h, x, y) {{
    const mesh = BABYLON.MeshBuilder.CreateBox("wb_" + x + "_" + y, {{width:w,height:h,depth:d}}, bScene);
    mesh.position.set(x, y, -d/2); mesh.material = wallMat;
  }}
  box(wallThick, wallH, -(halfVW + wallThick/2), wallH/2);
  box(wallThick, wallH,  (halfVW + wallThick/2), wallH/2);
  box(vao.largura + wallThick*2, lintelH, 0, vao.altura + lintelH/2);
  box(vao.largura, sillH, 0, -sillH/2);
}}

window.toggleDoor = function() {{
  isDoorOpen = !isDoorOpen;
  const btn = document.getElementById("toggleBtn");
  animatables.forEach(a => {{ a.target = isDoorOpen ? a.openVal : 0; }});
  btn.textContent = isDoorOpen ? "🚧 Fechar" : "🚧 Abrir porta";
  btn.classList.toggle("active", isDoorOpen);
  const slider = document.getElementById("angleSlider");
  const label  = document.getElementById("angleLabel");
  if (slider) {{ slider.value = isDoorOpen ? 90 : 0; label.textContent = (isDoorOpen?90:0)+"°"; }}
}};

window.setGlassColor = function(key, el) {{
  const c = VIDRO_MATS[key] || VIDRO_MATS.default;
  const hexStr = c.cor.replace("#","");
  const r = parseInt(hexStr.slice(0,2),16)/255;
  const g = parseInt(hexStr.slice(2,4),16)/255;
  const b = parseInt(hexStr.slice(4,6),16)/255;
  glassMeshes.forEach(mesh => {{
    if (!mesh || !mesh.material) return;
    mesh.material.albedoColor.r = r;
    mesh.material.albedoColor.g = g;
    mesh.material.albedoColor.b = b;
    mesh.material.alpha = c.alpha || 0.1;
    mesh.material.metallic = c.metal || 0;
  }});
  document.querySelectorAll(".color-swatch").forEach(s => s.classList.remove("active"));
  if (el) el.classList.add("active");
}};

window.resetCamera = function() {{
  const cam = SCENE.ambiente.camera_inicial;
  camera.setPosition(new BABYLON.Vector3(cam.posicao.x, cam.posicao.y, cam.posicao.z));
}};

window.screenshot = function() {{
  bScene.render();
  const cnv = engine.getRenderingCanvas();
  const tip = (SCENE.tipologia || "render").replace(/[^a-z0-9]/gi,"_");
  cnv.toBlob(blob => {{
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url; a.download = "vdx_" + tip + ".png";
    document.body.appendChild(a); a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  }}, "image/png");
}};
</script>
</body>
</html>"""


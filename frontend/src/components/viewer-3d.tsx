'use client'

import { useEffect, useRef, useCallback, useState } from 'react'
import type { Engine, Scene, TransformNode, PBRMaterial, Vector3 } from '@babylonjs/core'
import type { SceneJSON, VidroScene } from '@/lib/types'

const GLASS_COLORS: Record<string, string> = {
  incolor: '#B8D4E3',
  bronze: '#8B6914',
  fumê: '#4A4A4A',
  'verde-claro': '#6AAB7A',
  azul: '#3A7BC8',
  espelhado: '#D0D8E0',
}

const HARDWARE_FINISHES: Record<string, { color: string; roughness: number; metalness: number }> = {
  cromado:   { color: '#C8D0D8', roughness: 0.1, metalness: 0.95 },
  preto:     { color: '#1A1A1A', roughness: 0.3, metalness: 0.8 },
  dourado:   { color: '#C9A84C', roughness: 0.15, metalness: 0.9 },
  inox:      { color: '#A8AEB4', roughness: 0.2, metalness: 0.9 },
  escovado:  { color: '#9EA4AA', roughness: 0.4, metalness: 0.85 },
}

interface Viewer3DProps {
  scene: SceneJSON | null
  className?: string
  onScreenshot?: (blob: Blob) => void
  onReady?: () => void
  corVidro?: string
  acabamento?: string
}

interface AnimState {
  vidroId: string
  pivotNode: TransformNode
  animacao: NonNullable<VidroScene['animacao']>
  currentAngle: number
  targetAngle: number
  currentPos: Vector3
  targetPos: Vector3
  originalPos: Vector3
}

function hexToRgb(hex: string): [number, number, number] {
  const r = parseInt(hex.slice(1, 3), 16) / 255
  const g = parseInt(hex.slice(3, 5), 16) / 255
  const b = parseInt(hex.slice(5, 7), 16) / 255
  return [r, g, b]
}

export default function Viewer3D({ scene, className = '', onScreenshot, onReady, corVidro, acabamento }: Viewer3DProps) {
  const containerRef = useRef<HTMLDivElement>(null)
  const engineRef = useRef<Engine | null>(null)
  const babylonSceneRef = useRef<Scene | null>(null)
  const canvasElemRef = useRef<HTMLCanvasElement | null>(null)
  const animStatesRef = useRef<AnimState[]>([])
  const glassMatsRef = useRef<PBRMaterial[]>([])
  const hardwareMatsRef = useRef<PBRMaterial[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [isAnimating, setIsAnimating] = useState(false)
  const [sliderAngle, setSliderAngle] = useState(0)
  const [maxAngle, setMaxAngle] = useState(90)
  const [animType, setAnimType] = useState<'rotacional' | 'deslizante' | null>(null)
  const mountedRef = useRef(false)

  const takeScreenshot = useCallback(() => {
    if (!canvasElemRef.current || !onScreenshot) return
    canvasElemRef.current.toBlob((blob) => {
      if (blob) onScreenshot(blob)
    }, 'image/png')
  }, [onScreenshot])

  useEffect(() => {
    if (containerRef.current) {
      (containerRef.current as HTMLDivElement & { takeScreenshot?: () => void }).takeScreenshot = takeScreenshot
    }
  }, [takeScreenshot])

  const applyAngle = useCallback((angleDeg: number) => {
    animStatesRef.current.forEach((state) => {
      if (state.animacao.tipo === 'pivotante') {
        state.targetAngle = (angleDeg * Math.PI) / 180
      } else if (state.animacao.tipo === 'basculante') {
        state.targetAngle = (angleDeg * Math.PI) / 180
      } else if (state.animacao.tipo === 'deslizante') {
        const pct = angleDeg / 90
        const delta = (pct * (state.animacao.distancia_max ?? 500)) / 1000
        const dir = state.originalPos.x < 0 ? -1 : 1
        state.targetPos.set(
          state.originalPos.x + dir * delta,
          state.originalPos.y,
          state.originalPos.z,
        )
      }
    })
  }, [])

  const handleSliderChange = useCallback((val: number) => {
    setSliderAngle(val)
    setIsAnimating(val > 0)
    applyAngle(val)
  }, [applyAngle])

  const toggleAnimation = useCallback(() => {
    setIsAnimating((prev) => {
      const next = !prev
      const target = next ? maxAngle : 0
      setSliderAngle(target)
      applyAngle(target)
      return next
    })
  }, [maxAngle, applyAngle])

  useEffect(() => {
    if (!containerRef.current || !scene) return

    const sceneData: SceneJSON = scene
    mountedRef.current = true
    setIsLoading(true)
    setSliderAngle(0)
    setIsAnimating(false)

    async function init() {
      const {
        Engine, Scene, ArcRotateCamera, Vector3, Color3, Color4,
        HemisphericLight, DirectionalLight, MeshBuilder,
        PBRMaterial, StandardMaterial, TransformNode, Texture,
      } = await import('@babylonjs/core')

      if (!mountedRef.current || !containerRef.current) return

      // Cleanup previous instance
      if (engineRef.current) {
        engineRef.current.stopRenderLoop()
        babylonSceneRef.current?.dispose()
        babylonSceneRef.current = null
        engineRef.current.dispose()
        engineRef.current = null
      }
      if (canvasElemRef.current) {
        canvasElemRef.current.remove()
        canvasElemRef.current = null
      }

      const container = containerRef.current
      const canvas = document.createElement('canvas')
      canvas.style.cssText = 'position:absolute;top:0;left:0;width:100%;height:100%;display:block;'
      container.appendChild(canvas)
      canvasElemRef.current = canvas

      const S = 0.001  // mm → meters

      // ── Engine ─────────────────────────────────────────────────────────────
      const engine = new Engine(canvas, true, {
        preserveDrawingBuffer: true,
        stencil: true,
        antialias: sceneData.ambiente.antialias ?? true,
      })
      engineRef.current = engine

      // ── Scene ──────────────────────────────────────────────────────────────
      const bScene = new Scene(engine)
      bScene.useRightHandedSystem = true
      bScene.clearColor = new Color4(0.839, 0.816, 0.784, 1)  // #D6D0C8
      babylonSceneRef.current = bScene

      // ── Camera ─────────────────────────────────────────────────────────────
      const camData = sceneData.ambiente.camera_inicial
      const targetV = new Vector3(camData.target.x * S, camData.target.y * S, camData.target.z * S)
      const posV = new Vector3(camData.posicao.x * S, camData.posicao.y * S, camData.posicao.z * S)
      const camera = new ArcRotateCamera('cam', 0, Math.PI / 2, 3, targetV, bScene)
      camera.setPosition(posV)
      camera.lowerRadiusLimit = 0.3
      camera.upperRadiusLimit = 20
      camera.wheelPrecision = 100
      camera.panningSensibility = 500
      camera.attachControl(canvas, true)

      // ── Lights ─────────────────────────────────────────────────────────────
      const hemi = new HemisphericLight('hemi', new Vector3(0, 1, 0), bScene)
      hemi.intensity = 0.7
      hemi.groundColor = new Color3(0.4, 0.4, 0.4)

      const key = new DirectionalLight('key', new Vector3(-1, -2, -1.5).normalize(), bScene)
      key.intensity = 2.5
      key.diffuse = new Color3(1, 0.97, 0.9)

      const fill = new DirectionalLight('fill', new Vector3(1.5, -0.5, 0.5).normalize(), bScene)
      fill.intensity = 1.0
      fill.diffuse = new Color3(0.8, 0.88, 1.0)

      const rim = new DirectionalLight('rim', new Vector3(0, -1, 2).normalize(), bScene)
      rim.intensity = 0.6
      rim.diffuse = new Color3(1, 0.9, 0.7)

      // ── Floor ──────────────────────────────────────────────────────────────
      {
        const pisoData = sceneData.ambiente.piso
        const sz = 512, grid = 64
        const cv = document.createElement('canvas')
        cv.width = sz; cv.height = sz
        const ctx = cv.getContext('2d')!
        ctx.fillStyle = pisoData.cor
        ctx.fillRect(0, 0, sz, sz)
        ctx.strokeStyle = 'rgba(180,160,140,0.22)'
        ctx.lineWidth = 1
        for (let i = 0; i <= sz; i += grid) {
          ctx.beginPath(); ctx.moveTo(i, 0); ctx.lineTo(i, sz); ctx.stroke()
          ctx.beginPath(); ctx.moveTo(0, i); ctx.lineTo(sz, i); ctx.stroke()
        }
        const floorTex = new Texture(cv.toDataURL(), bScene)
        floorTex.uScale = 20; floorTex.vScale = 20
        const floorMat = new StandardMaterial('floorMat', bScene)
        floorMat.diffuseTexture = floorTex
        floorMat.specularColor = new Color3(0, 0, 0)
        const floor = MeshBuilder.CreateGround('floor', { width: 20, height: 20 }, bScene)
        floor.material = floorMat
      }

      // ── Walls / Vão ────────────────────────────────────────────────────────
      if (sceneData.vao?.presente !== false) {
        const vaoData = sceneData.vao
        const vW = vaoData.largura * S
        const vH = vaoData.altura * S
        const vD = vaoData.profundidade * S
        const sideThick = 0.3

        const wallMat = new StandardMaterial('wallMat', bScene)
        wallMat.diffuseColor = Color3.FromHexString(vaoData.material.cor)
        wallMat.specularColor = new Color3(0.03, 0.03, 0.03)
        wallMat.backFaceCulling = false

        const backWall = MeshBuilder.CreateBox('backWall', { width: vW + 0.6, height: vH + 0.3, depth: 0.01 }, bScene)
        backWall.position.set(0, vH / 2, -vD / 2)
        backWall.material = wallMat

        const leftPillar = MeshBuilder.CreateBox('leftPillar', { width: sideThick, height: vH, depth: vD }, bScene)
        leftPillar.position.set(-vW / 2 - sideThick / 2, vH / 2, 0)
        leftPillar.material = wallMat

        const rightPillar = MeshBuilder.CreateBox('rightPillar', { width: sideThick, height: vH, depth: vD }, bScene)
        rightPillar.position.set(vW / 2 + sideThick / 2, vH / 2, 0)
        rightPillar.material = wallMat

        const topBeam = MeshBuilder.CreateBox('topBeam', { width: vW + sideThick * 2, height: 0.2, depth: vD }, bScene)
        topBeam.position.set(0, vH + 0.1, 0)
        topBeam.material = wallMat
      }

      // ── Vidros ─────────────────────────────────────────────────────────────
      animStatesRef.current = []
      glassMatsRef.current = []
      hardwareMatsRef.current = []
      const pivotNodeMap = new Map<string, { node: TransformNode; pivoX: number }>()

      for (const vidro of sceneData.vidros) {
        const mat = vidro.material
        const glassMat = new PBRMaterial(`glass_${vidro.id}`, bScene)
        glassMat.albedoColor = Color3.FromHexString(mat.cor)
        glassMat.metallic = mat.metalness
        glassMat.roughness = mat.roughness
        glassMat.alpha = mat.opacidade
        glassMat.needDepthPrePass = true
        glassMat.subSurface.isRefractionEnabled = true
        glassMat.subSurface.indexOfRefraction = mat.ior ?? 1.52
        glassMat.subSurface.linkRefractionWithTransparency = true
        glassMat.environmentIntensity = mat.envMapIntensity ?? 1.2
        if (mat.clearcoat > 0) {
          glassMat.clearCoat.isEnabled = true
          glassMat.clearCoat.intensity = mat.clearcoat
          glassMat.clearCoat.roughness = mat.clearcoatRoughness ?? 0.03
        }
        glassMatsRef.current.push(glassMat)

        const glassMesh = MeshBuilder.CreateBox(`vidro_${vidro.id}`, {
          width: vidro.largura * S,
          height: vidro.altura * S,
          depth: vidro.espessura * S,
        }, bScene)
        glassMesh.material = glassMat

        const pivotNode = new TransformNode(`pivot_${vidro.nome}`, bScene)
        const anim = vidro.animacao

        if (anim && anim.tipo !== 'fixo' && anim.ponto_pivo) {
          const pivo = anim.ponto_pivo
          pivotNode.position.set(pivo.x * S, pivo.y * S, pivo.z * S)
          glassMesh.position.set(
            (-pivo.x + vidro.posicao.x) * S,
            vidro.posicao.y * S,
            vidro.posicao.z * S,
          )
        } else {
          pivotNode.position.set(vidro.posicao.x * S, vidro.posicao.y * S, vidro.posicao.z * S)
          glassMesh.position.set(0, 0, 0)
        }
        glassMesh.parent = pivotNode

        if (anim?.ponto_pivo) {
          pivotNodeMap.set(vidro.nome, { node: pivotNode, pivoX: anim.ponto_pivo.x * S })
        }

        if (anim && anim.tipo !== 'fixo') {
          animStatesRef.current.push({
            vidroId: vidro.id,
            pivotNode,
            animacao: anim,
            currentAngle: 0,
            targetAngle: 0,
            currentPos: pivotNode.position.clone(),
            targetPos: pivotNode.position.clone(),
            originalPos: pivotNode.position.clone(),
          })
        }
      }

      const firstAnim = animStatesRef.current[0]?.animacao
      if (firstAnim) {
        const isDeslizante = firstAnim.tipo === 'deslizante'
        setAnimType(isDeslizante ? 'deslizante' : 'rotacional')
        setMaxAngle(isDeslizante ? 90 : (firstAnim.angulo_max ?? 90))
      }

      // ── Ferragens ──────────────────────────────────────────────────────────
      type FerragemMat = typeof sceneData.ferragens[0]['material']

      function makeHardwareMat(m: FerragemMat, name: string): PBRMaterial {
        const mat = new PBRMaterial(name, bScene)
        mat.albedoColor = Color3.FromHexString(m.cor)
        mat.metallic = m.metalness
        mat.roughness = m.roughness
        if ((m.clearcoat ?? 0) > 0) {
          mat.clearCoat.isEnabled = true
          mat.clearCoat.intensity = m.clearcoat ?? 0
          mat.clearCoat.roughness = m.clearcoatRoughness ?? 0.1
        }
        mat.environmentIntensity = m.envMapIntensity ?? 1.0
        return mat
      }

      function createHinge(f: typeof sceneData.ferragens[0]): TransformNode {
        const hingeRoot = new TransformNode(`hinge_${f.id}`, bScene)
        const g = f.geometria; const m = f.material
        const w = (g.largura ?? 30) * S
        const h = (g.altura ?? 50) * S
        const d = (g.profundidade ?? 8) * S

        const body = MeshBuilder.CreateBox(`hinge_body_${f.id}`, { width: w, height: h, depth: d }, bScene)
        body.material = makeHardwareMat(m, `hinge_body_mat_${f.id}`)
        body.parent = hingeRoot

        const pinMat = new PBRMaterial(`hinge_pin_mat_${f.id}`, bScene)
        pinMat.albedoColor = new Color3(0.831, 0.686, 0.216)  // #D4AF37 gold
        pinMat.metallic = 1.0; pinMat.roughness = 0.1
        pinMat.clearCoat.isEnabled = true; pinMat.clearCoat.intensity = 0.5
        const pin = MeshBuilder.CreateCylinder(`hinge_pin_${f.id}`, {
          diameter: 5 * S, height: h + 4 * S, tessellation: 16,
        }, bScene)
        pin.material = pinMat
        pin.parent = hingeRoot

        const screwMat = new PBRMaterial(`hinge_screw_mat_${f.id}`, bScene)
        screwMat.albedoColor = new Color3(0.667, 0.667, 0.667)
        screwMat.metallic = 1.0; screwMat.roughness = 0.2
        screwMat.clearCoat.isEnabled = true; screwMat.clearCoat.intensity = 0.3

        const offsets: [number, number][] = [
          [-w * 0.28, h * 0.3], [w * 0.28, h * 0.3],
          [-w * 0.28, -h * 0.3], [w * 0.28, -h * 0.3],
        ]
        offsets.forEach(([sx, sy], i) => {
          const sc = MeshBuilder.CreateCylinder(`hinge_screw_${f.id}_${i}`, {
            diameter: 3.6 * S, height: d + S, tessellation: 8,
          }, bScene)
          sc.rotation.x = Math.PI / 2
          sc.position.set(sx, sy, 0)
          sc.parent = hingeRoot
          sc.material = screwMat
        })
        return hingeRoot
      }

      for (const ferragem of sceneData.ferragens) {
        if (ferragem.tipo === 'dobradica') {
          const hingeNode = createHinge(ferragem)
          const pm = pivotNodeMap.get(ferragem.peca_nome)
          if (pm) {
            hingeNode.position.set(
              ferragem.posicao.x * S - pm.pivoX,
              ferragem.posicao.y * S,
              ferragem.posicao.z * S,
            )
            hingeNode.parent = pm.node
          } else {
            hingeNode.position.set(ferragem.posicao.x * S, ferragem.posicao.y * S, ferragem.posicao.z * S)
          }
          continue
        }

        const fMat = makeHardwareMat(ferragem.material, `ferr_mat_${ferragem.id}`)
        hardwareMatsRef.current.push(fMat)

        const geo = ferragem.geometria
        const mesh = geo.tipo === 'cylinder'
          ? MeshBuilder.CreateCylinder(`ferr_${ferragem.id}`, {
              diameter: (geo.raio ?? 5) * 2 * S,
              height: (geo.comprimento ?? geo.altura ?? 30) * S,
              tessellation: 16,
            }, bScene)
          : geo.tipo === 'sphere'
          ? MeshBuilder.CreateSphere(`ferr_${ferragem.id}`, {
              diameter: (geo.raio ?? 5) * 2 * S,
              segments: 16,
            }, bScene)
          : MeshBuilder.CreateBox(`ferr_${ferragem.id}`, {
              width: (geo.largura ?? 10) * S,
              height: (geo.altura ?? 10) * S,
              depth: (geo.profundidade ?? 10) * S,
            }, bScene)

        mesh.material = fMat
        mesh.rotation.set(ferragem.rotacao.x, ferragem.rotacao.y, ferragem.rotacao.z)

        const pm = pivotNodeMap.get(ferragem.peca_nome)
        if (pm) {
          mesh.position.set(
            ferragem.posicao.x * S - pm.pivoX,
            ferragem.posicao.y * S,
            ferragem.posicao.z * S,
          )
          mesh.parent = pm.node
        } else {
          mesh.position.set(ferragem.posicao.x * S, ferragem.posicao.y * S, ferragem.posicao.z * S)
        }
      }

      // ── Animation LERP ─────────────────────────────────────────────────────
      const LERP = 0.05
      bScene.registerBeforeRender(() => {
        for (const state of animStatesRef.current) {
          if (state.animacao.tipo === 'pivotante') {
            state.currentAngle += (state.targetAngle - state.currentAngle) * LERP
            state.pivotNode.rotation.y = state.currentAngle
          } else if (state.animacao.tipo === 'basculante') {
            state.currentAngle += (state.targetAngle - state.currentAngle) * LERP
            state.pivotNode.rotation.x = state.currentAngle
          } else if (state.animacao.tipo === 'deslizante') {
            state.currentPos = Vector3.Lerp(state.currentPos, state.targetPos, LERP)
            state.pivotNode.position.copyFrom(state.currentPos)
          }
        }
      })

      // ── Resize ─────────────────────────────────────────────────────────────
      const handleResize = () => engine.resize()
      window.addEventListener('resize', handleResize)

      // ── Render loop ────────────────────────────────────────────────────────
      engine.runRenderLoop(() => {
        if (mountedRef.current) bScene.render()
      })

      setIsLoading(false)
      onReady?.()

      return () => {
        window.removeEventListener('resize', handleResize)
      }
    }

    let cleanup: (() => void) | undefined
    init().then((c) => { cleanup = c })

    return () => {
      mountedRef.current = false
      if (engineRef.current) {
        engineRef.current.stopRenderLoop()
        babylonSceneRef.current?.dispose()
        babylonSceneRef.current = null
        engineRef.current.dispose()
        engineRef.current = null
      }
      if (canvasElemRef.current) {
        canvasElemRef.current.remove()
        canvasElemRef.current = null
      }
      cleanup?.()
    }
  }, [scene, onReady])

  useEffect(() => {
    if (!corVidro) return
    const hex = GLASS_COLORS[corVidro] ?? corVidro
    const [r, g, b] = hexToRgb(hex)
    glassMatsRef.current.forEach((mat) => {
      mat.albedoColor.r = r
      mat.albedoColor.g = g
      mat.albedoColor.b = b
    })
  }, [corVidro])

  useEffect(() => {
    if (!acabamento) return
    const finish = HARDWARE_FINISHES[acabamento]
    if (!finish) return
    const [r, g, b] = hexToRgb(finish.color)
    hardwareMatsRef.current.forEach((mat) => {
      mat.albedoColor.r = r
      mat.albedoColor.g = g
      mat.albedoColor.b = b
      mat.metallic = finish.metalness
      mat.roughness = finish.roughness
    })
  }, [acabamento])

  const hasAnim = !isLoading && animStatesRef.current.length > 0

  return (
    <div className={`relative overflow-hidden bg-gray-800 ${className}`}>
      <div ref={containerRef} className="w-full h-full" />

      {isLoading && (
        <div className="absolute inset-0 flex flex-col items-center justify-center bg-gray-900/80 text-white gap-3">
          <div className="w-10 h-10 border-4 border-white/20 border-t-white rounded-full animate-spin" />
          <span className="text-sm font-medium tracking-wide">Carregando cena 3D…</span>
        </div>
      )}

      {!isLoading && onScreenshot && (
        <button
          onClick={takeScreenshot}
          className="absolute top-4 right-4 bg-white/10 hover:bg-white/20 backdrop-blur-sm border border-white/20 text-white px-3 py-2 rounded-lg text-sm transition-all"
          title="Capturar screenshot"
        >
          📷
        </button>
      )}

      {hasAnim && (
        <div className="absolute bottom-4 left-4 right-4 flex flex-col gap-2">
          <div className="bg-black/50 backdrop-blur-sm rounded-xl px-4 py-2.5 flex items-center gap-3">
            <span className="text-white text-xs font-mono w-10 shrink-0">
              {animType === 'deslizante'
                ? `${Math.round((sliderAngle / 90) * 100)}%`
                : `${sliderAngle}°`}
            </span>
            <input
              type="range"
              min={0}
              max={maxAngle}
              step={1}
              value={sliderAngle}
              onChange={(e) => handleSliderChange(Number(e.target.value))}
              className="flex-1 accent-white h-1.5 cursor-pointer"
            />
            <span className="text-white/50 text-xs shrink-0">
              {animType === 'deslizante' ? '100%' : `${maxAngle}°`}
            </span>
          </div>
          <div className="flex justify-end">
            <button
              onClick={toggleAnimation}
              className="bg-white/10 hover:bg-white/20 backdrop-blur-sm border border-white/20 text-white px-4 py-2 rounded-lg text-sm font-medium transition-all"
            >
              {isAnimating ? '⏸ Fechar' : '▶ Abrir'}
            </button>
          </div>
        </div>
      )}
    </div>
  )
}

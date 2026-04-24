'use client'

import { useEffect, useRef, useCallback, useState } from 'react'
import type * as ThreeTypes from 'three'
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
  group: ThreeTypes.Group
  animacao: NonNullable<VidroScene['animacao']>
  currentAngle: number
  targetAngle: number
  currentPos: ThreeTypes.Vector3
  targetPos: ThreeTypes.Vector3
  originalPos: ThreeTypes.Vector3
}

export default function Viewer3D({ scene, className = '', onScreenshot, onReady, corVidro, acabamento }: Viewer3DProps) {
  const containerRef = useRef<HTMLDivElement>(null)
  const rendererRef = useRef<ThreeTypes.WebGLRenderer | null>(null)
  const sceneRef = useRef<ThreeTypes.Scene | null>(null)
  const cameraRef = useRef<ThreeTypes.PerspectiveCamera | null>(null)
  const controlsRef = useRef<ThreeTypes.EventDispatcher | null>(null)
  const animFrameRef = useRef<number>(0)
  const animStatesRef = useRef<AnimState[]>([])
  const glassMeshesRef = useRef<ThreeTypes.MeshPhysicalMaterial[]>([])
  const hardwareMeshesRef = useRef<(ThreeTypes.MeshPhysicalMaterial | ThreeTypes.MeshStandardMaterial)[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [isAnimating, setIsAnimating] = useState(false)
  const [sliderAngle, setSliderAngle] = useState(0)
  const [maxAngle, setMaxAngle] = useState(90)
  const [animType, setAnimType] = useState<'rotacional' | 'deslizante' | null>(null)
  const mountedRef = useRef(false)

  const takeScreenshot = useCallback(() => {
    if (!rendererRef.current || !onScreenshot) return
    rendererRef.current.domElement.toBlob((blob) => {
      if (blob) onScreenshot(blob)
    }, 'image/png')
  }, [onScreenshot])

  useEffect(() => {
    if (containerRef.current) {
      (containerRef.current as HTMLDivElement & { takeScreenshot?: () => void }).takeScreenshot =
        takeScreenshot
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
        const delta = pct * (state.animacao.distancia_max ?? 500) / 1000
        const dir = state.originalPos.x < 0 ? -1 : 1
        state.targetPos.set(
          state.originalPos.x + dir * delta,
          state.originalPos.y,
          state.originalPos.z
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
      const THREE = await import('three')
      const oc = await import('three/examples/jsm/controls/OrbitControls.js')
      const re = await import('three/examples/jsm/environments/RoomEnvironment.js')
      const OrbitControls = oc.OrbitControls
      const RoomEnvironment = re.RoomEnvironment

      if (!mountedRef.current || !containerRef.current) return

      if (rendererRef.current) {
        cancelAnimationFrame(animFrameRef.current)
        rendererRef.current.dispose()
        rendererRef.current.domElement.remove()
        rendererRef.current = null
      }

      const container = containerRef.current
      const width = container.clientWidth || 800
      const height = container.clientHeight || 600

      // ── Renderer ──────────────────────────────────────────────────────────
      const renderer = new THREE.WebGLRenderer({
        antialias: sceneData.ambiente.antialias ?? true,
        preserveDrawingBuffer: true,
        alpha: false,
      })
      renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2))
      renderer.setSize(width, height)
      renderer.outputColorSpace = THREE.SRGBColorSpace
      renderer.toneMapping = THREE.ACESFilmicToneMapping
      renderer.toneMappingExposure = sceneData.ambiente.toneMappingExposure ?? 1.2
      renderer.shadowMap.enabled = true
      renderer.shadowMap.type = THREE.PCFSoftShadowMap
      container.appendChild(renderer.domElement)
      rendererRef.current = renderer

      // ── Scene ─────────────────────────────────────────────────────────────
      const threeScene = new THREE.Scene()
      threeScene.background = new THREE.Color('#D6D0C8')
      sceneRef.current = threeScene

      const pmremGenerator = new THREE.PMREMGenerator(renderer)
      pmremGenerator.compileEquirectangularShader()
      const envTexture = pmremGenerator.fromScene(new RoomEnvironment(), 0.04).texture
      threeScene.environment = envTexture
      pmremGenerator.dispose()

      // ── Camera ────────────────────────────────────────────────────────────
      const cam = sceneData.ambiente.camera_inicial
      const scale = 0.001

      const camera = new THREE.PerspectiveCamera(45, width / height, 0.01, 100)
      camera.position.set(cam.posicao.x * scale, cam.posicao.y * scale, cam.posicao.z * scale)
      camera.lookAt(cam.target.x * scale, cam.target.y * scale, cam.target.z * scale)
      cameraRef.current = camera

      // ── Controls ──────────────────────────────────────────────────────────
      const controls = new OrbitControls(camera, renderer.domElement)
      controls.target.set(cam.target.x * scale, cam.target.y * scale, cam.target.z * scale)
      controls.enableDamping = true
      controls.dampingFactor = 0.06
      controls.minDistance = 0.3
      controls.maxDistance = 20
      controls.update()
      controlsRef.current = controls as unknown as ThreeTypes.EventDispatcher

      // ── Lighting ──────────────────────────────────────────────────────────
      threeScene.add(new THREE.AmbientLight(0xffffff, 0.4))

      const keyLight = new THREE.DirectionalLight(0xfff5e0, 2.0)
      keyLight.position.set(2, 4, 3)
      keyLight.castShadow = true
      keyLight.shadow.mapSize.width = 2048
      keyLight.shadow.mapSize.height = 2048
      keyLight.shadow.camera.near = 0.01
      keyLight.shadow.camera.far = 20
      keyLight.shadow.camera.left = -3
      keyLight.shadow.camera.right = 3
      keyLight.shadow.camera.top = 3
      keyLight.shadow.camera.bottom = -3
      keyLight.shadow.bias = -0.0005
      threeScene.add(keyLight)

      const fillLight = new THREE.DirectionalLight(0xc8d8ff, 0.8)
      fillLight.position.set(-3, 1, -1)
      threeScene.add(fillLight)

      const rimLight = new THREE.DirectionalLight(0xffddaa, 0.6)
      rimLight.position.set(0, 2, -4)
      threeScene.add(rimLight)

      // ── Floor (CanvasTexture tile) ─────────────────────────────────────────
      const pisoData = sceneData.ambiente.piso
      {
        const sz = 512, grid = 64
        const cv = document.createElement("canvas")
        cv.width = sz; cv.height = sz
        const ctx = cv.getContext("2d")!
        ctx.fillStyle = pisoData.cor
        ctx.fillRect(0, 0, sz, sz)
        ctx.strokeStyle = "rgba(180,160,140,0.22)"
        ctx.lineWidth = 1
        for (let i = 0; i <= sz; i += grid) {
          ctx.beginPath(); ctx.moveTo(i, 0); ctx.lineTo(i, sz); ctx.stroke()
          ctx.beginPath(); ctx.moveTo(0, i); ctx.lineTo(sz, i); ctx.stroke()
        }
        const tex = new THREE.CanvasTexture(cv)
        tex.wrapS = tex.wrapT = THREE.RepeatWrapping
        tex.repeat.set(20, 20)
        const floor = new THREE.Mesh(
          new THREE.PlaneGeometry(20, 20),
          new THREE.MeshStandardMaterial({
            map: tex, roughness: 0.85, metalness: 0.0,
            envMapIntensity: pisoData.envMapIntensity,
          })
        )
        floor.rotation.x = -Math.PI / 2
        floor.receiveShadow = true
        threeScene.add(floor)
      }

      // ── Walls ─────────────────────────────────────────────────────────────
      if (sceneData.vao && sceneData.vao.presente !== false) {
        const vaoData = sceneData.vao
        const wallTex = (() => {
          const sz = 256
          const cv = document.createElement("canvas")
          cv.width = sz; cv.height = sz
          const ctx = cv.getContext("2d")!
          ctx.fillStyle = vaoData.material.cor
          ctx.fillRect(0, 0, sz, sz)
          const id = ctx.getImageData(0, 0, sz, sz)
          for (let i = 0; i < id.data.length; i += 4) {
            const n = (Math.random() - 0.5) * 16
            id.data[i]   = Math.min(255, Math.max(0, id.data[i]   + n))
            id.data[i+1] = Math.min(255, Math.max(0, id.data[i+1] + n))
            id.data[i+2] = Math.min(255, Math.max(0, id.data[i+2] + n))
          }
          ctx.putImageData(id, 0, 0)
          const t = new THREE.CanvasTexture(cv)
          t.wrapS = t.wrapT = THREE.RepeatWrapping
          t.repeat.set(3, 3)
          return t
        })()
        const wallMat = new THREE.MeshStandardMaterial({
          map: wallTex,
          roughness: vaoData.material.roughness,
          metalness: vaoData.material.metalness,
          side: THREE.DoubleSide,
        })
        const vW = vaoData.largura * scale
        const vH = vaoData.altura * scale
        const vD = vaoData.profundidade * scale
  
        const backWall = new THREE.Mesh(new THREE.PlaneGeometry(vW + 0.6, vH + 0.3), wallMat)
        backWall.position.set(0, vH / 2, -vD / 2)
        backWall.receiveShadow = true
        threeScene.add(backWall)
  
        const sideThick = 0.3
        const pillarMat = new THREE.MeshStandardMaterial({
          map: wallTex,
          roughness: vaoData.material.roughness,
          metalness: vaoData.material.metalness,
        })
        const pillarGeo = new THREE.BoxGeometry(sideThick, vH, vD)
        const leftPillar = new THREE.Mesh(pillarGeo, pillarMat)
        leftPillar.position.set(-vW / 2 - sideThick / 2, vH / 2, 0)
        leftPillar.receiveShadow = true
        leftPillar.castShadow = true
        threeScene.add(leftPillar)
  
        const rightPillar = new THREE.Mesh(pillarGeo, pillarMat)
        rightPillar.position.set(vW / 2 + sideThick / 2, vH / 2, 0)
        rightPillar.receiveShadow = true
        rightPillar.castShadow = true
        threeScene.add(rightPillar)
  
        const topBeam = new THREE.Mesh(new THREE.BoxGeometry(vW + sideThick * 2, 0.2, vD), pillarMat)
        topBeam.position.set(0, vH + 0.1, 0)
        topBeam.receiveShadow = true
        threeScene.add(topBeam)
  
  
      }

      // ── Vidros ────────────────────────────────────────────────────────────
      animStatesRef.current = []
      glassMeshesRef.current = []
      hardwareMeshesRef.current = []
      const pivotGroupMap = new Map<string, { group: ThreeTypes.Group; pivoX: number }>()

      for (const vidro of sceneData.vidros) {
        const mat = vidro.material
        const vidroMat = new THREE.MeshPhysicalMaterial({
          color: new THREE.Color(mat.cor),
          transparent: true,
          opacity: mat.opacidade,
          transmission: mat.transmission,
          ior: mat.ior,
          thickness: mat.thickness * scale,
          roughness: mat.roughness,
          metalness: mat.metalness,
          clearcoat: mat.clearcoat,
          clearcoatRoughness: mat.clearcoatRoughness,
          envMapIntensity: mat.envMapIntensity,
          attenuationColor: new THREE.Color(mat.attenuationColor),
          attenuationDistance: mat.attenuationDistance * scale,
          side: THREE.DoubleSide,
        })

        glassMeshesRef.current.push(vidroMat)
        const geo = new THREE.BoxGeometry(
          vidro.largura * scale,
          vidro.altura * scale,
          vidro.espessura * scale
        )
        const mesh = new THREE.Mesh(geo, vidroMat)
        mesh.castShadow = true
        mesh.receiveShadow = true
        if (vidro.rotacao) {
          mesh.rotation.set(
            THREE.MathUtils.degToRad(vidro.rotacao.x || 0),
            THREE.MathUtils.degToRad(vidro.rotacao.y || 0),
            THREE.MathUtils.degToRad(vidro.rotacao.z || 0)
          )
        }

        const group = new THREE.Group()
        const anim = vidro.animacao
        if (anim && anim.tipo !== 'fixo' && anim.ponto_pivo) {
          const pivo = anim.ponto_pivo
          mesh.position.set(
            -pivo.x * scale + vidro.posicao.x * scale,
            vidro.posicao.y * scale,
            vidro.posicao.z * scale
          )
          group.position.set(pivo.x * scale, pivo.y * scale, pivo.z * scale)
        } else {
          mesh.position.set(0, 0, 0)
          group.position.set(
            vidro.posicao.x * scale,
            vidro.posicao.y * scale,
            vidro.posicao.z * scale
          )
        }

        group.add(mesh)
        threeScene.add(group)

        if (anim && anim.ponto_pivo) {
          pivotGroupMap.set(vidro.nome, { group, pivoX: anim.ponto_pivo.x * scale })
        }

        if (anim && anim.tipo !== 'fixo') {
          animStatesRef.current.push({
            vidroId: vidro.id,
            group,
            animacao: anim,
            currentAngle: 0,
            targetAngle: 0,
            currentPos: group.position.clone(),
            targetPos: group.position.clone(),
            originalPos: group.position.clone(),
          })
        }
      }

      // Derive anim metadata for UI
      const firstAnim = animStatesRef.current[0]?.animacao
      if (firstAnim) {
        const isDeslizante = firstAnim.tipo === 'deslizante'
        setAnimType(isDeslizante ? 'deslizante' : 'rotacional')
        setMaxAngle(isDeslizante ? 90 : (firstAnim.angulo_max ?? 90))
      }

      // ── Ferragens ─────────────────────────────────────────────────────────
      for (const ferragem of sceneData.ferragens) {
        const mat = ferragem.material
        let ferragemMat: ThreeTypes.MeshPhysicalMaterial | ThreeTypes.MeshStandardMaterial

        if ((mat.clearcoat ?? 0) > 0) {
          ferragemMat = new THREE.MeshPhysicalMaterial({
            color: new THREE.Color(mat.cor),
            roughness: mat.roughness,
            metalness: mat.metalness,
            clearcoat: mat.clearcoat ?? 0,
            clearcoatRoughness: mat.clearcoatRoughness ?? 0.1,
            envMapIntensity: mat.envMapIntensity ?? 1.0,
          })
        } else {
          ferragemMat = new THREE.MeshStandardMaterial({
            color: new THREE.Color(mat.cor),
            roughness: mat.roughness,
            metalness: mat.metalness,
            envMapIntensity: mat.envMapIntensity ?? 1.0,
          })
        }

        const geo = ferragem.geometria
        let geometry: ThreeTypes.BufferGeometry
        if (geo.tipo === 'cylinder') {
          geometry = new THREE.CylinderGeometry(
            (geo.raio ?? 5) * scale,
            (geo.raio ?? 5) * scale,
            (geo.comprimento ?? geo.altura ?? 30) * scale,
            16
          )
        } else if (geo.tipo === 'sphere') {
          geometry = new THREE.SphereGeometry((geo.raio ?? 5) * scale, 16, 16)
        } else {
          geometry = new THREE.BoxGeometry(
            (geo.largura ?? 10) * scale,
            (geo.altura ?? 10) * scale,
            (geo.profundidade ?? 10) * scale
          )
        }

        hardwareMeshesRef.current.push(ferragemMat)
        const mesh = new THREE.Mesh(geometry, ferragemMat)
        mesh.rotation.set(ferragem.rotacao.x, ferragem.rotacao.y, ferragem.rotacao.z)
        mesh.castShadow = true
        const pm = pivotGroupMap.get(ferragem.peca_nome)
        if (pm) {
          mesh.position.set(
            ferragem.posicao.x * scale - pm.pivoX,
            ferragem.posicao.y * scale,
            ferragem.posicao.z * scale
          )
          pm.group.add(mesh)
        } else {
          mesh.position.set(ferragem.posicao.x * scale, ferragem.posicao.y * scale, ferragem.posicao.z * scale)
          threeScene.add(mesh)
        }
      }

      // ── Resize handler ────────────────────────────────────────────────────
      const handleResize = () => {
        if (!containerRef.current || !rendererRef.current || !cameraRef.current) return
        const w = containerRef.current.clientWidth
        const h = containerRef.current.clientHeight
        renderer.setSize(w, h)
        camera.aspect = w / h
        camera.updateProjectionMatrix()
      }
      window.addEventListener('resize', handleResize)

      // ── Animation loop ────────────────────────────────────────────────────
      const LERP = 0.05

      function animate() {
        animFrameRef.current = requestAnimationFrame(animate)
        controls.update()

        for (const state of animStatesRef.current) {
          if (state.animacao.tipo === 'pivotante') {
            state.currentAngle += (state.targetAngle - state.currentAngle) * LERP
            state.group.rotation.y = state.currentAngle
          } else if (state.animacao.tipo === 'basculante') {
            state.currentAngle += (state.targetAngle - state.currentAngle) * LERP
            state.group.rotation.x = state.currentAngle
          } else if (state.animacao.tipo === 'deslizante') {
            state.currentPos.lerp(state.targetPos, LERP)
            state.group.position.copy(state.currentPos)
          }
        }

        renderer.render(threeScene, camera)
      }
      animate()

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
      cancelAnimationFrame(animFrameRef.current)
      if (rendererRef.current) {
        rendererRef.current.dispose()
        rendererRef.current.domElement.remove()
        rendererRef.current = null
      }
      cleanup?.()
    }
  }, [scene, onReady])

  useEffect(() => {
    if (!corVidro) return
    const hexColor = GLASS_COLORS[corVidro] ?? corVidro
    glassMeshesRef.current.forEach((mat) => {
      mat.color.set(hexColor)
      mat.needsUpdate = true
    })
  }, [corVidro])

  useEffect(() => {
    if (!acabamento) return
    const finish = HARDWARE_FINISHES[acabamento]
    if (!finish) return
    hardwareMeshesRef.current.forEach((mat) => {
      mat.color.set(finish.color)
      mat.roughness = finish.roughness
      mat.metalness = finish.metalness
      mat.needsUpdate = true
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
          {/* Slider de abertura */}
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
          {/* Botão rápido */}
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

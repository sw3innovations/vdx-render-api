import { useEffect, useRef, useCallback, useState } from 'react'
import type { VDXViewerProps, SceneJSON, VidroScene } from './types'

interface AnimState {
  vidroId: string
  group: object & { rotation: { x: number; y: number }; position: { x: number } }
  animacao: NonNullable<VidroScene['animacao']>
  currentAngle: number
  targetAngle: number
}

/**
 * VDXViewer — 3D photorealistic glass fixture viewer.
 *
 * Renders a SceneJSON from the VDX API using Three.js r165 with:
 * - MeshPhysicalMaterial (transmission + IOR + attenuation) for glass
 * - PMREMGenerator + RoomEnvironment for reflections
 * - ACES Filmic tone mapping
 * - Smooth open/close animation
 * - Screenshot capture
 *
 * @example
 * ```tsx
 * const client = new VDXClient('my-api-key')
 * <VDXViewer client={client} tipologia="porta_pivotante_simples" largura={900} altura={2100} />
 * ```
 */
export function VDXViewer({
  client,
  tipologia,
  largura,
  altura,
  corVidro = 'incolor',
  espessura = 8,
  className = '',
  onScreenshot,
  onReady,
  onSceneLoad,
}: VDXViewerProps) {
  const containerRef = useRef<HTMLDivElement>(null)
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const rendererRef = useRef<any>(null)
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const controlsRef = useRef<any>(null)
  const animFrameRef = useRef<number>(0)
  const animStatesRef = useRef<AnimState[]>([])
  const mountedRef = useRef(false)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [isAnimating, setIsAnimating] = useState(false)
  const [hasAnimatable, setHasAnimatable] = useState(false)

  const takeScreenshot = useCallback(() => {
    if (!rendererRef.current || !onScreenshot) return
    rendererRef.current.domElement.toBlob((blob: Blob | null) => {
      if (blob) onScreenshot(blob)
    }, 'image/png')
  }, [onScreenshot])

  const toggleAnimation = useCallback(() => {
    setIsAnimating((prev) => {
      const next = !prev
      animStatesRef.current.forEach((state) => {
        if (state.animacao.tipo === 'pivotante') {
          state.targetAngle = next
            ? ((state.animacao.angulo_max ?? 90) * Math.PI) / 180
            : 0
        } else if (state.animacao.tipo === 'basculante') {
          state.targetAngle = next
            ? ((state.animacao.angulo_max ?? 45) * Math.PI) / 180
            : 0
        } else if (state.animacao.tipo === 'deslizante') {
          // handled separately via targetPos
        }
      })
      return next
    })
  }, [])

  useEffect(() => {
    mountedRef.current = true
    setIsLoading(true)
    setError(null)

    const container = containerRef.current
    if (!container) return

    async function init() {
      let sceneData: SceneJSON
      try {
        sceneData = await client.getScene(tipologia, largura, altura, corVidro, espessura)
        onSceneLoad?.(sceneData)
      } catch (err) {
        if (!mountedRef.current) return
        setError(err instanceof Error ? err.message : String(err))
        setIsLoading(false)
        return
      }

      if (!mountedRef.current || !container) return

      // Dynamically import Three.js (peer dependency — keeps SDK bundle small)
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      let THREE: any, OrbitControls: any, RoomEnvironment: any
      try {
        const [threeModule, ocModule, reModule] = await Promise.all([
          import('three'),
          import('three/examples/jsm/controls/OrbitControls.js'),
          import('three/examples/jsm/environments/RoomEnvironment.js'),
        ])
        THREE = threeModule
        OrbitControls = ocModule.OrbitControls
        RoomEnvironment = reModule.RoomEnvironment
      } catch {
        setError('three.js not found — add "three" to your dependencies')
        setIsLoading(false)
        return
      }

      if (!mountedRef.current || !container) return

      // Dispose previous renderer if re-mounting
      if (rendererRef.current) {
        cancelAnimationFrame(animFrameRef.current)
        rendererRef.current.dispose()
        rendererRef.current.domElement.remove()
        rendererRef.current = null
      }

      const width = container.clientWidth || 800
      const height = container.clientHeight || 600
      const scale = 0.001 // mm → m

      // ── Renderer ────────────────────────────────────────────────────────────
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

      // ── Scene ────────────────────────────────────────────────────────────────
      const threeScene = new THREE.Scene()
      threeScene.background = new THREE.Color('#D6D0C8')

      // ── Environment (PMREM + RoomEnvironment) ────────────────────────────────
      const pmrem = new THREE.PMREMGenerator(renderer)
      pmrem.compileEquirectangularShader()
      const envTexture = pmrem.fromScene(new RoomEnvironment(), 0.04).texture
      threeScene.environment = envTexture
      pmrem.dispose()

      // ── Camera ───────────────────────────────────────────────────────────────
      const cam = sceneData.ambiente.camera_inicial
      const camera = new THREE.PerspectiveCamera(45, width / height, 0.01, 100)
      camera.position.set(cam.posicao.x * scale, cam.posicao.y * scale, cam.posicao.z * scale)
      camera.lookAt(cam.target.x * scale, cam.target.y * scale, cam.target.z * scale)

      // ── Controls ─────────────────────────────────────────────────────────────
      const controls = new OrbitControls(camera, renderer.domElement)
      controls.target.set(cam.target.x * scale, cam.target.y * scale, cam.target.z * scale)
      controls.enableDamping = true
      controls.dampingFactor = 0.06
      controls.minDistance = 0.3
      controls.maxDistance = 20
      controls.update()
      controlsRef.current = controls

      // ── Lighting ─────────────────────────────────────────────────────────────
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

      // ── Floor ────────────────────────────────────────────────────────────────
      const pisoData = sceneData.ambiente.piso
      const floor = new THREE.Mesh(
        new THREE.PlaneGeometry(20, 20),
        new THREE.MeshStandardMaterial({
          color: new THREE.Color(pisoData.cor),
          roughness: pisoData.roughness,
          metalness: pisoData.metalness,
          envMapIntensity: pisoData.envMapIntensity,
        })
      )
      floor.rotation.x = -Math.PI / 2
      floor.receiveShadow = true
      threeScene.add(floor)

      // ── Walls (vão) ──────────────────────────────────────────────────────────
      const vaoData = sceneData.vao
      const wallMat = new THREE.MeshStandardMaterial({
        color: new THREE.Color(vaoData.material.cor),
        roughness: vaoData.material.roughness,
        metalness: vaoData.material.metalness,
        side: THREE.BackSide,
      })
      const pillarMat = new THREE.MeshStandardMaterial({
        color: new THREE.Color(vaoData.material.cor),
        roughness: vaoData.material.roughness,
        metalness: vaoData.material.metalness,
      })
      const vW = vaoData.largura * scale
      const vH = vaoData.altura * scale
      const vD = vaoData.profundidade * scale
      const sideThick = 0.3

      const backWall = new THREE.Mesh(new THREE.PlaneGeometry(vW + 0.6, vH + 0.3), wallMat)
      backWall.position.set(0, vH / 2, -vD / 2)
      backWall.receiveShadow = true
      threeScene.add(backWall)

      const pillarGeo = new THREE.BoxGeometry(sideThick, vH, vD)
      const leftPillar = new THREE.Mesh(pillarGeo, pillarMat)
      leftPillar.position.set(-vW / 2 - sideThick / 2, vH / 2, 0)
      leftPillar.castShadow = true
      leftPillar.receiveShadow = true
      threeScene.add(leftPillar)

      const rightPillar = new THREE.Mesh(pillarGeo, pillarMat)
      rightPillar.position.set(vW / 2 + sideThick / 2, vH / 2, 0)
      rightPillar.castShadow = true
      rightPillar.receiveShadow = true
      threeScene.add(rightPillar)

      const topBeam = new THREE.Mesh(new THREE.BoxGeometry(vW + sideThick * 2, 0.2, vD), pillarMat)
      topBeam.position.set(0, vH + 0.1, 0)
      topBeam.receiveShadow = true
      threeScene.add(topBeam)

      // ── Vidros ───────────────────────────────────────────────────────────────
      animStatesRef.current = []

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

        const mesh = new THREE.Mesh(
          new THREE.BoxGeometry(vidro.largura * scale, vidro.altura * scale, vidro.espessura * scale),
          vidroMat
        )
        mesh.castShadow = true
        mesh.receiveShadow = true

        const group = new THREE.Group()
        const anim = vidro.animacao

        if (anim && anim.tipo !== 'fixo' && anim.ponto_pivo) {
          const pivo = anim.ponto_pivo
          mesh.position.set(
            -pivo.x * scale + vidro.posicao.x * scale,
            (vidro.posicao.y - vidro.altura / 2) * scale,
            vidro.posicao.z * scale
          )
          group.position.set(pivo.x * scale, pivo.y * scale, pivo.z * scale)
        } else {
          mesh.position.set(0, 0, 0)
          group.position.set(vidro.posicao.x * scale, vidro.posicao.y * scale, vidro.posicao.z * scale)
        }

        group.add(mesh)
        threeScene.add(group)

        if (anim && anim.tipo !== 'fixo') {
          animStatesRef.current.push({
            vidroId: vidro.id,
            group,
            animacao: anim,
            currentAngle: 0,
            targetAngle: 0,
          })
        }
      }

      setHasAnimatable(animStatesRef.current.length > 0)

      // ── Ferragens ────────────────────────────────────────────────────────────
      for (const ferragem of sceneData.ferragens) {
        const mat = ferragem.material
        const ferragemMat = (mat.clearcoat ?? 0) > 0
          ? new THREE.MeshPhysicalMaterial({
              color: new THREE.Color(mat.cor),
              roughness: mat.roughness,
              metalness: mat.metalness,
              clearcoat: mat.clearcoat ?? 0,
              clearcoatRoughness: mat.clearcoatRoughness ?? 0.1,
              envMapIntensity: mat.envMapIntensity ?? 1.0,
            })
          : new THREE.MeshStandardMaterial({
              color: new THREE.Color(mat.cor),
              roughness: mat.roughness,
              metalness: mat.metalness,
              envMapIntensity: mat.envMapIntensity ?? 1.0,
            })

        const geo = ferragem.geometria
        const geometry = geo.tipo === 'cylinder'
          ? new THREE.CylinderGeometry(
              (geo.raio ?? 5) * scale,
              (geo.raio ?? 5) * scale,
              (geo.comprimento ?? geo.altura ?? 30) * scale,
              16
            )
          : geo.tipo === 'sphere'
          ? new THREE.SphereGeometry((geo.raio ?? 5) * scale, 16, 16)
          : new THREE.BoxGeometry(
              (geo.largura ?? 10) * scale,
              (geo.altura ?? 10) * scale,
              (geo.profundidade ?? 10) * scale
            )

        const mesh = new THREE.Mesh(geometry, ferragemMat)
        mesh.position.set(ferragem.posicao.x * scale, ferragem.posicao.y * scale, ferragem.posicao.z * scale)
        mesh.rotation.set(ferragem.rotacao.x, ferragem.rotacao.y, ferragem.rotacao.z)
        mesh.castShadow = true
        threeScene.add(mesh)
      }

      // ── Resize ───────────────────────────────────────────────────────────────
      const handleResize = () => {
        if (!container || !rendererRef.current) return
        const w = container.clientWidth
        const h = container.clientHeight
        renderer.setSize(w, h)
        camera.aspect = w / h
        camera.updateProjectionMatrix()
      }
      window.addEventListener('resize', handleResize)

      // ── Render loop ──────────────────────────────────────────────────────────
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
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [client, tipologia, largura, altura, corVidro, espessura])

  return (
    <div
      style={{ position: 'relative', overflow: 'hidden', background: '#1a1a2e' }}
      className={className}
    >
      <div ref={containerRef} style={{ width: '100%', height: '100%' }} />

      {isLoading && !error && (
        <div style={{
          position: 'absolute', inset: 0, display: 'flex', flexDirection: 'column',
          alignItems: 'center', justifyContent: 'center',
          background: 'rgba(0,0,0,0.7)', color: '#fff', gap: 12,
        }}>
          <div style={{
            width: 40, height: 40, border: '4px solid rgba(255,255,255,0.2)',
            borderTopColor: '#fff', borderRadius: '50%',
            animation: 'vdx-spin 0.8s linear infinite',
          }} />
          <span style={{ fontSize: 14, fontWeight: 500, letterSpacing: 1 }}>
            Carregando cena 3D…
          </span>
          <style>{`@keyframes vdx-spin { to { transform: rotate(360deg); } }`}</style>
        </div>
      )}

      {error && (
        <div style={{
          position: 'absolute', inset: 0, display: 'flex', flexDirection: 'column',
          alignItems: 'center', justifyContent: 'center',
          background: 'rgba(220,50,50,0.85)', color: '#fff', gap: 8, padding: 24,
        }}>
          <span style={{ fontSize: 18 }}>⚠</span>
          <span style={{ fontSize: 13, textAlign: 'center', maxWidth: 280 }}>{error}</span>
        </div>
      )}

      {!isLoading && !error && hasAnimatable && (
        <button
          onClick={toggleAnimation}
          style={{
            position: 'absolute', bottom: 16, right: 16,
            background: 'rgba(255,255,255,0.1)', border: '1px solid rgba(255,255,255,0.2)',
            backdropFilter: 'blur(8px)', color: '#fff', padding: '8px 16px',
            borderRadius: 8, fontSize: 13, fontWeight: 500, cursor: 'pointer',
          }}
        >
          {isAnimating ? '⏸ Fechar' : '▶ Abrir'}
        </button>
      )}

      {!isLoading && !error && onScreenshot && (
        <button
          onClick={takeScreenshot}
          style={{
            position: 'absolute', top: 16, right: 16,
            background: 'rgba(255,255,255,0.1)', border: '1px solid rgba(255,255,255,0.2)',
            backdropFilter: 'blur(8px)', color: '#fff', padding: '8px 12px',
            borderRadius: 8, fontSize: 16, cursor: 'pointer',
          }}
          title="Capturar screenshot"
        >
          📷
        </button>
      )}
    </div>
  )
}

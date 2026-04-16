'use client'

import { useEffect, useRef, useCallback, useState } from 'react'
import type * as ThreeTypes from 'three'
import type { SceneJSON, VidroScene } from '@/lib/types'

interface Viewer3DProps {
  scene: SceneJSON | null
  className?: string
  onScreenshot?: (blob: Blob) => void
  onReady?: () => void
}

interface AnimState {
  vidroId: string
  group: ThreeTypes.Group
  animacao: NonNullable<VidroScene['animacao']>
  currentAngle: number
  targetAngle: number
  currentPos: ThreeTypes.Vector3
  targetPos: ThreeTypes.Vector3
}

export default function Viewer3D({ scene, className = '', onScreenshot, onReady }: Viewer3DProps) {
  const containerRef = useRef<HTMLDivElement>(null)
  const rendererRef = useRef<ThreeTypes.WebGLRenderer | null>(null)
  const sceneRef = useRef<ThreeTypes.Scene | null>(null)
  const cameraRef = useRef<ThreeTypes.PerspectiveCamera | null>(null)
  const controlsRef = useRef<ThreeTypes.EventDispatcher | null>(null)
  const animFrameRef = useRef<number>(0)
  const animStatesRef = useRef<AnimState[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [isAnimating, setIsAnimating] = useState(false)
  const mountedRef = useRef(false)

  const takeScreenshot = useCallback(() => {
    if (!rendererRef.current || !onScreenshot) return
    rendererRef.current.domElement.toBlob((blob) => {
      if (blob) onScreenshot(blob)
    }, 'image/png')
  }, [onScreenshot])

  // Expose takeScreenshot on the container element for external access
  useEffect(() => {
    if (containerRef.current) {
      (containerRef.current as HTMLDivElement & { takeScreenshot?: () => void }).takeScreenshot =
        takeScreenshot
    }
  }, [takeScreenshot])

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
          state.targetPos.setX(next ? (state.animacao.distancia_max ?? 500) / 1000 : 0)
        }
      })
      return next
    })
  }, [])

  useEffect(() => {
    if (!containerRef.current || !scene) return

    // Capture non-null scene for use inside async init
    const sceneData: SceneJSON = scene

    mountedRef.current = true
    setIsLoading(true)

    async function init() {
      const THREE = await import('three')
      const oc = await import('three/examples/jsm/controls/OrbitControls.js')
      const re = await import('three/examples/jsm/environments/RoomEnvironment.js')
      const OrbitControls = oc.OrbitControls
      const RoomEnvironment = re.RoomEnvironment

      if (!mountedRef.current || !containerRef.current) return

      // Clean up previous renderer
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

      // ── Environment (PMREMGenerator + RoomEnvironment) ─────────────────────
      const pmremGenerator = new THREE.PMREMGenerator(renderer)
      pmremGenerator.compileEquirectangularShader()
      const envTexture = pmremGenerator.fromScene(new RoomEnvironment(), 0.04).texture
      threeScene.environment = envTexture
      pmremGenerator.dispose()

      // ── Camera ────────────────────────────────────────────────────────────
      const cam = sceneData.ambiente.camera_inicial
      const scale = 0.001 // mm → m

      const camera = new THREE.PerspectiveCamera(45, width / height, 0.01, 100)
      camera.position.set(
        cam.posicao.x * scale,
        cam.posicao.y * scale,
        cam.posicao.z * scale
      )
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
      const ambient = new THREE.AmbientLight(0xffffff, 0.4)
      threeScene.add(ambient)

      // Key light (warm, directional, casts shadows)
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

      // Fill light (cool blue)
      const fillLight = new THREE.DirectionalLight(0xc8d8ff, 0.8)
      fillLight.position.set(-3, 1, -1)
      threeScene.add(fillLight)

      // Rim light (warm orange)
      const rimLight = new THREE.DirectionalLight(0xffddaa, 0.6)
      rimLight.position.set(0, 2, -4)
      threeScene.add(rimLight)

      // ── Floor ─────────────────────────────────────────────────────────────
      const pisoData = sceneData.ambiente.piso
      const floorGeo = new THREE.PlaneGeometry(20, 20)
      const floorMat = new THREE.MeshStandardMaterial({
        color: new THREE.Color(pisoData.cor),
        roughness: pisoData.roughness,
        metalness: pisoData.metalness,
        envMapIntensity: pisoData.envMapIntensity,
      })
      const floor = new THREE.Mesh(floorGeo, floorMat)
      floor.rotation.x = -Math.PI / 2
      floor.receiveShadow = true
      threeScene.add(floor)

      // ── Walls (vão) ───────────────────────────────────────────────────────
      const vaoData = sceneData.vao
      const wallMat = new THREE.MeshStandardMaterial({
        color: new THREE.Color(vaoData.material.cor),
        roughness: vaoData.material.roughness,
        metalness: vaoData.material.metalness,
        side: THREE.BackSide,
      })

      const vW = vaoData.largura * scale
      const vH = vaoData.altura * scale
      const vD = vaoData.profundidade * scale

      // Back wall
      const backWallGeo = new THREE.PlaneGeometry(vW + 0.6, vH + 0.3)
      const backWall = new THREE.Mesh(backWallGeo, wallMat)
      backWall.position.set(0, vH / 2, -vD / 2)
      backWall.receiveShadow = true
      threeScene.add(backWall)

      // Left wall panel (pillar left)
      const sideThick = 0.3
      const pillarGeo = new THREE.BoxGeometry(sideThick, vH, vD)
      const pillarMat = new THREE.MeshStandardMaterial({
        color: new THREE.Color(vaoData.material.cor),
        roughness: vaoData.material.roughness,
        metalness: vaoData.material.metalness,
      })
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

      // Top beam
      const beamGeo = new THREE.BoxGeometry(vW + sideThick * 2, 0.2, vD)
      const topBeam = new THREE.Mesh(beamGeo, pillarMat)
      topBeam.position.set(0, vH + 0.1, 0)
      topBeam.receiveShadow = true
      threeScene.add(topBeam)

      // ── Vidros ────────────────────────────────────────────────────────────
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

        const geo = new THREE.BoxGeometry(
          vidro.largura * scale,
          vidro.altura * scale,
          vidro.espessura * scale
        )
        const mesh = new THREE.Mesh(geo, vidroMat)
        mesh.castShadow = true
        mesh.receiveShadow = true

        const group = new THREE.Group()

        // Apply pivot offset if animatable
        const anim = vidro.animacao
        if (anim && anim.tipo !== 'fixo' && anim.ponto_pivo) {
          const pivo = anim.ponto_pivo
          // mesh is offset from group origin by pivot
          mesh.position.set(
            (vidro.posicao.x - pivo.x) * scale,
            (vidro.posicao.y - pivo.y) * scale - (vidro.altura / 2) * scale,
            (vidro.posicao.z - pivo.z) * scale
          )
          // For pivotante (door pivot): mesh x-center is at -width/2 from pivot
          // Re-position mesh so pivot is at group origin
          mesh.position.set(
            -pivo.x * scale + vidro.posicao.x * scale,
            (vidro.posicao.y - vidro.altura / 2) * scale,
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

        if (anim && anim.tipo !== 'fixo') {
          animStatesRef.current.push({
            vidroId: vidro.id,
            group,
            animacao: anim,
            currentAngle: 0,
            targetAngle: 0,
            currentPos: new THREE.Vector3(),
            targetPos: new THREE.Vector3(),
          })
        }
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

        const mesh = new THREE.Mesh(geometry, ferragemMat)
        mesh.position.set(
          ferragem.posicao.x * scale,
          ferragem.posicao.y * scale,
          ferragem.posicao.z * scale
        )
        mesh.rotation.set(
          ferragem.rotacao.x,
          ferragem.rotacao.y,
          ferragem.rotacao.z
        )
        mesh.castShadow = true
        threeScene.add(mesh)
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

        // Smooth animation interpolation
        for (const state of animStatesRef.current) {
          if (state.animacao.tipo === 'pivotante') {
            state.currentAngle += (state.targetAngle - state.currentAngle) * LERP
            state.group.rotation.y = state.currentAngle
          } else if (state.animacao.tipo === 'basculante') {
            state.currentAngle += (state.targetAngle - state.currentAngle) * LERP
            state.group.rotation.x = state.currentAngle
          } else if (state.animacao.tipo === 'deslizante') {
            state.currentPos.lerp(state.targetPos, LERP)
            state.group.position.x = state.currentPos.x
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

  return (
    <div className={`relative overflow-hidden bg-gray-800 ${className}`}>
      <div ref={containerRef} className="w-full h-full" />

      {isLoading && (
        <div className="absolute inset-0 flex flex-col items-center justify-center bg-gray-900/80 text-white gap-3">
          <div className="w-10 h-10 border-4 border-white/20 border-t-white rounded-full animate-spin" />
          <span className="text-sm font-medium tracking-wide">Carregando cena 3D…</span>
        </div>
      )}

      {!isLoading && animStatesRef.current.length > 0 && (
        <button
          onClick={toggleAnimation}
          className="absolute bottom-4 right-4 bg-white/10 hover:bg-white/20 backdrop-blur-sm border border-white/20 text-white px-4 py-2 rounded-lg text-sm font-medium transition-all"
        >
          {isAnimating ? '⏸ Fechar' : '▶ Abrir'}
        </button>
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
    </div>
  )
}

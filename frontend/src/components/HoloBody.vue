<script setup lang="ts">
/**
 * Rotating holographic body (Three.js) shown inside the vital ring.
 * Each body zone is a hotspot anchored to a 3D point on the figure and re-projected
 * to the screen every frame, so the dots turn with the body. Drag sideways to rotate.
 * If WebGL is not available the component emits `unavailable` and the ring falls
 * back to its flat silhouette.
 */
import * as THREE from 'three'
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js'
import { onBeforeUnmount, onMounted, ref } from 'vue'
import { buildBody } from './body/humanoid'

export interface HoloZone {
  zone: string
  color: string
  monitored: boolean
  flagged: boolean
  critical: boolean
  aria: string
}

const props = defineProps<{
  zones: HoloZone[]
  openZone?: string | null
  /** Duration of one heartbeat, e.g. "0.81s" (from the latest heart rate). */
  beat: string
}>()
const emit = defineEmits<{ zone: [zone: string]; unavailable: [] }>()

// Where each zone sits on the figure (y up, figure faces +z) and which way the surface faces.
const ANCHORS: Record<string, { p: [number, number, number]; n: [number, number, number] }> = {
  brain: { p: [0, 0.925, 0.04], n: [0, 0.8, 0.6] },
  eyes: { p: [0, 0.848, 0.098], n: [0, 0, 1] },
  head: { p: [0, 0.768, 0.082], n: [0, -0.2, 1] },   // body temperature
  heart: { p: [0.045, 0.56, 0.104], n: [0.1, 0, 1] },
  abdomen: { p: [0, 0.36, 0.094], n: [0, 0, 1] },
  bones: { p: [0.108, -0.2, 0.07], n: [0.2, 0, 1] },
}

const host = ref<HTMLDivElement>()
const spots = ref<HTMLButtonElement[]>([])
const ready = ref(false)

let renderer: THREE.WebGLRenderer | undefined
let controls: OrbitControls | undefined
let observer: ResizeObserver | undefined
let frame = 0
let resumeTimer: number | undefined
const disposables: { dispose: () => void }[] = []

const HOLO_VERTEX = /* glsl */ `
  varying vec3 vNormal;
  varying vec3 vView;
  varying float vY;
  void main() {
    vec4 world = modelMatrix * vec4(position, 1.0);
    vec4 mv = viewMatrix * world;
    vNormal = normalize(normalMatrix * normal);
    vView = normalize(-mv.xyz);
    vY = world.y;
    gl_Position = projectionMatrix * mv;
  }`
const HOLO_FRAGMENT = /* glsl */ `
  uniform float uTime;
  uniform float uScan;
  uniform vec3 uColor;
  varying vec3 vNormal;
  varying vec3 vView;
  varying float vY;
  void main() {
    float facing = abs(dot(normalize(vNormal), normalize(vView)));
    float fresnel = pow(1.0 - facing, 2.0);                         // bright rim
    float lines = 0.5 + 0.5 * sin(vY * 260.0 - uTime * 2.2);        // fine scan lines
    float beam = smoothstep(0.07, 0.0, abs(vY - uScan));            // sweeping scan beam
    float alpha = 0.04 + fresnel * 0.85 + lines * 0.02 + beam * 0.5;
    vec3 color = uColor * (0.55 + fresnel * 0.9) + vec3(0.7, 1.0, 0.95) * beam * 0.6;
    gl_FragColor = vec4(color, alpha);
  }`

function track<T extends { dispose: () => void }>(x: T): T { disposables.push(x); return x }

function buildScene(el: HTMLDivElement) {
  renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true })
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2))
  renderer.setClearColor(0x000000, 0)
  el.appendChild(renderer.domElement)

  const TEAL = 0x5eead4   // --accent-2 of the "Orbit Teal" theme
  const scene = new THREE.Scene()
  const camera = new THREE.PerspectiveCamera(30, 1, 0.1, 50)
  camera.position.set(0, 0, 4.0)

  const uniforms = { uTime: { value: 0 }, uScan: { value: 0 }, uColor: { value: new THREE.Color(TEAL) } }
  const holo = track(new THREE.ShaderMaterial({
    uniforms, vertexShader: HOLO_VERTEX, fragmentShader: HOLO_FRAGMENT,
    transparent: true, depthWrite: false, side: THREE.DoubleSide, blending: THREE.AdditiveBlending,
  }))
  const wire = track(new THREE.MeshBasicMaterial({ color: TEAL, wireframe: true, transparent: true, opacity: 0.05,
    depthWrite: false, blending: THREE.AdditiveBlending }))
  const additive = (color: number, opacity: number) => track(new THREE.MeshBasicMaterial({ color, transparent: true,
    opacity, depthWrite: false, blending: THREE.AdditiveBlending }))

  const body = new THREE.Group()
  scene.add(body)
  const skin = buildBody(84, holo, 80000)   // smooth translucent surface
  const mesh = buildBody(40, wire, 30000)   // coarser copy drawn as a faint wireframe
  body.add(skin, mesh)
  disposables.push(skin.geometry, mesh.geometry)

  // Glowing points scattered over the surface.
  const src = skin.geometry.getAttribute('position')
  const used = skin.geometry.drawRange.count
  const dots: number[] = []
  for (let k = 0; k < 2000; k++) {
    const i = Math.floor(Math.random() * used)
    dots.push(src.getX(i) * skin.scale.x, src.getY(i) * skin.scale.y, src.getZ(i) * skin.scale.z)
  }
  const dotGeo = track(new THREE.BufferGeometry())
  dotGeo.setAttribute('position', new THREE.Float32BufferAttribute(dots, 3))
  body.add(new THREE.Points(dotGeo, track(new THREE.PointsMaterial({ color: 0xc8fff3, size: 0.009, sizeAttenuation: true,
    transparent: true, opacity: 0.6, depthWrite: false, blending: THREE.AdditiveBlending }))))

  // Inner anatomy: brain, heart, spine.
  const sphere = track(new THREE.SphereGeometry(1, 20, 14))
  const brainMat = additive(0xc8fff3, 0.4)
  for (const side of [-1, 1]) {
    const lobe = new THREE.Mesh(sphere, brainMat)
    lobe.position.set(side * 0.027, 0.865, 0.008)
    lobe.scale.set(0.03, 0.043, 0.062)
    body.add(lobe)
  }
  const heart = new THREE.Group()
  const heartMat = additive(0xc8fff3, 0.6)
  const chambers: [number, number, number, number][] = [[-0.012, 0.012, 0, 0.02], [0.012, 0.012, 0, 0.02], [0, -0.012, 0, 0.021]]
  for (const [x, y, z, r] of chambers) {
    const c = new THREE.Mesh(sphere, heartMat)
    c.position.set(x, y, z); c.scale.setScalar(r)
    heart.add(c)
  }
  heart.position.set(0.035, 0.555, 0.03)
  heart.rotation.z = -0.35
  body.add(heart)
  const spineMat = additive(0xc8fff3, 0.32)
  const vertebra = track(new THREE.BoxGeometry(0.03, 0.013, 0.022))
  for (let i = 0; i < 24; i++) {
    const t = i / 23
    const v = new THREE.Mesh(vertebra, spineMat)
    v.position.set(0, 0.75 - t * 0.57, -0.045 + 0.018 * Math.sin(t * Math.PI * 2 - 0.6))
    v.scale.setScalar(0.8 + 0.5 * t)
    body.add(v)
  }

  // Thin ring that follows the scan beam.
  const ringPts = Array.from({ length: 73 }, (_, i) => new THREE.Vector3(Math.cos(i / 72 * Math.PI * 2) * 0.4, 0, Math.sin(i / 72 * Math.PI * 2) * 0.4))
  const scanRing = new THREE.Line(track(new THREE.BufferGeometry().setFromPoints(ringPts)),
    track(new THREE.LineBasicMaterial({ color: TEAL, transparent: true, opacity: 0.35, depthWrite: false, blending: THREE.AdditiveBlending })))
  scene.add(scanRing)

  controls = new OrbitControls(camera, renderer.domElement)
  controls.enablePan = false
  controls.enableZoom = false          // the page keeps scrolling normally over the ring
  controls.enableDamping = true
  controls.dampingFactor = 0.08
  controls.rotateSpeed = 0.8
  controls.minPolarAngle = controls.maxPolarAngle = Math.PI / 2 - 0.004   // horizontal rotation only
  controls.autoRotate = true
  controls.autoRotateSpeed = 0.9
  controls.addEventListener('start', () => { controls!.autoRotate = false; window.clearTimeout(resumeTimer) })
  controls.addEventListener('end', () => { resumeTimer = window.setTimeout(() => { if (controls) controls.autoRotate = true }, 3500) })
  renderer.domElement.style.touchAction = 'pan-y'   // vertical swipes still scroll the page on touch screens

  const resize = () => {
    const w = el.clientWidth, h = el.clientHeight
    if (!w || !h || !renderer) return
    renderer.setSize(w, h, false)
    camera.aspect = w / h
    camera.updateProjectionMatrix()
  }
  observer = new ResizeObserver(resize)
  observer.observe(el)
  resize()

  const started = performance.now()
  const beatSeconds = () => parseFloat(props.beat) || 1
  const p = new THREE.Vector3(), n = new THREE.Vector3(), toCam = new THREE.Vector3()
  const tick = () => {
    frame = requestAnimationFrame(tick)
    const t = (performance.now() - started) / 1000
    uniforms.uTime.value = t
    const scan = 0.95 - ((t * 0.3) % 1) * 1.9
    uniforms.uScan.value = scan
    scanRing.position.y = scan
    scanRing.scale.setScalar(0.5 + 0.5 * Math.sin(Math.max(0, Math.min(1, (scan + 0.95) / 1.9)) * Math.PI))
    // The inner heart beats at the astronaut's latest heart rate.
    const phase = ((t / beatSeconds()) % 1) * Math.PI * 2
    heart.scale.setScalar(1 + 0.14 * Math.max(0, Math.sin(phase)) ** 6 + 0.07 * Math.max(0, Math.sin(phase - 0.9)) ** 6)
    controls!.update()
    renderer!.render(scene, camera)

    const w = el.clientWidth, h = el.clientHeight
    props.zones.forEach((z, i) => {
      const node = spots.value[i], a = ANCHORS[z.zone]
      if (!node || !a) return
      p.set(...a.p).applyMatrix4(body.matrixWorld)
      n.set(...a.n).normalize().transformDirection(body.matrixWorld)
      const front = n.dot(toCam.copy(camera.position).sub(p).normalize())
      p.project(camera)
      node.style.transform = `translate(-50%, -50%) translate(${((p.x + 1) / 2) * w}px, ${((1 - p.y) / 2) * h}px)`
      node.classList.toggle('behind', front < 0.05)
    })
  }
  tick()
  ready.value = true
}

function hover(on: boolean) {
  if (!controls) return
  window.clearTimeout(resumeTimer)
  if (on) controls.autoRotate = false
  else resumeTimer = window.setTimeout(() => { if (controls) controls.autoRotate = true }, 1500)
}

onMounted(() => {
  if (!host.value) return
  try {
    buildScene(host.value)
  } catch (e) {
    console.warn('3D body unavailable, using the flat silhouette:', e)
    emit('unavailable')
  }
})

onBeforeUnmount(() => {
  cancelAnimationFrame(frame)
  window.clearTimeout(resumeTimer)
  observer?.disconnect()
  controls?.dispose()
  disposables.forEach((d) => d.dispose())
  renderer?.dispose()
  renderer?.domElement.remove()
})
</script>

<template>
  <div class="holo">
    <div ref="host" class="stage" :class="{ ready }" aria-hidden="true"></div>
    <button
      v-for="z in zones" :key="z.zone" ref="spots" type="button" class="spot"
      :class="{ open: z.zone === openZone, muted: !z.monitored, flagged: z.flagged, fast: z.critical, small: z.zone === 'eyes' || z.zone === 'head' || z.zone === 'brain' }"
      :style="{ '--c': z.color }" :data-zone="z.zone" :aria-label="z.aria" :aria-expanded="z.zone === openZone"
      aria-controls="body-zone-panel" @click="emit('zone', z.zone)"
      @mouseenter="hover(true)" @mouseleave="hover(false)" @focus="hover(true)" @blur="hover(false)"
    >
      <span v-if="z.flagged" class="halo"></span>
      <span class="core" :class="{ beat: z.zone === 'heart' }" :style="z.zone === 'heart' ? { animationDuration: beat } : undefined"></span>
    </button>
  </div>
</template>

<style scoped>
.holo { position: absolute; inset: 0; border-radius: 50%; overflow: hidden;
  background: radial-gradient(circle at 50% 50%, rgba(94, 234, 212, 0.10), transparent 68%); }
.stage { position: absolute; inset: 0; opacity: 0; transition: opacity .8s ease; cursor: grab; }
.stage.ready { opacity: 1; }
.stage:active { cursor: grabbing; }
.stage :deep(canvas) { width: 100%; height: 100%; display: block; }

.spot { --c: #2dd4bf; position: absolute; left: 0; top: 0; width: 30px; height: 30px; padding: 0; border: 0; border-radius: 50%;
  background: none; cursor: pointer; will-change: transform; transition: opacity .25s; }
.spot.small { width: 18px; height: 18px; }
.spot.behind { opacity: .25; }
.spot:hover, .spot:focus-visible { opacity: 1; z-index: 2; }
.core { position: absolute; inset: 9px; border-radius: 50%; background: var(--c);
  box-shadow: 0 0 8px 1px var(--c), 0 0 0 2px rgba(8, 19, 22, .85); }
.small .core { inset: 5px; }
.muted .core { box-shadow: 0 0 0 2px rgba(8, 19, 22, .85); }
.spot:hover .core, .spot:focus-visible .core { filter: brightness(1.3); }
.spot.open { outline: 2px solid var(--accent-2); outline-offset: 1px; }
.halo { position: absolute; inset: 3px; border-radius: 50%; border: 2px solid var(--c); pointer-events: none;
  animation: halo 2s ease-out infinite; }
.small .halo { inset: 0; }
.fast .halo { animation-duration: 1s; }
.beat { animation: beat 1s ease-in-out infinite; }
@keyframes beat { 0%, 100% { transform: scale(1); } 15% { transform: scale(1.25); } 30% { transform: scale(1); } 45% { transform: scale(1.12); } }
@keyframes halo { 0% { transform: scale(.6); opacity: .8; } 100% { transform: scale(1.7); opacity: 0; } }
@media (prefers-reduced-motion: reduce) { .halo, .beat { animation: none; } }
</style>

<script setup lang="ts">
/**
 * Rotating holographic body (Three.js). Hotspots are anchored to 3D points on
 * the mesh and re-projected to the screen every frame, so they turn with the body.
 */
import * as THREE from 'three'
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js'
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'
import type { Level } from '../types'
import { buildBody } from './body/humanoid'

export interface BodyZone {
  key: string
  label: string      // e.g. "Brain · Sleep"
  level: Level
  summary: string    // e.g. "5.1 h"
}

const props = defineProps<{ zones: BodyZone[]; selected: string | null }>()
const emit = defineEmits<{ select: [key: string] }>()

// Where each hotspot sits on the body, and which way the surface faces there.
const ANCHORS: Record<string, { p: [number, number, number]; n: [number, number, number] }> = {
  brain: { p: [0, 0.875, 0.088], n: [0, 0.25, 1] },
  heart: { p: [0.045, 0.56, 0.104], n: [0.1, 0, 1] },
  torso: { p: [0, 0.37, 0.094], n: [0, 0, 1] },
  forearm: { p: [0.46, 0.405, 0.04], n: [0, 0.25, 1] },
}
const LEVEL_COLOR: Record<Level, number> = { normal: 0x3ccf7a, attention: 0xf5b942, critical: 0xff5a5f, no_data: 0x6b7a90 }
const LEVEL_WORD: Record<Level, string> = { normal: 'Nominal', attention: 'Attention', critical: 'Critical', no_data: 'No data' }
const LEVEL_SHAPE: Record<Level, string> = { normal: '●', attention: '▲', critical: '■', no_data: '○' }

const host = ref<HTMLDivElement>()
const spots = ref<HTMLButtonElement[]>([])
const failed = ref(false)
const ready = ref(false)

let renderer: THREE.WebGLRenderer | undefined
let controls: OrbitControls | undefined
let observer: ResizeObserver | undefined
let frame = 0
let resumeTimer: number | undefined
const organMaterials: Record<string, THREE.MeshBasicMaterial> = {}
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
    float alpha = 0.03 + fresnel * 0.85 + lines * 0.02 + beam * 0.5;
    vec3 color = uColor * (0.55 + fresnel * 0.9) + vec3(0.6, 1.0, 1.0) * beam * 0.6;
    gl_FragColor = vec4(color, alpha);
  }`

function track<T extends { dispose: () => void }>(x: T): T { disposables.push(x); return x }

function buildScene(el: HTMLDivElement) {
  renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true })
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2))
  renderer.setClearColor(0x000000, 0)
  el.appendChild(renderer.domElement)

  const scene = new THREE.Scene()
  const camera = new THREE.PerspectiveCamera(30, 1, 0.1, 50)
  camera.position.set(0, 0.02, 4.6)

  const uniforms = { uTime: { value: 0 }, uScan: { value: 0 }, uColor: { value: new THREE.Color(0x37e6ff) } }
  const holo = track(new THREE.ShaderMaterial({
    uniforms, vertexShader: HOLO_VERTEX, fragmentShader: HOLO_FRAGMENT,
    transparent: true, depthWrite: false, side: THREE.DoubleSide, blending: THREE.AdditiveBlending,
  }))
  const wire = track(new THREE.MeshBasicMaterial({
    color: 0x37e6ff, wireframe: true, transparent: true, opacity: 0.045,
    depthWrite: false, blending: THREE.AdditiveBlending,
  }))

  const body = new THREE.Group()
  scene.add(body)
  const skin = buildBody(96, holo, 90000)        // smooth translucent surface
  const mesh = buildBody(44, wire, 40000)        // coarser copy drawn as a subtle wireframe
  body.add(skin, mesh)
  disposables.push(skin.geometry, mesh.geometry)

  // --- Particle shell: glowing points scattered over the surface ---------
  const src = skin.geometry.getAttribute('position')
  const used = skin.geometry.drawRange.count
  const dots: number[] = []
  for (let k = 0; k < 4200; k++) {
    const i = Math.floor(Math.random() * used)   // random pick: no visible grid pattern
    dots.push(src.getX(i) * skin.scale.x, src.getY(i) * skin.scale.y, src.getZ(i) * skin.scale.z)
  }
  const dotGeo = track(new THREE.BufferGeometry())
  dotGeo.setAttribute('position', new THREE.Float32BufferAttribute(dots, 3))
  body.add(new THREE.Points(dotGeo, track(new THREE.PointsMaterial({ color: 0xa8f6ff, size: 0.007, sizeAttenuation: true,
    transparent: true, opacity: 0.6, depthWrite: false, blending: THREE.AdditiveBlending }))))

  // --- Vessel-like strands running from the heart to head, hands and feet -
  const strandMat = track(new THREE.LineBasicMaterial({ color: 0x7fefff, transparent: true, opacity: 0.3,
    depthWrite: false, blending: THREE.AdditiveBlending }))
  const routes: [number, number, number][][] = [
    [[0.03, 0.56, 0.02], [0.02, 0.66, 0.0], [0.0, 0.75, 0.0], [0.0, 0.86, 0.0]],
    [[0.03, 0.56, 0.02], [0.12, 0.61, 0.0], [0.21, 0.6, 0.0], [0.38, 0.47, 0.0], [0.54, 0.335, 0.01], [0.59, 0.3, 0.02]],
    [[0.03, 0.56, 0.02], [0.05, 0.4, 0.01], [0.095, 0.18, 0.0], [0.108, -0.33, 0.01], [0.11, -0.85, 0.0], [0.116, -0.92, 0.08]],
  ]
  for (const route of routes) for (const side of route === routes[0] ? [1] : [-1, 1]) for (let k = 0; k < 3; k++) {
    const pts = route.map(([x, y, z], i) => new THREE.Vector3(
      side * x + (i ? Math.sin(i * 2.1 + k * 2) * 0.012 : 0), y, z + (i ? Math.cos(i * 1.7 + k * 2.4) * 0.012 : 0)))
    const curve = new THREE.CatmullRomCurve3(pts)
    body.add(new THREE.Line(track(new THREE.BufferGeometry().setFromPoints(curve.getPoints(60))), strandMat))
  }

  // --- Inner anatomy: brain, heart, spine -------------------------------
  const organ = (key: string, opacity: number) => {
    const m = track(new THREE.MeshBasicMaterial({ color: 0x9ff3ff, transparent: true, opacity,
      depthWrite: false, blending: THREE.AdditiveBlending }))
    organMaterials[key] = m
    return m
  }
  const sphere = track(new THREE.SphereGeometry(1, 24, 16))
  const brainMat = organ('brain', 0.42)
  for (const side of [-1, 1]) {
    const lobe = new THREE.Mesh(sphere, brainMat)
    lobe.position.set(side * 0.027, 0.865, 0.008)
    lobe.scale.set(0.03, 0.043, 0.062)
    body.add(lobe)
  }
  const brainWire = new THREE.Mesh(track(new THREE.IcosahedronGeometry(1, 2)),
    track(new THREE.MeshBasicMaterial({ color: 0xffffff, wireframe: true, transparent: true, opacity: 0.16,
      depthWrite: false, blending: THREE.AdditiveBlending })))
  brainWire.position.set(0, 0.865, 0.008)
  brainWire.scale.set(0.058, 0.046, 0.066)
  body.add(brainWire)

  const heart = new THREE.Group()
  const heartMat = organ('heart', 0.6)
  const chambers: [number, number, number, number][] = [[-0.012, 0.012, 0, 0.02], [0.012, 0.012, 0, 0.02], [0, -0.012, 0, 0.021]]
  for (const [x, y, z, r] of chambers) {
    const c = new THREE.Mesh(sphere, heartMat)
    c.position.set(x, y, z); c.scale.setScalar(r)
    heart.add(c)
  }
  heart.position.set(0.035, 0.555, 0.03)
  heart.rotation.z = -0.35
  body.add(heart)

  const spineMat = organ('spine', 0.34)
  const vertebra = track(new THREE.BoxGeometry(0.03, 0.013, 0.022))
  for (let i = 0; i < 24; i++) {
    const t = i / 23
    const v = new THREE.Mesh(vertebra, spineMat)
    v.position.set(0, 0.75 - t * 0.57, -0.045 + 0.018 * Math.sin(t * Math.PI * 2 - 0.6))
    v.scale.setScalar(0.8 + 0.5 * t)
    body.add(v)
  }
  const torsoGlow = new THREE.Mesh(sphere, organ('torso', 0.12))
  torsoGlow.position.set(0, 0.37, 0.01); torsoGlow.scale.set(0.085, 0.09, 0.055)
  body.add(torsoGlow)
  const armGlow = new THREE.Mesh(sphere, organ('forearm', 0.2))
  armGlow.position.set(0.46, 0.4, 0.005); armGlow.scale.set(0.022, 0.095, 0.022); armGlow.rotation.z = 0.87
  body.add(armGlow)

  // --- Projector base and scan ring -------------------------------------
  const lineMat = track(new THREE.LineBasicMaterial({ color: 0x37e6ff, transparent: true, opacity: 0.35,
    depthWrite: false, blending: THREE.AdditiveBlending }))
  const circle = (r: number) => {
    const pts = Array.from({ length: 97 }, (_, i) => new THREE.Vector3(Math.cos(i / 96 * Math.PI * 2) * r, 0, Math.sin(i / 96 * Math.PI * 2) * r))
    return new THREE.Line(track(new THREE.BufferGeometry().setFromPoints(pts)), lineMat)
  }
  for (const r of [0.2, 0.36, 0.52]) { const c = circle(r); c.position.y = -0.965; scene.add(c) }
  const scanRing = circle(0.4)
  scene.add(scanRing)

  controls = new OrbitControls(camera, renderer.domElement)
  controls.target.set(0, 0, 0)
  controls.enablePan = false
  controls.enableZoom = false
  controls.enableDamping = true
  controls.dampingFactor = 0.08
  controls.rotateSpeed = 0.7
  controls.minPolarAngle = controls.maxPolarAngle = Math.PI / 2 - 0.004   // horizontal rotation only
  controls.autoRotate = true
  controls.autoRotateSpeed = 0.9
  controls.addEventListener('start', () => { controls!.autoRotate = false; window.clearTimeout(resumeTimer) })
  controls.addEventListener('end', () => { resumeTimer = window.setTimeout(() => { if (controls) controls.autoRotate = true }, 3500) })

  const resize = () => {
    const w = el.clientWidth, h = el.clientHeight
    if (!w || !h || !renderer) return
    renderer.setSize(w, h, false)
    camera.aspect = w / h
    // Keep the whole figure in view whatever the panel shape.
    camera.fov = w / h < 0.72 ? 30 * (0.72 / (w / h)) : 30
    camera.updateProjectionMatrix()
  }
  observer = new ResizeObserver(resize)
  observer.observe(el)
  resize()

  const started = performance.now()
  const p = new THREE.Vector3(), n = new THREE.Vector3(), toCam = new THREE.Vector3()
  const tick = () => {
    frame = requestAnimationFrame(tick)
    const t = (performance.now() - started) / 1000
    uniforms.uTime.value = t
    const scan = 0.95 - ((t * 0.32) % 1) * 1.9   // top to bottom, then restart
    uniforms.uScan.value = scan
    scanRing.position.y = scan
    scanRing.scale.setScalar(0.55 + 0.45 * Math.sin(Math.max(0, Math.min(1, (scan + 0.95) / 1.9)) * Math.PI))
    heart.scale.setScalar(1 + 0.12 * Math.max(0, Math.sin(t * 6.3)) ** 6 + 0.06 * Math.max(0, Math.sin(t * 6.3 - 0.9)) ** 6)
    controls!.update()
    renderer!.render(scene, camera)

    // Re-project every hotspot from its 3D anchor to screen pixels.
    const w = el.clientWidth, h = el.clientHeight
    props.zones.forEach((z, i) => {
      const node = spots.value[i], a = ANCHORS[z.key]
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

function tintOrgans() {
  for (const z of props.zones) {
    const m = organMaterials[z.key]
    if (m) m.color.setHex(z.level === 'normal' || z.level === 'no_data' ? 0x9ff3ff : LEVEL_COLOR[z.level])
  }
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
    tintOrgans()
  } catch (e) {
    console.warn('3D view unavailable:', e)
    failed.value = true
  }
})
watch(() => props.zones, tintOrgans, { deep: true })

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
    <div ref="host" class="stage" :class="{ ready }"></div>

    <template v-if="!failed">
      <button
        v-for="z in zones" :key="z.key" ref="spots" type="button"
        class="spot" :class="[z.level, { selected: z.key === selected }]"
        :aria-label="`${z.label}: ${LEVEL_WORD[z.level]}, ${z.summary}`"
        @click="emit('select', z.key)" @mouseenter="hover(true)" @mouseleave="hover(false)"
        @focus="hover(true)" @blur="hover(false)"
      >
        <span class="halo"></span><span class="halo late"></span><span class="core"></span>
        <span class="tip">
          <b>{{ z.label }}</b>
          <span><i aria-hidden="true">{{ LEVEL_SHAPE[z.level] }}</i> {{ LEVEL_WORD[z.level] }} · {{ z.summary }}</span>
        </span>
      </button>
      <p class="hint">Drag to rotate</p>
    </template>

    <!-- If WebGL is not available the zones stay reachable as plain buttons. -->
    <div v-else class="fallback">
      <p>3D view unavailable on this device.</p>
      <button v-for="z in zones" :key="z.key" type="button" :class="[z.level, { selected: z.key === selected }]"
        @click="emit('select', z.key)">
        <i aria-hidden="true">{{ LEVEL_SHAPE[z.level] }}</i> {{ z.label }} · {{ z.summary }}
      </button>
    </div>
  </div>
</template>

<style scoped>
.holo { position: relative; width: 100%; height: 100%; overflow: hidden;
  background: radial-gradient(ellipse 60% 55% at 50% 52%, rgba(55, 230, 255, 0.10), transparent 70%); }
.stage { position: absolute; inset: 0; opacity: 0; transition: opacity .8s ease; cursor: grab; }
.stage.ready { opacity: 1; }
.stage:active { cursor: grabbing; }
.stage :deep(canvas) { width: 100%; height: 100%; display: block; }

.spot { --c: var(--ok); position: absolute; left: 0; top: 0; width: 34px; height: 34px; padding: 0; border: 0;
  background: none; cursor: pointer; will-change: transform; transition: opacity .25s; }
.spot.attention { --c: var(--warn); }
.spot.critical { --c: var(--crit); }
.spot.no_data { --c: var(--muted); }
.spot.behind { opacity: .28; }
.core { position: absolute; inset: 11px; border-radius: 50%; background: var(--c);
  box-shadow: 0 0 10px 2px var(--c), 0 0 0 2px rgba(6, 9, 17, .8); }
.halo { position: absolute; inset: 4px; border-radius: 50%; border: 2px solid var(--c); opacity: 0;
  animation: pulse 2.2s ease-out infinite; }
.halo.late { animation-delay: 1.1s; }
.spot.critical .halo { animation-duration: 1.1s; }
.spot.selected .core { inset: 8px; box-shadow: 0 0 16px 5px var(--c), 0 0 0 2px #fff; }
@keyframes pulse { 0% { transform: scale(.45); opacity: .95; } 100% { transform: scale(1.75); opacity: 0; } }
@media (prefers-reduced-motion: reduce) { .halo { animation: none; opacity: .5; } }

.tip { position: absolute; left: 42px; top: 50%; transform: translateY(-50%); display: none; flex-direction: column;
  gap: 2px; white-space: nowrap; text-align: left; padding: 7px 11px; border-radius: 8px; font-size: 13px;
  color: var(--text); background: rgba(8, 14, 26, .94); border: 1px solid var(--c); pointer-events: none; z-index: 3; }
.tip b { font-size: 13px; }
.tip span { color: var(--c); font-size: 12px; }
.tip i { font-style: normal; }
.spot:hover .tip, .spot:focus-visible .tip { display: flex; }
.spot:hover, .spot:focus-visible { z-index: 4; opacity: 1; }
.spot:focus-visible { outline: 2px solid #fff; outline-offset: 2px; border-radius: 50%; }

.hint { position: absolute; left: 0; right: 0; bottom: 6px; margin: 0; text-align: center; font-size: 12px;
  letter-spacing: .08em; text-transform: uppercase; color: var(--muted); pointer-events: none; }
.fallback { position: absolute; inset: 0; display: flex; flex-direction: column; gap: 10px; align-items: center; justify-content: center; }
.fallback p { color: var(--muted); }
.fallback button { --c: var(--ok); font: inherit; padding: 10px 16px; min-width: 260px; text-align: left; border-radius: 10px;
  background: var(--panel); color: var(--text); border: 1px solid var(--c); cursor: pointer; }
.fallback button.attention { --c: var(--warn); } .fallback button.critical { --c: var(--crit); }
.fallback button.selected { outline: 2px solid #fff; }
.fallback i { font-style: normal; color: var(--c); }
</style>

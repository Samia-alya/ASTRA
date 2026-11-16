<script setup lang="ts">
/**
 * "Vital ring": one arc per indicator around a rotating holographic body (HoloBody, Three.js).
 * If WebGL is unavailable the flat silhouette is drawn instead.
 * - Arc colour = indicator level; the selected arc is thicker.
 * - Body dots = worst level of each body zone (indicator.body_zone).
 * - The heart dot beats at the latest heart rate; flagged zones glow.
 * Clicking an arc or its label selects an indicator; clicking a body part opens its info panel
 * (emits `zone`). Eyes and bones are shown for information only (not monitored).
 */
import { computed, ref } from 'vue'
import { BODY_ZONES } from '../bodyZones'
import HoloBody from './HoloBody.vue'
import type { IndicatorMeta, IndicatorStatus } from '../types'
import { LEVEL_COLOR, LEVEL_LABEL, LEVEL_ORDER } from '../types'

const props = defineProps<{
  indicators: IndicatorStatus[]
  meta: Record<string, IndicatorMeta>
  selected: string | null
  /** Body zone whose panel is open, if any. */
  openZone?: string | null
}>()
const emit = defineEmits<{ select: [indicator: string]; zone: [zone: string] }>()
const box = ref<HTMLDivElement | null>(null)
/** false when WebGL is not available: the flat SVG silhouette is used instead. */
const holo = ref(true)

const C = 300 // centre of the 600x600 viewBox
const R = 250 // ring radius
const GAP = 4 // degrees between arcs

function point(r: number, deg: number) {
  const a = ((deg - 90) * Math.PI) / 180
  return { x: C + r * Math.cos(a), y: C + r * Math.sin(a) }
}

const arcs = computed(() => {
  const n = props.indicators.length || 1
  const step = 360 / n
  return props.indicators.map((s, i) => {
    const start = i * step + GAP
    const end = (i + 1) * step - GAP
    const p1 = point(R, start)
    const p2 = point(R, end)
    const label = point(R + 24, (start + end) / 2)
    const large = end - start > 180 ? 1 : 0
    return {
      key: s.indicator,
      d: `M${p1.x.toFixed(1)} ${p1.y.toFixed(1)} A${R} ${R} 0 ${large} 1 ${p2.x.toFixed(1)} ${p2.y.toFixed(1)}`,
      color: LEVEL_COLOR[s.level],
      width: s.indicator === props.selected ? 22 : 10,
      lx: label.x,
      anchor: label.x > C + 30 ? 'start' : label.x < C - 30 ? 'end' : 'middle',
      ly: label.y + 5,
      text: props.meta[s.indicator]?.short ?? s.label,
      aria: `${s.label}: ${s.value ?? 'no data'} ${s.unit}, ${s.level}`,
    }
  })
})

// Body zones on the silhouette (silhouette coordinates, see <g transform>).
// `hit` is the clickable area, as large as the neighbouring zones allow.
type Hit = { kind: 'circle'; x: number; y: number; r: number } | { kind: 'rect'; x: number; y: number; w: number; h: number }
const ZONE_SHAPES: Record<string, { mark: 'dot' | 'eyes' | 'legs'; x: number; y: number; r: number; hit: Hit }> = {
  bones: { mark: 'legs', x: 0, y: 0, r: 0, hit: { kind: 'rect', x: 72, y: 296, w: 116, h: 160 } },
  abdomen: { mark: 'dot', x: 130, y: 196, r: 10, hit: { kind: 'circle', x: 130, y: 196, r: 30 } },
  heart: { mark: 'dot', x: 146, y: 126, r: 11, hit: { kind: 'circle', x: 146, y: 126, r: 30 } },
  // Drawn before the eyes: where the two hit areas overlap, the eyes (on top) win.
  head: { mark: 'dot', x: 130, y: 57, r: 7, hit: { kind: 'circle', x: 130, y: 57, r: 16 } },
  eyes: { mark: 'eyes', x: 130, y: 39, r: 0, hit: { kind: 'rect', x: 104, y: 32, w: 52, h: 14 } },
  brain: { mark: 'dot', x: 130, y: 17, r: 11, hit: { kind: 'circle', x: 130, y: 17, r: 16 } },
}
const UNMONITORED = '#6f8f8b' // muted grey-teal, readable against the silhouette

const zones = computed(() =>
  Object.entries(ZONE_SHAPES).map(([zone, shape]) => {
    const info = BODY_ZONES[zone]!
    const list = props.indicators.filter((i) => i.body_zone === zone)
    const worst = [...list].sort((a, b) => LEVEL_ORDER[a.level] - LEVEL_ORDER[b.level])[0]
    const monitored = info.monitored && !!worst
    return {
      zone,
      ...shape,
      monitored,
      color: monitored ? LEVEL_COLOR[worst!.level] : UNMONITORED,
      flagged: monitored && (worst!.level === 'attention' || worst!.level === 'critical'),
      critical: monitored && worst!.level === 'critical',
      aria: `${info.name}: ${monitored ? LEVEL_LABEL[worst!.level] : 'not monitored in this prototype'}`,
    }
  }),
)

/** Give keyboard focus back to a body zone (used when its panel closes). */
function focusZone(zone: string) {
  box.value?.querySelector<HTMLElement | SVGGElement>(`[data-zone="${zone}"]`)?.focus()
}
defineExpose({ focusZone })

const beat = computed(() => {
  const hr = props.indicators.find((i) => i.indicator === 'heart_rate')?.value
  return `${(60 / (hr && hr > 20 ? hr : 60)).toFixed(2)}s`
})

function onKey(e: KeyboardEvent, action: () => void) {
  if (e.key === 'Enter' || e.key === ' ') {
    e.preventDefault()
    action()
  }
}
</script>

<template>
  <div ref="box" class="ring-box">
  <svg viewBox="-90 -40 780 680" class="ring" role="group" aria-label="Vital ring">
    <circle :cx="C" :cy="C" :r="R + 56" fill="none" stroke="var(--track)" stroke-width="2" stroke-dasharray="2 8"
      stroke-linecap="round" class="orbit" />
    <circle :cx="C" :cy="C" :r="R" fill="none" stroke="var(--track)" stroke-width="12" />

    <g v-for="a in arcs" :key="a.key" class="arc" role="button" tabindex="0" :aria-label="a.aria"
      @click="emit('select', a.key)" @keydown="onKey($event, () => emit('select', a.key))">
      <path :d="a.d" fill="none" stroke="transparent" stroke-width="40" />
      <path :d="a.d" fill="none" :stroke="a.color" :stroke-width="a.width" stroke-linecap="round" class="arc-line" />
      <text :x="a.lx" :y="a.ly" :text-anchor="a.anchor" class="arc-label">{{ a.text }}</text>
    </g>

    <g v-if="!holo" transform="translate(205 120) scale(0.73)">
      <ellipse cx="130" cy="38" rx="28" ry="34" fill="#143036" class="deco" />
      <path fill="#143036" class="deco"
        d="M116 70 L144 70 L146 84 Q188 88 198 106 L214 232 Q216 244 206 246 L200 246 L184 130 L180 218 L186 276 L178 460 L154 460 L140 290 L120 290 L106 460 L82 460 L74 276 L80 218 L76 130 L60 246 L54 246 Q44 244 46 232 L62 106 Q72 88 114 84 Z" />
      <g v-for="z in zones" :key="z.zone" class="zone" :class="{ open: z.zone === openZone, muted: !z.monitored }"
        role="button" tabindex="0" :data-zone="z.zone" :aria-label="z.aria" :aria-expanded="z.zone === openZone"
        aria-controls="body-zone-panel" @click="emit('zone', z.zone)" @keydown="onKey($event, () => emit('zone', z.zone))">
        <!-- Clickable area; outlined on hover, focus and while its panel is open. -->
        <circle v-if="z.hit.kind === 'circle'" :cx="z.hit.x" :cy="z.hit.y" :r="z.hit.r" class="hit" />
        <rect v-else :x="z.hit.x" :y="z.hit.y" :width="z.hit.w" :height="z.hit.h" rx="10" class="hit" />

        <template v-if="z.mark === 'dot'">
          <circle v-if="z.flagged" :cx="z.x" :cy="z.y" :r="z.r * 2" fill="none" :stroke="z.color" stroke-width="2"
            class="halo" :class="{ fast: z.critical }" />
          <circle :cx="z.x" :cy="z.y" :r="z.r" :fill="z.color" class="mark" :class="{ beat: z.zone === 'heart' }"
            :style="z.zone === 'heart' ? { animationDuration: beat } : undefined" />
        </template>
        <g v-else-if="z.mark === 'eyes'" class="mark" :fill="z.color">
          <ellipse cx="119" cy="39" rx="5" ry="3" />
          <ellipse cx="141" cy="39" rx="5" ry="3" />
        </g>
        <g v-else class="mark" :stroke="z.color" stroke-width="7" stroke-linecap="round">
          <line x1="94" y1="318" x2="94" y2="432" />
          <line x1="166" y1="318" x2="166" y2="432" />
        </g>
      </g>
    </g>
  </svg>
  <!-- 3D body, centred in the ring (same place as the silhouette). Sized in viewBox units: a circle of
       radius 222 around the centre (300, 300), just inside the arcs. -->
  <div v-if="holo" class="body3d">
    <HoloBody :zones="zones" :open-zone="openZone" :beat="beat" @zone="emit('zone', $event)" @unavailable="holo = false" />
  </div>
  </div>
</template>

<style scoped>
.ring-box { position: relative; width: 100%; max-width: 580px; margin: 0 auto; }
.ring { width: 100%; height: auto; display: block; }
/* viewBox is 780 x 680 starting at (-90, -40): circle r=222 at (300, 300) -> percentages below. */
.body3d { position: absolute; left: 21.54%; top: 17.35%; width: 56.92%; height: 65.29%; }
.arc, .zone { cursor: pointer; outline: none; }
.arc-line { transition: stroke-width .25s ease, stroke .3s; }
.arc:hover .arc-line, .arc:focus-visible .arc-line { filter: brightness(1.25); }
.arc:focus-visible .arc-label, .arc:hover .arc-label { fill: var(--text); }
.arc-label { font-family: 'Inter', sans-serif; font-size: 16px; fill: var(--muted); transition: fill .2s; }
/* Only the transparent .hit shape of each zone takes clicks. Decorative shapes (silhouette, animated
   halos, dots, eye/leg marks) let them through, so an expanding halo never steals a neighbour's click. */
.deco, .halo, .mark { pointer-events: none; }
.zone { pointer-events: all; }
.hit { fill: transparent; stroke: transparent; stroke-width: 4; transition: stroke .2s; pointer-events: all; }
.zone:hover .hit { stroke: var(--border-strong); }
.zone:focus-visible .hit, .zone.open .hit { stroke: var(--accent-2); }
.zone:hover .mark, .zone:focus-visible .mark { filter: brightness(1.3); }

.beat { transform-box: fill-box; transform-origin: center; animation: beat 1s ease-in-out infinite; }
@keyframes beat { 0%, 100% { transform: scale(1); } 15% { transform: scale(1.25); } 30% { transform: scale(1); } 45% { transform: scale(1.12); } }

.halo { transform-box: fill-box; transform-origin: center; animation: halo 2s ease-out infinite; }
.halo.fast { animation-duration: 1s; }
@keyframes halo { 0% { transform: scale(.6); opacity: .8; } 100% { transform: scale(1.2); opacity: 0; } }
</style>

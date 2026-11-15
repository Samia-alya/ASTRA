<script setup lang="ts">
/**
 * "Vital ring": one arc per indicator around a body silhouette.
 * - Arc colour = indicator level; the selected arc is thicker.
 * - Body dots = worst level of each body zone (indicator.body_zone).
 * - The heart dot beats at the latest heart rate; flagged zones glow.
 * Clicking an arc, a label or a body zone selects an indicator.
 */
import { computed } from 'vue'
import type { IndicatorMeta, IndicatorStatus } from '../types'
import { LEVEL_COLOR, LEVEL_ORDER } from '../types'

const props = defineProps<{
  indicators: IndicatorStatus[]
  meta: Record<string, IndicatorMeta>
  selected: string | null
}>()
const emit = defineEmits<{ select: [indicator: string] }>()

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

// Body zones -> position on the silhouette (silhouette coordinates, see <g transform>).
const ZONE_POS: Record<string, { x: number; y: number; r: number; name: string }> = {
  brain: { x: 130, y: 22, r: 13, name: 'Brain: sleep and mood' },
  head: { x: 130, y: 54, r: 7, name: 'Body temperature' },
  heart: { x: 146, y: 126, r: 11, name: 'Heart and blood pressure' },
  abdomen: { x: 130, y: 196, r: 10, name: 'Metabolism: glucose' },
}

const zones = computed(() =>
  Object.entries(ZONE_POS).map(([zone, pos]) => {
    const list = props.indicators.filter((i) => i.body_zone === zone)
    const worst = [...list].sort((a, b) => LEVEL_ORDER[a.level] - LEVEL_ORDER[b.level])[0]
    return {
      zone,
      ...pos,
      worst,
      color: worst ? LEVEL_COLOR[worst.level] : LEVEL_COLOR.no_data,
      flagged: worst ? worst.level === 'attention' || worst.level === 'critical' : false,
      critical: worst?.level === 'critical',
    }
  }),
)

const beat = computed(() => {
  const hr = props.indicators.find((i) => i.indicator === 'heart_rate')?.value
  return `${(60 / (hr && hr > 20 ? hr : 60)).toFixed(2)}s`
})

function onKey(e: KeyboardEvent, key?: string) {
  if (key && (e.key === 'Enter' || e.key === ' ')) {
    e.preventDefault()
    emit('select', key)
  }
}
</script>

<template>
  <svg viewBox="-90 -40 780 680" class="ring" role="group" aria-label="Vital ring">
    <circle :cx="C" :cy="C" :r="R + 56" fill="none" stroke="var(--track)" stroke-width="2" stroke-dasharray="2 8"
      stroke-linecap="round" class="orbit" />
    <circle :cx="C" :cy="C" :r="R" fill="none" stroke="var(--track)" stroke-width="12" />

    <g v-for="a in arcs" :key="a.key" class="arc" role="button" tabindex="0" :aria-label="a.aria"
      @click="emit('select', a.key)" @keydown="onKey($event, a.key)">
      <path :d="a.d" fill="none" stroke="transparent" stroke-width="40" />
      <path :d="a.d" fill="none" :stroke="a.color" :stroke-width="a.width" stroke-linecap="round" class="arc-line" />
      <text :x="a.lx" :y="a.ly" :text-anchor="a.anchor" class="arc-label">{{ a.text }}</text>
    </g>

    <g transform="translate(205 120) scale(0.73)">
      <ellipse cx="130" cy="38" rx="28" ry="34" fill="#143036" />
      <path fill="#143036"
        d="M116 70 L144 70 L146 84 Q188 88 198 106 L214 232 Q216 244 206 246 L200 246 L184 130 L180 218 L186 276 L178 460 L154 460 L140 290 L120 290 L106 460 L82 460 L74 276 L80 218 L76 130 L60 246 L54 246 Q44 244 46 232 L62 106 Q72 88 114 84 Z" />
      <g v-for="z in zones" :key="z.zone" class="zone" role="button" tabindex="0" :aria-label="z.name"
        @click="z.worst && emit('select', z.worst.indicator)" @keydown="onKey($event, z.worst?.indicator)">
        <circle v-if="z.flagged" :cx="z.x" :cy="z.y" :r="z.r * 2" fill="none" :stroke="z.color" stroke-width="2"
          class="halo" :class="{ fast: z.critical }" />
        <circle :cx="z.x" :cy="z.y" :r="z.r" :fill="z.color" :class="{ beat: z.zone === 'heart' }"
          :style="z.zone === 'heart' ? { animationDuration: beat } : undefined" />
      </g>
    </g>
  </svg>
</template>

<style scoped>
.ring { width: 100%; max-width: 580px; height: auto; display: block; margin: 0 auto; }
.arc, .zone { cursor: pointer; outline: none; }
.arc-line { transition: stroke-width .25s ease, stroke .3s; }
.arc:hover .arc-line, .arc:focus-visible .arc-line { filter: brightness(1.25); }
.arc:focus-visible .arc-label, .arc:hover .arc-label { fill: var(--text); }
.arc-label { font-family: 'Inter', sans-serif; font-size: 16px; fill: var(--muted); transition: fill .2s; }
.zone:hover circle, .zone:focus-visible circle { filter: brightness(1.3); }

.beat { transform-box: fill-box; transform-origin: center; animation: beat 1s ease-in-out infinite; }
@keyframes beat { 0%, 100% { transform: scale(1); } 15% { transform: scale(1.25); } 30% { transform: scale(1); } 45% { transform: scale(1.12); } }

.halo { transform-box: fill-box; transform-origin: center; animation: halo 2s ease-out infinite; }
.halo.fast { animation-duration: 1s; }
@keyframes halo { 0% { transform: scale(.6); opacity: .8; } 100% { transform: scale(1.2); opacity: 0; } }
</style>

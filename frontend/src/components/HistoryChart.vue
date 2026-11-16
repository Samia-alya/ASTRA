<script setup lang="ts">
import Plotly from 'plotly.js-dist-min'
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import { dailyMeans, inPeriod, missionDayAt, periodWindow, rollingMean } from '../stats'
import { parseUtc } from '../time'
import type { Measurement } from '../types'
import { fmt } from '../types'

const props = defineProps<{
  data: Measurement[]
  label: string
  unit: string
  baseline: number | null
  color: string
  /** Length of the displayed period, ending at the latest measurement (ignored in mission view). */
  days: number
  /** Set = whole-mission view: x-axis in mission days, the latest measurement being on this day. */
  missionDay?: number | null
}>()
const el = ref<HTMLDivElement>()
const HALF_DAY = 12 * 60 * 60 * 1000

// One marker shape per data source, so device and manual points stand out from the simulated history.
type Source = Measurement['source']
const MARKERS: Record<Source, { symbol: 'circle' | 'diamond' | 'square'; size: number; label: string }> = {
  simulated: { symbol: 'circle', size: 6, label: 'Simulated' },
  manual: { symbol: 'diamond', size: 11, label: 'Manual entry' },
  device: { symbol: 'square', size: 8, label: 'Device (simulated)' },
}
const ORDER: Source[] = ['simulated', 'manual', 'device']

const mission = computed(() => !!props.missionDay)
const shownData = computed(() => (mission.value ? props.data : inPeriod(props.data, props.days)))
const present = computed(() => ORDER.filter((src) => shownData.value.some((m) => m.source === src)))

const LAYOUT_BASE = {
  paper_bgcolor: 'transparent', plot_bgcolor: 'transparent',
  font: { color: '#9fb8b5', family: 'Inter, sans-serif', size: 12 },
  margin: { t: 10, r: 10, b: 30, l: 40 }, showlegend: false,
  yaxis: { gridcolor: '#16292d', zeroline: false },
  hoverlabel: { bgcolor: '#123036', bordercolor: '#1a3338', font: { color: '#e6f4f1' } },
}

/** Whole mission: daily values drawn lightly, 7-day rolling average on top, x-axis in mission days. */
function drawMission(missionDay: number) {
  const data = shownData.value
  const latest = data.length ? Math.max(...data.map((m) => parseUtc(m.timestamp))) : 0
  const dayOf = (m: Measurement) => missionDayAt(m.timestamp, latest, missionDay)
  const label = (day: number, v: number) => `Day ${Math.max(1, Math.round(day))} · ${fmt(v, props.unit)} ${props.unit}`
  const traces: Partial<Plotly.Data>[] = []
  const daily = dailyMeans(data, missionDay)
  traces.push({
    x: daily.map((d) => d.day), y: daily.map((d) => d.value), type: 'scatter', mode: 'lines', name: 'Daily',
    line: { color: props.color, width: 1 }, opacity: 0.25, hoverinfo: 'skip',
  })
  for (const src of ORDER) {
    const pts = data.filter((m) => m.source === src)
    if (!pts.length) continue
    const mk = MARKERS[src]
    traces.push({
      x: pts.map(dayOf), y: pts.map((m) => m.value), type: 'scatter', mode: 'markers', name: mk.label,
      marker: { color: props.color, size: Math.max(4, mk.size - 2), symbol: mk.symbol, opacity: 0.35 },
      text: pts.map((m) => label(dayOf(m), m.value)), customdata: pts.map((m) => m.device_name ?? mk.label),
      hovertemplate: '%{text}<br>%{customdata}<extra></extra>',
    })
  }
  const avg = rollingMean(daily, 7)
  traces.push({
    x: avg.map((d) => d.day), y: avg.map((d) => d.value), type: 'scatter', mode: 'lines', name: '7-day average',
    line: { color: props.color, width: 3, shape: 'spline', smoothing: 0.6 },
    text: avg.map((d) => `${label(d.day, d.value)} (7-day average)`), hovertemplate: '%{text}<extra></extra>',
  })
  if (props.baseline !== null) {
    traces.push({
      x: [1, missionDay], y: [props.baseline, props.baseline], type: 'scatter', mode: 'lines',
      name: 'Your baseline', line: { dash: 'dash', color: '#6f8f8b', width: 1.5 }, hoverinfo: 'skip',
    })
  }
  Plotly.react(el.value!, traces as Plotly.Data[], {
    ...LAYOUT_BASE,
    xaxis: {
      type: 'linear', gridcolor: '#16292d', zeroline: false, tickprefix: 'Day ',
      range: [0.5, missionDay + 0.5], nticks: 8,
    },
  }, { displayModeBar: false, responsive: true })
}

function draw() {
  if (!el.value) return
  if (props.missionDay) return drawMission(props.missionDay)
  const shown = shownData.value
  const w = periodWindow(props.data, props.days)
  // Half a day of padding on each side so the first and last daily points are not clipped.
  const range: [string, string] | undefined = w ? [new Date(w.start + HALF_DAY).toISOString(), new Date(w.end + HALF_DAY).toISOString()] : undefined
  const x = shown.map((m) => m.timestamp)
  const y = shown.map((m) => m.value)
  const traces: Partial<Plotly.Data>[] = [
    { x, y, type: 'scatter', mode: 'lines', name: props.label, line: { color: props.color, width: 3 }, hoverinfo: 'skip' },
  ]
  for (const src of ORDER) {
    const pts = shown.filter((m) => m.source === src)
    if (!pts.length) continue
    const mk = MARKERS[src]
    traces.push({
      x: pts.map((m) => m.timestamp), y: pts.map((m) => m.value), type: 'scatter', mode: 'markers', name: mk.label,
      marker: { color: props.color, size: mk.size, symbol: mk.symbol, line: { color: '#081316', width: src === 'simulated' ? 0 : 1.5 } },
      customdata: pts.map((m) => m.device_name ?? mk.label),
      hovertemplate: `%{y} ${props.unit}<br>%{x|%b %d, %H:%M} UTC<br>%{customdata}<extra></extra>`,
    })
  }
  if (props.baseline !== null && range) {
    traces.push({
      x: range, y: [props.baseline, props.baseline], type: 'scatter', mode: 'lines',
      name: 'Your baseline', line: { dash: 'dash', color: '#6f8f8b', width: 1.5 }, hoverinfo: 'skip',
    })
  }
  Plotly.react(el.value, traces as Plotly.Data[], {
    ...LAYOUT_BASE,
    xaxis: { type: 'date', gridcolor: '#16292d', zeroline: false, tickformat: '%b %d', range, autorange: !range },
  }, { displayModeBar: false, responsive: true })
}

watch(() => [props.data, props.baseline, props.color, props.days, props.missionDay, el.value], draw, { deep: true })
onBeforeUnmount(() => el.value && Plotly.purge(el.value))
</script>

<template>
  <div ref="el" class="chart" role="img" :aria-label="`${label} history chart`"></div>
  <ul v-if="present.length > 1 || mission" class="legend" aria-label="Chart legend">
    <li v-if="mission">
      <svg viewBox="0 0 12 12" aria-hidden="true" :style="{ color }"><path d="M0 6 H12" stroke="currentColor" stroke-width="3" /></svg>
      7-day average
    </li>
    <li v-for="src in present" :key="src">
      <svg viewBox="0 0 12 12" aria-hidden="true" :style="{ color }">
        <circle v-if="src === 'simulated'" cx="6" cy="6" r="3.5" fill="currentColor" />
        <path v-else-if="src === 'manual'" d="M6 0.8 L11.2 6 L6 11.2 L0.8 6 Z" fill="currentColor" />
        <rect v-else x="1.5" y="1.5" width="9" height="9" fill="currentColor" />
      </svg>
      {{ MARKERS[src].label }}
    </li>
  </ul>
</template>

<style scoped>
.chart { width: 100%; height: 240px; }
.legend { list-style: none; margin: 0; padding: 0; display: flex; flex-wrap: wrap; gap: 4px 16px; font-size: 12px; color: var(--muted); }
.legend li { display: flex; align-items: center; gap: 6px; }
.legend svg { width: 12px; height: 12px; flex: none; }
</style>

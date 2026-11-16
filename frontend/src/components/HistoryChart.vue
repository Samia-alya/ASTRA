<script setup lang="ts">
import Plotly from 'plotly.js-dist-min'
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import { inPeriod, periodWindow } from '../stats'
import type { Measurement } from '../types'

const props = defineProps<{
  data: Measurement[]
  label: string
  unit: string
  baseline: number | null
  color: string
  /** Length of the displayed period, ending at the latest measurement. */
  days: number
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

const shownData = computed(() => inPeriod(props.data, props.days))
const present = computed(() => ORDER.filter((src) => shownData.value.some((m) => m.source === src)))

function draw() {
  if (!el.value) return
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
    paper_bgcolor: 'transparent', plot_bgcolor: 'transparent',
    font: { color: '#9fb8b5', family: 'Inter, sans-serif', size: 12 },
    margin: { t: 10, r: 10, b: 30, l: 40 }, showlegend: false,
    xaxis: { gridcolor: '#16292d', zeroline: false, tickformat: '%b %d', range, autorange: !range },
    yaxis: { gridcolor: '#16292d', zeroline: false },
    hoverlabel: { bgcolor: '#123036', bordercolor: '#1a3338', font: { color: '#e6f4f1' } },
  }, { displayModeBar: false, responsive: true })
}

watch(() => [props.data, props.baseline, props.color, props.days, el.value], draw, { deep: true })
onBeforeUnmount(() => el.value && Plotly.purge(el.value))
</script>

<template>
  <div ref="el" class="chart" role="img" :aria-label="`${label} history chart`"></div>
  <ul v-if="present.length > 1" class="legend" aria-label="Data sources">
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

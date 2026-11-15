<script setup lang="ts">
import Plotly from 'plotly.js-dist-min'
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'
import type { TrendResponse } from '../types'

const props = defineProps<{ trend: TrendResponse | null; label: string; unit: string }>()
const el = ref<HTMLDivElement>()
let observer: ResizeObserver | undefined

function draw() {
  if (!el.value || !props.trend) return
  const t = props.trend
  const pts = t.points
  if (!pts.length) { Plotly.purge(el.value); return }
  const byDay = pts.every((p) => p.flight_day !== null)
  const x = pts.map((p) => (byDay ? (p.flight_day as number) : p.timestamp))
  const y = pts.map((p) => p.value)
  const traces: Partial<Plotly.Data>[] = []
  const band = t.half_band
  const hasBand = band !== null && pts.every((p) => p.expected !== null)

  if (hasBand) {
    // Ribbon = where this astronaut is expected to be on each flight day.
    traces.push({ x, y: pts.map((p) => (p.expected as number) - band), type: 'scatter', mode: 'lines',
      line: { width: 0 }, hoverinfo: 'skip', showlegend: false })
    traces.push({ x, y: pts.map((p) => (p.expected as number) + band), type: 'scatter', mode: 'lines',
      line: { width: 0 }, fill: 'tonexty', fillcolor: 'rgba(60,207,122,0.17)', hoverinfo: 'skip',
      name: t.space_adjusted ? 'Expected range in flight' : 'Your normal range' })
  }
  if (t.preflight !== null) {
    traces.push({ x: [x[0], x[x.length - 1]], y: [t.preflight, t.preflight], type: 'scatter', mode: 'lines',
      name: 'Before flight (Earth)', line: { dash: 'dot', color: '#8b97a8', width: 1.5 } })
  }
  if (t.space_adjusted && t.earth_reference_high !== null) {
    traces.push({ x: [x[0], x[x.length - 1]], y: [t.earth_reference_high, t.earth_reference_high],
      type: 'scatter', mode: 'lines', name: 'Earth alert level', line: { dash: 'dash', color: '#ff5a5f', width: 1.5 } })
  }
  // In-range points are circles, out-of-range points are triangles (shape + colour).
  const out = pts.map((p) => hasBand && Math.abs(p.value - (p.expected as number)) > (band as number))
  traces.push({ x, y, type: 'scatter', mode: 'lines+markers', name: props.label,
    line: { color: '#37e6ff', width: 1.4 },
    marker: { size: out.map((o) => (o ? 8 : 4)), symbol: out.map((o) => (o ? 'triangle-up' : 'circle')),
      color: out.map((o) => (o ? '#f5b942' : '#37e6ff')) },
    hovertemplate: `${byDay ? 'Day %{x}' : '%{x}'}: %{y} ${props.unit}<extra></extra>` })
  // Today: the latest measurement.
  const lastX = x[x.length - 1]!, lastY = y[y.length - 1]!
  traces.push({ x: [lastX], y: [lastY], type: 'scatter', mode: 'markers', name: 'Today', showlegend: false,
    marker: { size: 13, color: 'rgba(0,0,0,0)', line: { color: '#ffffff', width: 2 } }, hoverinfo: 'skip' })

  Plotly.react(el.value, traces as Plotly.Data[], {
    paper_bgcolor: 'rgba(0,0,0,0)', plot_bgcolor: 'rgba(0,0,0,0)', font: { color: '#c9d4e3', size: 12 },
    margin: { t: 30, r: 20, b: 64, l: 50 }, showlegend: true,
    legend: { orientation: 'h', x: 0, y: -0.16, yanchor: 'top', font: { size: 12 }, bgcolor: 'rgba(0,0,0,0)' },
    xaxis: { title: { text: byDay ? 'Flight day' : '', standoff: 6 }, gridcolor: '#18233a', zeroline: false },
    yaxis: { title: { text: props.unit, standoff: 4 }, gridcolor: '#18233a', zeroline: false },
    shapes: [{ type: 'line', x0: lastX, x1: lastX, yref: 'paper', y0: 0, y1: 1,
      line: { color: 'rgba(255,255,255,0.55)', width: 1, dash: 'dot' } }],
    annotations: [{ x: lastX, yref: 'paper', y: 1, yanchor: 'bottom', xanchor: 'right', showarrow: false,
      text: byDay ? `Today · day ${lastX}` : 'Today', font: { size: 12, color: '#ffffff' } }],
  }, { displayModeBar: false, responsive: true })
}

onMounted(() => {
  draw()
  // The chart fills its panel: redraw to the new size whenever the panel changes.
  if (el.value) {
    observer = new ResizeObserver(() => { if (el.value && props.trend?.points.length) Plotly.Plots.resize(el.value) })
    observer.observe(el.value)
  }
})
watch(() => [props.trend, props.label], draw, { deep: true })
onBeforeUnmount(() => { observer?.disconnect(); if (el.value) Plotly.purge(el.value) })
</script>

<template>
  <div ref="el" class="chart"></div>
</template>

<style scoped>
.chart { width: 100%; height: 100%; min-height: 0; }
</style>

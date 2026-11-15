<script setup lang="ts">
import Plotly from 'plotly.js-dist-min'
import { onBeforeUnmount, ref, watch } from 'vue'
import type { Measurement } from '../types'

const props = defineProps<{ data: Measurement[]; label: string; unit: string; baseline: number | null; color: string }>()
const el = ref<HTMLDivElement>()

function draw() {
  if (!el.value) return
  const x = props.data.map((m) => m.timestamp)
  const y = props.data.map((m) => m.value)
  const traces: Partial<Plotly.Data>[] = [
    {
      x, y, type: 'scatter', mode: 'lines+markers', name: props.label,
      line: { color: props.color, width: 3 },
      marker: { color: props.color, size: 5 },
      hovertemplate: `%{y} ${props.unit}<br>%{x|%b %d}<extra></extra>`,
    },
  ]
  if (props.baseline !== null && x.length) {
    traces.push({
      x: [x[0], x[x.length - 1]], y: [props.baseline, props.baseline], type: 'scatter', mode: 'lines',
      name: 'Your baseline', line: { dash: 'dash', color: '#5c606b', width: 1.5 }, hoverinfo: 'skip',
    })
  }
  Plotly.react(el.value, traces as Plotly.Data[], {
    paper_bgcolor: 'transparent', plot_bgcolor: 'transparent',
    font: { color: '#a7a49c', family: 'Inter, sans-serif', size: 12 },
    margin: { t: 10, r: 10, b: 30, l: 40 }, showlegend: false,
    xaxis: { gridcolor: '#1f2229', zeroline: false, tickformat: '%b %d' },
    yaxis: { gridcolor: '#1f2229', zeroline: false },
    hoverlabel: { bgcolor: '#1e2128', bordercolor: '#4a4e59', font: { color: '#eceae4' } },
  }, { displayModeBar: false, responsive: true })
}

watch(() => [props.data, props.baseline, props.color, el.value], draw, { deep: true })
onBeforeUnmount(() => el.value && Plotly.purge(el.value))
</script>

<template>
  <div ref="el" class="chart" role="img" :aria-label="`${label} history chart`"></div>
</template>

<style scoped>
.chart { width: 100%; height: 240px; }
</style>

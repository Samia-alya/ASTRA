<script setup lang="ts">
import Plotly from 'plotly.js-dist-min'
import { onBeforeUnmount, ref, watch } from 'vue'
import type { Measurement } from '../types'

const props = defineProps<{ data: Measurement[]; label: string; unit: string; baseline: number | null }>()
const el = ref<HTMLDivElement>()

function draw() {
  if (!el.value) return
  const x = props.data.map((m) => m.timestamp)
  const traces: Partial<Plotly.Data>[] = [
    { x, y: props.data.map((m) => m.value), type: 'scatter', mode: 'lines+markers', name: props.label,
      line: { color: '#5aa9ff' } },
  ]
  if (props.baseline !== null && x.length) {
    traces.push({ x: [x[0], x[x.length - 1]], y: [props.baseline, props.baseline], type: 'scatter',
      mode: 'lines', name: 'Ta référence', line: { dash: 'dot', color: '#9aa4b2' } })
  }
  Plotly.react(el.value, traces as Plotly.Data[], {
    title: { text: `${props.label} (${props.unit})` },
    paper_bgcolor: 'transparent', plot_bgcolor: 'transparent', font: { color: '#e6edf3' },
    margin: { t: 40, r: 10, b: 40, l: 50 }, legend: { orientation: 'h' },
  }, { displayModeBar: false, responsive: true })
}

watch(() => [props.data, props.baseline, el.value], draw, { deep: true })
onBeforeUnmount(() => el.value && Plotly.purge(el.value))
</script>

<template>
  <div ref="el" class="chart"></div>
</template>

<style scoped>
.chart { width: 100%; height: 320px; }
</style>

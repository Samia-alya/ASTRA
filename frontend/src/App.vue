<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { api } from './api'
import HistoryChart from './components/HistoryChart.vue'
import IndicatorGrid from './components/IndicatorGrid.vue'
import MeasurementForm from './components/MeasurementForm.vue'
import VitalRing from './components/VitalRing.vue'
import type { Astronaut, IndicatorMeta, IndicatorStatus, Measurement, StatusResponse } from './types'
import { fmt, LEVEL_COLOR, LEVEL_LABEL, LEVEL_ORDER, plainName } from './types'

const astronauts = ref<Astronaut[]>([])
const astronautId = ref<number | null>(null)
const status = ref<StatusResponse | null>(null)
const meta = ref<Record<string, IndicatorMeta>>({})
const selected = ref<string | null>(null)
const history = ref<Measurement[]>([])
const error = ref('')

// Environment -> display name and one-way signal delay to Earth.
const ENVIRONMENTS: Record<string, { name: string; delay: string }> = {
  station: { name: 'Low Earth orbit', delay: 'near real-time' },
  lunar_base: { name: 'Lunar base', delay: '1.3 s one-way' },
  mars_transit: { name: 'Mars transit', delay: '3–22 min one-way' },
}
const env = computed(() => {
  const e = status.value?.astronaut.environment ?? ''
  return ENVIRONMENTS[e] ?? { name: e, delay: '—' }
})

const greeting = computed(() => {
  const h = new Date().getHours()
  return h < 12 ? 'Good morning' : h < 18 ? 'Good afternoon' : 'Good evening'
})

const flagged = computed(() =>
  (status.value?.indicators ?? [])
    .filter((i) => i.level === 'attention' || i.level === 'critical')
    .sort((a, b) => LEVEL_ORDER[a.level] - LEVEL_ORDER[b.level] || deviation(b) - deviation(a)),
)

function deviation(i: IndicatorStatus) {
  if (i.value === null || !i.baseline) return 0
  return Math.abs(i.value - i.baseline) / Math.abs(i.baseline)
}


const headline = computed(() => {
  const list = flagged.value
  if (!status.value) return ''
  if (!list.length) return 'All signals are steady today.'
  const top = list[0]!
  const dir = top.value !== null && top.baseline !== null && top.value < top.baseline ? 'down' : 'up'
  const first = top.level === 'critical'
    ? `Your ${plainName(top.label)} needs attention now.`
    : `Your ${plainName(top.label)} is ${dir}.`
  const rest = list.length === 1 ? 'One signal needs a look.' : `${list.length} signals need a look.`
  return `${first} ${rest}`
})

const sel = computed(() => status.value?.indicators.find((i) => i.indicator === selected.value) ?? null)
const selMeta = computed(() => (selected.value ? meta.value[selected.value] : undefined))
const hasSimulated = computed(() => history.value.some((m) => m.source === 'simulated'))

const deltaText = computed(() => {
  const s = sel.value
  if (!s || s.value === null || s.baseline === null) return ''
  const d = s.value - s.baseline
  const abs = Math.abs(d)
  const amount = abs >= 10 ? abs.toFixed(0) : abs.toFixed(1)
  const unit = s.unit.startsWith('/') ? 'points' : s.unit
  if (s.level === 'normal') return 'Close to your baseline'
  return `${amount} ${unit} ${d > 0 ? 'above' : 'below'} your baseline`
})

const guidance = computed(() => {
  const s = sel.value
  if (!s) return ''
  return selMeta.value?.guidance?.[s.level] ?? 'Keep your regular measurement schedule.'
})

async function loadStatus() {
  if (astronautId.value === null) return
  try {
    error.value = ''
    status.value = await api.status(astronautId.value)
    if (!selected.value) selected.value = flagged.value[0]?.indicator ?? status.value.indicators[0]?.indicator ?? null
    await loadHistory()
  } catch (e) {
    error.value = (e as Error).message
  }
}

async function loadHistory() {
  if (astronautId.value === null || !selected.value) return
  history.value = await api.measurements(astronautId.value, selected.value)
}

onMounted(async () => {
  try {
    ;[astronauts.value, meta.value] = await Promise.all([api.astronauts(), api.indicators()])
    astronautId.value = astronauts.value[0]?.id ?? null
  } catch {
    error.value = 'Cannot reach the API. Is the backend running on port 8000?'
  }
})

watch(astronautId, () => { selected.value = null; loadStatus() })
watch(selected, loadHistory)
</script>

<template>
  <header class="top">
    <div class="brand">
      <svg width="28" height="28" viewBox="0 0 28 28" aria-hidden="true">
        <circle cx="14" cy="14" r="12" fill="none" stroke="currentColor" stroke-width="2" />
        <path d="M4 15 H9 L11.5 9 L15 20 L17.5 13 H24" fill="none" stroke="var(--watch)" stroke-width="2"
          stroke-linejoin="round" stroke-linecap="round" />
      </svg>
      <span>Houston Pulse</span>
    </div>
    <div class="meta" v-if="status">
      <label class="crew">
        <span class="sr-only">Crew member</span>
        <select v-model="astronautId">
          <option v-for="a in astronauts" :key="a.id" :value="a.id">{{ a.name }}</option>
        </select>
      </label>
      <span>{{ env.name }} · Day {{ status.astronaut.mission_day }}</span>
      <span>Earth delay {{ env.delay }}</span>
      <span class="pill">Simulated data</span>
    </div>
  </header>

  <p v-if="error" class="error" role="alert">{{ error }}</p>

  <main v-if="status">
    <section class="hero">
      <div class="ring-wrap">
        <VitalRing :indicators="status.indicators" :meta="meta" :selected="selected" @select="selected = $event" />
      </div>
      <div class="intro">
        <span class="hello">{{ greeting }}, {{ status.astronaut.name }}</span>
        <h1>{{ headline }}</h1>
        <IndicatorGrid :indicators="status.indicators" :meta="meta" :selected="selected" @select="selected = $event" />
      </div>
    </section>

    <section class="detail" v-if="sel">
      <div class="card chart-card">
        <div class="chart-head">
          <div class="big">
            <span class="label">{{ sel.label }} · history</span>
            <span class="num">{{ fmt(sel.value, sel.unit) }}<small> {{ sel.unit }}</small></span>
          </div>
          <div class="state">
            <span class="delta">{{ deltaText }}</span>
            <span class="tag" :class="sel.level">{{ LEVEL_LABEL[sel.level] }}</span>
          </div>
        </div>
        <ul class="reasons">
          <li v-for="r in sel.reasons" :key="r">{{ r }}</li>
        </ul>
        <HistoryChart :data="history" :label="sel.label" :unit="sel.unit" :baseline="sel.baseline"
          :color="LEVEL_COLOR[sel.level]" />
        <span v-if="hasSimulated" class="sim-note">Simulated data · dashed line = your personal baseline</span>
      </div>

      <div class="card guide">
        <h2>What it measures</h2>
        <p>{{ selMeta?.what }}</p>
        <h2>Why it matters up here</h2>
        <p>{{ selMeta?.why_in_space }}</p>
        <h2>What you can do now</h2>
        <p>{{ guidance }}</p>
        <button class="primary" type="button">Message flight surgeon</button>
      </div>
    </section>

    <section class="card" v-if="astronautId !== null">
      <MeasurementForm :astronaut-id="astronautId" :indicators="meta" :preset="selected" @saved="loadStatus" />
    </section>

    <p class="disclaimer">{{ status.disclaimer }}</p>
  </main>
</template>

<style scoped>
.top { display: flex; flex-wrap: wrap; align-items: center; justify-content: space-between; gap: 12px 24px; }
.brand { display: flex; align-items: center; gap: 12px; font-family: var(--display); font-size: 18px; font-weight: 700; }
.meta { display: flex; flex-wrap: wrap; align-items: center; gap: 8px 20px; font-size: 14px; color: var(--muted); }
.crew select {
  font: inherit; color: var(--text); background: var(--panel); border: 1.5px solid var(--border);
  border-radius: 10px; min-height: 40px; padding: 0 10px;
}
.pill { font-size: 12px; font-weight: 600; padding: 4px 10px; border-radius: 99px; border: 1.5px solid var(--muted); }
.sr-only { position: absolute; width: 1px; height: 1px; overflow: hidden; clip: rect(0 0 0 0); }

main { display: flex; flex-direction: column; gap: 24px; margin-top: 24px; }

.hero { display: flex; flex-wrap: wrap; gap: 32px; align-items: center; }
.ring-wrap { flex: 1 1 440px; min-width: 0; }
.intro { flex: 1 1 520px; min-width: 0; display: flex; flex-direction: column; gap: 20px; }
.hello { font-size: 14px; color: var(--muted); }
h1 { margin: -14px 0 0; font-family: var(--display); font-size: clamp(28px, 3.2vw, 40px); line-height: 1.12; font-weight: 500; }

.detail { display: flex; flex-wrap: wrap; gap: 20px; }
.card { background: var(--panel); border-radius: 20px; padding: 24px; }
.chart-card { flex: 999 1 560px; min-width: 0; display: flex; flex-direction: column; gap: 12px; }
.chart-head { display: flex; flex-wrap: wrap; align-items: flex-end; justify-content: space-between; gap: 12px; }
.big { display: flex; flex-direction: column; gap: 4px; }
.label { font-size: 14px; color: var(--muted); }
.num { font-family: var(--display); font-size: 48px; font-weight: 500; line-height: 1; }
.num small { font-size: 20px; color: var(--muted); }
.state { display: flex; align-items: center; gap: 12px; }
.delta { font-size: 15px; color: var(--text-2); }
.reasons { margin: 0; padding-left: 18px; font-size: 14px; color: var(--text-2); line-height: 1.5; }
.sim-note { font-size: 12px; color: var(--muted); }

.guide { flex: 1 1 320px; min-width: 0; display: flex; flex-direction: column; gap: 8px; }
.guide h2 { margin: 8px 0 0; font-size: 15px; font-weight: 600; }
.guide h2:first-child { margin-top: 0; }
.guide p { margin: 0; font-size: 15px; line-height: 1.55; color: var(--text-2); }
.primary {
  margin-top: auto; min-height: 48px; border-radius: 14px; border: none; cursor: pointer;
  background: var(--text); color: var(--bg); font-weight: 600; font-size: 15px;
}
.guide .primary { margin-top: 16px; }

.disclaimer { margin: 0; font-size: 12px; color: #8c8980; }
.error { color: var(--critical); }
</style>

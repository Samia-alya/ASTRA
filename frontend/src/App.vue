<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { api } from './api'
import AlertsPanel from './components/AlertsPanel.vue'
import HolographicBody3D, { type BodyZone } from './components/HolographicBody3D.vue'
import MeasurementForm from './components/MeasurementForm.vue'
import MetricPanel from './components/MetricPanel.vue'
import ModalDialog from './components/ModalDialog.vue'
import PvtTest from './components/PvtTest.vue'
import type { Astronaut, IndicatorMeta, IndicatorStatus, Level, StatusResponse, TrendResponse } from './types'

// Body zones shown on the hologram and the indicators each one carries.
const ZONES: { key: string; label: string; indicators: string[] }[] = [
  { key: 'brain', label: 'Brain · Sleep', indicators: ['sleep_hours', 'alertness', 'mood', 'pvt_lapses', 'pvt_mean_rt'] },
  { key: 'heart', label: 'Heart · Blood pressure', indicators: ['heart_rate', 'bp_systolic', 'bp_diastolic'] },
  { key: 'torso', label: 'Core · Temperature', indicators: ['temperature'] },
  { key: 'forearm', label: 'Forearm · Glucose', indicators: ['glucose'] },
]
const RANK: Record<Level, number> = { critical: 0, attention: 1, normal: 2, no_data: 3 }
const ENV_SHORT: Record<string, string> = { mars_transit: 'Mars Transit', station: 'Space Station', lunar_base: 'Lunar Base' }
const READY = { GO: { text: 'GO', shape: '●' }, CAUTION: { text: 'CAUTION', shape: '▲' }, NO_GO: { text: 'NO-GO', shape: '■' } }

const astronauts = ref<Astronaut[]>([])
const astronautId = ref<number | null>(null)
const status = ref<StatusResponse | null>(null)
const meta = ref<Record<string, IndicatorMeta>>({})
const zone = ref<string | null>(null)
const indicator = ref<string | null>(null)
const trend = ref<TrendResponse | null>(null)
const error = ref('')
const open = ref<'alerts' | 'pvt' | 'log' | null>(null)

const byKey = computed(() => {
  const map: Record<string, IndicatorStatus> = {}
  for (const s of status.value?.indicators ?? []) map[s.indicator] = s
  return map
})
function zoneMetrics(key: string): IndicatorStatus[] {
  const z = ZONES.find((x) => x.key === key)
  return (z?.indicators ?? []).map((k) => byKey.value[k]).filter((s): s is IndicatorStatus => !!s)
}
const bodyZones = computed<BodyZone[]>(() => ZONES.map((z) => {
  const list = zoneMetrics(z.key)
  const worst = [...list].sort((a, b) => RANK[a.level] - RANK[b.level])[0]
  return {
    key: z.key, label: z.label, level: worst?.level ?? 'no_data',
    summary: worst && worst.value !== null ? `${worst.value} ${worst.unit}` : 'no data',
  }
}))
const metrics = computed(() => (zone.value ? zoneMetrics(zone.value) : []))
const zoneLabel = computed(() => ZONES.find((z) => z.key === zone.value)?.label ?? '')
const falseAlarms = computed(() => status.value?.indicators.reduce((n, i) => n + i.earth_false_alarms, 0) ?? 0)
const pill = computed(() => {
  const m = status.value?.mission
  if (!m) return ''
  const delay = m.one_way_delay_min ? `${m.one_way_delay_min[0]}–${m.one_way_delay_min[1]} min delay` : 'Live link to Earth'
  return `Day ${m.flight_day} • ${ENV_SHORT[m.environment] ?? m.environment_label} • ${delay}`
})

function selectZone(key: string) {
  zone.value = key
  const list = zoneMetrics(key)
  const worst = [...list].sort((a, b) => RANK[a.level] - RANK[b.level])[0]
  indicator.value = worst?.indicator ?? null
}

async function loadStatus() {
  if (astronautId.value === null) return
  try {
    status.value = await api.status(astronautId.value)
    if (!zone.value) {
      // Start on the zone that most needs attention; if all is well, show temperature
      // (the clearest example of a value that is normal in space but not on Earth).
      const sorted = [...bodyZones.value].sort((a, b) => RANK[a.level] - RANK[b.level])
      selectZone(sorted[0] && sorted[0].level !== 'normal' ? sorted[0].key : 'torso')
    }
    await loadTrend()
  } catch (e) {
    error.value = (e as Error).message
  }
}

async function loadTrend() {
  if (astronautId.value === null || !indicator.value) return
  trend.value = await api.trend(astronautId.value, indicator.value)
}

async function exportReport() {
  if (astronautId.value === null) return
  const report = await api.report(astronautId.value)
  const url = URL.createObjectURL(new Blob([JSON.stringify(report, null, 2)], { type: 'application/json' }))
  const a = document.createElement('a')
  a.href = url
  a.download = `astrovitals-report-FD${status.value?.mission.flight_day ?? ''}.json`
  a.click()
  URL.revokeObjectURL(url)
}

onMounted(async () => {
  try {
    ;[astronauts.value, meta.value] = await Promise.all([api.astronauts(), api.indicators()])
    astronautId.value = astronauts.value[0]?.id ?? null
  } catch {
    error.value = 'Unable to reach the API. Is the backend running?'
  }
})

watch(astronautId, () => { zone.value = null; indicator.value = null; trend.value = null; loadStatus() })
watch(indicator, loadTrend)
</script>

<template>
  <div class="app">
    <header class="bar">
      <div class="brand"><span class="mark" aria-hidden="true">✚</span>AstroVitals</div>
      <select v-if="astronauts.length" v-model="astronautId" class="who" aria-label="Crew member">
        <option v-for="a in astronauts" :key="a.id" :value="a.id">{{ a.name }}</option>
      </select>
      <span v-if="status" class="pill">{{ pill }}</span>
      <span class="grow"></span>
      <template v-if="status">
        <button type="button" class="btn alerts" :class="{ none: !status.alerts.length }" @click="open = 'alerts'">
          <i aria-hidden="true">▲</i>
          {{ status.alerts.length || 'No' }} Clinical Alert{{ status.alerts.length === 1 ? '' : 's' }}
        </button>
        <span class="ready" :class="status.readiness.status" :title="status.readiness.label">
          <i aria-hidden="true">{{ READY[status.readiness.status].shape }}</i>{{ READY[status.readiness.status].text }}
        </span>
        <button type="button" class="btn" @click="open = 'pvt'">Vigilance Test (PVT)</button>
        <button type="button" class="btn primary" @click="open = 'log'">+ Log Metric</button>
      </template>
    </header>

    <p v-if="error" class="error">{{ error }}</p>

    <main v-if="status" class="main">
      <section class="left">
        <HolographicBody3D :zones="bodyZones" :selected="zone" @select="selectZone" />
        <div class="notes">
          <p v-if="falseAlarms > 0"><b>{{ falseAlarms }} false alarms avoided</b> vs an Earth-calibrated tool</p>
          <p v-else-if="!status.mission.adaptation_model_applies">Weightlessness model not applied in this environment</p>
          <p class="fine">Simulated data · Monitoring aid, not a medical diagnosis</p>
        </div>
      </section>
      <section class="right">
        <MetricPanel :zone-label="zoneLabel" :metrics="metrics" :selected="indicator" :trend="trend"
          :alerts="status.alerts" :meta="meta" @select="indicator = $event" @open-alerts="open = 'alerts'" />
      </section>
    </main>

    <ModalDialog v-if="open === 'alerts' && status" side :title="`${status.alerts.length} clinical alert${status.alerts.length === 1 ? '' : 's'}`" @close="open = null">
      <p class="ready-line" :class="status.readiness.status">
        <b>{{ status.readiness.label }}</b>
        <span v-if="status.mission.autonomy === 'earth_independent'"> · {{ status.mission.comm_delay }}</span>
      </p>
      <AlertsPanel v-if="status.alerts.length" :alerts="status.alerts" />
      <p v-else class="empty">No cross-indicator alert is active. {{ status.readiness.reasons.join(' ') }}</p>
      <template #footer>
        <button type="button" class="btn" @click="exportReport">Export report for Mission Control</button>
        <span class="fine">{{ status.disclaimer }}</span>
      </template>
    </ModalDialog>

    <ModalDialog v-if="open === 'pvt' && astronautId !== null" title="Vigilance test (PVT-B)" @close="open = null">
      <PvtTest :astronaut-id="astronautId" @saved="loadStatus" />
    </ModalDialog>

    <ModalDialog v-if="open === 'log' && astronautId !== null" title="Log a metric" @close="open = null">
      <MeasurementForm :astronaut-id="astronautId" :indicators="meta" @saved="loadStatus(); open = null" />
    </ModalDialog>
  </div>
</template>

<style scoped>
.app { width: 100vw; height: 100vh; display: flex; flex-direction: column; overflow: hidden; background: var(--bg); }
.bar { flex: none; display: flex; align-items: center; gap: 10px; height: 56px; padding: 0 18px; border-bottom: 1px solid var(--line); }
.brand { display: flex; align-items: center; gap: 8px; font-size: 19px; font-weight: 700; letter-spacing: .01em; white-space: nowrap; }
.mark { color: var(--cyan); }
.who { font: inherit; font-size: 14px; padding: 6px 8px; border-radius: 8px; background: transparent; color: var(--text);
  border: 1px solid transparent; cursor: pointer; max-width: 170px; }
.who:hover, .who:focus { border-color: var(--line); }
.who option { background: #0b1220; }
.pill { font-size: 13px; padding: 6px 13px; border-radius: 999px; border: 1px solid var(--line); color: var(--muted); white-space: nowrap; }
.grow { flex: 1; }
.btn { font: inherit; font-size: 14px; padding: 8px 14px; border-radius: 9px; border: 1px solid var(--line); background: transparent;
  color: var(--text); cursor: pointer; white-space: nowrap; display: inline-flex; align-items: center; gap: 7px; }
.btn:hover { border-color: var(--cyan); }
.btn.primary { background: var(--cyan); border-color: var(--cyan); color: #041018; font-weight: 600; }
.btn.alerts { border-color: var(--warn); color: var(--warn); }
.btn.alerts.none { border-color: var(--line); color: var(--muted); }
.btn i, .ready i { font-style: normal; font-size: 12px; }
.ready { font-size: 14px; font-weight: 700; letter-spacing: .04em; padding: 7px 13px; border-radius: 9px; white-space: nowrap;
  display: inline-flex; align-items: center; gap: 7px; background: var(--ok); color: #04210f; }
.ready.CAUTION { background: var(--warn); color: #2b1a00; }
.ready.NO_GO { background: var(--crit); color: #fff; }

.main { flex: 1; min-height: 0; display: grid; grid-template-columns: minmax(300px, 40%) 1fr; }
.left { position: relative; min-height: 0; min-width: 0; border-right: 1px solid var(--line); }
.notes { position: absolute; left: 16px; top: 12px; right: 16px; pointer-events: none; }
.notes p { margin: 0 0 2px; font-size: 13px; color: var(--cyan); }
.notes .fine { color: var(--muted); font-size: 12px; }
.right { min-height: 0; min-width: 0; padding: 12px 16px 14px; }

.ready-line { margin: 0 0 12px; font-size: 14px; color: var(--ok); }
.ready-line.CAUTION { color: var(--warn); } .ready-line.NO_GO { color: var(--crit); }
.ready-line span { color: var(--muted); }
.empty { color: var(--muted); }
.fine { font-size: 12px; color: var(--muted); }
.error { margin: 12px 18px; color: var(--crit); }

@media (max-width: 1180px) {
  .pill { display: none; }
  .bar { gap: 8px; padding: 0 12px; }
}
</style>

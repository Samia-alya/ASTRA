<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { api } from './api'
import HistoryChart from './components/HistoryChart.vue'
import IndicatorGrid from './components/IndicatorGrid.vue'
import MeasurementForm from './components/MeasurementForm.vue'
import TodayChecks from './components/TodayChecks.vue'
import DevicesCard from './components/DevicesCard.vue'
import SourcesDialog from './components/SourcesDialog.vue'
import BodyZonePanel from './components/BodyZonePanel.vue'
import { BODY_ZONES, ZONE_ORDER } from './bodyZones'
import VitalRing from './components/VitalRing.vue'
import FlightSurgeonReport from './components/FlightSurgeonReport.vue'
import AutonomyPanel from './components/AutonomyPanel.vue'
import { envFor, loadEnvironments } from './environments'
import { formatUtc, type OnboardLog } from './report'
import type {
  Astronaut, AutonomyResponse, ChecksResponse, Device, IndicatorMeta, IndicatorStatus, Measurement, StatusResponse,
} from './types'
import { fmt, LEVEL_COLOR, LEVEL_LABEL, LEVEL_ORDER, plainName } from './types'
import { missionStats, periodStats } from './stats'
import { sourceText, useNow } from './time'

const astronauts = ref<Astronaut[]>([])
const astronautId = ref<number | null>(null)
const status = ref<StatusResponse | null>(null)
const meta = ref<Record<string, IndicatorMeta>>({})
const selected = ref<string | null>(null)
const history = ref<Measurement[]>([])
const error = ref('')
const checks = ref<ChecksResponse | null>(null)
const devices = ref<Device[]>([])

// --- Body zone info panel (opened by clicking a body part on the ring) ---
const openZone = ref<string | null>(null)
const sourcesDialog = ref<InstanceType<typeof SourcesDialog> | null>(null)
const ring = ref<InstanceType<typeof VitalRing> | null>(null)
const zonePanel = ref<InstanceType<typeof BodyZonePanel> | null>(null)
let zoneOpener: HTMLElement | SVGElement | null = null

function worstInZone(zone: string) {
  return (status.value?.indicators ?? [])
    .filter((i) => i.body_zone === zone)
    .sort((a, b) => LEVEL_ORDER[a.level] - LEVEL_ORDER[b.level])[0]
}

/** Open a body zone's panel; for a monitored zone, also select its worst indicator (as before). */
async function onZone(zone: string) {
  const wasOpen = openZone.value !== null
  const active = document.activeElement
  if (!wasOpen) zoneOpener = active instanceof HTMLElement || active instanceof SVGElement ? active : null
  openZone.value = zone
  const worst = BODY_ZONES[zone]?.monitored ? worstInZone(zone) : undefined
  if (worst) selected.value = worst.indicator
  await nextTick()
  // The panel opens below the ring, often off screen on a laptop: bring it into view, then focus it.
  zonePanel.value?.reveal()
  zonePanel.value?.focusHeading()
}

async function closeZone() {
  const zone = openZone.value
  openZone.value = null
  await nextTick()
  if (zoneOpener?.isConnected) zoneOpener.focus()
  else if (zone) ring.value?.focusZone(zone)
  zoneOpener = null
}

// Selecting an indicator elsewhere (arc, grid, panel row) moves an open panel to that indicator's zone.
watch(selected, (key) => {
  if (!openZone.value || !key) return
  const zone = status.value?.indicators.find((i) => i.indicator === key)?.body_zone
  if (zone && zone !== openZone.value && BODY_ZONES[zone]) openZone.value = zone
})
const now = useNow()
// Indicators that just received a new device value, highlighted for a moment.
const updated = ref<string[]>([])
let updatedTimer: number | undefined
const form = ref<InstanceType<typeof MeasurementForm> | null>(null)

const dueChecks = computed(() => checks.value?.items.filter((c) => !c.done) ?? [])
const dueText = computed(() => {
  const n = dueChecks.value.length
  return `${n} measurement${n === 1 ? '' : 's'} due today: ${dueChecks.value.map((c) => c.label).join(', ')}`
})

function logNow(indicator: string) {
  form.value?.logNow(indicator)
}

// History period: lives here (not in the chart) so it survives indicator / astronaut switches.
// 'mission' = the whole stay since day 1.
type Period = 7 | 14 | 30 | 'mission'
const PERIODS: Period[] = [7, 14, 30, 'mission']
const period = ref<Period>(14)
const periodDays = computed(() => (period.value === 'mission' ? 30 : period.value))
const isMission = computed(() => period.value === 'mission')
const missionDay = computed(() => status.value?.astronaut.mission_day ?? null)

const reportOpen = ref(false)

const env = computed(() => envFor(status.value?.astronaut.environment ?? ''))
const isCritical = computed(() => status.value?.overall_level === 'critical')

// Earth-independent mode (critical alert + Earth too far to answer in time).
const autonomy = ref<AutonomyResponse | null>(null)
const autonomous = computed(() => !!status.value?.autonomy.active)

async function loadAutonomy() {
  const id = astronautId.value
  autonomy.value = id !== null && autonomous.value ? await api.autonomy(id) : null
}

const onboard = computed<OnboardLog | null>(() => {
  const a = autonomy.value
  if (!a) return null
  const actions = a.groups
    .flatMap((g) => g.steps.filter((s) => s.checked_at).map((s) => ({
      indicator: g.label, step: s.text, ts: s.checked_at!, sent: s.in_last_report,
    })))
    .sort((x, y) => x.ts.localeCompare(y.ts))
    .map(({ indicator, step, ts, sent }) => ({ indicator, step, at: formatUtc(new Date(ts)), sent }))
  return { actions, sentAt: a.report_sent_at ? formatUtc(new Date(a.report_sent_at)) : null }
})

async function onReportSend() {
  if (!autonomous.value || astronautId.value === null) return
  try {
    await api.sendReport(astronautId.value)
    await loadAutonomy()
  } catch (e) {
    error.value = (e as Error).message
  }
}

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


// Split in parts so the signal count can be highlighted; the sentence itself is unchanged.
const headline = computed(() => {
  const list = flagged.value
  if (!status.value) return { lead: '', count: '', tail: '' }
  if (!list.length) return { lead: 'All signals are steady today.', count: '', tail: '' }
  const top = list[0]!
  const dir = top.value !== null && top.baseline !== null && top.value < top.baseline ? 'down' : 'up'
  const first = top.level === 'critical'
    ? `Your ${plainName(top.label)} needs attention now.`
    : `Your ${plainName(top.label)} is ${dir}.`
  return list.length === 1
    ? { lead: first, count: 'One signal', tail: 'needs a look.' }
    : { lead: first, count: `${list.length} signals`, tail: 'need a look.' }
})

const sel = computed(() => status.value?.indicators.find((i) => i.indicator === selected.value) ?? null)
const selMeta = computed(() => (selected.value ? meta.value[selected.value] : undefined))
const stats = computed(() => periodStats(history.value, periodDays.value))

function withUnit(v: number | null, unit: string) {
  return v === null ? '—' : `${fmt(v, unit)} ${unit}`
}
/** "+1.2 h", "−0.6 h", "0 h", or "—" */
function signedText(c: number | null, unit: string) {
  if (c === null) return '—'
  const abs = fmt(Math.abs(c), unit)
  const sign = Number(abs) === 0 ? '' : c > 0 ? '+' : '−'
  return `${sign}${abs} ${unit}`
}
const changeText = computed(() => signedText(stats.value.change, sel.value?.unit ?? ''))
const mStats = computed(() => missionStats(history.value, missionDay.value ?? 1))
const changeColor = computed(() => (!sel.value || sel.value.level === 'no_data' ? undefined : LEVEL_COLOR[sel.value.level]))
const rangeText = computed(() => {
  const { min, max } = stats.value.current
  const unit = sel.value?.unit ?? ''
  return min === null || max === null ? '—' : `${fmt(min, unit)}–${fmt(max, unit)} ${unit}`
})

// Every device in this app is simulated, so device rows count as simulated data too.
const hasSimulated = computed(() =>
  history.value.some((m) => m.source === 'simulated'
    || (m.source === 'device' && devices.value.find((d) => d.id === m.device_id)?.simulated !== false)),
)

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
  // Earth-independent mode: "contact your flight surgeon now" would contradict the onboard panel.
  if (autonomous.value && s.level === 'critical') {
    return 'Earth cannot respond in time. Follow the onboard monitoring steps in the panel above, '
      + 'then send a report to Earth. Re-measure every 2 hours.'
  }
  return selMeta.value?.guidance?.[s.level] ?? 'Keep your regular measurement schedule.'
})

async function loadStatus() {
  if (astronautId.value === null) return
  try {
    error.value = ''
    const id = astronautId.value
    const [s, c, d] = await Promise.all([api.status(id), api.checks(id), api.devices(id)])
    status.value = s
    checks.value = c
    devices.value = d
    await loadAutonomy()
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
    ;[astronauts.value, meta.value] = await Promise.all([api.astronauts(), api.indicators(), loadEnvironments()])
    astronautId.value = astronauts.value[0]?.id ?? null
  } catch {
    error.value = 'Cannot reach the API. Is the backend running on port 8000?'
  }
})

watch(astronautId, () => { selected.value = null; updated.value = []; loadStatus() })

// --- Live updates: every 5 s while the tab is visible, never two refreshes at once. ---
const REFRESH_MS = 5000
let refreshing = false
let refreshTimer: number | undefined

function markUpdated(prev: StatusResponse, next: StatusResponse) {
  if (prev.astronaut.id !== next.astronaut.id) return
  const keys = next.indicators
    .filter((n) => {
      const p = prev.indicators.find((i) => i.indicator === n.indicator)
      return n.last_source?.type === 'device' && p && p.last_timestamp !== n.last_timestamp
    })
    .map((n) => n.indicator)
  if (!keys.length) return
  updated.value = keys
  window.clearTimeout(updatedTimer)
  updatedTimer = window.setTimeout(() => { updated.value = [] }, 1500)
}

async function refresh() {
  const id = astronautId.value
  if (id === null || !status.value || refreshing || document.hidden) return
  refreshing = true
  try {
    const sel = selected.value
    const [s, c, d, h] = await Promise.all([
      api.status(id), api.checks(id), api.devices(id), sel ? api.measurements(id, sel) : Promise.resolve(null),
    ])
    if (id !== astronautId.value) return // the crew member changed meanwhile: drop stale data
    if (status.value) markUpdated(status.value, s)
    status.value = s
    checks.value = c
    devices.value = d
    if (h && sel === selected.value) history.value = h
    await loadAutonomy() // a live device reading can switch Earth-independent mode on or off
    error.value = ''
  } catch (e) {
    error.value = `Live update failed: ${(e as Error).message}`
  } finally {
    refreshing = false
  }
}

function onVisibility() {
  if (!document.hidden) refresh()
}

onMounted(() => {
  refreshTimer = window.setInterval(refresh, REFRESH_MS)
  document.addEventListener('visibilitychange', onVisibility)
})
onBeforeUnmount(() => {
  window.clearInterval(refreshTimer)
  window.clearTimeout(updatedTimer)
  document.removeEventListener('visibilitychange', onVisibility)
})
watch(selected, loadHistory)
</script>

<template>
  <header class="top">
    <div class="brand">
      <img src="/favicon.svg?v=2" width="40" height="40" alt="" />
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

  <div v-if="status && dueChecks.length" class="reminder" role="status">
    <svg class="reminder-icon" viewBox="0 0 20 20" aria-hidden="true">
      <circle cx="10" cy="10" r="8.25" fill="none" stroke="currentColor" stroke-width="2" />
      <path d="M10 5.5 V10 L13 12" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" />
    </svg>
    <span class="reminder-text">{{ dueText }}</span>
    <button type="button" @click="logNow(dueChecks[0]!.indicator)">
      Log now<span class="sr-only"> {{ dueChecks[0]!.label }}</span>
    </button>
  </div>

  <p v-if="error" class="error" role="alert">{{ error }}</p>

  <main v-if="status">
    <section class="hero">
      <div class="ring-wrap">
        <VitalRing ref="ring" :indicators="status.indicators" :meta="meta" :selected="selected" :open-zone="openZone"
          @select="selected = $event" @zone="onZone" />
        <div class="zone-hint">
          <p>Tap a body part to learn more.</p>
          <div class="zone-chips" role="group" aria-label="Body parts">
            <button v-for="z in ZONE_ORDER" :key="z" type="button" :class="{ muted: !BODY_ZONES[z]!.monitored }"
              :aria-expanded="openZone === z" aria-controls="body-zone-panel" @click="onZone(z)">
              {{ BODY_ZONES[z]!.short }}
            </button>
          </div>
        </div>
        <BodyZonePanel v-if="openZone" ref="zonePanel" :zone="openZone" :indicators="status.indicators"
          :selected="selected" @select="selected = $event" @close="closeZone" />
      </div>
      <div class="intro">
        <span class="hello">{{ greeting }}, {{ status.astronaut.name }}</span>
        <!-- Explicit {{ ' ' }}: Vue drops a whitespace-only text node at the start of a <template> block. -->
        <h1>{{ headline.lead }}<template v-if="headline.count">{{ ' ' }}<span class="count">{{ headline.count
          }}</span>{{ ' ' + headline.tail }}</template></h1>
        <IndicatorGrid :indicators="status.indicators" :meta="meta" :selected="selected" :now="now" :updated="updated"
          @select="selected = $event" />
      </div>
    </section>

    <AutonomyPanel v-if="autonomy && astronautId !== null" :astronaut-id="astronautId" :data="autonomy"
      @changed="loadAutonomy" @preview="reportOpen = true" />
    <section v-else-if="isCritical" class="contact-now" aria-labelledby="contact-now-title">
      <div>
        <h2 id="contact-now-title">Earth can respond in time</h2>
        <p>{{ status.autonomy.reason }}</p>
      </div>
      <button type="button" class="primary critical" aria-haspopup="dialog" @click="reportOpen = true">
        Contact flight surgeon now
      </button>
    </section>

    <section class="detail" v-if="sel">
      <div class="card chart-card">
        <div class="chart-head">
          <div class="big">
            <span class="label">{{ sel.label }} · history</span>
            <span v-if="sel.last_source" class="src" :class="sel.last_source.type">
              {{ sourceText(sel.last_source, sel.last_timestamp, now) }}</span>
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
        <div class="periods" role="group" aria-label="History period">
          <button v-for="p in PERIODS" :key="p" type="button" :aria-pressed="period === p"
            @click="period = p">{{ p === 'mission' ? 'Mission' : `${p} days` }}</button>
        </div>
        <HistoryChart :data="history" :label="sel.label" :unit="sel.unit" :baseline="sel.baseline"
          :color="LEVEL_COLOR[sel.level]" :days="periodDays" :mission-day="isMission ? missionDay : null" />
        <dl v-if="isMission" class="stats">
          <div>
            <dt>Mission average</dt>
            <dd>{{ withUnit(mStats.average, sel.unit) }}</dd>
          </div>
          <div>
            <dt>First 2 weeks</dt>
            <dd>{{ withUnit(mStats.firstTwoWeeks, sel.unit) }}
              <small v-if="mStats.firstTwoWeeks === null">not enough data</small></dd>
          </div>
          <div>
            <dt>Last 2 weeks</dt>
            <dd>{{ withUnit(mStats.lastTwoWeeks, sel.unit) }}</dd>
          </div>
          <div>
            <dt>Change</dt>
            <dd :style="{ color: changeColor }">{{ signedText(mStats.change, sel.unit) }}</dd>
          </div>
        </dl>
        <dl v-else class="stats">
          <div>
            <dt>Average (last {{ periodDays }} days)</dt>
            <dd>{{ withUnit(stats.current.average, sel.unit) }}</dd>
          </div>
          <div>
            <dt>Previous {{ periodDays }} days</dt>
            <dd>{{ withUnit(stats.previous.average, sel.unit) }}
              <small v-if="!stats.previous.count">not enough data</small></dd>
          </div>
          <div>
            <dt>Change</dt>
            <dd :style="{ color: changeColor }">{{ changeText }}</dd>
          </div>
          <div>
            <dt>Range</dt>
            <dd>{{ rangeText }}</dd>
          </div>
        </dl>
        <span v-if="hasSimulated" class="sim-note">Simulated data · dashed line = your personal baseline</span>
      </div>

      <div class="card guide">
        <h2>What it measures</h2>
        <p>{{ selMeta?.what }}</p>
        <h2>Why it matters up here</h2>
        <p>{{ selMeta?.why_in_space }}</p>
        <h2>What you can do now</h2>
        <p>{{ guidance }}</p>
        <button v-if="!autonomous" class="primary" :class="{ critical: isCritical }" type="button"
          aria-haspopup="dialog" @click="reportOpen = true">
          {{ isCritical ? 'Contact flight surgeon now' : 'Message flight surgeon' }}
        </button>
      </div>
    </section>

    <section class="log-row" v-if="astronautId !== null">
      <div class="card form-card">
        <MeasurementForm ref="form" :astronaut-id="astronautId" :indicators="meta" :preset="selected"
          @saved="loadStatus" />
      </div>
      <div class="card checks-card" v-if="checks">
        <TodayChecks :checks="checks" @log="logNow" />
      </div>
      <div class="card devices-card">
        <DevicesCard :devices="devices" :meta="meta" :now="now" />
      </div>
    </section>

    <FlightSurgeonReport :open="reportOpen" :status="status" :meta="meta" :env="env" :onboard="onboard"
      @close="reportOpen = false" @send="onReportSend" />
  </main>

  <footer class="foot">
    <span>Built for the NASA Space Apps Challenge 2026 · Space context: NASA Human Research Program ·
      <button type="button" class="sources-link" aria-haspopup="dialog" @click="sourcesDialog?.open()">Sources</button></span>
    <span>Simulated data · Monitoring aid, not a medical diagnosis</span>
  </footer>
  <SourcesDialog ref="sourcesDialog" />
</template>

<style scoped>
.top { display: flex; flex-wrap: wrap; align-items: center; justify-content: space-between; gap: 12px 24px; }
.brand { display: flex; align-items: center; gap: 12px; font-family: var(--display); font-size: 18px; font-weight: 700; }
.meta { display: flex; flex-wrap: wrap; align-items: center; gap: 8px 20px; font-size: 14px; color: var(--muted); }
.crew select {
  font: inherit; color: var(--text); background: var(--panel); border: 1px solid var(--border);
  border-radius: 12px; min-height: 44px; padding: 0 12px;
}
.pill {
  font-size: 12px; font-weight: 600; padding: 4px 10px; border-radius: 99px;
  border: 1px solid var(--accent); color: var(--accent);
}
.sr-only { position: absolute; width: 1px; height: 1px; overflow: hidden; clip: rect(0 0 0 0); }

main { display: flex; flex-direction: column; gap: 24px; margin-top: 24px; }

/* flex-start: the right column stays anchored when the body zone panel grows the ring column
   (with `center` it re-centred and jumped down ~180 px). */
.hero { display: flex; flex-wrap: wrap; gap: 32px; align-items: flex-start; }
.ring-wrap { flex: 1 1 440px; min-width: 0; }
.zone-hint { display: flex; flex-direction: column; align-items: center; gap: 8px; margin-top: 4px; }
.zone-hint p { margin: 0; font-size: 13px; color: var(--muted); }
.zone-chips { display: flex; flex-wrap: wrap; justify-content: center; gap: 6px; }
.zone-chips button {
  min-height: 44px; padding: 0 14px; border-radius: 12px; border: 1px solid var(--border); cursor: pointer;
  background: transparent; color: var(--text-2); font-size: 13px; font-weight: 600;
}
.zone-chips button.muted { color: var(--muted); border-style: dashed; }
.zone-chips button:hover { border-color: var(--border-strong); background: var(--panel-2); }
.zone-chips button[aria-expanded='true'] { border-color: var(--accent-2); border-style: solid; background: var(--panel-2); color: var(--text); }
.intro { flex: 1 1 520px; min-width: 0; display: flex; flex-direction: column; gap: 20px; }
/* Side-by-side layout only (the columns stack below ~1090 px): a small top offset keeps the
   headline where the old centred layout put it next to the ring (~50 px at 1440 px wide). */
@media (min-width: 1100px) { .intro { padding-top: min(3.5vw, 56px); } }
.hello { font-size: 14px; color: var(--muted); }
h1 { margin: -14px 0 0; font-family: var(--display); font-size: clamp(28px, 3.2vw, 40px); line-height: 1.15; font-weight: 600; }
h1 .count { color: var(--accent-2); }

.detail { display: flex; flex-wrap: wrap; gap: 20px; }
.card { background: var(--panel); border: 1px solid var(--border); border-radius: 22px; padding: 24px; }
.chart-card { flex: 999 1 560px; min-width: 0; display: flex; flex-direction: column; gap: 12px; }
.chart-head { display: flex; flex-wrap: wrap; align-items: flex-end; justify-content: space-between; gap: 12px; }
.big { display: flex; flex-direction: column; gap: 4px; }
.label { font-size: 14px; color: var(--muted); }
.num { font-family: var(--display); font-size: 48px; font-weight: 600; line-height: 1; }
.num small { font-size: 20px; color: var(--muted); }
.state { display: flex; align-items: center; gap: 12px; }
.delta { font-size: 15px; color: var(--text-2); }
.reasons { margin: 0; padding-left: 18px; font-size: 14px; color: var(--text-2); line-height: 1.5; }
.periods { display: flex; flex-wrap: wrap; gap: 8px; }
.periods button {
  min-height: 44px; padding: 0 16px; border: 1px solid var(--border); border-radius: 12px; cursor: pointer;
  background: transparent; color: var(--text-2); font-size: 14px; font-weight: 600;
}
.periods button:hover { border-color: var(--border-strong); background: var(--panel-2); }
.periods button[aria-pressed='true'] { background: var(--accent); border-color: var(--accent); color: var(--on-accent); }

.stats { margin: 0; display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 12px 20px; }
@media (max-width: 560px) { .stats { grid-template-columns: repeat(2, minmax(0, 1fr)); } }
.stats div { display: flex; flex-direction: column; gap: 2px; }
.stats dt { font-size: 12px; color: var(--muted); }
.stats dd { margin: 0; font-size: 16px; font-weight: 600; }
.stats small { display: block; font-size: 12px; font-weight: 400; color: var(--muted); }

.sim-note { font-size: 12px; color: var(--muted); }

.guide { flex: 1 1 320px; min-width: 0; display: flex; flex-direction: column; gap: 8px; }
.guide h2 { margin: 8px 0 0; font-size: 15px; font-weight: 600; }
.guide h2:first-child { margin-top: 0; }
.guide p { margin: 0; font-size: 15px; line-height: 1.55; color: var(--text-2); }
.primary {
  margin-top: auto; min-height: 48px; border-radius: 14px; border: none; cursor: pointer;
  background: var(--accent); color: var(--on-accent); font-weight: 600; font-size: 15px;
}
.guide .primary { margin-top: 16px; }
.primary.critical { background: var(--critical); color: var(--on-critical); }

.reminder {
  display: flex; flex-wrap: wrap; align-items: center; gap: 8px 12px; margin-top: 16px;
  padding: 8px 8px 8px 16px; border-radius: 16px; border: 1px solid #5c4a12;
  background: #2a2410; color: var(--text); font-size: 14px;
}
.reminder-icon { width: 18px; height: 18px; flex: none; color: var(--watch); }
.reminder-text { flex: 1 1 220px; }
.reminder button {
  min-height: 44px; padding: 0 16px; border-radius: 10px; border: none; cursor: pointer;
  background: var(--watch); color: var(--on-watch); font-weight: 600; font-size: 14px;
}

.contact-now {
  display: flex; flex-wrap: wrap; align-items: center; justify-content: space-between; gap: 12px 24px;
  padding: 20px 24px; border-radius: 22px; background: var(--panel); border: 1.5px solid var(--critical);
}
.contact-now h2 { margin: 0 0 4px; font-size: 16px; font-weight: 600; }
.contact-now p { margin: 0; font-size: 15px; line-height: 1.5; color: var(--text-2); max-width: 72ch; }
.contact-now .primary { flex: 0 1 280px; min-width: 220px; padding: 0 20px; }

.log-row { display: flex; flex-wrap: wrap; gap: 20px; align-items: flex-start; }
.form-card { flex: 2 1 440px; min-width: 0; }
.checks-card { flex: 1 1 300px; min-width: 0; }
.devices-card { flex: 1 1 300px; min-width: 0; }
.src { font-size: 13px; color: var(--muted); }
.src.device { color: var(--accent); }

.foot {
  display: flex; flex-wrap: wrap; justify-content: space-between; gap: 6px 24px;
  margin-top: 40px; padding-top: 16px; border-top: 1px solid #16292d; font-size: 12px; color: #7f9996;
}
.sources-link {
  padding: 4px 2px; margin: -4px 0; border: none; background: none; cursor: pointer;
  font: inherit; color: inherit; text-decoration: underline; text-underline-offset: 2px;
}
.sources-link:hover { color: var(--text-2); }
.error { color: var(--critical); }
</style>

<script setup lang="ts">
/** Right column: metric tabs + key figures, the 145-day chart, then guidance. */
import { computed, ref, watch } from 'vue'
import type { Alert, IndicatorMeta, IndicatorStatus, Level, TrendResponse } from '../types'
import HistoryChart from './HistoryChart.vue'

const props = defineProps<{
  zoneLabel: string
  metrics: IndicatorStatus[]          // indicators of the selected body zone
  selected: string | null
  trend: TrendResponse | null
  alerts: Alert[]
  meta: Record<string, IndicatorMeta>
}>()
const emit = defineEmits<{ select: [indicator: string]; openAlerts: [] }>()

const SHAPE: Record<Level, string> = { normal: '●', attention: '▲', critical: '■', no_data: '○' }
const WORD: Record<Level, string> = { normal: 'Nominal', attention: 'Attention', critical: 'Critical', no_data: 'No data' }
const SHORT: Record<string, string> = {
  heart_rate: 'Heart Rate', bp_systolic: 'Systolic BP', bp_diastolic: 'Diastolic BP', glucose: 'Blood Glucose',
  temperature: 'Core Temperature', sleep_hours: 'Sleep', mood: 'Mood', alertness: 'Alertness',
  pvt_lapses: 'PVT Lapses', pvt_mean_rt: 'PVT Reaction Time',
}
// Generic, non-prescriptive next steps when a value is off and no cross-indicator alert covers it.
const GENERIC_STEPS = [
  'Measure again after 10 minutes of rest to rule out a one-off reading.',
  'If it stays outside your range, tell the Crew Medical Officer.',
  'Include it in the next report to Mission Control.',
]

const tab = ref<'action' | 'context'>('action')
const current = computed(() => props.metrics.find((m) => m.indicator === props.selected) ?? null)
const info = computed(() => (current.value ? props.meta[current.value.indicator] ?? null : null))
const related = computed(() => props.alerts.filter((a) => current.value && a.indicators.includes(current.value.indicator)))
const hasSimulated = computed(() => props.trend?.points.some((p) => p.source === 'simulated') ?? false)
watch(() => props.selected, () => { tab.value = 'action' })

function fmt(v: number | null, digits = 1): string {
  if (v === null) return '—'
  return Number.isInteger(v) ? String(v) : v.toFixed(digits)
}
const slope = computed(() => {
  const s = current.value?.slope_per_day ?? null
  if (s === null) return '—'
  const r = Math.abs(s) < 0.005 ? 0 : s
  return `${r > 0 ? '+' : ''}${r.toFixed(Math.abs(r) < 1 ? 2 : 1)} ${current.value!.unit}/day`
})
</script>

<template>
  <section class="panel" v-if="current">
    <!-- Top: metric tabs + three key figures -->
    <div class="top">
      <div class="tabs" role="tablist" :aria-label="zoneLabel">
        <button v-for="m in metrics" :key="m.indicator" role="tab" type="button"
          :aria-selected="m.indicator === selected" :class="[m.level, { on: m.indicator === selected }]"
          @click="emit('select', m.indicator)">
          <i aria-hidden="true">{{ SHAPE[m.level] }}</i>{{ SHORT[m.indicator] ?? m.label }}
        </button>
      </div>
      <div class="kpis">
        <div class="kpi" :class="current.level">
          <span>Current value</span>
          <b>{{ fmt(current.value) }} <small>{{ current.unit }}</small></b>
          <em><i aria-hidden="true">{{ SHAPE[current.level] }}</i> {{ WORD[current.level] }}</em>
        </div>
        <div class="kpi">
          <span>{{ current.space_adjusted ? 'Space baseline' : 'Personal baseline' }}</span>
          <b>{{ fmt(current.baseline) }} <small>{{ current.unit }}</small></b>
          <em v-if="current.preflight !== null">On Earth: {{ fmt(current.preflight) }} {{ current.unit }}</em>
        </div>
        <div class="kpi">
          <span>5-day trend</span>
          <b>{{ slope }}</b>
          <em v-if="current.deviation_pct !== null">{{ current.deviation_pct > 0 ? '+' : '' }}{{ current.deviation_pct }}% vs baseline</em>
        </div>
      </div>
    </div>

    <!-- Middle: the chart takes all remaining height -->
    <div class="plot">
      <span v-if="hasSimulated" class="sim">SIMULATED DATA</span>
      <HistoryChart :trend="trend" :label="SHORT[current.indicator] ?? current.label" :unit="current.unit" />
    </div>

    <!-- Bottom: guidance, no accordion -->
    <div class="guide">
      <div class="tabs small" role="tablist" aria-label="Guidance">
        <button role="tab" type="button" :aria-selected="tab === 'action'" :class="{ on: tab === 'action' }" @click="tab = 'action'">Recommended action</button>
        <button role="tab" type="button" :aria-selected="tab === 'context'" :class="{ on: tab === 'context' }" @click="tab = 'context'">NASA HRP context</button>
      </div>

      <div v-if="tab === 'action'" class="content">
        <template v-if="related.length">
          <div v-for="a in related" :key="a.rule" class="rule">
            <p class="head"><i aria-hidden="true">▲</i> <b>{{ a.title }}</b>
              <span v-if="a.blocks_critical_ops" class="tag">Blocks critical operations</span></p>
            <ol><li v-for="s in a.actions" :key="s">{{ s }}</li></ol>
          </div>
          <button type="button" class="link" @click="emit('openAlerts')">See the evidence and sources →</button>
        </template>
        <template v-else-if="current.level === 'critical'">
          <p class="head crit"><i aria-hidden="true">■</i> <b>Contact the Crew Medical Officer now.</b></p>
          <ul><li v-for="r in current.reasons" :key="r">{{ r }}</li></ul>
        </template>
        <template v-else-if="current.level === 'attention'">
          <p class="head"><i aria-hidden="true">▲</i> <b>Outside your usual range.</b></p>
          <ul class="why"><li v-for="r in current.reasons" :key="r">{{ r }}</li></ul>
          <ol><li v-for="s in GENERIC_STEPS" :key="s">{{ s }}</li></ol>
        </template>
        <template v-else>
          <p class="head ok"><i aria-hidden="true">●</i> <b>No action needed.</b></p>
          <ul class="why"><li v-for="r in current.reasons" :key="r">{{ r }}</li></ul>
          <p v-if="current.earth_level !== 'normal' && current.earth_level !== 'no_data'" class="earth">
            An Earth-calibrated tool would raise an alert here. {{ current.earth_reasons.join(' ') }}
          </p>
        </template>
        <p class="fine">Suggestions for the crew, not prescriptions. Monitoring aid only, not a medical diagnosis.</p>
      </div>

      <div v-else class="content">
        <template v-if="info">
          <p><b>What it measures.</b> {{ info.what }}</p>
          <p><b>Why it matters in space.</b> {{ info.why_in_space }}</p>
          <template v-if="current.adaptation">
            <p><b>What is normal in flight.</b> {{ current.adaptation.summary }}</p>
            <p class="fine">{{ current.adaptation.source }}</p>
            <p class="fine">{{ current.adaptation.ramp_basis }}</p>
          </template>
          <p v-if="current.earth_false_alarms > 0">
            <b>{{ current.earth_false_alarms }} false alarms avoided</b> on this indicator: readings an Earth-calibrated
            tool would have flagged although they match normal adaptation.
          </p>
          <p class="fine" v-for="s in info.sources" :key="s"><a :href="s" target="_blank" rel="noopener">{{ s }}</a></p>
        </template>
      </div>
    </div>
  </section>
</template>

<style scoped>
.panel { height: 100%; min-height: 0; display: flex; flex-direction: column; gap: 10px; }
.top { display: flex; flex-direction: column; gap: 10px; flex: none; }
.tabs { display: flex; gap: 6px; flex-wrap: wrap; }
.tabs button { font: inherit; font-size: 14px; padding: 7px 13px; border-radius: 999px; cursor: pointer; white-space: nowrap;
  background: transparent; color: var(--muted); border: 1px solid var(--line); display: flex; align-items: center; gap: 7px; }
.tabs button i { font-style: normal; font-size: 11px; color: var(--ok); }
.tabs button.attention i { color: var(--warn); } .tabs button.critical i { color: var(--crit); }
.tabs button:hover { color: var(--text); }
.tabs button.on { color: #041018; background: var(--cyan); border-color: var(--cyan); font-weight: 600; }
.tabs button.on i { color: #041018; }
.tabs.small button { font-size: 13px; padding: 5px 12px; }

.kpis { display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; }
.kpi { display: flex; flex-direction: column; gap: 1px; padding: 10px 14px; border-radius: 12px; background: var(--panel);
  border: 1px solid var(--line); min-width: 0; }
.kpi.attention { border-color: var(--warn); } .kpi.critical { border-color: var(--crit); }
.kpi span { font-size: 12px; letter-spacing: .06em; text-transform: uppercase; color: var(--muted); }
.kpi b { font-size: 24px; line-height: 1.2; font-variant-numeric: tabular-nums; white-space: nowrap; }
.kpi small { font-size: 13px; font-weight: 400; color: var(--muted); }
.kpi em { font-style: normal; font-size: 12px; color: var(--muted); min-height: 15px; }
.kpi.attention em { color: var(--warn); } .kpi.critical em { color: var(--crit); } .kpi.normal em { color: var(--ok); }
.kpi em i { font-style: normal; }

.plot { position: relative; flex: 1 1 0; min-height: 150px; border-radius: 12px; background: var(--panel); border: 1px solid var(--line);
  padding: 6px 6px 4px; overflow: hidden; }
.sim { position: absolute; left: 12px; top: 10px; z-index: 1; font-size: 12px; font-weight: 700; letter-spacing: .05em;
  background: var(--warn); color: #2b1a00; padding: 1px 7px; border-radius: 5px; }

.guide { flex: none; height: clamp(150px, 27vh, 250px); display: flex; flex-direction: column; gap: 8px; padding: 10px 14px;
  border-radius: 12px; background: var(--panel); border: 1px solid var(--line); min-height: 0; }
.content { flex: 1; min-height: 0; overflow-y: auto; font-size: 14px; line-height: 1.45; padding-right: 6px; }
.content p { margin: 0 0 6px; }
.content ol, .content ul { margin: 0 0 8px; padding-left: 20px; }
.head { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
.head i { font-style: normal; color: var(--warn); }
.head.ok i { color: var(--ok); } .head.crit i { color: var(--crit); }
.why { color: var(--muted); overflow-wrap: anywhere; }
.tag { font-size: 12px; font-weight: 700; padding: 1px 7px; border-radius: 5px; background: var(--crit); color: #fff; }
.earth { border-left: 3px solid var(--cyan); padding-left: 10px; overflow-wrap: anywhere; }
.fine { font-size: 12px; color: var(--muted); overflow-wrap: anywhere; }
.link { font: inherit; font-size: 13px; padding: 0; border: 0; background: none; color: var(--cyan); cursor: pointer; margin-bottom: 6px; }
.rule + .rule { margin-top: 4px; }
</style>

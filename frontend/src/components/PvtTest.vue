<script setup lang="ts">
/**
 * Brief Psychomotor Vigilance Test (PVT-B), after Basner, Mollicone & Dinges (2011):
 * 3 minutes, 1-4 s between stimuli, a lapse is a response of 355 ms or more.
 * https://pmc.ncbi.nlm.nih.gov/articles/PMC3197786
 * Browser timing is NOT hardware-calibrated: indicative only.
 */
import { computed, onBeforeUnmount, ref } from 'vue'
import { api } from '../api'

const props = defineProps<{ astronautId: number }>()
const emit = defineEmits<{ saved: [] }>()

const LAPSE_MS = 355         // PVT-B lapse threshold
const FALSE_START_MS = 100   // faster than this is anticipation, not a reaction
const ISI_MIN = 1000, ISI_MAX = 4000
const TIMEOUT_MS = 30000     // no response at all counts as a lapse

type Phase = 'idle' | 'waiting' | 'stimulus' | 'feedback' | 'done'
const phase = ref<Phase>('idle')
const duration = ref(180)
const alertness = ref(7)
const display = ref('')
const remaining = ref(0)
const rts = ref<number[]>([])
const falseStarts = ref(0)
const timeouts = ref(0)
const saving = ref(false)
const saved = ref(false)
const error = ref('')

let startedAt = 0, shownAt = 0
let timer: number | undefined, raf: number | undefined, clock: number | undefined

const lapses = computed(() => rts.value.filter((r) => r >= LAPSE_MS).length + timeouts.value)
const meanRt = computed(() => (rts.value.length ? rts.value.reduce((a, b) => a + b, 0) / rts.value.length : null))
const speed = computed(() => (rts.value.length
  ? rts.value.reduce((a, b) => a + 1000 / b, 0) / rts.value.length : null))

function clearTimers() {
  if (timer) window.clearTimeout(timer)
  if (raf) cancelAnimationFrame(raf)
  if (clock) window.clearInterval(clock)
  timer = raf = clock = undefined
}

function start() {
  rts.value = []; falseStarts.value = 0; timeouts.value = 0
  saved.value = false; error.value = ''
  startedAt = performance.now()
  remaining.value = duration.value
  clock = window.setInterval(() => {
    remaining.value = Math.max(0, Math.ceil(duration.value - (performance.now() - startedAt) / 1000))
  }, 250)
  window.addEventListener('keydown', onKey)
  nextTrial()
}

function nextTrial() {
  if (performance.now() - startedAt >= duration.value * 1000) return finish()
  phase.value = 'waiting'
  display.value = ''
  timer = window.setTimeout(showStimulus, ISI_MIN + Math.random() * (ISI_MAX - ISI_MIN))
}

function showStimulus() {
  phase.value = 'stimulus'
  shownAt = performance.now()
  const tick = () => {
    const elapsed = performance.now() - shownAt
    if (elapsed >= TIMEOUT_MS) { timeouts.value++; display.value = 'No response'; return afterResponse() }
    display.value = `${Math.round(elapsed)}`
    raf = requestAnimationFrame(tick)
  }
  raf = requestAnimationFrame(tick)
}

function respond() {
  if (phase.value === 'waiting') {
    falseStarts.value++
    display.value = 'Too early'
    if (timer) window.clearTimeout(timer)
    return afterResponse()
  }
  if (phase.value !== 'stimulus') return
  const rt = performance.now() - shownAt
  if (raf) cancelAnimationFrame(raf)
  if (rt < FALSE_START_MS) { falseStarts.value++; display.value = 'Too early' }
  else { rts.value.push(rt); display.value = `${Math.round(rt)} ms` }
  afterResponse()
}

function afterResponse() {
  phase.value = 'feedback'
  timer = window.setTimeout(nextTrial, 1000)  // result stays visible for 1 s
}

function finish() {
  clearTimers()
  window.removeEventListener('keydown', onKey)
  phase.value = 'done'
}

function onKey(e: KeyboardEvent) {
  if (e.code === 'Space') { e.preventDefault(); if (!e.repeat) respond() }
}

async function save() {
  if (meanRt.value === null) { error.value = 'No valid response recorded.'; return }
  saving.value = true; error.value = ''
  try {
    await api.addMeasurement(props.astronautId, 'alertness', alertness.value)
    await api.addMeasurement(props.astronautId, 'pvt_lapses', lapses.value)
    await api.addMeasurement(props.astronautId, 'pvt_mean_rt', Math.round(meanRt.value))
    saved.value = true
    emit('saved')
  } catch (e) {
    error.value = (e as Error).message
  } finally {
    saving.value = false
  }
}

onBeforeUnmount(() => { clearTimers(); window.removeEventListener('keydown', onKey) })
</script>

<template>
  <div class="pvt">
    <div v-if="phase === 'idle' || phase === 'done'" class="setup">
      <p class="how">
        First rate how alert you feel. Then a counter appears at random moments: press
        <kbd>Space</kbd> or tap the box as fast as you can each time. The tool compares how you
        feel with how you perform.
      </p>
      <label>How alert do you feel right now? <b>{{ alertness }}/10</b>
        <input type="range" min="0" max="10" step="1" v-model.number="alertness" />
      </label>
      <label>Length
        <select v-model.number="duration">
          <option :value="180">3 minutes (standard PVT-B)</option>
          <option :value="60">1 minute (demo only, not the validated length)</option>
        </select>
      </label>
      <button class="go" @click="start">{{ phase === 'done' ? 'Run again' : 'Start test' }}</button>
    </div>

    <div v-else class="run">
      <div class="box" :class="phase" @pointerdown.prevent="respond">
        <span v-if="phase === 'waiting'" class="hint">Wait for the counter…</span>
        <span v-else class="num">{{ display }}</span>
      </div>
      <div class="meta">{{ remaining }} s left · {{ rts.length }} responses · press Space or tap</div>
    </div>

    <div v-if="phase === 'done'" class="result">
      <div><b>{{ lapses }}</b><span>lapses (≥ {{ LAPSE_MS }} ms)</span></div>
      <div><b>{{ meanRt === null ? '—' : Math.round(meanRt) }}</b><span>mean reaction time (ms)</span></div>
      <div><b>{{ falseStarts }}</b><span>false starts</span></div>
      <div><b>{{ speed === null ? '—' : speed.toFixed(2) }}</b><span>response speed (1/s)</span></div>
      <div><b>{{ alertness }}/10</b><span>self-rated alertness</span></div>
      <button class="go" :disabled="saving || saved" @click="save">{{ saved ? 'Saved' : 'Save to my record' }}</button>
      <p v-if="error" class="error">{{ error }}</p>
    </div>

    <p class="note">
      Method: Basner, Mollicone &amp; Dinges, Acta Astronautica 2011 (3 min, 1–4 s intervals, lapse ≥ 355 ms).
      Timing in a browser is not hardware-calibrated; results are indicative.
    </p>
  </div>
</template>

<style scoped>
.pvt h3 { margin: 0 0 8px; }
.how { margin: 0 0 10px; line-height: 1.5; }
.setup { display: flex; flex-direction: column; gap: 12px; max-width: 560px; }
label { display: flex; flex-direction: column; gap: 6px; font-size: 15px; }
select, input[type='range'] { font: inherit; }
select { padding: 8px 10px; border-radius: 8px; border: 1px solid var(--border); background: var(--bg); color: inherit; }
kbd { border: 1px solid var(--border); border-radius: 4px; padding: 0 6px; background: var(--bg); }
.go { align-self: flex-start; font: inherit; font-weight: 600; padding: 10px 18px; border-radius: 8px; border: none;
  background: var(--accent); color: #001; cursor: pointer; }
.go:disabled { opacity: .6; cursor: default; }
.box { height: 200px; border-radius: 12px; border: 2px solid var(--border); background: #05070f; display: flex;
  align-items: center; justify-content: center; cursor: pointer; user-select: none; touch-action: manipulation; }
.box.stimulus { border-color: var(--crit); }
.num { font-size: 64px; font-weight: 700; font-variant-numeric: tabular-nums; color: #ffd84d; }
.box.feedback .num { color: var(--text); font-size: 44px; }
.hint { color: var(--muted); }
.meta { margin-top: 6px; font-size: 13px; color: var(--muted); }
.result { display: flex; flex-wrap: wrap; gap: 18px; align-items: center; margin-top: 14px; }
.result div { display: flex; flex-direction: column; }
.result b { font-size: 26px; }
.result span { font-size: 12px; color: var(--muted); }
.note { font-size: 12px; color: var(--muted); margin: 12px 0 0; }
.error { color: var(--crit); width: 100%; margin: 0; }
</style>

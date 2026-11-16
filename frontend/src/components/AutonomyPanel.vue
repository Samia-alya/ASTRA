<script setup lang="ts">
// Earth-independent mode panel: onboard monitoring steps, report transmission and signal countdown.
// Monitoring and communication only: no diagnosis, no medication, no treatment.
import { computed, onUnmounted, ref, watch } from 'vue'
import { api } from '../api'
import { duration } from '../environments'
import { formatUtc } from '../report'
import type { AutonomyResponse } from '../types'

const props = defineProps<{ astronautId: number; data: AutonomyResponse }>()
const emit = defineEmits<{ changed: []; preview: [] }>()

const busy = ref(false)
const error = ref('')

const delay = computed(() => props.data.autonomy.one_way_delay_s)
const reply = computed(() => props.data.autonomy.earliest_reply_s)
const checkedCount = computed(() =>
  props.data.groups.reduce((n, g) => n + g.steps.filter((s) => s.checked_at).length, 0),
)
// What the last report actually contained (frozen when it was sent), not what is checked now.
const sentCount = computed(() => props.data.report_steps.length)
const newCount = computed(() => props.data.new_steps_since_report)

function plural(n: number, word: string): string {
  return `${n} ${word}${n === 1 ? '' : 's'}`
}

function hhmm(iso: string): string {
  return formatUtc(new Date(iso)).slice(11)
}

async function toggle(indicator: string, index: number, checked: boolean) {
  error.value = ''
  try {
    await api.setStep(props.astronautId, indicator, index, checked)
    emit('changed')
  } catch (e) {
    error.value = `Could not save this step: ${(e as Error).message}. Try again.`
  }
}

async function send() {
  busy.value = true
  error.value = ''
  try {
    await api.sendReport(props.astronautId)
    emit('changed')
  } catch (e) {
    error.value = `Could not record the transmission: ${(e as Error).message}. Try again.`
  } finally {
    busy.value = false
  }
}

// --- Countdown -----------------------------------------------------------------
// Simulated clock: real time × speed, accumulated tick by tick so switching speed never jumps back.
const demoSpeed = ref(false)
const elapsed = ref(0) // simulated seconds since the report was sent
let last = Date.now()

watch(
  () => props.data.report_sent_at,
  (sent) => {
    elapsed.value = sent ? Math.max((Date.now() - new Date(sent).getTime()) / 1000, 0) : 0
    last = Date.now()
  },
  { immediate: true },
)

const timer = window.setInterval(() => {
  const now = Date.now()
  if (props.data.report_sent_at) elapsed.value += ((now - last) / 1000) * (demoSpeed.value ? 60 : 1)
  last = now
}, 250)
onUnmounted(() => window.clearInterval(timer))

const phase = computed<'not_sent' | 'in_transit' | 'awaiting' | 'replied'>(() => {
  if (!props.data.report_sent_at) return 'not_sent'
  if (elapsed.value < delay.value) return 'in_transit'
  if (elapsed.value < reply.value) return 'awaiting'
  return 'replied'
})

function mmss(s: number): string {
  const t = Math.max(Math.ceil(s), 0)
  return `${String(Math.floor(t / 60)).padStart(2, '0')}:${String(t % 60).padStart(2, '0')}`
}

const countdown = computed(() => {
  if (phase.value === 'in_transit') return { label: 'Reaches Earth in', value: mmss(delay.value - elapsed.value) }
  if (phase.value === 'awaiting') return { label: 'Earliest reply in', value: mmss(reply.value - elapsed.value) }
  return null
})
</script>

<template>
  <section class="autonomy" aria-labelledby="autonomy-title">
    <div class="banner">
      <svg viewBox="0 0 20 20" aria-hidden="true">
        <path d="M10 2.5 L18 17 H2 Z" fill="none" stroke="currentColor" stroke-width="2" stroke-linejoin="round" />
        <path d="M10 8 V11.5 M10 14 V14.2" stroke="currentColor" stroke-width="2" stroke-linecap="round" />
      </svg>
      <h2 id="autonomy-title">Earth cannot respond in time — act on board</h2>
    </div>

    <dl class="facts">
      <div><dt>One-way signal delay</dt><dd>{{ duration(delay) }}</dd></div>
      <div><dt>Earliest reply from Earth</dt><dd>{{ duration(reply) }}</dd></div>
      <div><dt>Mode</dt><dd>Earth-independent</dd></div>
    </dl>
    <p class="reason">{{ data.autonomy.reason }}</p>

    <div class="cols">
      <div class="steps">
        <div v-for="g in data.groups" :key="g.indicator" class="group">
          <h3>{{ g.label }} · onboard monitoring steps</h3>
          <ul>
            <li v-for="s in g.steps" :key="s.index" :class="{ checked: s.checked_at }">
              <label>
                <input type="checkbox" :checked="!!s.checked_at"
                  @change="toggle(g.indicator, s.index, ($event.target as HTMLInputElement).checked)" />
                <span class="text">{{ s.text }}</span>
              </label>
              <span class="time">{{ s.checked_at ? `Done ${hhmm(s.checked_at)}` : 'To do' }}</span>
            </li>
          </ul>
        </div>
        <p class="note">Monitoring and communication steps only. Not a diagnosis or a treatment plan.</p>
      </div>

      <div class="link">
        <h3>Report to Earth</h3>
        <p v-if="!data.report_sent_at" class="sub">
          Will include {{ plural(checkedCount, 'checked step') }} with their times.
        </p>
        <template v-else>
          <p class="sub">Last report included {{ plural(sentCount, 'checked step') }} with their times.</p>
          <p v-if="newCount" class="new">{{ plural(newCount, 'new step') }} since last report</p>
        </template>
        <div class="buttons">
          <button type="button" class="send" :disabled="busy" @click="send">
            {{ data.report_sent_at ? 'Send updated report to Earth' : 'Send report to Earth' }}
          </button>
          <button type="button" class="ghost" aria-haspopup="dialog" @click="emit('preview')">Preview report</button>
        </div>

        <p v-if="data.report_sent_at" class="sent">Sent {{ hhmm(data.report_sent_at) }}</p>

        <div v-if="countdown" class="countdown">
          <span class="c-label" role="status">{{ countdown.label }}</span>
          <span class="c-value">{{ countdown.value }}</span>
        </div>

        <div v-if="phase === 'replied'" class="reply" role="status">
          <span class="sim">SIMULATED</span>
          <p><strong>Flight surgeon, Houston:</strong> Report received with {{ plural(sentCount, 'onboard step') }}
            logged. Keep following the onboard monitoring steps and the
            2-hour re-measurement schedule. Send an updated report after your next measurement.</p>
          <p class="sim-note">Simulated reply for the demo. No real flight surgeon is connected.</p>
        </div>

        <button type="button" class="speed" :aria-pressed="demoSpeed" @click="demoSpeed = !demoSpeed">
          <span class="switch" aria-hidden="true"><span /></span>
          Demo speed ×60
          <span class="sim">Simulation</span>
        </button>

        <p v-if="error" class="error" role="alert">{{ error }}</p>
      </div>
    </div>
  </section>
</template>

<style scoped>
.autonomy {
  display: flex; flex-direction: column; gap: 16px; padding: 24px;
  background: var(--panel); border: 1.5px solid var(--critical); border-radius: 22px;
}
.banner {
  display: flex; align-items: center; gap: 12px; padding: 12px 16px; margin: -8px -8px 0;
  border-radius: 14px; background: var(--critical); color: var(--on-critical);
}
.banner svg { width: 22px; height: 22px; flex: none; }
.banner h2 { margin: 0; font-family: var(--display); font-size: 18px; font-weight: 600; line-height: 1.3; }

.facts { margin: 0; display: flex; flex-wrap: wrap; gap: 8px 32px; }
.facts div { display: flex; flex-direction: column; gap: 2px; }
.facts dt { font-size: 12px; color: var(--muted); }
.facts dd { margin: 0; font-family: var(--display); font-size: 20px; font-weight: 600; }
.reason { margin: 0; font-size: 15px; line-height: 1.5; color: var(--text-2); max-width: 72ch; }

.cols { display: flex; flex-wrap: wrap; gap: 24px; }
.steps { flex: 2 1 420px; min-width: 0; display: flex; flex-direction: column; gap: 16px; }
.link {
  flex: 1 1 280px; min-width: 0; display: flex; flex-direction: column; gap: 12px;
  padding: 16px; border-radius: 16px; background: var(--panel-2);
}
h3 { margin: 0; font-size: 15px; font-weight: 600; }
.group { display: flex; flex-direction: column; gap: 8px; }
ul { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; }
li {
  display: flex; align-items: center; justify-content: space-between; gap: 12px;
  border-bottom: 1px solid var(--border); min-height: 48px;
}
li:last-child { border-bottom: none; }
label { display: flex; align-items: center; gap: 12px; flex: 1; min-width: 0; padding: 8px 0; cursor: pointer; }
input[type='checkbox'] { width: 22px; height: 22px; flex: none; accent-color: var(--accent); cursor: pointer; }
.text { font-size: 15px; line-height: 1.4; }
li.checked .text { color: var(--muted); }
.time { font-size: 13px; color: var(--muted); white-space: nowrap; }
li.checked .time { color: var(--nominal); }
.note { margin: 0; font-size: 12px; color: var(--muted); }

.sub { margin: -6px 0 0; font-size: 13px; color: var(--muted); }
.buttons { display: flex; flex-wrap: wrap; gap: 8px; }
.buttons button {
  flex: 1 1 140px; min-height: 48px; border-radius: 14px; cursor: pointer; font-weight: 600; font-size: 15px;
}
.send { background: var(--critical); color: var(--on-critical); border: none; }
.send:disabled { opacity: .6; cursor: progress; }
.ghost { background: transparent; color: var(--text); border: 1.5px solid var(--border-strong); }
.ghost:hover { background: var(--panel); }
.sent { margin: 0; font-size: 13px; color: var(--text-2); }
.new {
  align-self: flex-start; margin: -4px 0 0; font-size: 13px; font-weight: 600; color: var(--watch);
}

.countdown { display: flex; flex-direction: column; gap: 2px; }
.c-label { font-size: 13px; color: var(--muted); }
.c-value { font-family: var(--display); font-size: 40px; font-weight: 600; line-height: 1; font-variant-numeric: tabular-nums; }

.reply {
  display: flex; flex-direction: column; gap: 6px; padding: 12px 14px; border-radius: 12px;
  border: 1.5px dashed var(--watch); background: var(--panel);
}
.reply p { margin: 0; font-size: 14px; line-height: 1.5; }
.sim {
  align-self: flex-start; font-size: 11px; font-weight: 700; letter-spacing: .06em; padding: 3px 8px;
  border-radius: 99px; background: var(--watch); color: var(--on-watch);
}
.reply .sim-note { font-size: 12px; color: var(--muted); }

.speed {
  display: flex; align-items: center; gap: 10px; min-height: 44px; padding: 0 4px; cursor: pointer;
  background: transparent; border: none; color: var(--text-2); font-size: 14px; font-weight: 600;
}
.speed .sim { align-self: center; }
.switch {
  width: 36px; height: 20px; border-radius: 99px; background: var(--track); border: 1px solid var(--border-strong);
  position: relative; flex: none; transition: background .15s;
}
.switch span {
  position: absolute; top: 2px; left: 2px; width: 14px; height: 14px; border-radius: 50%;
  background: var(--muted); transition: transform .15s;
}
.speed[aria-pressed='true'] .switch { background: var(--watch); border-color: var(--watch); }
.speed[aria-pressed='true'] .switch span { transform: translateX(16px); background: var(--on-watch); }
.error { margin: 0; color: var(--critical); font-size: 14px; }

@media (max-width: 480px) {
  .autonomy { padding: 16px; }
  .banner { margin: 0; }
}
</style>

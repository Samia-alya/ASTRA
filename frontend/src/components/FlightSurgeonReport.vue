<script setup lang="ts">
import { computed, nextTick, ref, watch } from 'vue'
import type { EnvironmentInfo } from '../environments'
import { buildReport, type OnboardLog, REPORT_FOOTER, REPORT_TITLE, reportSections } from '../report'
import type { IndicatorMeta, StatusResponse } from '../types'

const props = defineProps<{
  open: boolean
  status: StatusResponse
  meta: Record<string, IndicatorMeta>
  env: EnvironmentInfo
  /** Earth-independent mode only: checked onboard steps and last transmission. */
  onboard?: OnboardLog | null
}>()
const emit = defineEmits<{ close: []; send: [] }>()

const dialog = ref<HTMLDialogElement | null>(null)
const note = ref('')
const generatedAt = ref(new Date())
const copyState = ref<'idle' | 'copied' | 'failed'>('idle')
const sent = ref(false)
let opener: HTMLElement | null = null
let copyTimer: number | undefined

const onboard = computed(() => props.onboard ?? null)
const r = computed(() => reportSections(props.status, props.meta, props.env, generatedAt.value, onboard.value))
const reportText = computed(() =>
  buildReport(props.status, props.meta, props.env, note.value, generatedAt.value, onboard.value),
)
const autonomous = computed(() => props.status.autonomy.active)
const isCritical = computed(() => r.value.overallLevel === 'critical')

watch(
  () => props.open,
  async (open) => {
    const el = dialog.value
    if (!el) return
    if (open && !el.open) {
      opener = document.activeElement instanceof HTMLElement ? document.activeElement : null
      generatedAt.value = new Date()
      copyState.value = 'idle'
      sent.value = false
      el.showModal()
      await nextTick()
      el.querySelector<HTMLElement>('textarea')?.focus()
    } else if (!open && el.open) {
      el.close()
    }
  },
  { flush: 'post' },
)

// Fires for Esc, the Close button and programmatic close alike.
function onClose() {
  emit('close')
  opener?.focus()
  opener = null
}

async function copy() {
  window.clearTimeout(copyTimer)
  try {
    if (!navigator.clipboard?.writeText) throw new Error('Clipboard API unavailable')
    await navigator.clipboard.writeText(reportText.value)
    copyState.value = 'copied'
    copyTimer = window.setTimeout(() => (copyState.value = 'idle'), 2500)
  } catch {
    copyState.value = 'failed'
    await nextTick()
    dialog.value?.querySelector<HTMLTextAreaElement>('.fallback textarea')?.select()
  }
}

function send() {
  sent.value = true
  emit('send')
}
</script>

<template>
  <dialog ref="dialog" class="report" aria-labelledby="fs-report-title" @close="onClose">
    <div class="scroll">
      <p v-if="isCritical && autonomous" class="banner" role="alert">
        <strong>Earth-independent mode.</strong> A reply from Earth takes at least
        {{ Math.round(status.autonomy.earliest_reply_s / 60) }} min. Keep following the onboard monitoring steps.
      </p>
      <p v-else-if="isCritical" class="banner" role="alert">
        <strong>Critical.</strong> Contact the flight surgeon now. Do not wait for the next scheduled check-in.
      </p>

      <h2 id="fs-report-title">{{ REPORT_TITLE }}</h2>

      <dl class="facts">
        <div><dt>Crew member</dt><dd>{{ r.crew }}</dd></div>
        <div><dt>Mission</dt><dd>{{ r.mission }}</dd></div>
        <div><dt>Environment</dt><dd>{{ r.environment }}</dd></div>
        <div><dt>Mission day</dt><dd>{{ r.missionDay }}</dd></div>
        <div><dt>Generated</dt><dd>{{ r.generated }}</dd></div>
        <div><dt>Overall level</dt><dd><span class="tag" :class="r.overallLevel">{{ r.overallLabel }}</span></dd></div>
      </dl>

      <h3>Flagged indicators</h3>
      <p v-if="!r.flagged.length" class="nominal">All indicators nominal.</p>
      <ul v-else class="flagged">
        <li v-for="f in r.flagged" :key="f.key" :class="f.level">
          <div class="row">
            <span class="name">{{ f.label }}</span>
            <span class="tag" :class="f.level">{{ f.levelLabel }}</span>
          </div>
          <div class="values">
            <span><span class="k">Now</span> {{ f.value }}</span>
            <span><span class="k">Personal baseline</span> {{ f.baseline }}</span>
          </div>
          <ul class="reasons">
            <li v-for="reason in f.reasons" :key="reason">{{ reason }}</li>
          </ul>
        </li>
      </ul>

      <h3>Other indicators</h3>
      <ul class="others">
        <li v-for="o in r.others" :key="o.key"><span>{{ o.label }}</span><span>{{ o.value }}</span></li>
      </ul>

      <template v-if="r.onboard">
        <h3>Onboard actions (Earth-independent mode)</h3>
        <p v-if="!r.onboard.actions.length" class="nominal">No onboard step checked yet.</p>
        <ul v-else class="others">
          <li v-for="a in r.onboard.actions" :key="a.indicator + a.step">
            <span>{{ a.indicator }}: {{ a.step }}</span><span>{{ a.at }}</span>
          </li>
        </ul>
        <p v-if="r.onboard.sentAt" class="nominal">Last sent to Earth: {{ r.onboard.sentAt }}</p>
      </template>

      <label class="note">
        <span>Note to flight surgeon</span>
        <textarea v-model="note" rows="3" placeholder="Symptoms, what you have already tried, questions…" />
      </label>

      <div v-if="copyState === 'failed'" class="fallback">
        <p role="alert">Clipboard unavailable in this browser. Select the text below and copy it manually.</p>
        <textarea readonly rows="8" :value="reportText" aria-label="Report text" />
      </div>

      <p v-if="sent" class="sent" role="status">
        Report queued for transmission. Estimated arrival: {{ env.delay }}.
      </p>

      <p class="footer">{{ REPORT_FOOTER }}</p>
    </div>

    <div class="actions">
      <button type="button" class="btn" @click="copy">
        <span aria-live="polite">{{ copyState === 'copied' ? 'Copied' : 'Copy report' }}</span>
      </button>
      <button type="button" class="btn" :class="isCritical ? 'danger' : 'primary'" @click="send">
        Send to Earth
      </button>
      <button type="button" class="btn ghost" @click="dialog?.close()">Close</button>
    </div>
  </dialog>
</template>

<style scoped>
.report {
  width: min(720px, calc(100vw - 24px));
  max-height: calc(100dvh - 24px);
  padding: 0;
  border: 1.5px solid var(--border-strong);
  border-radius: 20px;
  background: var(--panel);
  color: var(--text);
  overflow: hidden;
}
.report[open] { display: flex; flex-direction: column; }
.report::backdrop { background: rgba(5, 6, 8, 0.82); }

.scroll { overflow-y: auto; padding: 24px; display: flex; flex-direction: column; gap: 12px; }

.banner {
  margin: 0; padding: 12px 16px; border-radius: 12px;
  background: var(--critical); color: var(--on-critical); font-size: 15px; line-height: 1.45;
}

h2 { margin: 0; font-family: var(--display); font-size: 20px; font-weight: 600; line-height: 1.25; }
h3 { margin: 8px 0 0; font-size: 15px; font-weight: 600; }

.facts {
  margin: 0; display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 10px 16px;
}
.facts div { display: flex; flex-direction: column; gap: 2px; }
.facts dt { font-size: 12px; color: var(--muted); }
.facts dd { margin: 0; font-size: 15px; }

.nominal { margin: 0; color: var(--text-2); }

.flagged, .others, .reasons { list-style: none; margin: 0; padding: 0; }
.flagged { display: flex; flex-direction: column; gap: 10px; }
.flagged > li {
  background: var(--panel-2); border-radius: 14px; padding: 14px 16px;
  border-left: 4px solid var(--watch); display: flex; flex-direction: column; gap: 6px;
}
.flagged > li.critical { border-left-color: var(--critical); }
.row { display: flex; align-items: center; justify-content: space-between; gap: 12px; }
.name { font-weight: 600; }
.values { display: flex; flex-wrap: wrap; gap: 4px 20px; font-size: 15px; }
.k { color: var(--muted); font-size: 13px; margin-right: 4px; }
.reasons { display: flex; flex-direction: column; gap: 2px; font-size: 14px; line-height: 1.45; color: var(--text-2); }
.reasons li::before { content: '•'; margin-right: 8px; color: var(--muted); }

.others { display: flex; flex-direction: column; }
.others li {
  display: flex; justify-content: space-between; gap: 12px; padding: 8px 0;
  border-bottom: 1px solid var(--border); font-size: 15px;
}
.others li span:first-child { color: var(--text-2); }

.note { display: flex; flex-direction: column; gap: 6px; margin-top: 8px; font-size: 14px; font-weight: 600; }
textarea {
  font: inherit; font-size: 16px; font-weight: 400; color: var(--text); background: var(--bg);
  border: 1.5px solid var(--border-strong); border-radius: 12px; padding: 10px 12px; resize: vertical;
}
textarea::placeholder { color: var(--muted); }

.fallback { display: flex; flex-direction: column; gap: 6px; }
.fallback p { margin: 0; color: var(--watch); font-size: 14px; }
.fallback textarea { font-family: ui-monospace, Consolas, monospace; font-size: 13px; }

.sent {
  margin: 0; padding: 12px 16px; border-radius: 12px; font-size: 15px;
  background: var(--panel-2); color: var(--text); border: 1px solid var(--accent);
}
.footer { margin: 4px 0 0; font-size: 12px; color: var(--muted); }

.actions {
  display: flex; flex-wrap: wrap; gap: 10px; padding: 16px 24px;
  border-top: 1px solid var(--border); background: var(--panel);
}
.btn {
  flex: 1 1 140px; min-height: 48px; border-radius: 14px; cursor: pointer;
  font-weight: 600; font-size: 15px; border: 1.5px solid var(--border-strong);
  background: transparent; color: var(--text);
}
.btn.primary { background: var(--accent); color: var(--on-accent); border-color: var(--accent); }
.btn.danger { background: var(--critical); color: var(--on-critical); border-color: var(--critical); }
.btn.ghost { flex: 0 1 110px; }

@media (max-width: 480px) {
  .scroll { padding: 18px 16px; }
  .actions { padding: 12px 16px; }
  .btn.ghost { flex: 1 1 100%; }
}
</style>

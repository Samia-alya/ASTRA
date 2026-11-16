<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { BODY_ZONES } from '../bodyZones'
import type { IndicatorStatus } from '../types'
import { fmt, LEVEL_LABEL, LEVEL_ORDER } from '../types'

const props = defineProps<{ zone: string; indicators: IndicatorStatus[]; selected: string | null }>()
const emit = defineEmits<{ select: [indicator: string]; close: [] }>()

const heading = ref<HTMLHeadingElement | null>(null)
const info = computed(() => BODY_ZONES[props.zone])
const rows = computed(() => props.indicators.filter((i) => i.body_zone === props.zone))
const worst = computed(() => [...rows.value].sort((a, b) => LEVEL_ORDER[a.level] - LEVEL_ORDER[b.level])[0])
const monitored = computed(() => !!info.value?.monitored && rows.value.length > 0)

const root = ref<HTMLElement | null>(null)

/** Scroll the panel into view if it is not fully visible (smooth unless reduced motion is preferred). */
function reveal() {
  const el = root.value
  if (!el) return
  const r = el.getBoundingClientRect()
  if (r.top >= 0 && r.bottom <= window.innerHeight) return
  const smooth = !window.matchMedia('(prefers-reduced-motion: reduce)').matches
  el.scrollIntoView({ block: 'nearest', behavior: smooth ? 'smooth' : 'auto' })
}

/** Move focus to the heading without a second scroll jump (reveal() handles scrolling). */
function focusHeading() {
  heading.value?.focus({ preventScroll: true })
}
defineExpose({ focusHeading, reveal })

// Esc closes the panel, unless a modal dialog (e.g. the flight surgeon report) is open.
function onKey(e: KeyboardEvent) {
  if (e.key === 'Escape' && !e.defaultPrevented && !document.querySelector('dialog[open]')) emit('close')
}
onMounted(() => document.addEventListener('keydown', onKey))
onBeforeUnmount(() => document.removeEventListener('keydown', onKey))
</script>

<template>
  <section v-if="info" id="body-zone-panel" ref="root" class="panel" aria-labelledby="body-zone-title">
    <div class="head">
      <h2 id="body-zone-title" ref="heading" tabindex="-1">{{ info.name }}</h2>
      <span v-if="monitored && worst" class="tag" :class="worst.level">{{ LEVEL_LABEL[worst.level] }}</span>
      <span v-else class="pill-muted">Not monitored in this prototype</span>
      <button type="button" class="close" aria-label="Close body zone panel" @click="emit('close')">
        <svg viewBox="0 0 20 20" aria-hidden="true">
          <path d="M5 5 L15 15 M15 5 L5 15" stroke="currentColor" stroke-width="2" stroke-linecap="round" />
        </svg>
      </button>
    </div>

    <dl class="texts">
      <div><dt>Function</dt><dd>{{ info.function }}</dd></div>
      <div><dt>In space</dt><dd>{{ info.inSpace }}</dd></div>
    </dl>

    <ul v-if="monitored" class="rows" aria-label="Indicators for this body part">
      <li v-for="r in rows" :key="r.indicator">
        <button type="button" :aria-pressed="r.indicator === selected" @click="emit('select', r.indicator)">
          <span class="label">{{ r.label }}</span>
          <span class="value">{{ fmt(r.value, r.unit) }} <small>{{ r.unit }}</small></span>
          <span class="tag" :class="r.level">{{ LEVEL_LABEL[r.level] }}</span>
        </button>
      </li>
    </ul>
  </section>
</template>

<style scoped>
.panel {
  margin-top: 12px; padding: 18px 20px; border-radius: 22px; background: var(--panel); border: 1px solid var(--border);
  display: flex; flex-direction: column; gap: 12px; animation: appear .2s ease-out;
}
@keyframes appear { from { opacity: 0; transform: translateY(4px); } to { opacity: 1; transform: none; } }

.head { display: flex; align-items: center; flex-wrap: wrap; gap: 8px 12px; }
h2 { margin: 0; font-family: var(--display); font-size: 18px; font-weight: 600; flex: 1 1 auto; }
h2:focus-visible { outline-offset: 4px; }
.pill-muted {
  font-size: 12px; font-weight: 600; padding: 4px 10px; border-radius: 99px;
  border: 1px solid var(--border-strong); color: var(--muted);
}
.close {
  width: 44px; height: 44px; flex: none; display: grid; place-items: center; margin: -8px -10px -8px 0;
  border: none; border-radius: 12px; background: transparent; color: var(--muted); cursor: pointer;
}
.close:hover { background: var(--panel-2); color: var(--text); }
.close svg { width: 18px; height: 18px; }

.texts { margin: 0; display: flex; flex-direction: column; gap: 10px; }
.texts dt { font-size: 12px; font-weight: 600; color: var(--muted); text-transform: uppercase; letter-spacing: .04em; }
.texts dd { margin: 2px 0 0; font-size: 14.5px; line-height: 1.5; color: var(--text-2); }

.rows { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: 6px; }
.rows button {
  width: 100%; min-height: 48px; display: grid; grid-template-columns: 1fr auto auto; align-items: center; gap: 12px;
  padding: 6px 12px; border-radius: 14px; border: 1px solid var(--border); background: transparent;
  color: var(--text); text-align: left; cursor: pointer;
}
.rows button:hover { border-color: var(--border-strong); }
.rows button[aria-pressed='true'] { border-color: var(--accent-2); background: var(--panel-2); }
.rows .label { font-size: 14px; color: var(--text-2); min-width: 0; }
.rows .value { font-size: 15px; font-weight: 600; white-space: nowrap; }
.rows small { font-size: 12px; font-weight: 400; color: var(--muted); }
</style>

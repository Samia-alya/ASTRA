<script setup lang="ts">
import { computed, nextTick, ref, watch } from 'vue'
import { api } from '../api'
import type { IndicatorMeta } from '../types'
import { allowedText, validateValue } from '../validation'

const props = defineProps<{ astronautId: number; indicators: Record<string, IndicatorMeta>; preset: string | null }>()
const emit = defineEmits<{ saved: [] }>()

const indicator = ref(props.preset ?? Object.keys(props.indicators)[0] ?? '')
// v-model.number gives '' for an empty field, so anything that is not a number counts as empty.
const value = ref<number | string | null>(null)
const error = ref('') // backend / network errors
const busy = ref(false)
const valueInput = ref<HTMLInputElement | null>(null)

watch(() => props.preset, (p) => { if (p) indicator.value = p })

// Plausibility limits for data entry only, not medical thresholds (see src/validation.ts).
const current = computed(() => props.indicators[indicator.value])
const limits = computed(() => current.value?.input)
const hint = computed(() => allowedText(current.value))
const numeric = computed(() => (typeof value.value === 'number' ? value.value : null))
const invalidMsg = computed(() => (numeric.value === null ? '' : validateValue(current.value, numeric.value)))
const canSave = computed(() => numeric.value !== null && !invalidMsg.value && !busy.value)
const shownError = computed(() => invalidMsg.value || error.value)

// A new value or indicator makes an earlier server error stale.
watch([value, indicator], () => { error.value = '' })

/** Preselect an indicator, then bring the value input into view and focus it. */
async function logNow(key: string) {
  indicator.value = key
  error.value = ''
  await nextTick()
  const input = valueInput.value
  if (!input) return
  const smooth = !window.matchMedia('(prefers-reduced-motion: reduce)').matches
  input.scrollIntoView({ block: 'center', behavior: smooth ? 'smooth' : 'auto' })
  input.focus({ preventScroll: true })
}
defineExpose({ logNow })

async function submit() {
  if (!canSave.value || numeric.value === null) return
  error.value = ''
  busy.value = true
  try {
    await api.addMeasurement(props.astronautId, indicator.value, numeric.value)
    value.value = null
    emit('saved')
  } catch (e) {
    error.value = (e as Error).message
  } finally {
    busy.value = false
  }
}
</script>

<template>
  <form class="form" novalidate @submit.prevent="submit">
    <h2>Log a measurement</h2>
    <label class="field">
      <span>Indicator</span>
      <select v-model="indicator">
        <option v-for="(meta, key) in indicators" :key="key" :value="key">{{ meta.label }} ({{ meta.unit }})</option>
      </select>
    </label>
    <label class="field">
      <span>Value</span>
      <input ref="valueInput" v-model.number="value" type="number" inputmode="decimal" placeholder="e.g. 72"
        :min="limits?.min" :max="limits?.max" :step="limits?.step ?? 'any'"
        :aria-invalid="shownError ? 'true' : undefined" aria-describedby="mf-hint mf-error" />
    </label>
    <button :disabled="!canSave">{{ busy ? 'Saving…' : 'Save' }}</button>
    <p v-if="hint" id="mf-hint" class="hint">{{ hint }}</p>
    <p id="mf-error" class="error" aria-live="polite">{{ shownError }}</p>
  </form>
</template>

<style scoped>
.form { display: flex; flex-wrap: wrap; gap: 12px; align-items: flex-end; }
h2 { width: 100%; margin: 0; font-size: 16px; font-weight: 600; }
.field { display: flex; flex-direction: column; gap: 6px; flex: 1 1 200px; font-size: 13px; color: var(--muted); }
select, input {
  font: inherit; font-size: 15px; min-height: 48px; padding: 0 12px; border-radius: 12px;
  border: 1.5px solid var(--border); background: var(--bg); color: var(--text);
}
button {
  min-height: 48px; padding: 0 24px; border-radius: 12px; border: none; cursor: pointer;
  background: var(--text); color: var(--bg); font-weight: 600; font-size: 15px;
}
button:disabled { opacity: .6; cursor: not-allowed; }
input[aria-invalid='true'] { border-color: var(--critical); }
.hint { width: 100%; margin: -4px 0 0; font-size: 13px; color: var(--muted); }
.error { width: 100%; margin: 0; color: var(--critical); font-size: 14px; }</style>

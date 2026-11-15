<script setup lang="ts">
import { computed, nextTick, ref, watch } from 'vue'
import { api } from '../api'
import type { IndicatorMeta } from '../types'
import { celsiusText, hoursText } from '../units'
import { allowedText, validateValue } from '../validation'

const props = defineProps<{ astronautId: number; indicators: Record<string, IndicatorMeta>; preset: string | null }>()
const emit = defineEmits<{ saved: [] }>()

// Indicators entered as a fixed choice instead of a typed number.
const CHOICES: Record<string, { value: number; label: string }[]> = {
  mood: [
    { value: 1, label: 'Very low' },
    { value: 2, label: 'Low' },
    { value: 3, label: 'Okay' },
    { value: 4, label: 'Good' },
    { value: 5, label: 'Very good' },
  ],
}

const indicator = ref(props.preset ?? Object.keys(props.indicators)[0] ?? '')
// v-model.number gives '' for an empty field, so anything that is not a number counts as empty.
const value = ref<number | string | null>(null)
const error = ref('') // backend / network errors
const busy = ref(false)
const valueField = ref<HTMLElement | null>(null)

watch(() => props.preset, (p) => { if (p) indicator.value = p })
// A value typed for one indicator means nothing for another.
watch(indicator, () => { value.value = null })
// A new value or indicator makes an earlier server error stale.
watch([value, indicator], () => { error.value = '' })

const current = computed(() => props.indicators[indicator.value])
const input = computed(() => current.value?.input)
const choices = computed(() => CHOICES[indicator.value])
const unit = computed(() => current.value?.unit ?? '')

// Plausibility limits for data entry only, not medical thresholds (see src/validation.ts).
const hint = computed(() => (choices.value ? '' : allowedText(current.value)))
const numeric = computed(() => (typeof value.value === 'number' ? value.value : null))
const invalidMsg = computed(() => (numeric.value === null ? '' : validateValue(current.value, numeric.value)))
const canSave = computed(() => numeric.value !== null && !invalidMsg.value && !busy.value)
const shownError = computed(() => invalidMsg.value || error.value)

// Display-only conversion of a valid value; what is saved stays in °C / hours.
const conversion = computed(() => {
  const v = numeric.value
  if (v === null || invalidMsg.value) return ''
  if (indicator.value === 'temperature') return celsiusText(v)
  if (indicator.value === 'sleep_hours') return hoursText(v)
  return ''
})

const describedBy = computed(() =>
  [input.value?.help && 'mf-help', hint.value && 'mf-hint', conversion.value && 'mf-conv', 'mf-error']
    .filter(Boolean)
    .join(' '),
)

/** Preselect an indicator, then bring its control into view and focus it (first option for a choice). */
async function logNow(key: string) {
  indicator.value = key
  error.value = ''
  await nextTick()
  const control = valueField.value?.querySelector<HTMLInputElement>('input')
  if (!control) return
  const smooth = !window.matchMedia('(prefers-reduced-motion: reduce)').matches
  valueField.value!.scrollIntoView({ block: 'center', behavior: smooth ? 'smooth' : 'auto' })
  control.focus({ preventScroll: true })
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
    <div class="fields">
      <label class="field select-field">
        <span class="label">Indicator</span>
        <select v-model="indicator">
          <option v-for="(meta, key) in indicators" :key="key" :value="key">{{ meta.label }} ({{ meta.unit }})</option>
        </select>
      </label>

      <div ref="valueField" class="field value-field" :class="{ wide: choices }">
        <fieldset v-if="choices" class="choices" role="radiogroup" :aria-describedby="describedBy">
          <legend class="label">{{ current?.label }}</legend>
          <label v-for="c in choices" :key="c.value" class="choice">
            <input v-model="value" type="radio" name="mf-choice" :value="c.value" class="sr-only" />
            <span class="n">{{ c.value }}</span>
            <span class="t">{{ c.label }}</span>
          </label>
        </fieldset>

        <template v-else>
          <label class="label" for="mf-value">Value<span class="sr-only"> in {{ unit }}</span></label>
          <div class="input-group" :class="{ invalid: !!shownError }">
            <input id="mf-value" v-model.number="value" type="number" inputmode="decimal"
              :placeholder="input?.placeholder" :min="input?.min" :max="input?.max" :step="input?.step ?? 'any'"
              :aria-invalid="shownError ? 'true' : undefined" :aria-describedby="describedBy" />
            <span class="unit" aria-hidden="true">{{ unit }}</span>
          </div>
        </template>

        <p v-if="input?.help" id="mf-help" class="help">{{ input.help }}</p>
        <p v-if="hint" id="mf-hint" class="hint">{{ hint }}</p>
        <p v-if="conversion" id="mf-conv" class="conv">{{ conversion }}</p>
        <p id="mf-error" class="error" aria-live="polite">{{ shownError }}</p>
      </div>
    </div>
    <button class="save" :disabled="!canSave">{{ busy ? 'Saving…' : 'Save' }}</button>
  </form>
</template>

<style scoped>
.form { display: flex; flex-direction: column; gap: 14px; }
h2 { margin: 0; font-size: 16px; font-weight: 600; }
.fields { display: flex; flex-wrap: wrap; gap: 12px 16px; align-items: flex-start; }
.field { display: flex; flex-direction: column; gap: 6px; min-width: 0; }
.select-field { flex: 1 1 220px; }
.value-field { flex: 1 1 240px; }
.value-field.wide { flex-basis: 100%; }
.label { font-size: 13px; color: var(--muted); padding: 0; }

select, .input-group {
  font: inherit; font-size: 15px; min-height: 48px; border-radius: 12px;
  border: 1.5px solid var(--border); background: var(--bg); color: var(--text);
}
select { padding: 0 12px; }
.input-group { display: flex; align-items: center; }
.input-group:focus-within { outline: 2px solid var(--text); outline-offset: 2px; }
.input-group.invalid { border-color: var(--critical); }
.input-group input {
  flex: 1; min-width: 0; min-height: 45px; padding: 0 12px; border: none; background: transparent;
  color: var(--text); font: inherit; font-size: 15px;
}
.input-group input:focus-visible { outline: none; }
.input-group input::placeholder { color: var(--muted); }
.unit { padding: 0 14px 0 4px; font-size: 14px; color: var(--muted); white-space: nowrap; }

.choices { border: none; margin: 0; padding: 0; display: flex; flex-wrap: wrap; gap: 6px; min-width: 0; }
.choices legend { margin-bottom: 6px; }
.choice {
  flex: 1 1 0; min-width: 56px; min-height: 56px; padding: 6px 4px; border-radius: 12px; cursor: pointer;
  display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 2px;
  border: 1.5px solid var(--border); background: var(--bg); color: var(--text-2); text-align: center;
}
.choice:hover { border-color: var(--border-strong); }
.choice:has(input:checked) { background: var(--text); border-color: var(--text); color: var(--bg); }
.choice:has(input:focus-visible) { outline: 2px solid var(--text); outline-offset: 2px; }
.choice .n { font-size: 16px; font-weight: 600; }
.choice .t { font-size: 12px; line-height: 1.2; }

.help, .hint, .conv, .error { margin: 0; font-size: 13px; line-height: 1.4; }
.help { color: var(--text-2); }
.hint { color: var(--muted); }
.conv { color: var(--nominal); font-size: 14px; font-weight: 600; }
.error { color: var(--critical); font-size: 14px; }

.save {
  align-self: flex-start; min-height: 48px; padding: 0 28px; border-radius: 12px; border: none; cursor: pointer;
  background: var(--text); color: var(--bg); font-weight: 600; font-size: 15px;
}
.save:disabled { opacity: .6; cursor: not-allowed; }

.sr-only {
  position: absolute; width: 1px; height: 1px; padding: 0; margin: -1px; overflow: hidden;
  clip: rect(0 0 0 0); white-space: nowrap; border: 0;
}
</style>

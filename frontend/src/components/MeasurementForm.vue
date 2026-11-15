<script setup lang="ts">
import { ref, watch } from 'vue'
import { api } from '../api'
import type { IndicatorMeta } from '../types'

const props = defineProps<{ astronautId: number; indicators: Record<string, IndicatorMeta>; preset: string | null }>()
const emit = defineEmits<{ saved: [] }>()

const indicator = ref(props.preset ?? Object.keys(props.indicators)[0] ?? '')
const value = ref<number | null>(null)
const error = ref('')
const busy = ref(false)

watch(() => props.preset, (p) => { if (p) indicator.value = p })

async function submit() {
  error.value = ''
  if (value.value === null || Number.isNaN(value.value)) {
    error.value = 'Enter a numeric value.'
    return
  }
  busy.value = true
  try {
    await api.addMeasurement(props.astronautId, indicator.value, value.value)
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
  <form class="form" @submit.prevent="submit">
    <h2>Log a measurement</h2>
    <label class="field">
      <span>Indicator</span>
      <select v-model="indicator">
        <option v-for="(meta, key) in indicators" :key="key" :value="key">{{ meta.label }} ({{ meta.unit }})</option>
      </select>
    </label>
    <label class="field">
      <span>Value</span>
      <input v-model.number="value" type="number" step="any" inputmode="decimal" placeholder="e.g. 72" />
    </label>
    <button :disabled="busy">{{ busy ? 'Saving…' : 'Save' }}</button>
    <p v-if="error" class="error" role="alert">{{ error }}</p>
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
button:disabled { opacity: .6; cursor: wait; }
.error { width: 100%; margin: 0; color: var(--critical); font-size: 14px; }
</style>

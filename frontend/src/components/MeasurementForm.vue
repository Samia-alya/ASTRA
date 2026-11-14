<script setup lang="ts">
import { ref } from 'vue'
import { api } from '../api'
import type { IndicatorMeta } from '../types'

const props = defineProps<{ astronautId: number; indicators: Record<string, IndicatorMeta> }>()
const emit = defineEmits<{ saved: [] }>()

const indicator = ref(Object.keys(props.indicators)[0] ?? '')
const value = ref<number | null>(null)
const error = ref('')
const busy = ref(false)

async function submit() {
  error.value = ''
  if (value.value === null || Number.isNaN(value.value)) {
    error.value = 'Entre une valeur numérique.'
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
    <h3>Nouvelle mesure</h3>
    <select v-model="indicator">
      <option v-for="(meta, key) in indicators" :key="key" :value="key">{{ meta.label }} ({{ meta.unit }})</option>
    </select>
    <input v-model.number="value" type="number" step="any" placeholder="Valeur" />
    <button :disabled="busy">Enregistrer</button>
    <p v-if="error" class="error">{{ error }}</p>
  </form>
</template>

<style scoped>
.form { display: flex; flex-wrap: wrap; gap: 8px; align-items: center; }
.form h3 { width: 100%; margin: 0 0 4px; }
select, input, button { font: inherit; padding: 8px 10px; border-radius: 8px; border: 1px solid var(--border);
  background: var(--bg); color: inherit; }
button { background: var(--accent); color: #001; border: none; cursor: pointer; font-weight: 600; }
.error { color: var(--crit); width: 100%; margin: 0; }
</style>

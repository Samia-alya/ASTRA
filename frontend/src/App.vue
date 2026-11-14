<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { api } from './api'
import HistoryChart from './components/HistoryChart.vue'
import IndicatorCard from './components/IndicatorCard.vue'
import MeasurementForm from './components/MeasurementForm.vue'
import type { Astronaut, IndicatorMeta, Measurement, StatusResponse } from './types'

const astronauts = ref<Astronaut[]>([])
const astronautId = ref<number | null>(null)
const status = ref<StatusResponse | null>(null)
const meta = ref<Record<string, IndicatorMeta>>({})
const selected = ref<string | null>(null)
const history = ref<Measurement[]>([])
const error = ref('')

const OVERALL = {
  normal: 'Tout va bien',
  attention: 'Certains indicateurs demandent ton attention',
  critical: 'Contacte le médecin de vol',
  no_data: 'Pas encore de données',
}

const selectedStatus = computed(() => status.value?.indicators.find((i) => i.indicator === selected.value) ?? null)
const hasSimulated = computed(() => history.value.some((m) => m.source === 'simulated'))

async function loadStatus() {
  if (astronautId.value === null) return
  try {
    status.value = await api.status(astronautId.value)
    const first = status.value.indicators.find((i) => i.level !== 'normal') ?? status.value.indicators[0]
    if (!selected.value && first) selected.value = first.indicator
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
    ;[astronauts.value, meta.value] = await Promise.all([api.astronauts(), api.indicators()])
    astronautId.value = astronauts.value[0]?.id ?? null
  } catch {
    error.value = "Impossible de joindre l'API. Le backend tourne-t-il sur le port 8000 ?"
  }
})

watch(astronautId, () => { selected.value = null; loadStatus() })
watch(selected, loadHistory)
</script>

<template>
  <header>
    <h1>Houston Pulse</h1>
    <select v-if="astronauts.length" v-model="astronautId">
      <option v-for="a in astronauts" :key="a.id" :value="a.id">{{ a.name }} · {{ a.mission }}</option>
    </select>
  </header>

  <p v-if="error" class="error">{{ error }}</p>

  <main v-if="status">
    <section class="overall" :class="status.overall_level">
      <strong>{{ OVERALL[status.overall_level] }}</strong>
      <span>Jour {{ status.astronaut.mission_day }} · {{ status.astronaut.environment }}</span>
    </section>

    <section class="grid">
      <IndicatorCard
        v-for="s in status.indicators" :key="s.indicator" :status="s"
        :selected="s.indicator === selected" @select="selected = s.indicator"
      />
    </section>

    <section class="detail" v-if="selectedStatus">
      <div class="panel">
        <span v-if="hasSimulated" class="sim">DONNÉES SIMULÉES</span>
        <HistoryChart :data="history" :label="selectedStatus.label" :unit="selectedStatus.unit"
          :baseline="selectedStatus.baseline" />
      </div>
      <div class="panel guide" v-if="meta[selectedStatus.indicator]">
        <h3>{{ selectedStatus.label }}</h3>
        <p><b>Ce que ça mesure :</b> {{ meta[selectedStatus.indicator]!.what }}</p>
        <p><b>Pourquoi c'est important dans l'espace :</b> {{ meta[selectedStatus.indicator]!.why_in_space }}</p>
        <!-- TODO (Membre 3) : section "Que faire ?" selon le niveau, basée sur des sources fiables -->
      </div>
    </section>

    <section class="panel" v-if="astronautId !== null">
      <MeasurementForm :astronaut-id="astronautId" :indicators="meta" @saved="loadStatus" />
    </section>

    <p class="disclaimer">{{ status.disclaimer }}</p>
  </main>
</template>

<style scoped>
header { display: flex; justify-content: space-between; align-items: center; gap: 16px; flex-wrap: wrap; }
header select { font: inherit; padding: 8px; border-radius: 8px; background: var(--panel); color: inherit;
  border: 1px solid var(--border); }
main { display: flex; flex-direction: column; gap: 16px; }
.overall { display: flex; justify-content: space-between; padding: 14px 18px; border-radius: 12px;
  background: var(--panel); border-left: 6px solid var(--ok); }
.overall.attention { border-left-color: var(--warn); }
.overall.critical { border-left-color: var(--crit); }
.grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(230px, 1fr)); gap: 12px; }
.detail { display: grid; grid-template-columns: 2fr 1fr; gap: 12px; }
@media (max-width: 800px) { .detail { grid-template-columns: 1fr; } }
.panel { background: var(--panel); border: 1px solid var(--border); border-radius: 12px; padding: 14px; position: relative; }
.guide p { font-size: 14px; line-height: 1.5; }
.sim { position: absolute; top: 10px; right: 12px; z-index: 1; font-size: 11px; font-weight: 700;
  letter-spacing: .05em; background: var(--warn); color: #2b1a00; padding: 2px 8px; border-radius: 6px; }
.disclaimer { font-size: 12px; opacity: .7; }
.error { color: var(--crit); }
</style>

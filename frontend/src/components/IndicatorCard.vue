<script setup lang="ts">
import type { IndicatorStatus } from '../types'

defineProps<{ status: IndicatorStatus; selected: boolean }>()
defineEmits<{ select: [] }>()

// Status is never carried by colour alone: shape + word + colour.
const LEVEL_LABEL = { normal: 'Normal', attention: 'Attention', critical: 'Critical', no_data: 'No data' }
const LEVEL_SHAPE = { normal: '●', attention: '▲', critical: '■', no_data: '○' }
const TREND_ICON = { up: '↗', down: '↘', stable: '→' }
</script>

<template>
  <button class="card" :class="[status.level, { selected }]" @click="$emit('select')">
    <div class="head">
      <span class="label">{{ status.label }}</span>
      <span class="badge"><span aria-hidden="true">{{ LEVEL_SHAPE[status.level] }}</span> {{ LEVEL_LABEL[status.level] }}</span>
    </div>
    <div class="value">
      {{ status.value ?? '—' }} <small>{{ status.unit }}</small>
      <span class="trend">{{ TREND_ICON[status.trend] }}</span>
    </div>
    <div class="baseline" v-if="status.space_adjusted && status.expected !== null">
      Expected in flight today: {{ status.expected }} {{ status.unit }}
      <span v-if="status.preflight !== null">· on Earth: {{ status.preflight }}</span>
    </div>
    <div class="baseline" v-else-if="status.baseline !== null">Your baseline: {{ status.baseline }} {{ status.unit }}</div>
    <div class="earth" v-if="status.level === 'normal' && status.earth_level !== 'normal'">
      An Earth-calibrated tool would raise an alert here.
    </div>
    <ul class="reasons">
      <li v-for="r in status.reasons" :key="r">{{ r }}</li>
    </ul>
  </button>
</template>

<style scoped>
.card {
  text-align: left; border: 2px solid var(--border); border-left-width: 6px; border-radius: 12px;
  padding: 14px; background: var(--panel); color: inherit; cursor: pointer; font: inherit;
}
.card.selected { outline: 2px solid var(--accent); }
.card.normal { border-left-color: var(--ok); }
.card.attention { border-left-color: var(--warn); }
.card.critical { border-left-color: var(--crit); }
.head { display: flex; justify-content: space-between; align-items: center; gap: 8px; }
.label { font-weight: 600; }
.badge { font-size: 12px; padding: 2px 8px; border-radius: 99px; background: var(--border); white-space: nowrap; }
.normal .badge { background: var(--ok); color: #04210f; }
.attention .badge { background: var(--warn); color: #2b1a00; }
.critical .badge { background: var(--crit); color: #fff; }
.value { font-size: 28px; font-weight: 700; margin: 8px 0 2px; }
.value small { font-size: 14px; font-weight: 400; opacity: .7; }
.trend { font-size: 18px; margin-left: 6px; opacity: .8; }
.baseline { font-size: 13px; opacity: .75; }
.earth { margin-top: 8px; font-size: 12px; padding: 4px 8px; border-radius: 6px;
  border: 1px dashed var(--accent); color: var(--accent); }
.reasons { margin: 8px 0 0; padding-left: 18px; font-size: 13px; overflow-wrap: anywhere; }
</style>

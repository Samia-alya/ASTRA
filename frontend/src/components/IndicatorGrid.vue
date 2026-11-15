<script setup lang="ts">
import type { IndicatorMeta, IndicatorStatus } from '../types'
import { fmt } from '../types'

defineProps<{ indicators: IndicatorStatus[]; meta: Record<string, IndicatorMeta>; selected: string | null }>()
const emit = defineEmits<{ select: [indicator: string] }>()

const ARROW = { up: '↑', down: '↓', stable: '→' }
</script>

<template>
  <div class="grid">
    <button v-for="s in indicators" :key="s.indicator" class="item" :class="{ on: s.indicator === selected }"
      :aria-pressed="s.indicator === selected" @click="emit('select', s.indicator)">
      <span class="dot" :class="s.level"></span>
      <span class="body">
        <span class="name">{{ meta[s.indicator]?.short ?? s.label }}</span>
        <span class="value">{{ fmt(s.value, s.unit) }} <small>{{ s.unit }}</small></span>
      </span>
      <span class="arrow" :aria-label="`trend ${s.trend}`">{{ ARROW[s.trend] }}</span>
    </button>
  </div>
</template>

<style scoped>
.grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 10px; }
.item {
  display: grid; grid-template-columns: 12px 1fr auto; align-items: center; gap: 12px;
  width: 100%; min-height: 56px; padding: 10px 14px; border-radius: 14px;
  border: 1.5px solid var(--border); background: var(--panel); color: var(--text); text-align: left; cursor: pointer;
  transition: border-color .2s, background .2s;
}
.item:hover { border-color: var(--border-strong); }
.item.on { border-color: var(--text); background: var(--panel-2); }
.body { display: flex; flex-direction: column; gap: 2px; min-width: 0; }
.name { font-size: 14px; color: var(--muted); }
.value { font-size: 18px; font-weight: 600; }
.value small { font-size: 13px; font-weight: 400; color: var(--muted); }
.arrow { font-size: 15px; color: var(--muted); }
</style>

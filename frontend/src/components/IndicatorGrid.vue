<script setup lang="ts">
import type { IndicatorMeta, IndicatorStatus } from '../types'
import { fmt } from '../types'
import { sourceText } from '../time'

withDefaults(defineProps<{
  indicators: IndicatorStatus[]
  meta: Record<string, IndicatorMeta>
  selected: string | null
  /** Clock for "5 s ago" labels. */
  now: number
  /** Indicators that just received a new device value (briefly highlighted). */
  updated?: string[]
}>(), { updated: () => [] })
const emit = defineEmits<{ select: [indicator: string] }>()

const ARROW = { up: '↑', down: '↓', stable: '→' }
</script>

<template>
  <div class="grid">
    <button v-for="s in indicators" :key="s.indicator" class="item"
      :class="{ on: s.indicator === selected, flash: updated.includes(s.indicator) }"
      :aria-pressed="s.indicator === selected" @click="emit('select', s.indicator)">
      <span class="dot" :class="s.level"></span>
      <span class="body">
        <span class="name">{{ meta[s.indicator]?.short ?? s.label }}</span>
        <span class="value">{{ fmt(s.value, s.unit) }} <small>{{ s.unit }}</small></span>
        <span v-if="s.last_source" class="src" :class="s.last_source.type">
          {{ sourceText(s.last_source, s.last_timestamp, now) }}</span>
      </span>
      <span class="arrow" :aria-label="`trend ${s.trend}`">{{ ARROW[s.trend] }}</span>
    </button>
  </div>
</template>

<style scoped>
.grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 10px; }
.item {
  display: grid; grid-template-columns: 12px 1fr auto; align-items: center; gap: 12px;
  width: 100%; min-height: 58px; padding: 10px 14px; border-radius: 16px;
  border: 1px solid var(--border); background: var(--panel); color: var(--text); text-align: left; cursor: pointer;
  transition: border-color .2s, background .2s, box-shadow .4s;
}
.item:hover { border-color: var(--border-strong); }
.item.on { border-color: var(--accent-2); background: var(--panel-2); }
.body { display: flex; flex-direction: column; gap: 2px; min-width: 0; }
.name { font-size: 14px; color: var(--muted); }
.value { font-size: 18px; font-weight: 600; }
.value small { font-size: 13px; font-weight: 400; color: var(--muted); }
.arrow { font-size: 15px; color: var(--muted); }
.src { font-size: 11.5px; color: var(--muted); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.src.device { color: var(--accent); }
/* New device value: short highlight. Without motion it is simply shown for the same 1.5 s. */
.item.flash { border-color: var(--accent); background: var(--panel-2); box-shadow: 0 0 0 3px rgba(45, 212, 191, 0.25); }
</style>

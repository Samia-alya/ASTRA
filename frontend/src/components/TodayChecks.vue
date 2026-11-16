<script setup lang="ts">
import { computed, onUnmounted, ref } from 'vue'
import type { CheckItem, ChecksResponse } from '../types'

const props = defineProps<{ checks: ChecksResponse }>()
const emit = defineEmits<{ log: [indicator: string] }>()

const pct = computed(() => (props.checks.total ? (props.checks.done_count / props.checks.total) * 100 : 0))

function ago(h: number | null): string {
  if (h === null) return 'never'
  if (h < 1) return 'less than 1 h ago'
  return `${Math.round(h)} h ago`
}

// Earth-independent mode: some indicators are re-measured every few hours; count down live.
const now = ref(Date.now())
const timer = window.setInterval(() => (now.value = Date.now()), 30_000)
onUnmounted(() => window.clearInterval(timer))

function nextIn(c: CheckItem): number | null {
  if (c.interval_hours === undefined || !c.last_timestamp) return null
  return (new Date(c.last_timestamp).getTime() + c.interval_hours * 3_600_000 - now.value) / 1000
}

function remaining(s: number): string {
  const m = Math.ceil(s / 60)
  return m < 60 ? `${m} min` : `${Math.floor(m / 60)} h ${String(m % 60).padStart(2, '0')} min`
}

function isDone(c: CheckItem): boolean {
  const n = nextIn(c)
  return n === null ? c.done : n > 0
}

function detail(c: CheckItem): string {
  if (c.interval_hours !== undefined) {
    const n = nextIn(c)
    const every = `every ${c.interval_hours} h (Earth-independent mode)`
    return n !== null && n > 0 ? `Next in ${remaining(n)} · ${every}` : `Due now · ${every}`
  }
  if (c.done) return `measured ${ago(c.hours_since_last)}`
  return c.hours_since_last === null
    ? 'Due · never measured'
    : `Overdue · last measured ${Math.round(c.hours_since_last)} h ago`
}
</script>

<template>
  <div class="checks">
    <div class="head">
      <h2 id="today-checks-title">Today's checks</h2>
      <span class="count">{{ checks.done_count }} of {{ checks.total }} done</span>
    </div>
    <div class="bar" aria-hidden="true"><span :style="{ width: pct + '%' }" /></div>

    <ul aria-labelledby="today-checks-title">
      <li v-for="c in checks.items" :key="c.indicator" :class="{ due: !isDone(c), tight: c.interval_hours }">
        <svg v-if="isDone(c)" class="icon" viewBox="0 0 20 20" aria-hidden="true">
          <circle cx="10" cy="10" r="9" fill="var(--nominal)" />
          <path d="M6 10.5 L8.8 13.2 L14 7.5" fill="none" stroke="var(--on-accent)" stroke-width="2.2"
            stroke-linecap="round" stroke-linejoin="round" />
        </svg>
        <svg v-else class="icon" viewBox="0 0 20 20" aria-hidden="true">
          <circle cx="10" cy="10" r="8.25" fill="none" stroke="var(--watch)" stroke-width="2" />
          <path d="M10 5.5 V10 L13 12" fill="none" stroke="var(--watch)" stroke-width="2"
            stroke-linecap="round" stroke-linejoin="round" />
        </svg>
        <div class="text">
          <span class="name">{{ c.label }}<span class="sr-only">: {{ isDone(c) ? 'done' : 'due' }}</span></span>
          <span class="when">{{ detail(c) }}</span>
        </div>
        <button v-if="!isDone(c)" type="button" class="log" @click="emit('log', c.indicator)">
          Log now<span class="sr-only"> {{ c.label }}</span>
        </button>
      </li>
    </ul>
  </div>
</template>

<style scoped>
.checks { display: flex; flex-direction: column; gap: 12px; }
.head { display: flex; align-items: baseline; justify-content: space-between; gap: 12px; }
h2 { margin: 0; font-size: 16px; font-weight: 600; }
.count { font-size: 14px; color: var(--text-2); }
.bar { height: 4px; border-radius: 99px; background: var(--track); overflow: hidden; }
.bar span { display: block; height: 100%; background: var(--nominal); border-radius: 99px; transition: width .3s; }

ul { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; }
li {
  display: flex; align-items: center; gap: 12px; min-height: 56px; padding: 6px 0;
  border-bottom: 1px solid var(--border);
}
li:last-child { border-bottom: none; }
.icon { width: 20px; height: 20px; flex: none; }
.text { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 2px; }
.name { font-size: 15px; }
.when { font-size: 13px; color: var(--muted); }
li.due .when { color: var(--watch); }
li.tight .when { color: var(--critical); }
.log {
  min-height: 44px; padding: 0 14px; border-radius: 12px; cursor: pointer; flex: none;
  background: transparent; color: var(--text); border: 1.5px solid var(--watch); font-weight: 600; font-size: 14px;
}
.log:hover { background: var(--panel-2); }
.sr-only { position: absolute; width: 1px; height: 1px; overflow: hidden; clip: rect(0 0 0 0); white-space: nowrap; }
</style>

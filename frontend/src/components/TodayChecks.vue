<script setup lang="ts">
import { computed } from 'vue'
import type { CheckItem, ChecksResponse } from '../types'

const props = defineProps<{ checks: ChecksResponse }>()
const emit = defineEmits<{ log: [indicator: string] }>()

const pct = computed(() => (props.checks.total ? (props.checks.done_count / props.checks.total) * 100 : 0))

function ago(h: number | null): string {
  if (h === null) return 'never'
  if (h < 1) return 'less than 1 h ago'
  return `${Math.round(h)} h ago`
}

function detail(c: CheckItem): string {
  if (c.done) return `measured ${ago(c.hours_since_last)}`
  return c.hours_since_last === null ? 'Due — never measured' : `Due — last measured ${ago(c.hours_since_last)}`
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
      <li v-for="c in checks.items" :key="c.indicator" :class="{ due: !c.done }">
        <svg v-if="c.done" class="icon" viewBox="0 0 20 20" aria-hidden="true">
          <circle cx="10" cy="10" r="9" fill="var(--nominal)" />
          <path d="M6 10.5 L8.8 13.2 L14 7.5" fill="none" stroke="#101114" stroke-width="2"
            stroke-linecap="round" stroke-linejoin="round" />
        </svg>
        <svg v-else class="icon" viewBox="0 0 20 20" aria-hidden="true">
          <circle cx="10" cy="10" r="8.25" fill="none" stroke="var(--watch)" stroke-width="2" />
          <path d="M10 5.5 V10 L13 12" fill="none" stroke="var(--watch)" stroke-width="2"
            stroke-linecap="round" stroke-linejoin="round" />
        </svg>
        <div class="text">
          <span class="name">{{ c.label }}<span class="sr-only">: {{ c.done ? 'done' : 'due' }}</span></span>
          <span class="when">{{ detail(c) }}</span>
        </div>
        <button v-if="!c.done" type="button" class="log" @click="emit('log', c.indicator)">
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
.bar { height: 6px; border-radius: 99px; background: var(--border); overflow: hidden; }
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
.log {
  min-height: 44px; padding: 0 14px; border-radius: 12px; cursor: pointer; flex: none;
  background: transparent; color: var(--text); border: 1.5px solid var(--watch); font-weight: 600; font-size: 14px;
}
.log:hover { background: var(--panel-2); }
.sr-only { position: absolute; width: 1px; height: 1px; overflow: hidden; clip: rect(0 0 0 0); white-space: nowrap; }
</style>

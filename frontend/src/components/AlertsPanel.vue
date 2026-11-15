<script setup lang="ts">
import type { Alert } from '../types'

defineProps<{ alerts: Alert[] }>()
</script>

<template>
  <section class="alerts">
    <article v-for="a in alerts" :key="a.rule" class="alert" :class="{ blocking: a.blocks_critical_ops }">
      <header>
        <span class="shape" aria-hidden="true">▲</span>
        <h3>{{ a.title }}</h3>
        <span v-if="a.blocks_critical_ops" class="tag">Blocks critical operations</span>
      </header>
      <p>{{ a.explanation }}</p>
      <div class="cols">
        <div>
          <h4>What we see</h4>
          <ul><li v-for="e in a.evidence" :key="e">{{ e }}</li></ul>
        </div>
        <div>
          <h4>Suggested next steps</h4>
          <ol><li v-for="s in a.actions" :key="s">{{ s }}</li></ol>
        </div>
      </div>
      <details>
        <summary>Why we say this</summary>
        <ul class="src"><li v-for="s in a.sources" :key="s">{{ s }}</li></ul>
        <p class="note">{{ a.validation }}</p>
      </details>
    </article>
  </section>
</template>

<style scoped>
.alerts { display: flex; flex-direction: column; gap: 12px; }
.alert { background: var(--panel); border: 1px solid var(--warn); border-left-width: 6px; border-radius: 12px; padding: 14px 18px; }
header { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }
h3 { margin: 0; font-size: 16px; flex: 1; min-width: 200px; }
h4 { margin: 10px 0 4px; font-size: 13px; text-transform: uppercase; letter-spacing: .04em; color: var(--muted); }
.shape { color: var(--warn); font-size: 18px; }
.tag { font-size: 12px; font-weight: 700; padding: 2px 8px; border-radius: 6px; background: var(--crit); color: #fff; }
p { margin: 8px 0 0; line-height: 1.5; font-size: 14px; }
li { font-size: 14px; }
.cols { display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap: 4px 18px; }
ul, ol { margin: 0; padding-left: 20px; line-height: 1.5; }
details { margin-top: 10px; font-size: 13px; }
summary { cursor: pointer; color: var(--accent); }
.src { margin-top: 6px; overflow-wrap: anywhere; }
.note { font-size: 12px; color: var(--muted); }
</style>

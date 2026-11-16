<script setup lang="ts">
import { ref } from 'vue'
import { SOURCE_GROUPS } from '../sources'

const dialog = ref<HTMLDialogElement | null>(null)
let opener: HTMLElement | null = null

function open() {
  opener = document.activeElement instanceof HTMLElement ? document.activeElement : null
  dialog.value?.showModal()
}

// Esc and the Close button both end here: give focus back to the "Sources" link.
function onClose() {
  opener?.focus()
  opener = null
}

defineExpose({ open })
</script>

<template>
  <dialog ref="dialog" class="sources" aria-labelledby="sources-title" @close="onClose">
    <div class="head">
      <h2 id="sources-title">Sources</h2>
      <button type="button" class="close" aria-label="Close sources" @click="dialog?.close()">
        <svg viewBox="0 0 20 20" aria-hidden="true">
          <path d="M5 5 L15 15 M15 5 L5 15" stroke="currentColor" stroke-width="2" stroke-linecap="round" />
        </svg>
      </button>
    </div>
    <p class="intro">References used in Houston Pulse. Thresholds are for the general adult population, not
      spaceflight flight rules. All crew data is simulated.</p>
    <section v-for="g in SOURCE_GROUPS" :key="g.title" :aria-labelledby="`src-${g.title}`">
      <h3 :id="`src-${g.title}`">{{ g.title }}</h3>
      <ul>
        <li v-for="s in g.items" :key="s.url + s.label">
          <a :href="s.url" target="_blank" rel="noopener">{{ s.label }}</a>
          <span>{{ s.detail }}</span>
        </li>
      </ul>
    </section>
  </dialog>
</template>

<style scoped>
.sources {
  width: min(560px, calc(100vw - 24px)); max-height: calc(100dvh - 24px); padding: 20px 22px;
  border: 1px solid var(--border-strong); border-radius: 20px; background: var(--panel); color: var(--text);
}
.sources::backdrop { background: rgba(4, 10, 12, 0.8); }
.head { display: flex; align-items: center; justify-content: space-between; gap: 12px; }
h2 { margin: 0; font-family: var(--display); font-size: 18px; font-weight: 600; }
.close {
  width: 44px; height: 44px; display: grid; place-items: center; margin: -8px -10px -8px 0;
  border: none; border-radius: 12px; background: transparent; color: var(--muted); cursor: pointer;
}
.close:hover { background: var(--panel-2); color: var(--text); }
.close svg { width: 18px; height: 18px; }
.intro { margin: 6px 0 4px; font-size: 13px; color: var(--muted); line-height: 1.45; }
h3 { margin: 14px 0 6px; font-size: 12px; font-weight: 600; color: var(--muted); text-transform: uppercase; letter-spacing: .04em; }
ul { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: 8px; }
li { display: flex; flex-direction: column; gap: 1px; font-size: 14px; }
li a { color: var(--accent); }
li span { font-size: 12.5px; color: var(--text-2); }
</style>

<script setup lang="ts">
import { onBeforeUnmount, onMounted } from 'vue'

defineProps<{ title: string; side?: boolean }>()
const emit = defineEmits<{ close: [] }>()

function onKey(e: KeyboardEvent) { if (e.key === 'Escape') emit('close') }
onMounted(() => window.addEventListener('keydown', onKey))
onBeforeUnmount(() => window.removeEventListener('keydown', onKey))
</script>

<template>
  <div class="veil" :class="{ side }" @click.self="emit('close')">
    <section class="sheet" role="dialog" aria-modal="true" :aria-label="title">
      <header>
        <h2>{{ title }}</h2>
        <button type="button" class="x" aria-label="Close" @click="emit('close')">✕</button>
      </header>
      <div class="body"><slot /></div>
      <footer v-if="$slots.footer"><slot name="footer" /></footer>
    </section>
  </div>
</template>

<style scoped>
.veil { position: fixed; inset: 0; z-index: 20; display: flex; align-items: center; justify-content: center;
  background: rgba(3, 5, 10, .72); backdrop-filter: blur(3px); }
.veil.side { justify-content: flex-end; align-items: stretch; }
.sheet { display: flex; flex-direction: column; width: min(680px, 94vw); max-height: 92vh; border-radius: 14px;
  background: #0b1220; border: 1px solid var(--line); box-shadow: 0 20px 60px rgba(0, 0, 0, .6); }
.side .sheet { width: min(560px, 96vw); max-height: none; height: 100vh; border-radius: 14px 0 0 14px; border-right: 0;
  animation: slide .22s ease-out; }
@keyframes slide { from { transform: translateX(40px); opacity: 0; } to { transform: none; opacity: 1; } }
header { display: flex; align-items: center; justify-content: space-between; padding: 14px 18px; border-bottom: 1px solid var(--line); }
h2 { margin: 0; font-size: 18px; }
.x { font: inherit; width: 34px; height: 34px; border-radius: 8px; border: 1px solid var(--line); background: transparent;
  color: var(--text); cursor: pointer; }
.x:hover { border-color: var(--cyan); }
.body { padding: 16px 18px; overflow-y: auto; min-height: 0; }
footer { padding: 12px 18px; border-top: 1px solid var(--line); display: flex; gap: 10px; align-items: center; flex-wrap: wrap; }
</style>

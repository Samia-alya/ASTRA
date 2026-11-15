<script setup lang="ts">
import { ago } from '../time'
import type { Device, IndicatorMeta } from '../types'

const props = defineProps<{ devices: Device[]; meta: Record<string, IndicatorMeta>; now: number }>()

function measures(d: Device): string {
  return d.indicators.map((k) => props.meta[k]?.label ?? k).join(', ')
}

function syncText(d: Device): string {
  if (d.status === 'online') return `last sync ${ago(d.last_seen, props.now)}`
  return d.last_seen ? `last sync ${ago(d.last_seen, props.now)}` : 'never synced'
}

// Simple line icons per device kind (decorative; the name says what it is).
const ICONS: Record<string, string> = {
  smart_shirt: 'M8 3 L4 5.5 L2.5 10 L5.5 11 L6 9.5 V21 H18 V9.5 L18.5 11 L21.5 10 L20 5.5 L16 3 Q12 6 8 3 Z',
  actigraphy_band: 'M9 2 H15 L15.5 6 M9 2 L8.5 6 M8.5 18 L9 22 H15 L15.5 18 M7 6 H17 A1 1 0 0 1 18 7 V17 A1 1 0 0 1 17 18 H7 A1 1 0 0 1 6 17 V7 A1 1 0 0 1 7 6 Z M9 12 H10.5 L11.5 10 L12.5 14 L13.5 12 H15',
  bp_cuff: 'M3 7 H15 V15 H3 Z M15 11 H18 A2.5 2.5 0 0 1 20.5 13.5 V18 M18.5 18 A2 2 0 1 0 22.5 18 A2 2 0 1 0 18.5 18',
  thermometer: 'M10 4 A2 2 0 0 1 14 4 V14.5 A4 4 0 1 1 10 14.5 Z M12 9 V16',
  glucometer: 'M12 3 C9 7 7 9.5 7 13 A5 5 0 0 0 17 13 C17 9.5 15 7 12 3 Z',
}
</script>

<template>
  <div class="devices">
    <h2 id="devices-title">Connected devices</h2>
    <p v-if="!devices.length" class="empty">No device paired.</p>
    <ul v-else aria-labelledby="devices-title">
      <li v-for="d in devices" :key="d.id">
        <svg class="icon" viewBox="0 0 24 24" aria-hidden="true">
          <path :d="ICONS[d.kind] ?? ICONS.thermometer" fill="none" stroke="currentColor" stroke-width="1.6"
            stroke-linecap="round" stroke-linejoin="round" />
        </svg>
        <div class="text">
          <span class="name">{{ d.name }}</span>
          <span class="what">{{ measures(d) }}</span>
          <span class="sync" :class="d.status">
            <span class="status-dot" :class="d.status" aria-hidden="true" />
            <strong>{{ d.status === 'online' ? 'Online' : 'Offline' }}</strong> · {{ syncText(d) }}
          </span>
        </div>
      </li>
    </ul>
    <p class="note">Simulated devices modeled on real crew hardware (CSA Bio-Monitor, Artemis II actigraphy).</p>
  </div>
</template>

<style scoped>
.devices { display: flex; flex-direction: column; gap: 12px; }
h2 { margin: 0; font-size: 16px; font-weight: 600; }
ul { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; }
li { display: flex; align-items: flex-start; gap: 12px; padding: 10px 0; border-bottom: 1px solid var(--border); }
li:last-child { border-bottom: none; }
.icon {
  width: 36px; height: 36px; flex: none; padding: 6px; border-radius: 10px;
  background: var(--panel-2); color: var(--accent-2);
}
.text { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 2px; }
.name { font-size: 15px; }
.what { font-size: 13px; color: var(--text-2); }
.sync { display: flex; align-items: center; gap: 6px; flex-wrap: wrap; font-size: 13px; color: var(--muted); }
.sync.online strong { color: var(--accent); }
.sync strong { font-weight: 600; }
.status-dot { width: 8px; height: 8px; border-radius: 50%; flex: none; background: var(--border-strong); }
.status-dot.online { background: var(--accent); animation: pulse 2s ease-out infinite; }
@keyframes pulse {
  0% { box-shadow: 0 0 0 0 rgba(45, 212, 191, 0.6); }
  100% { box-shadow: 0 0 0 8px rgba(45, 212, 191, 0); }
}
.empty { margin: 0; color: var(--muted); font-size: 14px; }
.note { margin: 0; font-size: 12px; color: var(--muted); line-height: 1.4; }
</style>

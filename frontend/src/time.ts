import { onBeforeUnmount, ref } from 'vue'
import type { LastSource } from './types'

/** API timestamps are UTC; SQLite drops the offset, so a timestamp without one is read as UTC. */
export function parseUtc(iso: string): number {
  return Date.parse(/[zZ]|[+-]\d\d:?\d\d$/.test(iso) ? iso : `${iso}Z`)
}

/** "12 s ago", "5 min ago", "3 h ago", "2 d ago" */
export function ago(iso: string | null, now: number): string {
  if (!iso) return 'never'
  const s = Math.max(0, Math.round((now - parseUtc(iso)) / 1000))
  if (s < 60) return `${s} s ago`
  const m = Math.round(s / 60)
  if (m < 60) return `${m} min ago`
  const h = Math.round(m / 60)
  if (h < 48) return `${h} h ago`
  return `${Math.round(h / 24)} d ago`
}

/** "via Bio-Monitor shirt (simulated) · 5 s ago", "manual entry · 3 h ago", "simulated data · 1 h ago" */
export function sourceText(src: LastSource | null, iso: string | null, now: number): string {
  if (!src) return ''
  const when = iso ? ` · ${ago(iso, now)}` : ''
  if (src.type === 'device') return `via ${src.device_name ?? 'device'}${when}`
  if (src.type === 'manual') return `manual entry${when}`
  return `simulated data${when}`
}

/** A clock that ticks every second, for "x s ago" labels. */
export function useNow(intervalMs = 1000) {
  const now = ref(Date.now())
  const t = window.setInterval(() => { now.value = Date.now() }, intervalMs)
  onBeforeUnmount(() => window.clearInterval(t))
  return now
}
